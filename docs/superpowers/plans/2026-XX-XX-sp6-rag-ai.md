# SP-6: RAG & AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the patient AI assistant backed by Tavily MCP (web-grounded RAG) + local pgvector retrieval, with structured outputs, citation validation, and prompt injection defense.

**Architecture:** Tavily MCP client for external evidence, local pgvector for patient records. Hybrid retrieval via Reciprocal Rank Fusion. Structured responses via Pydantic. Citations from Tavily URLs.

**Tech Stack:** Python httpx (Tavily MCP), sentence-transformers (embeddings), pgvector, Pydantic, FastAPI, vanilla JS

**Spec:** `docs/superpowers/specs/2026-XX-XX-clinical-platform-design.md` (especially §8 RAG Architecture, §9 LLM Integration)

**Depends on:** SP-1 through SP-5 (schema, dental, skeleton, patient, drugs)

## Global Constraints

- Tavily API key is a placeholder in `.env`; the system must gracefully fall back to local-only retrieval when the key is missing
- Patient queries enforce `patient_id` filter at the DB level — never in the LLM prompt
- All AI outputs are validated against `PatientChatResponse` Pydantic schema before returning to client
- Citations always include Tavily `url` + `title` when present
- LLM is pluggable via env (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`). Default: simple synthesis over retrieved context (no external LLM call) so the demo runs without an LLM key.

---

## Task 1: Database Migration — RAG Tables

**Files:**
- Create: `clinical-platform/database/migrations/006_rag.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 006_rag.sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(50) CHECK (document_type IN ('drug_info','clinical_guideline','patient_record','web_article','other')),
    content_hash VARCHAR(64) UNIQUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rag_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL,
    chunk_id UUID REFERENCES knowledge_chunks(id),
    claim_text TEXT,
    evidence_text TEXT,
    source VARCHAR(500),
    validated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rag_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieval_mode VARCHAR(50) DEFAULT 'hybrid' CHECK (retrieval_mode IN ('local','tavily','hybrid')),
    citations_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_chunks_doc ON knowledge_chunks(document_id);
CREATE INDEX idx_rag_citations_query ON rag_citations(query_id);
CREATE INDEX idx_rag_queries_patient ON rag_queries(patient_id, created_at DESC);
```

- [ ] **Step 2: Apply migration**

```bash
docker compose exec -T postgres psql -U clinical -d clinical_platform < database/migrations/006_rag.sql
```

- [ ] **Step 3: Commit**

```bash
git add database/migrations/
git commit -m "feat(db): knowledge_documents, knowledge_chunks, rag_citations, rag_queries tables"
```

---

## Task 2: Tavily MCP Client

**Files:**
- Create: `clinical-platform/backend/fastapi/app/rag/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/rag/tavily.py`

- [ ] **Step 1: Write tavily.py**

```python
# app/rag/tavily.py
"""Tavily MCP client. Falls back gracefully when API key is missing.

The MCP integration is invoked as a tool — but to keep this scaffold self-contained
without an MCP server, we call the Tavily REST API directly via httpx. The
function signature mirrors the MCP tool interface for portability.
"""
import os
import httpx
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyResult(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0.0


class TavilyClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.timeout = timeout
        self.enabled = bool(self.api_key) and self.api_key != "your-tavily-api-key"

    async def search(self, query: str, max_results: int = 5, topic: str = "general") -> List[TavilyResult]:
        if not self.enabled:
            return []
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "topic": topic,
            "include_answer": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(TAVILY_SEARCH_URL, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []

        results = []
        for item in data.get("results", []) or []:
            results.append(TavilyResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            ))
        return results
```

- [ ] **Step 2: Add `__init__.py`**

```python
# app/rag/__init__.py
from .tavily import TavilyClient, TavilyResult

__all__ = ["TavilyClient", "TavilyResult"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/rag/
git commit -m "feat(rag): Tavily MCP client with graceful fallback"
```

---

## Task 3: Local Embedding + Hybrid Retrieval

**Files:**
- Create: `clinical-platform/backend/fastapi/app/rag/embeddings.py`
- Create: `clinical-platform/backend/fastapi/app/rag/retrieval.py`

- [ ] **Step 1: Write embeddings.py**

```python
# app/rag/embeddings.py
"""Local embedding using sentence-transformers (small model for demo).

Falls back to a deterministic hash-based pseudo-embedding if the model
can't load (so the demo runs even without ML deps installed).
"""
import os
import hashlib
from typing import List

_DIM = 1536


def _hash_embed(text: str, dim: int = _DIM) -> List[float]:
    """Deterministic pseudo-embedding. NOT semantically meaningful — only used as a fallback."""
    vec = [0.0] * dim
    for i, token in enumerate(text.lower().split()[:dim]):
        h = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)
        vec[(i + h) % dim] += 1.0 / (1 + i * 0.01)
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm if norm > 0 else x for x in vec]


_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _try_load_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL
    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = None
    return _MODEL


def embed_text(text: str) -> List[float]:
    model = _try_load_model()
    if model is not None:
        try:
            vec = model.encode(text).tolist()
            # Pad / truncate to _DIM
            if len(vec) < _DIM:
                vec = vec + [0.0] * (_DIM - len(vec))
            else:
                vec = vec[:_DIM]
            return vec
        except Exception:
            pass
    return _hash_embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    return [embed_text(t) for t in texts]
```

- [ ] **Step 2: Write retrieval.py**

```python
# app/rag/retrieval.py
"""Hybrid retrieval: pgvector (local) + Tavily (web), fused with RRF."""
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from .embeddings import embed_text
from .tavily import TavilyClient


class RetrievedChunk:
    def __init__(self, content: str, source: str, score: float, metadata: Dict[str, Any] = None):
        self.content = content
        self.source = source
        self.score = score
        self.metadata = metadata or {}


class HybridRetriever:
    def __init__(self, tavily: Optional[TavilyClient] = None):
        self.tavily = tavily or TavilyClient()

    def _local_search(self, db: Session, query: str, patient_id: Optional[UUID], top_k: int = 5) -> List[RetrievedChunk]:
        emb = embed_text(query)
        emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
        params = {"emb": emb_str, "k": top_k}
        where = ["embedding IS NOT NULL"]
        # If patient-scoped, only look at patient_record chunks
        sql = """SELECT id, content, metadata, 1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                 FROM knowledge_chunks WHERE embedding IS NOT NULL"""
        if patient_id:
            sql += " AND (metadata->>'patient_id' = :pid OR document_id IN (SELECT id FROM knowledge_documents WHERE document_type = 'patient_record' AND metadata->>'patient_id' = :pid))"
            params["pid"] = str(patient_id)
        sql += " ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :k"
        rows = db.execute(text(sql), params).mappings().all()
        return [
            RetrievedChunk(
                content=r["content"], source=r["metadata"].get("source", "local") if r["metadata"] else "local",
                score=float(r["similarity"]),
                metadata=dict(r["metadata"] or {}),
            )
            for r in rows
        ]

    async def _tavily_search(self, query: str, max_results: int = 5) -> List[RetrievedChunk]:
        results = await self.tavily.search(query, max_results=max_results)
        return [
            RetrievedChunk(content=r.content, source=r.url, score=r.score, metadata={"title": r.title, "url": r.url})
            for r in results
        ]

    async def retrieve(
        self,
        db: Session,
        query: str,
        patient_id: Optional[UUID] = None,
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        local_results = self._local_search(db, query, patient_id, top_k=top_k)
        tavily_results = await self._tavily_search(query, max_results=top_k)

        # Reciprocal Rank Fusion (RRF)
        k = 60
        scores: Dict[str, float] = {}
        chunks: Dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(local_results):
            key = f"local:{chunk.content[:80]}"
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            chunks[key] = chunk

        for rank, chunk in enumerate(tavily_results):
            key = f"tavily:{chunk.content[:80]}"
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            chunks[key] = chunk

        fused = sorted(chunks.values(), key=lambda c: scores.get(f"local:{c.content[:80]}" if c in local_results else f"tavily:{c.content[:80]}", 0.0), reverse=True)
        return fused[:top_k]
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/rag/embeddings.py backend/fastapi/app/rag/retrieval.py
git commit -m "feat(rag): embeddings + hybrid retrieval with RRF"
```

---

## Task 4: Patient AI Assistant Service

**Files:**
- Create: `clinical-platform/backend/fastapi/app/ai/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/ai/patient_assistant.py`

- [ ] **Step 1: Write patient_assistant.py**

```python
# app/ai/patient_assistant.py
"""Patient-scoped AI assistant. Retrieves evidence + patient context, synthesizes a
structured response with citations. The synthesis step is pluggable via env.

Clinical safety: this is decision-support. Outputs use 'based on', 'evidence
indicates', 'no supporting record was found' language — never diagnosis or prescription.
"""
import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from ..rag import TavilyClient
from ..rag.retrieval import HybridRetriever


class Citation(BaseModel):
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    claim: Optional[str] = None
    evidence_excerpt: Optional[str] = None


class PatientChatResponse(BaseModel):
    patient_name: str
    patient_id: str
    summary: str
    dental_history: List[Dict[str, Any]] = []
    orthopedic_history: List[Dict[str, Any]] = []
    recent_procedures: List[Dict[str, Any]] = []
    current_medications: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    tooth_findings: List[Dict[str, Any]] = []
    bone_findings: List[Dict[str, Any]] = []
    important_notes: List[str] = []
    missing_information: List[str] = []
    citations: List[Citation] = []


class PatientAssistant:
    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever(TavilyClient())

    async def _gather_patient_context(self, db: Session, patient_id: UUID) -> Dict[str, Any]:
        # Patient identity
        p = db.execute(
            text("SELECT first_name, last_name, date_of_birth, gender FROM patients WHERE id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().first()
        if not p:
            return {}

        meds = db.execute(
            text("SELECT drug_name, dosage, frequency, status FROM medications WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        allergies = db.execute(
            text("SELECT allergen, severity, reaction FROM allergies WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        history = db.execute(
            text("SELECT condition_name, status FROM medical_histories WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        tooth_events = db.execute(
            text("""SELECT tooth_id, event_type, procedure_name, event_date, diagnosis
                    FROM tooth_events WHERE patient_id = :pid ORDER BY event_date DESC LIMIT 10"""),
            {"pid": str(patient_id)},
        ).mappings().all()
        bone_events = db.execute(
            text("""SELECT bone_id, event_type, diagnosis, event_date, treatment
                    FROM bone_events WHERE patient_id = :pid ORDER BY event_date DESC LIMIT 10"""),
            {"pid": str(patient_id)},
        ).mappings().all()

        return {
            "patient": dict(p),
            "medications": [dict(m) for m in meds],
            "allergies": [dict(a) for a in allergies],
            "medical_history": [dict(h) for h in history],
            "tooth_events": [dict(t) for t in tooth_events],
            "bone_events": [dict(b) for b in bone_events],
        }

    async def chat(self, db: Session, patient_id: UUID, message: str) -> PatientChatResponse:
        ctx = await self._gather_patient_context(db, patient_id)
        if not ctx:
            return PatientChatResponse(
                patient_name="(unknown)", patient_id=str(patient_id),
                summary="Patient not found.",
                important_notes=["No record exists for this patient ID."],
            )

        # Retrieve evidence (patient-scoped)
        chunks = await self.retriever.retrieve(db, message, patient_id=patient_id, top_k=5)
        citations = []
        for c in chunks:
            citations.append(Citation(
                source=c.source,
                title=c.metadata.get("title") if c.metadata else None,
                url=c.metadata.get("url") if c.metadata else None,
                evidence_excerpt=c.content[:280],
            ))

        p = ctx["patient"]
        meds = ctx["medications"]
        allergies = ctx["allergies"]
        history = ctx["medical_history"]
        tooth_events = ctx["tooth_events"]
        bone_events = ctx["bone_events"]

        # Synthesize summary (rule-based, no external LLM required for the demo)
        summary_parts = [
            f"Patient is {p.get('first_name', '')} {p.get('last_name', '')}".strip(),
        ]
        if p.get("date_of_birth"):
            summary_parts.append(f"DOB {p['date_of_birth']}")
        summary_parts.append(f"{len(meds)} medications on file")
        summary_parts.append(f"{len(allergies)} allergies on file")
        summary_parts.append(f"{len(history)} medical history entries")
        summary_parts.append(f"{len(tooth_events)} recent dental events")
        summary_parts.append(f"{len(bone_events)} recent orthopedic events")
        summary_parts.append(f"Retrieved {len(chunks)} evidence chunks for the query")

        summary = " • ".join(summary_parts)

        # Important notes (clinical safety language)
        important = [
            "This response is decision-support information based on retrieved records.",
            "It is NOT a diagnosis or prescription.",
        ]
        if not chunks:
            important.append("No supporting external evidence was retrieved. Local records only.")
            missing = ["External clinical evidence unavailable — Tavily API key may be missing"]
        else:
            missing = []

        return PatientChatResponse(
            patient_name=f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
            patient_id=str(patient_id),
            summary=summary,
            dental_history=[{"event_type": t["event_type"], "procedure": t["procedure_name"], "date": str(t["event_date"])} for t in tooth_events],
            orthopedic_history=[{"event_type": b["event_type"], "diagnosis": b["diagnosis"], "date": str(b["event_date"])} for b in bone_events],
            recent_procedures=[{"kind": "tooth", "detail": t["procedure_name"] or t["event_type"], "date": str(t["event_date"])} for t in tooth_events[:5]] +
                               [{"kind": "bone", "detail": b["event_type"], "date": str(b["event_date"])} for b in bone_events[:5]],
            current_medications=[{"drug": m["drug_name"], "dosage": m["dosage"], "frequency": m["frequency"], "status": m["status"]} for m in meds if m["status"] == "active"],
            allergies=[{"allergen": a["allergen"], "severity": a["severity"], "reaction": a["reaction"]} for a in allergies],
            tooth_findings=[],
            bone_findings=[],
            important_notes=important,
            missing_information=missing,
            citations=citations,
        )
```

- [ ] **Step 2: Add `__init__.py`**

```python
# app/ai/__init__.py
from .patient_assistant import PatientAssistant, PatientChatResponse, Citation

__all__ = ["PatientAssistant", "PatientChatResponse", "Citation"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/ai/
git commit -m "feat(ai): patient assistant with retrieval + structured response"
```

---

## Task 5: AI Chat API Endpoint

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/chat.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py`

- [ ] **Step 1: Write chat.py**

```python
# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext
from ..ai import PatientAssistant

router = APIRouter(prefix="/api/chat", tags=["chat"])

assistant = PatientAssistant()


class ChatRequest(BaseModel):
    patient_id: UUID
    message: str
    context: Optional[str] = None


@router.post("/patient")
async def chat_with_patient_assistant(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail={"code": "EMPTY_MESSAGE", "message": "Message cannot be empty"})
    response = await assistant.chat(db, req.patient_id, req.message)
    return response.model_dump()
```

- [ ] **Step 2: Modify main.py**

Append inside `app/main.py`:

```python
from .api import chat
app.include_router(chat.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/chat.py backend/fastapi/app/main.py
git commit -m "feat(ai): chat API endpoint with patient-scoped retrieval"
```

---

## Task 6: AI Assistant Frontend Page

**Files:**
- Create: `clinical-platform/frontend/js/pages/ai-assistant.js`

- [ ] **Step 1: Write ai-assistant.js**

```javascript
// js/pages/ai-assistant.js
import { apiCall } from '../api.js';

export class AIAssistantPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.history = [];
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;height:100vh;max-height:90vh">
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border)">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>AI Patient Assistant</strong>
          </div>
        </nav>
        <div id="chat-history" style="flex:1;overflow-y:auto;padding:24px"></div>
        <form id="chat-form" style="padding:16px 0;border-top:1px solid var(--color-border);display:flex;gap:8px">
          <input class="input" id="msg-input" placeholder="Ask about this patient..." style="flex:1" />
          <button type="submit" class="btn btn-primary">Send</button>
        </form>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    this.container.querySelector('#chat-form').onsubmit = (e) => this.send(e);
    this.historyEl = this.container.querySelector('#chat-history');

    // Initial assistant message
    this.addAssistantMessage('I can answer questions about this patient\'s clinical record. Try asking about their allergies, medications, or recent procedures.');
  }

  addUserMessage(text) {
    this.history.push({ role: 'user', text });
    this.renderMessage('user', text);
  }

  addAssistantMessage(text) {
    this.history.push({ role: 'assistant', text });
    this.renderMessage('assistant', text);
  }

  renderMessage(role, text) {
    const div = document.createElement('div');
    div.style.cssText = `margin-bottom:12px;padding:12px;border-radius:8px;max-width:80%;${
      role === 'user'
        ? 'background:var(--color-primary);color:white;margin-left:auto'
        : 'background:var(--color-surface);border:1px solid var(--color-border)'
    }`;
    div.innerHTML = text;
    this.historyEl.appendChild(div);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
  }

  renderStructured(data) {
    const div = document.createElement('div');
    div.style.cssText = 'margin-bottom:12px;padding:12px;border-radius:8px;background:var(--color-surface);border:1px solid var(--color-border);max-width:85%';
    const citations = data.citations || [];
    div.innerHTML = `
      <div style="margin-bottom:8px"><strong>${data.patient_name}</strong></div>
      <div class="text-secondary" style="font-size:14px;margin-bottom:8px">${data.summary}</div>
      ${data.current_medications?.length ? `
        <details style="margin-top:8px"><summary><strong>Medications (${data.current_medications.length})</strong></summary>
          <ul>${data.current_medications.map(m => `<li>${m.drug} ${m.dosage || ''} ${m.frequency || ''} <em>(${m.status})</em></li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.allergies?.length ? `
        <details style="margin-top:8px"><summary><strong>Allergies (${data.allergies.length})</strong></summary>
          <ul>${data.allergies.map(a => `<li>${a.allergen} <em>(${a.severity})</em> ${a.reaction || ''}</li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.recent_procedures?.length ? `
        <details style="margin-top:8px"><summary><strong>Recent Procedures (${data.recent_procedures.length})</strong></summary>
          <ul>${data.recent_procedures.map(p => `<li>${p.date} — ${p.kind}: ${p.detail}</li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.important_notes?.length ? `
        <div style="margin-top:8px;padding:8px;background:#fef3c7;border-radius:4px;font-size:13px">
          ⚠️ ${data.important_notes.join(' • ')}
        </div>
      ` : ''}
      ${data.missing_information?.length ? `
        <div style="margin-top:8px;padding:8px;background:#fee2e2;border-radius:4px;font-size:13px">
          Missing: ${data.missing_information.join(', ')}
        </div>
      ` : ''}
      ${citations.length ? `
        <details style="margin-top:8px"><summary><strong>Citations (${citations.length})</strong></summary>
          <ol style="font-size:12px">${citations.map(c => `
            <li>${c.title || c.source}${c.url ? ` — <a href="${c.url}" target="_blank" rel="noopener">${c.url.substring(0, 60)}...</a>` : ''}
              <div style="color:var(--color-text-secondary)">${c.evidence_excerpt || ''}</div>
            </li>
          `).join('')}</ol>
        </details>
      ` : ''}
    `;
    this.historyEl.appendChild(div);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
  }

  async send(e) {
    e.preventDefault();
    const input = this.container.querySelector('#msg-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    this.addUserMessage(message);
    try {
      const data = await apiCall('/api/chat/patient', {
        method: 'POST',
        body: JSON.stringify({ patient_id: this.patientId, message }),
      });
      this.renderStructured(data);
    } catch (e) {
      this.addAssistantMessage(`Error: ${e.message}`);
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/
git commit -m "feat(ai): AI assistant frontend with structured cards + citations"
```

---

## Summary

| Task | Deliverable | Status |
|------|------------|--------|
| 1 | RAG tables migration | |
| 2 | Tavily MCP client | |
| 3 | Embeddings + hybrid retrieval | |
| 4 | Patient assistant service | |
| 5 | Chat API endpoint | |
| 6 | AI assistant frontend | |

**Total tasks:** 6
