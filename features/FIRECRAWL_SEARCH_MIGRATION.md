# Firecrawl Search Migration Guide

## Overview

Executive Assistant now supports **two web search providers**:

1. **SearXNG** (default) - Self-hosted metasearch engine
2. **Firecrawl** (new) - Cloud API with content extraction

## Why Firecrawl?

### Advantages Over SearXNG

| Feature | SearXNG | Firecrawl |
|---------|---------|-----------|
| **Setup** | Deploy/maintain server | Just API key |
| **Dependencies** | `langchain-community` | None (already using for scrape) |
| **Result Quality** | Variable (depends on instance) | Premium sources |
| **Content Extraction** | Need separate scrape | Built-in! |
| **Advanced Filters** | Basic | Location, time, categories |
| **Sources** | Web only | Web, News, Images |
| **Categories** | None | GitHub, Research, PDF |

### Key Benefit: **Remove One Dependency**

By switching to Firecrawl, you can:
- ✅ Remove SearXNG server dependency
- ✅ Potentially remove `langchain-community` dependency
- ✅ Simplify your infrastructure
- ✅ Get better search results with content extraction

## Cost Comparison

### SearXNG
- **API Cost**: Free (self-hosted)
- **Infrastructure**: Server costs ($5-20/month for small instance)
- **Maintenance**: Updates, monitoring, scaling

### Firecrawl
- **API Cost**: 2 credits per 10 search results
- **With scraping**: +1 credit per result (basic scrape)
- **Example**: 10 searches with 5 results each = 10-20 credits depending on scraping
- **Pricing**: Check [Firecrawl Pricing](https://www.firecrawl.dev/pricing)

**Break-even analysis**: If you're paying $10+/month for SearXNG hosting, Firecrawl may be cheaper.

## Configuration

### Option 1: Use SearXNG (Default)

```bash
# docker/.env
SEARCH_PROVIDER=searxng
SEARXNG_HOST=https://your-searxng-instance.com
```

### Option 2: Use Firecrawl (New)

```bash
# docker/.env
SEARCH_PROVIDER=firecrawl
FIRECRAWL_API_KEY=fc-your-api-key
# SEARXNG_HOST not needed
```

### Option 3: Firecrawl with Fallback

```bash
# docker/.env
SEARCH_PROVIDER=firecrawl
FIRECRAWL_API_KEY=fc-your-api-key
SEARXNG_HOST=https://backup-searxng.example.com  # Fallback
```

If Firecrawl fails, the system automatically falls back to SearXNG (if configured).

## Migration Steps

### Phase 1: Test Firecrawl (Current Release)

1. **Get Firecrawl API Key**
   ```bash
   # Sign up at https://www.firecrawl.dev
   # Copy your API key
   ```

2. **Configure in Development**
   ```bash
   # docker/.env
   SEARCH_PROVIDER=firecrawl
   FIRECRAWL_API_KEY=fc-your-key
   ```

3. **Test Search Functionality**
   ```bash
   # Run test script
   uv run python tests/poc/test_firecrawl_search.py

   # Or test manually via Telegram/HTTP
   /message Search for "python async tutorial"
   ```

4. **Monitor Usage**
   - Check Firecrawl dashboard for credits used
   - Verify result quality meets your needs

### Phase 2: Switch Default (Future Release)

Once you've verified Firecrawl works well:

1. **Update Configuration**
   ```bash
   # config.yaml or docker/.env
   SEARCH_PROVIDER=firecrawl  # Will become default
   ```

2. **Remove SearXNG Server** (Optional)
   ```bash
   # Stop SearXNG container
   docker compose stop searxng

   # Remove from docker-compose.yml
   ```

3. **Remove Dependency** (Optional)
   ```bash
   # If no longer using SearXNG
   uv remove langchain-community
   ```

### Phase 3: Full Migration (Later)

- Make Firecrawl the only option
- Remove SearXNG code entirely
- Simplify codebase

## Firecrawl Search Features

### Basic Search
```python
result = await firecrawl_search.invoke({
    "query": "python async tutorial",
    "num_results": 5,
    "sources": "web",
})
```

### Search with Content Extraction
```python
result = await firecrawl_search.invoke({
    "query": "what is langchain",
    "num_results": 3,
    "scrape_results": True,  # Extracts full content!
})
```

### News Search
```python
result = await firecrawl_search.invoke({
    "query": "AI news",
    "sources": "news",
    "num_results": 10,
})
```

### Image Search
```python
result = await firecrawl_search.invoke({
    "query": "sunset wallpaper",
    "sources": "images",
    "num_results": 5,
})
```

### GitHub Search
```python
result = await firecrawl_search.invoke({
    "query": "web scraping python",
    "categories": ["github"],
    "num_results": 10,
})
```

### Research Search
```python
result = await firecrawl_search.invoke({
    "query": "machine learning transformers",
    "categories": ["research"],
    "num_results": 10,
})
```

### Time-Based Search
```python
result = await firecrawl_search.invoke({
    "query": "firecrawl updates",
    "num_results": 10,
    "tbs": "qdr:w",  # Past week
})
```

## Backward Compatibility

✅ **Fully backward compatible**

- SearXNG remains the default
- Existing installations continue working
- No breaking changes
- Gradual migration path

## FAQ

### Q: Will I break anything if I switch to Firecrawl?

**A**: No. The `search_web` tool interface remains the same. Only the backend implementation changes.

### Q: Can I use both SearXNG and Firecrawl?

**A**: Yes! Configure both, and Firecrawl will be used with automatic fallback to SearXNG if it fails.

### Q: What happens if I exceed my Firecrawl credits?

**A**: The search will fail with an error. Configure SearXNG as a fallback if needed.

### Q: Is Firecrawl faster than SearXNG?

**A**: Usually yes. Firecrawl uses optimized premium sources. SearXNG speed depends on your instance and network.

### Q: Can I remove SearXNG completely?

**A**: Not yet. SearXNG is still the default and is kept as a fallback. In a future release, we'll make Firecrawl the default and eventually remove SearXNG.

### Q: What about the `langchain-community` dependency?

**A**: Currently still required for SearXNG support. Once we make Firecrawl the default, you can optionally remove it if you don't use other `langchain-community` features.

## Testing

Before switching to Firecrawl in production:

1. **Run the test script**
   ```bash
   uv run python tests/poc/test_firecrawl_search.py
   ```

2. **Test in development environment**
   - Try various search queries
   - Check result quality
   - Verify content extraction works
   - Monitor credit usage

3. **Monitor costs**
   - Check Firecrawl dashboard
   - Calculate expected monthly cost
   - Compare with SearXNG hosting costs

## Summary

**Current State**: SearXNG default, Firecrawl optional
**Recommended**: Test Firecrawl in development
**Future**: Firecrawl becomes default, SearXNG deprecated

**Action Items**:
- ✅ Code complete (Phase 1)
- ✅ Test Firecrawl with your use cases
- ✅ Monitor costs and quality
- ⏳ Decide on migration timeline
- ⏳ Plan for SearXNG removal

---

**Need Help?**
- Firecrawl Docs: https://docs.firecrawl.dev
- Firecrawl Support: https://discord.gg/gSmWdAkdwd
- GitHub Issues: https://github.com/firecrawl/firecrawl
