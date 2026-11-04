"""MCP server exposing the agent's two skills over stdio."""

from mcp.server.fastmcp import FastMCP

from agent.tools import list_papers, read_pdf, search_web_async

mcp = FastMCP("Research Paper Assistant")


@mcp.tool()
def available_papers() -> list[str]:
    """List local PDF files currently available in the papers folder."""
    return list_papers()


@mcp.tool()
def read_local_pdf(file_name: str, question: str = "", max_pages: int = 12) -> dict:
    """Read a local PDF and return page-numbered excerpts relevant to the question."""
    return read_pdf(file_name=file_name, question=question, max_pages=max_pages)


@mcp.tool()
async def web_research(query: str, max_results: int = 5) -> dict:
    """Search public web sources for background knowledge and related research."""
    return await search_web_async(query=query, max_results=max_results)


if __name__ == "__main__":
    mcp.run(transport="stdio")
