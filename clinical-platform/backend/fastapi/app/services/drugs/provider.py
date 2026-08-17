# app/services/drugs/provider.py
"""Drug provider abstraction. Implementations: RxNorm (default)."""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class DrugConcept(BaseModel):
    rxnorm_cui: str
    name: str
    generic_name: Optional[str] = None
    drug_class: Optional[str] = None
    aliases: List[str] = []


class DrugProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[DrugConcept]:
        """Return list of drug concepts matching the query."""
        ...

    @abstractmethod
    async def resolve(self, name_or_cui: str) -> Optional[DrugConcept]:
        """Resolve a single drug name or CUI to a canonical concept."""
        ...