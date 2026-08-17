# SP-5: Drug Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement drug concept resolution via RxNorm and a drug-drug interaction checker. Cache resolved concepts and interaction pairs in PostgreSQL.

**Architecture:** A `DrugProvider` interface with an RxNorm implementation, a `DrugInteractionService` that queries our cached interactions table, and a FastAPI surface for `/api/drugs/resolve`, `/api/drugs/search`, and `/api/drug-interactions/check`.

**Tech Stack:** Python httpx (async), SQLAlchemy, Pydantic, FastAPI, RxNorm REST API

**Spec:** `docs/superpowers/specs/2026-XX-XX-clinical-platform-design.md` (especially §6.5, §7.5)

**Depends on:** SP-1 (schema, auth)

## Global Constraints

- RxNorm API has no auth, just JSON REST at `https://rxnav.nlm.nih.gov/REST`
- Cache ALL RxNorm lookups locally (24-hour TTL) so we don't hammer the upstream API
- Drug interaction checker compares any pair from `drug_concepts` joined via `drug_interactions`
- Unknown drugs return 422 with a structured error so the UI can suggest disambiguation

---

## Task 1: Database Migration — Drug Tables

**Files:**
- Create: `clinical-platform/database/migrations/005_drugs.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 005_drugs.sql
CREATE TABLE drug_concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rxnorm_cui VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    drug_class VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drug_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_concept_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) DEFAULT 'brand' CHECK (alias_type IN ('brand','synonym','abbreviation','other')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug_concept_id, alias)
);

CREATE TABLE drug_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_a_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    drug_b_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('minor','moderate','major','contraindicated')),
    mechanism TEXT,
    clinical_significance TEXT,
    evidence_source VARCHAR(255),
    evidence_strength VARCHAR(50) CHECK (evidence_strength IN ('theoretical','case_reports','established','unknown')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (drug_a_id < drug_b_id),
    UNIQUE(drug_a_id, drug_b_id)
);

CREATE TABLE drug_cache (
    rxnorm_cui VARCHAR(20) PRIMARY KEY,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drug_concepts_rxnorm ON drug_concepts(rxnorm_cui);
CREATE INDEX idx_drug_concepts_name ON drug_concepts USING gin(to_tsvector('english', name));
CREATE INDEX idx_drug_aliases_alias ON drug_aliases USING gin(to_tsvector('english', alias));
CREATE INDEX idx_drug_interactions_drugs ON drug_interactions(drug_a_id, drug_b_id);
```

- [ ] **Step 2: Apply migration**

```bash
docker compose exec -T postgres psql -U clinical -d clinical_platform < database/migrations/005_drugs.sql
```

- [ ] **Step 3: Commit**

```bash
git add database/migrations/
git commit -m "feat(db): drug_concepts, drug_aliases, drug_interactions, drug_cache tables"
```

---

## Task 2: Drug Provider Interface + RxNorm Implementation

**Files:**
- Create: `clinical-platform/backend/fastapi/app/services/drugs/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/services/drugs/provider.py`
- Create: `clinical-platform/backend/fastapi/app/services/drugs/rxnorm.py`

- [ ] **Step 1: Write provider.py (interface)**

```python
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
```

- [ ] **Step 2: Write rxnorm.py**

```python
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
```

- [ ] **Step 3: Add `__init__.py`**

```python
# app/services/drugs/__init__.py
from .provider import DrugProvider, DrugConcept
from .rxnorm import RxNormProvider

__all__ = ["DrugProvider", "DrugConcept", "RxNormProvider"]
```

- [ ] **Step 4: Commit**

```bash
git add backend/fastapi/app/services/drugs/
git commit -m "feat(drugs): DrugProvider interface + RxNorm implementation"
```

---

## Task 3: Drug Interaction Service + Seed Data

**Files:**
- Create: `clinical-platform/backend/fastapi/app/services/drugs/interactions.py`
- Create: `clinical-platform/database/seeds/drug_interactions.sql`

- [ ] **Step 1: Write interactions.py**

```python
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
```

- [ ] **Step 2: Write seed SQL for known interactions**

