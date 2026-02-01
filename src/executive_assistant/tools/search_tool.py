"""Web search tool supporting multiple providers.

Supports:
- SearXNG (self-hosted metasearch engine)
- Firecrawl (cloud API with content extraction)
"""

from langchain_core.tools import tool

from executive_assistant.config.settings import settings


def _get_searxng_params():
    """Get SearXNG connection parameters from settings."""
    searxng_url = settings.SEARXNG_HOST
    if not searxng_url:
        raise ValueError(
            "SearXNG host not configured. Please set SEARXNG_HOST in .env file."
        )
    return {"searx_host": searxng_url}


def _search_with_searxng(query: str, num_results: int) -> str:
    """Search using SearXNG metasearch engine."""
    try:
        params = _get_searxng_params()
    except ValueError as e:
        return f"Configuration error: {e}"

    # Import here to avoid errors if not installed
    try:
        from langchain_community.utilities import SearxSearchWrapper
    except ImportError:
        return "Error: langchain-community not installed. Run: uv add langchain-community"

    # Limit num_results
    num_results = max(1, min(20, int(num_results)))

    try:
        # Create SearXNG wrapper
        search = SearxSearchWrapper(**params)

        # Perform search
        results = search.results(query, num_results)

        if not results:
            return f"No results found for: {query}"

        # Format results
        output_lines = [f"Found {len(results)} result(s) for: {query}\n"]

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("link", result.get("url", "No URL"))
            snippet = result.get("snippet", result.get("body", ""))

            # Truncate snippet if too long
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."

            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   URL: {url}")
            if snippet:
                output_lines.append(f"   {snippet}")
            output_lines.append("")

        return "\n".join(output_lines).strip()

    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


async def _search_with_firecrawl(query: str, num_results: int, scrape_results: bool = False) -> str:
    """Search using Firecrawl API."""
    # Import here to avoid circular dependency
    from executive_assistant.tools.firecrawl_tool import firecrawl_search

    try:
        result = await firecrawl_search.invoke({
            "query": query,
            "num_results": num_results,
            "sources": "web",
            "scrape_results": scrape_results,
        })
        return result
    except Exception as e:
        return f"Firecrawl search error: {type(e).__name__}: {e}"


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """Search the web using the configured search provider.

    Provider is set via SEARCH_PROVIDER environment variable:
    - "searxng" (default): Self-hosted metasearch engine
    - "firecrawl": Cloud API with content extraction

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5, max: 20)

    Returns:
        Search results as formatted text with titles, URLs, and snippets.
        Firecrawl can optionally include full content from results.

    Examples:
        >>> search_web("python async await tutorial")
        "Found 5 results:\\n1. Python Async Await - Real Python..."

        >>> search_web("latest AI news", num_results=3)
        "Found 3 results:\\n1. ..."
    """
    # Check configured provider
    provider = settings.SEARCH_PROVIDER

    if provider == "firecrawl":
        # Use Firecrawl (async)
        import asyncio
        try:
            return asyncio.run(_search_with_firecrawl(query, num_results))
        except Exception as e:
            # Fallback to SearXNG if Firecrawl fails
            if settings.SEARXNG_HOST:
                return f"Firecrawl search failed, trying SearXNG...\n\n{_search_with_searxng(query, num_results)}"
            return f"Search error (Firecrawl unavailable and no SearXNG configured): {e}"
    elif provider == "searxng":
        # Use SearXNG (sync)
        return _search_with_searxng(query, num_results)
    else:
        return f"Error: Invalid SEARCH_PROVIDER '{provider}'. Use 'searxng' or 'firecrawl'."


def get_search_tools() -> list:
    """Get web search tools."""
    return [search_web]
