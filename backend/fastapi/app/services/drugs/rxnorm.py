# app/services/drugs/rxnorm.py
"""RxNorm REST API provider.

Docs: https://rxnav.nlm.nih.gov/REST.html

Endpoints used:
- /REST/approximateTerm.json — fuzzy search by name
- /REST/rxcui/{cui}/property.json — get properties for a CUI
- /REST/rxcui/{cui}/related.json?tty=IN+MIN+BN — get ingredients + brand names
"""
import httpx
from typing import List, Optional
from .provider import DrugProvider, DrugConcept


RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


class RxNormProvider(DrugProvider):
    def __init__(self, base_url: str = RXNORM_BASE, timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    async def search(self, query: str, limit: int = 10) -> List[DrugConcept]:
        params = {"term": query, "maxEntries": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/approximateTerm.json", params=params)
            r.raise_for_status()
            data = r.json()

        candidates = data.get("approximateGroup", {}).get("candidate", [])
        concepts = []
        for c in candidates:
            cui = c.get("rxcui")
            name = c.get("name")
            if not cui or not name:
                continue
            detail = await self.resolve(cui)
            if detail:
                concepts.append(detail)
        return concepts

    async def resolve(self, name_or_cui: str) -> Optional[DrugConcept]:
        if not name_or_cui:
            return None
        cui = name_or_cui.strip()
        # If not a CUI, search first
        if not cui.isdigit():
            results = await self.search(cui, limit=1)
            return results[0] if results else None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/rxcui/{cui}/property.json", params={"propName": "RxNorm Name"})
            r.raise_for_status()
            name_data = r.json()
            name = None
            props = name_data.get("propConceptGroup", {}).get("propConcept", [])
            if props:
                name = props[0].get("propName")

            # Related concepts for ingredients + brand names
            aliases: List[str] = []
            drug_class = None
            r2 = await client.get(
                f"{self.base_url}/rxcui/{cui}/related.json",
                params={"tty": "IN+MIN+BN"},
            )
            if r2.status_code == 200:
                rel = r2.json().get("relatedGroup", {}).get("conceptGroup", [])
                for grp in rel:
                    tty = grp.get("tty")
                    if tty == "VA" and grp.get("conceptProperties"):
                        drug_class = grp["conceptProperties"][0].get("name")
                    for cp in grp.get("conceptProperties", []) or []:
                        cn = cp.get("name")
                        if cn and cn != name:
                            aliases.append(cn)

        if not name:
            return None
        return DrugConcept(
            rxnorm_cui=cui, name=name, generic_name=None,
            drug_class=drug_class, aliases=aliases[:20],
        )