```sql
-- database/seeds/drug_interactions.sql
-- This seeds a small set of well-known interactions for the demo.
-- Real production would source from curated pharmacology databases.

-- First, ensure the drug_concepts exist (idempotent)
INSERT INTO drug_concepts (rxnorm_cui, name, drug_class) VALUES
    ('197361', 'Warfarin', 'Anticoagulant'),
    ('6809', 'Metformin', 'Biguanide antihyperglycemic'),
    ('29046', 'Lisinopril', 'ACE inhibitor'),
    ('36556', 'Simvastatin', 'HMG-CoA reductase inhibitor'),
    ('152923', 'Atorvastatin', 'HMG-CoA reductase inhibitor'),
    ('68091', 'Ibuprofen', 'NSAID'),
    ('161', 'Acetaminophen', 'Analgesic'),
    ('2556', 'Aspirin', 'NSAID / Antiplatelet'),
    ('208161', 'Amiodarone', 'Antiarrhythmic'),
    ('10180', 'Ciprofloxacin', 'Fluoroquinolone antibiotic')
ON CONFLICT (rxnorm_cui) DO NOTHING;

-- Map CUI -> ID for FK inserts
DO $$
DECLARE
    warfarin_id UUID;
    metformin_id UUID;
    lisinopril_id UUID;
    simvastatin_id UUID;
    atorvastatin_id UUID;
    ibuprofen_id UUID;
    acetaminophen_id UUID;
    aspirin_id UUID;
    amiodarone_id UUID;
    ciprofloxacin_id UUID;
BEGIN
    SELECT id INTO warfarin_id FROM drug_concepts WHERE rxnorm_cui = '197361';
    SELECT id INTO metformin_id FROM drug_concepts WHERE rxnorm_cui = '6809';
    SELECT id INTO lisinopril_id FROM drug_concepts WHERE rxnorm_cui = '29046';
    SELECT id INTO simvastatin_id FROM drug_concepts WHERE rxnorm_cui = '36556';
    SELECT id INTO atorvastatin_id FROM drug_concepts WHERE rxnorm_cui = '152923';
    SELECT id INTO ibuprofen_id FROM drug_concepts WHERE rxnorm_cui = '68091';
    SELECT id INTO acetaminophen_id FROM drug_concepts WHERE rxnorm_cui = '161';
    SELECT id INTO aspirin_id FROM drug_concepts WHERE rxnorm_cui = '2556';
    SELECT id INTO amiodarone_id FROM drug_concepts WHERE rxnorm_cui = '208161';
    SELECT id INTO ciprofloxacin_id FROM drug_concepts WHERE rxnorm_cui = '10180';

    INSERT INTO drug_interactions (drug_a_id, drug_b_id, severity, mechanism, clinical_significance, evidence_source, evidence_strength) VALUES
        (aspirin_id, ibuprofen_id, 'moderate', 'Both NSAIDs; reduced antiplatelet effect of aspirin', 'May reduce cardioprotective effect', 'FDA labeling', 'established'),
        (aspirin_id, warfarin_id, 'major', 'Additive anticoagulant/antiplatelet effects', 'Significantly increased bleeding risk', 'FDA labeling', 'established'),
        (ibuprofen_id, warfarin_id, 'major', 'NSAID-induced platelet inhibition + warfarin anticoagulation', 'Increased GI bleeding risk', 'DrugBank', 'established'),
        (simvastatin_id, amiodarone_id, 'major', 'CYP3A4 inhibition increases simvastatin levels', 'Increased risk of rhabdomyolysis', 'FDA labeling', 'established'),
        (atorvastatin_id, ciprofloxacin_id, 'moderate', 'CYP3A4 inhibition increases statin levels', 'Increased myopathy risk', 'DrugBank', 'established'),
        (lisinopril_id, ibuprofen_id, 'moderate', 'NSAIDs reduce ACE inhibitor antihypertensive effect', 'Reduced BP control, possible renal impairment', 'DrugBank', 'established'),
        (metformin_id, ciprofloxacin_id, 'moderate', 'Possible additive glucose dysregulation', 'Monitor blood glucose', 'DrugBank', 'theoretical'),
        (acetaminophen_id, warfarin_id, 'moderate', 'Possible CYP2C9 interaction at high doses', 'Increased INR with chronic high-dose APAP', 'DrugBank', 'case_reports')
    ON CONFLICT (drug_a_id, drug_b_id) DO NOTHING;
END $$;
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/services/drugs/interactions.py database/seeds/
git commit -m "feat(drugs): interaction service + seed interaction data"
```

