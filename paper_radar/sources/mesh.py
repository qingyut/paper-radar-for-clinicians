from __future__ import annotations

import requests

from paper_radar.utils import dedupe_preserve_order, normalize_whitespace


class MeSHClient:
    BASE_SPARQL = "https://id.nlm.nih.gov/mesh/sparql"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def _sparql(self, query: str) -> dict:
        params = {
            "query": query,
            "format": "JSON",
            "inference": "true",
            "year": "current",
        }
        r = requests.get(self.BASE_SPARQL, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def find_best_descriptor(self, keyword: str) -> dict | None:
        escaped = keyword.replace('"', '\\"')
        query = f'''
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT ?d ?label
FROM <http://id.nlm.nih.gov/mesh>
WHERE {{
  ?d a meshv:Descriptor .
  ?d meshv:active 1 .
  ?d rdfs:label ?label .
  FILTER(LCASE(STR(?label)) = LCASE("{escaped}"))
}}
LIMIT 1
'''
        data = self._sparql(query)
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            b = bindings[0]
            return {"uri": b["d"]["value"], "label": b["label"]["value"]}

        query = f'''
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT DISTINCT ?d ?label
FROM <http://id.nlm.nih.gov/mesh>
WHERE {{
  ?d a meshv:Descriptor .
  ?d meshv:active 1 .
  ?d rdfs:label ?label .
  OPTIONAL {{
    ?d meshv:concept ?c .
    ?c rdfs:label ?cLabel .
  }}
  FILTER(
    CONTAINS(LCASE(STR(?label)), LCASE("{escaped}")) ||
    CONTAINS(LCASE(STR(?cLabel)), LCASE("{escaped}"))
  )
}}
LIMIT 10
'''
        data = self._sparql(query)
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            b = bindings[0]
            return {"uri": b["d"]["value"], "label": b["label"]["value"]}

        return None

    def get_entry_terms(self, descriptor_uri: str) -> list[str]:
        descriptor_uri = normalize_whitespace(descriptor_uri)
        query = f'''
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT DISTINCT ?termLabel
FROM <http://id.nlm.nih.gov/mesh>
WHERE {{
  <{descriptor_uri}> meshv:concept ?concept .
  ?concept meshv:term ?term .
  ?term rdfs:label ?termLabel .
}}
LIMIT 100
'''
        data = self._sparql(query)
        bindings = data.get("results", {}).get("bindings", [])
        return dedupe_preserve_order([b["termLabel"]["value"] for b in bindings])
