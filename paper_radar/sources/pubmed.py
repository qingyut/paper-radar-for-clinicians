from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from paper_radar.models import PaperRecord
from paper_radar.utils import chunked, dedupe_preserve_order, normalize_whitespace


class PubMedClient:
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, *, tool: str = "paper-radar", email: str | None = None, api_key: str | None = None, timeout: int = 45):
        self.tool = tool
        self.email = email
        self.api_key = api_key
        self.timeout = timeout

    def _params(self, extra: dict) -> dict:
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        params.update(extra)
        return params

    def search_pmids(self, query: str, *, days: int = 30, retmax: int = 100) -> list[str]:
        params = self._params(
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "sort": "pub date",
                "reldate": days,
                "datetype": "pdat",
                "retmax": retmax,
            }
        )
        r = requests.get(f"{self.BASE}/esearch.fcgi", params=params, timeout=self.timeout)
        r.raise_for_status()
        payload = r.json()
        return payload.get("esearchresult", {}).get("idlist", [])

    def esummary(self, pmids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for batch in chunked(pmids, 200):
            params = self._params(
                {"db": "pubmed", "id": ",".join(batch), "retmode": "json"}
            )
            r = requests.get(f"{self.BASE}/esummary.fcgi", params=params, timeout=self.timeout)
            r.raise_for_status()
            payload = r.json().get("result", {})
            for pmid in batch:
                if pmid in payload:
                    out[pmid] = payload[pmid]
        return out

    def efetch_xml(self, pmids: list[str]) -> list[ET.Element]:
        articles: list[ET.Element] = []
        for batch in chunked(pmids, 100):
            params = self._params(
                {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
            )
            r = requests.get(f"{self.BASE}/efetch.fcgi", params=params, timeout=self.timeout)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            articles.extend(root.findall(".//PubmedArticle"))
        return articles

    @staticmethod
    def _article_abstract(article: ET.Element) -> str:
        parts = []
        for node in article.findall(".//Abstract/AbstractText"):
            label = node.attrib.get("Label")
            txt = "".join(node.itertext()).strip()
            if not txt:
                continue
            parts.append(f"{label}: {txt}" if label else txt)
        return normalize_whitespace(" ".join(parts))

    @staticmethod
    def _article_title(article: ET.Element) -> str:
        node = article.find(".//ArticleTitle")
        return normalize_whitespace("".join(node.itertext()) if node is not None else "")

    @staticmethod
    def _article_pubdate(article: ET.Element) -> str:
        pub = article.find(".//PubDate")
        if pub is None:
            return ""
        year = pub.findtext("Year") or ""
        month = pub.findtext("Month") or ""
        day = pub.findtext("Day") or ""
        return normalize_whitespace(" ".join([year, month, day]))

    @staticmethod
    def _article_authors(article: ET.Element) -> list[str]:
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            collective = author.findtext("CollectiveName")
            if collective:
                authors.append(collective)
                continue
            last = author.findtext("LastName") or ""
            fore = author.findtext("ForeName") or ""
            name = normalize_whitespace(" ".join([fore, last]))
            if name:
                authors.append(name)
        return dedupe_preserve_order(authors)

    @staticmethod
    def _article_journal(article: ET.Element) -> str:
        return normalize_whitespace(article.findtext(".//Journal/Title") or "")

    @staticmethod
    def _article_doi(article: ET.Element) -> str | None:
        for aid in article.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = normalize_whitespace(aid.text or "")
                return doi or None
        return None

    @staticmethod
    def _article_pubtypes(article: ET.Element) -> list[str]:
        return dedupe_preserve_order(
            [normalize_whitespace(n.text or "") for n in article.findall(".//PublicationTypeList/PublicationType")]
        )

    @staticmethod
    def _mesh_terms(article: ET.Element) -> list[str]:
        terms = []
        for mh in article.findall(".//MeshHeadingList/MeshHeading"):
            desc = mh.find("DescriptorName")
            if desc is not None and desc.text:
                terms.append(normalize_whitespace(desc.text))
        return dedupe_preserve_order(terms)

    def fetch_records(self, pmids: list[str]) -> list[PaperRecord]:
        summary_map = self.esummary(pmids)
        xml_articles = self.efetch_xml(pmids)

        records = []
        for article in xml_articles:
            pmid = normalize_whitespace(article.findtext(".//PMID") or "")
            title = self._article_title(article) or normalize_whitespace(summary_map.get(pmid, {}).get("title", ""))
            published = self._article_pubdate(article) or normalize_whitespace(summary_map.get(pmid, {}).get("pubdate", ""))
            journal = self._article_journal(article) or normalize_whitespace(summary_map.get(pmid, {}).get("fulljournalname", ""))
            doi = self._article_doi(article)
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            record = PaperRecord(
                source="pubmed",
                source_id=pmid,
                title=title,
                abstract=self._article_abstract(article),
                url=url,
                published=published,
                authors=self._article_authors(article),
                journal_or_category=journal,
                doi=doi,
                publication_types=self._article_pubtypes(article),
                mesh_terms=self._mesh_terms(article),
                raw=summary_map.get(pmid, {}),
            )
            records.append(record)
        return records

    def search(self, query: str, *, days: int = 30, retmax: int = 100) -> list[PaperRecord]:
        pmids = self.search_pmids(query, days=days, retmax=retmax)
        if not pmids:
            return []
        return self.fetch_records(pmids)