---

## Task 4: Drug API Endpoints

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/drugs.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py`

- [ ] **Step 1: Write drugs.py**

```python
# app/api/drugs.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext
from ..services.drugs import RxNormProvider
from ..services.drugs.interactions import DrugInteractionService

router = APIRouter(prefix="/api", tags=["drugs"])

provider = RxNormProvider()
interaction_service = DrugInteractionService(provider)


class ResolveRequest(BaseModel):
    name: str


class ResolveResponse(BaseModel):
    rxnorm_cui: str
    name: str
    generic_name: Optional[str]
    drug_class: Optional[str]
    aliases: List[str]


@router.post("/drugs/resolve", response_model=ResolveResponse)
async def resolve_drug(req: ResolveRequest, user: UserContext = Depends(get_user_context)):
    concept = await provider.resolve(req.name)
    if not concept:
        raise HTTPException(status_code=422, detail={"code": "DRUG_NOT_FOUND", "message": f"Could not resolve drug: {req.name}"})
    return ResolveResponse(
        rxnorm_cui=concept.rxnorm_cui, name=concept.name,
        generic_name=concept.generic_name, drug_class=concept.drug_class,
        aliases=concept.aliases,
    )


@router.get("/drugs/search", response_model=List[ResolveResponse])
async def search_drugs(q: str = Query(..., min_length=2), limit: int = 10, user: UserContext = Depends(get_user_context)):
    concepts = await provider.search(q, limit=limit)
    return [
        ResolveResponse(
            rxnorm_cui=c.rxnorm_cui, name=c.name,
            generic_name=c.generic_name, drug_class=c.drug_class,
            aliases=c.aliases,
        )
        for c in concepts
    ]


class InteractionCheckRequest(BaseModel):
    drugs: List[str]


