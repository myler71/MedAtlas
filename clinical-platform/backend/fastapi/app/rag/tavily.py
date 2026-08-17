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