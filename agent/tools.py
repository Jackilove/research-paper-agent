"""Validated tools shared by the MCP server and the agent loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pymupdf
import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAPERS_DIR = PROJECT_ROOT / "papers"


class ReadPdfInput(BaseModel):
    """Arguments accepted by the local-document skill."""

    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(description="PDF filename located in the project's papers directory.")
    question: str = Field(
        default="", description="Question used to select relevant passages from the document."
    )
    max_pages: int = Field(default=12, ge=1, le=50)
    start_page: int = Field(default=1, ge=1, description='First page to read, one-based. Use next_page from the previous result to continue.')

    @field_validator("file_name")
    @classmethod
    def reject_paths(cls, value: str) -> str:
        if Path(value).name != value or not value.lower().endswith(".pdf"):
            raise ValueError("file_name must be a PDF filename without directory components")
        return value


class SearchWebInput(BaseModel):
    """Arguments accepted by the web-research skill."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=300)
    max_results: int = Field(default=5, ge=1, le=10)


def list_papers() -> list[str]:
    """List PDFs that are safely available to the agent."""
    DEFAULT_PAPERS_DIR.mkdir(exist_ok=True)
    return sorted(path.name for path in DEFAULT_PAPERS_DIR.glob("*.pdf"))


def _score(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def read_pdf(file_name: str, question: str = "", max_pages: int = 12, start_page: int = 1) -> dict[str, Any]:
    """Read a local PDF and return the passages most relevant to a question."""
    args = ReadPdfInput(file_name=file_name, question=question, max_pages=max_pages, start_page=start_page)
    path = DEFAULT_PAPERS_DIR / args.file_name
    if not path.exists():
        return {"ok": False, "error": f"PDF not found: {args.file_name}", "available": list_papers()}

    try:
        document = pymupdf.open(path)
        total_pages = len(document)
        if args.start_page > total_pages:
            document.close()
            return {'ok': False, 'error': 'start_page exceeds total_pages', 'total_pages': total_pages}
        pages: list[dict[str, Any]] = []
        end_page = min(total_pages, args.start_page - 1 + min(args.max_pages, 12))
        for index in range(args.start_page - 1, end_page):
            page = document[index]
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": index + 1, "text": text})
        document.close()
    except Exception as exc:  # keep tool errors safe for the agent
        return {"ok": False, "error": f"Could not parse PDF: {exc}"}

    evidence = pages
    clipped = [
        {"page": item["page"], "excerpt": item["text"][:14000], 'truncated': len(item['text']) > 14000}
        for item in evidence
    ]
    return {
        "ok": bool(pages),
        "error": None if pages else 'No extractable text; this PDF may require OCR.',
        "total_pages": total_pages,
        "next_page": end_page + 1 if end_page < total_pages else None,
        "source": args.file_name,
        "pages_scanned": len(pages),
        "evidence": clipped,
    }


async def search_web_async(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the public DuckDuckGo Instant Answer API without storing user data."""
    args = SearchWebInput(query=query, max_results=max_results)
    url = "https://api.duckduckgo.com/"
    params = {"q": args.query, "format": "json", "no_html": "1", "no_redirect": "1"}
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Web search failed: {exc}"}

    results: list[dict[str, str]] = []
    if payload.get("AbstractText"):
        results.append({
            "title": payload.get("Heading", args.query),
            "url": payload.get("AbstractURL", ""),
            "snippet": payload["AbstractText"],
        })
    for topic in payload.get("RelatedTopics", []):
        if "Topics" in topic:
            topic_items = topic["Topics"]
        else:
            topic_items = [topic]
        for item in topic_items:
            text = item.get("Text")
            first_url = item.get("FirstURL")
            if text and first_url:
                results.append({"title": text.split(" - ")[0], "url": first_url, "snippet": text})
            if len(results) >= args.max_results:
                break
        if len(results) >= args.max_results:
            break
    return {"ok": True, "query": args.query, "results": results[: args.max_results]}


def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Synchronous wrapper used by the command-line agent."""
    import asyncio

    return asyncio.run(search_web_async(query, max_results))


FUNCTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_pdf",
            "description": "Read a PDF from the local papers folder and return page-numbered evidence. Use it for questions about a local paper.",
            "parameters": ReadPdfInput.model_json_schema(),
            "strict": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the public web for factual background or related work. Return source URLs and snippets.",
            "parameters": SearchWebInput.model_json_schema(),
            "strict": False,
        },
    },
]


def call_tool(name: str, raw_arguments: str) -> str:
    """Execute only the agent's allow-listed tools and serialize a safe result."""
    try:
        arguments = json.loads(raw_arguments)
        if name == "read_pdf":
            result = read_pdf(**arguments)
        elif name == "search_web":
            result = search_web(**arguments)
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"ok": False, "error": f"Tool input error: {exc}"}
    return json.dumps(result, ensure_ascii=False)
