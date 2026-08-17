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