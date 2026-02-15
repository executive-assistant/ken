from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain_core.tools import tool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config.settings import Settings, get_settings
from src.llm import get_llm

if TYPE_CHECKING:
    from langgraph.graph import CompiledStateGraph


@dataclass
class AgentContext:
    user_id: str
    project_id: str | None = None


def _make_user_backend_factory(user_id: str, data_path: Path):
    """Create a backend factory with user-isolated filesystem routes.

    Returns a factory function that receives runtime from create_deep_agent.

    Routes:
        /user/*     → /data/users/{user_id}/ (user's private data)
        /shared/*   → /data/shared/ (team-shared resources)
        /*          → StateBackend (ephemeral workspace, per-thread)

    The agent can organize its own structure within /user/ (e.g., /user/memories/)

    Args:
        user_id: User identifier for isolation
        data_path: Base data path (e.g., /data)

    Returns:
        Backend factory function for create_deep_agent
    """
    user_dir = data_path / "users" / user_id
    shared_dir = data_path / "shared"

    user_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.mkdir(parents=True, exist_ok=True)

    def make_backend(runtime) -> CompositeBackend:
        return CompositeBackend(
            default=StateBackend(runtime),
            routes={
                "/user/": FilesystemBackend(
                    root_dir=str(user_dir),
                    virtual_mode=True,
                ),
                "/shared/": FilesystemBackend(
                    root_dir=str(shared_dir),
                    virtual_mode=True,
                ),
            },
        )

    return make_backend


@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information.

    Uses Tavily if configured, otherwise falls back to Firecrawl.

    Args:
        query: The search query

    Returns:
        Search results as a formatted string
    """
    settings = get_settings()

    if settings.tavily_api_key:
        return _web_search_tavily(query, settings.tavily_api_key)
    elif settings.firecrawl_api_key:
        return _web_search_firecrawl(query, settings.firecrawl_api_key, settings.firecrawl_base_url)
    else:
        return "Error: No search API configured. Set either TAVILY_API_KEY or FIRECRAWL_API_KEY in your .env file."


def _web_search_tavily(query: str, api_key: str) -> str:
    """Search using Tavily API."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    results = client.search(query, max_results=5)

    if not results.get("results"):
        return "No results found."

    output = []
    for r in results["results"]:
        output.append(
            f"**{r.get('title', 'Untitled')}**\n{r.get('url', '')}\n{r.get('content', '')}\n"
        )

    return "\n---\n".join(output)


def _web_search_firecrawl(query: str, api_key: str, base_url: str) -> str:
    """Search using Firecrawl API."""
    import httpx

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"query": query, "limit": 5}

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{base_url}/search", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = data.get("data", data.get("results", []))
        if not results:
            return "No results found."

        output = []
        for r in results[:5]:
            title = r.get("title", r.get("metadata", {}).get("title", "Untitled"))
            url = r.get("url", r.get("metadata", {}).get("sourceURL", ""))
            content = r.get("description", r.get("markdown", ""))[:300]
            output.append(f"**{title}**\n{url}\n{content}\n")

        return "\n---\n".join(output)
    except httpx.HTTPStatusError as e:
        return f"Error searching: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error searching: {e}"


@tool
def web_scrape(url: str) -> str:
    """Scrape content from a web page using Firecrawl.

    Args:
        url: The URL to scrape

    Returns:
        The page content as markdown
    """
    import httpx

    settings = get_settings()
    api_key = settings.firecrawl_api_key
    base_url = settings.firecrawl_base_url

    if not api_key:
        return "Error: FIRECRAWL_API_KEY not configured. Set it in your .env file."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url, "formats": ["markdown"]}

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{base_url}/scrape", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        if "data" in data and "markdown" in data["data"]:
            return data["data"]["markdown"]
        return str(data.get("data", data))
    except httpx.HTTPStatusError as e:
        return f"Error scraping {url}: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error scraping {url}: {e}"


@tool
def web_crawl(url: str, max_pages: int = 10) -> str:
    """Crawl a website starting from a URL using Firecrawl.

    Args:
        url: The starting URL to crawl
        max_pages: Maximum number of pages to crawl (default: 10)

    Returns:
        List of crawled URLs and their content summaries
    """
    import httpx

    settings = get_settings()
    api_key = settings.firecrawl_api_key
    base_url = settings.firecrawl_base_url

    if not api_key:
        return "Error: FIRECRAWL_API_KEY not configured. Set it in your .env file."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url, "limit": max_pages, "scrapeOptions": {"formats": ["markdown"]}}

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{base_url}/crawl", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("data", [])[:max_pages]:
            source_url = item.get("metadata", {}).get("sourceURL", item.get("url", "Unknown"))
            md_content = item.get("markdown", "")[:500]
            results.append(f"**{source_url}**\n{md_content}...\n")

        return "\n---\n".join(results) if results else "No pages crawled."
    except httpx.HTTPStatusError as e:
        return f"Error crawling {url}: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error crawling {url}: {e}"


