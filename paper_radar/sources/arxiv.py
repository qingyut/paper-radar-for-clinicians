from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from paper_radar.models import PaperRecord
from paper_radar.utils import dedupe_preserve_order, normalize_whitespace

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivClient:
    BASE = "https://export.arxiv.org/api/query"

    def __init__(self, timeout: int = 45, polite_delay_sec: float = 3.0):
        self.timeout = timeout
        self.polite_delay_sec = polite_delay_sec

    @staticmethod
    def _submitted_date_filter(days: int) -> str:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return f"submittedDate:[{start.strftime('%Y%m%d%H%M')}+TO+{end.strftime('%Y%m%d%H%M')}]"

    def search(self, arxiv_query: str, *, days: int = 30, max_results: int = 100) -> list[PaperRecord]:
        full_query = f"{arxiv_query}+AND+{self._submitted_date_filter(days)}"
        params = {
            "search_query": full_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        r = requests.get(self.BASE, params=params, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(self.polite_delay_sec)
        root = ET.fromstring(r.text)
        return self._parse_feed(root)

    def _parse_feed(self, root: ET.Element) -> list[PaperRecord]:
        records = []
        for entry in root.findall("atom:entry", ATOM_NS):
            entry_id = normalize_whitespace(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
            source_id = entry_id.rsplit("/", 1)[-1]
            title = normalize_whitespace(entry.findtext("atom:title", default="", namespaces=ATOM_NS))
            abstract = normalize_whitespace(entry.findtext("atom:summary", default="", namespaces=ATOM_NS))
            published = normalize_whitespace(entry.findtext("atom:published", default="", namespaces=ATOM_NS)[:10])

            authors = []
            for author in entry.findall("atom:author", ATOM_NS):
                name = normalize_whitespace(author.findtext("atom:name", default="", namespaces=ATOM_NS))
                if name:
                    authors.append(name)

            categories = [
                cat.attrib.get("term", "")
                for cat in entry.findall("atom:category", ATOM_NS)
                if cat.attrib.get("term")
            ]
            doi = None
            doi_node = entry.find("arxiv:doi", ATOM_NS)
            if doi_node is not None and doi_node.text:
                doi = normalize_whitespace(doi_node.text)

            url = entry_id.replace("http://", "https://")
            journal_ref = entry.find("arxiv:journal_ref", ATOM_NS)
            journal_or_category = normalize_whitespace(
                (journal_ref.text if journal_ref is not None and journal_ref.text else ", ".join(categories[:3]))
            )

            records.append(
                PaperRecord(
                    source="arxiv",
                    source_id=source_id,
                    title=title,
                    abstract=abstract,
                    url=url,
                    published=published,
                    authors=dedupe_preserve_order(authors),
                    journal_or_category=journal_or_category,
                    doi=doi,
                    publication_types=["Preprint"],
                    keywords=dedupe_preserve_order(categories),
                    raw={"categories": categories},
                )
            )
        return records