@router.post("/drug-interactions/check")
async def check_interactions(req: InteractionCheckRequest, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    if len(req.drugs) < 2:
        raise HTTPException(status_code=400, detail={"code": "NEED_2_DRUGS", "message": "Need at least 2 drugs to check interactions"})
    result = await interaction_service.check(db, req.drugs)
    return result.model_dump()
```

- [ ] **Step 2: Modify main.py**

Append inside `app/main.py`:

```python
from .api import drugs
app.include_router(drugs.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/drugs.py backend/fastapi/app/main.py
git commit -m "feat(drugs): resolve/search/interactions API endpoints"
```

---

## Task 5: Drug Interaction Checker Frontend

**Files:**
- Create: `clinical-platform/frontend/js/pages/drug-checker.js`

- [ ] **Step 1: Write drug-checker.js**

```javascript
// js/pages/drug-checker.js
import { apiCall } from '../api.js';

export class DrugCheckerPage {
  constructor(container, role, onBack) {
    this.container = container;
    this.role = role;
    this.onBack = onBack;
    this.drugs = [];
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Drug Interaction Checker</strong>
          </div>
        </nav>
        <div class="card">
          <p class="text-secondary">Add 2 or more drugs to check for known interactions. Powered by RxNorm.</p>
          <div class="flex gap-md mt-md">
            <input class="input" id="drug-input" placeholder="Drug name (e.g., warfarin)" style="flex:1" />
            <button class="btn btn-primary" id="btn-add">Add Drug</button>
          </div>
          <div id="drug-list" class="flex gap-sm mt-md" style="flex-wrap:wrap"></div>
          <button class="btn btn-primary btn-lg mt-md" id="btn-check" disabled>Check Interactions</button>
          <div id="results" class="mt-md"></div>
        </div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    this.container.querySelector('#btn-add').onclick = () => this.addDrug();
    this.container.querySelector('#drug-input').onkeydown = (e) => { if (e.key === 'Enter') this.addDrug(); };
    this.container.querySelector('#btn-check').onclick = () => this.check();
    this.renderDrugList();
  }

  addDrug() {
    const input = this.container.querySelector('#drug-input');
    const val = input.value.trim();
    if (!val) return;
    if (!this.drugs.includes(val)) this.drugs.push(val);
    input.value = '';
    this.renderDrugList();
  }

  removeDrug(d) {
    this.drugs = this.drugs.filter(x => x !== d);
    this.renderDrugList();
  }

  renderDrugList() {
    const list = this.container.querySelector('#drug-list');
    list.innerHTML = this.drugs.map(d => `
      <div style="padding:6px 12px;background:var(--color-bg);border-radius:16px;display:flex;gap:8px;align-items:center">
        <span>${d}</span>
        <button class="btn" style="padding:0 6px;color:var(--color-danger)" data-remove="${d}">×</button>
      </div>
    `).join('');
    list.querySelectorAll('[data-remove]').forEach(btn => {
      btn.onclick = () => this.removeDrug(btn.dataset.remove);
    });
    this.container.querySelector('#btn-check').disabled = this.drugs.length < 2;
  }

  async check() {
    const results = this.container.querySelector('#results');
    results.innerHTML = '<p class="text-secondary">Checking...</p>';
    try {
      const data = await apiCall('/api/drug-interactions/check', {
        method: 'POST',
        body: JSON.stringify({ drugs: this.drugs }),
      });
      this.renderResults(data);
    } catch (e) {
      results.innerHTML = `<p style="color:var(--color-danger)">${e.message}</p>`;
    }
  }

  renderResults(data) {
    const results = this.container.querySelector('#results');
    const interactions = data.interactions || [];
    const warnings = data.warnings || [];
    const resolved = data.drugs_resolved || [];

    results.innerHTML = `
      <h4 style="margin-top:24px">Resolved Drugs</h4>
      <ul>
        ${resolved.map(r => `<li><strong>${r.input}</strong> → ${r.name || 'NOT FOUND'}${r.drug_class ? ` <span class="text-secondary">(${r.drug_class})</span>` : ''}</li>`).join('')}
      </ul>

      ${warnings.length > 0 ? `<p style="color:var(--color-warning);margin-top:8px">⚠️ ${warnings.join('; ')}</p>` : ''}

      <h4 style="margin-top:24px">Interactions Found: ${interactions.length}</h4>
      ${interactions.length === 0 ? '<p class="text-secondary">No known interactions in the database. This does NOT mean the combination is safe — always consult clinical references.</p>' : ''}
      ${interactions.map(i => `
        <div class="card mt-md" style="border-left:4px solid ${this.severityColor(i.severity)}">
          <div style="display:flex;justify-content:space-between">
            <strong>${i.drug_a} + ${i.drug_b}</strong>
            <span style="color:${this.severityColor(i.severity)};font-weight:700">${i.severity.toUpperCase()}</span>
          </div>
          ${i.mechanism ? `<p class="text-secondary mt-md"><strong>Mechanism:</strong> ${i.mechanism}</p>` : ''}
          ${i.clinical_significance ? `<p><strong>Clinical significance:</strong> ${i.clinical_significance}</p>` : ''}
          <p class="text-secondary" style="font-size:12px;margin-top:8px">Source: ${i.evidence_source || 'unknown'} (${i.evidence_strength || 'unknown'})</p>
        </div>
      `).join('')}
    `;
  }

  severityColor(s) {
    return {
      minor: '#16a34a',
      moderate: '#d97706',
      major: '#dc2626',
      contraindicated: '#7f1d1d',
    }[s] || '#64748b';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/
git commit -m "feat(drugs): drug interaction checker UI"
```

---

## Summary

| Task | Deliverable | Status |
|------|------------|--------|
| 1 | Drug tables migration | |
| 2 | DrugProvider interface + RxNorm impl | |
| 3 | Interaction service + seed data | |
| 4 | Drug API endpoints (resolve, search, check) | |
| 5 | Drug interaction checker frontend | |

**Total tasks:** 5
