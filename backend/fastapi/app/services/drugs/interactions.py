# app/services/drugs/interactions.py
"""Drug-drug interaction checker.

Reads from the drug_interactions table; resolves drug names via the provider
and caches new concepts in drug_concepts on the fly.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from .rxnorm import RxNormProvider


class DrugInteraction(BaseModel):
    drug_a: str
    drug_a_cui: str
    drug_b: str
    drug_b_cui: str
    severity: str
    mechanism: Optional[str]
    clinical_significance: Optional[str]
    evidence_source: Optional[str]
    evidence_strength: Optional[str]


class InteractionCheckResult(BaseModel):
    drugs_resolved: List[dict]
    interactions: List[DrugInteraction]
    warnings: List[str] = []


class DrugInteractionService:
    def __init__(self, provider: Optional[RxNormProvider] = None):
        self.provider = provider or RxNormProvider()

    async def check(self, db: Session, drug_names: List[str]) -> InteractionCheckResult:
        # Resolve each name to a canonical concept
        resolved = []
        cuis = []
        for name in drug_names:
            concept = await self.provider.resolve(name)
            if not concept:
                resolved.append({"input": name, "resolved": False, "cui": None, "name": None})
                continue
            cuis.append(concept.rxnorm_cui)
            resolved.append({
                "input": name, "resolved": True,
                "cui": concept.rxnorm_cui, "name": concept.name,
                "drug_class": concept.drug_class,
            })
            # Upsert into drug_concepts
            db.execute(
                text("""INSERT INTO drug_concepts (rxnorm_cui, name, drug_class)
                        VALUES (:cui, :n, :dc)
                        ON CONFLICT (rxnorm_cui) DO UPDATE SET name = EXCLUDED.name, drug_class = EXCLUDED.drug_class, updated_at = NOW()"""),
                {"cui": concept.rxnorm_cui, "n": concept.name, "dc": concept.drug_class},
            )
            for alias in (concept.aliases or [])[:5]:
                db.execute(
                    text("""INSERT INTO drug_aliases (drug_concept_id, alias, alias_type)
                            SELECT id, :alias, 'synonym' FROM drug_concepts WHERE rxnorm_cui = :cui
                            ON CONFLICT (drug_concept_id, alias) DO NOTHING"""),
                    {"alias": alias, "cui": concept.rxnorm_cui},
                )
        db.commit()

        # Find all pairs (a < b) of CUIs
        interactions: List[DrugInteraction] = []
        for i in range(len(cuis)):
            for j in range(i + 1, len(cuis)):
                a, b = sorted([cuis[i], cuis[j]])
                rows = db.execute(
                    text("""SELECT dc_a.name AS drug_a_name, dc_a.rxnorm_cui AS drug_a_cui,
                                   dc_b.name AS drug_b_name, dc_b.rxnorm_cui AS drug_b_cui,
                                   di.severity, di.mechanism, di.clinical_significance,
                                   di.evidence_source, di.evidence_strength
                            FROM drug_interactions di
                            JOIN drug_concepts dc_a ON dc_a.id = di.drug_a_id
                            JOIN drug_concepts dc_b ON dc_b.id = di.drug_b_id
                            WHERE dc_a.rxnorm_cui = :a AND dc_b.rxnorm_cui = :b"""),
                    {"a": a, "b": b},
                ).mappings().all()
                for r in rows:
                    interactions.append(DrugInteraction(
                        drug_a=r["drug_a_name"], drug_a_cui=r["drug_a_cui"],
                        drug_b=r["drug_b_name"], drug_b_cui=r["drug_b_cui"],
                        severity=r["severity"], mechanism=r["mechanism"],
                        clinical_significance=r["clinical_significance"],
                        evidence_source=r["evidence_source"], evidence_strength=r["evidence_strength"],
                    ))

        warnings = []
        unresolved = [r["input"] for r in resolved if not r["resolved"]]
        if unresolved:
            warnings.append(f"Could not resolve: {', '.join(unresolved)}")

        return InteractionCheckResult(drugs_resolved=resolved, interactions=interactions, warnings=warnings)