@tool
def web_map(url: str, search_query: str | None = None) -> str:
    """Map a website to discover all URLs. Optionally filter by search query.

    Args:
        url: The base URL to map
        search_query: Optional search query to filter URLs (e.g., "blog", "docs")

    Returns:
        List of discovered URLs
    """
    import httpx

    settings = get_settings()
    api_key = settings.firecrawl_api_key
    base_url = settings.firecrawl_base_url

    if not api_key:
        return "Error: FIRECRAWL_API_KEY not configured. Set it in your .env file."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url}
    if search_query:
        payload["search"] = search_query

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{base_url}/map", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        links = data.get("links", [])
        if not links:
            return "No URLs found."

        return "\n".join(f"- {link}" for link in links[:50])
    except httpx.HTTPStatusError as e:
        return f"Error mapping {url}: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error mapping {url}: {e}"


def _get_model(settings: Settings):
    """Get the LLM model from settings."""
    provider, model = settings.llm.get_default_provider_model()
    return get_llm(provider=provider, model=model)


def _collect_skill_paths(settings: Settings, user_id: str) -> list[str]:
    """Collect skill paths from shared and user directories.

    Priority:
    1. Team skills - /data/shared/skills/
    2. User skills - /data/users/{user_id}/skills/
    """
    skill_paths = []

    team_skills = settings.shared_path / "skills"
    if team_skills.exists():
        skill_paths.append(str(team_skills))

    user_skills = settings.get_user_path(user_id) / "skills"
    if user_skills.exists():
        skill_paths.append(str(user_skills))

    return skill_paths


SUBAGENTS = [
    {
        "name": "coder",
        "description": "Write, debug, and refactor code. Use for programming tasks.",
        "system_prompt": "You are a specialized coding assistant. Write clean, well-documented code.",
    },
    {
        "name": "researcher",
        "description": "Search the web and gather information. Use for research tasks.",
        "system_prompt": "You are a specialized research assistant. Gather and synthesize information from web search and scraping tools.",
    },
    {
        "name": "planner",
        "description": "Break down complex tasks into actionable steps. Use for planning.",
        "system_prompt": "You are a specialized planning assistant. Analyze and organize complex tasks into manageable steps.",
    },
]


def _build_system_prompt(agent_name: str) -> str:
    """Build the system prompt with the agent's name."""
    return f"""You are {agent_name}, a deep agent with executive assistant capabilities.

## Filesystem Structure
- `/user/` - Your private data directory (organize as needed: memories, projects, notes)
- `/shared/` - Team-shared resources (skills, knowledge base, templates)
- `/workspace/` - Ephemeral workspace (cleared between threads)

## Capabilities
- **Planning**: Break down complex tasks using the todo list
- **File Operations**: Read, write, edit files in /user/ and /shared/
- **Web Search**: Use web_search to find current information
- **Web Scraping**: Use web_scrape, web_crawl, web_map for web data
- **Subagents**: Delegate specialized work to coder, researcher, or planner

## Guidelines
1. Organize user data in /user/ (e.g., /user/memories/, /user/projects/)
2. Check /shared/ for team resources and skills
3. Save important information for future sessions
4. Ask for clarification when uncertain about user needs
"""


@asynccontextmanager
async def create_ken_agent(
    settings: Settings | None = None,
    user_id: str = "default",
    skills: list[str] | None = None,
) -> AsyncIterator[CompiledStateGraph]:
    """Create an Executive Assistant deep agent with Postgres checkpoints and user-isolated memory.

    Args:
        settings: Application settings (defaults to global settings)
        user_id: User identifier for memory isolation
        skills: Override skill paths (if None, uses three-tier skill system)

    Yields:
        Compiled LangGraph agent ready for invocation
    """
    if settings is None:
        settings = get_settings()

    model = _get_model(settings)
    db_uri = settings.database_url
    agent_name = settings.agent_name

    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        await checkpointer.setup()

        skill_paths = skills if skills is not None else _collect_skill_paths(settings, user_id)

        agent_kwargs: dict[str, Any] = {
            "name": f"ea-{user_id}",
            "model": model,
            "system_prompt": _build_system_prompt(agent_name),
            "checkpointer": checkpointer,
            "backend": _make_user_backend_factory(user_id, settings.data_path),
            "tools": [web_search, web_scrape, web_crawl, web_map],
            "subagents": SUBAGENTS,
        }

        if skill_paths:
            agent_kwargs["skills"] = skill_paths

        agent = create_deep_agent(**agent_kwargs)

        yield agent
