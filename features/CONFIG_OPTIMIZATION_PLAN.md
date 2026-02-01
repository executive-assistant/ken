# Configuration File Optimization Plan

## Executive Summary

Analysis of current configuration files (`.env`, `.env.example`, `config.yaml`) against Python/Docker industry best practices.

**Current Status:** Configuration is functional but has several areas for improvement in organization, security, and maintainability.

---

## Current Configuration Files

### 1. `.env` (Actual - contains secrets)
**Location:** `docker/.env`

**Issues Found:**
- ⚠️ **SECRETS EXPOSED**: Contains real API keys in version control
  - `ANTHROPIC_API_KEY=sk-ant-api03-...` (exposed!)
  - `OPENAI_API_KEY=sk-proj-...` (exposed!)
  - `ZHIPUAI_API_KEY=fe487af6...` (exposed!)
  - `OLLAMA_CLOUD_API_KEY=046845d8...` (exposed!)
  - `TELEGRAM_BOT_TOKEN=8371069399:...` (multiple tokens exposed!)

- ❌ **DEPRECATED CONFIGURATION**: Still references `SEARXNG_HOST` (removed in latest commit)
  ```bash
  SEARXNG_HOST=https://searxng.research-stack.gongchatea.com.au
  ```

- ⚠️ **INCONSISTENT ORGANIZATION**: Mix of commented/uncommented values
  ```bash
  # Some are commented:
  # DEFAULT_LLM_PROVIDER=anthropic

  # Others are not:
  EXECUTIVE_ASSISTANT_CHANNELS=telegram,http
  TELEGRAM_BOT_TOKEN=8371069399:...
  ```

- ⚠️ **DUPLICATE VALUES**: Multiple bot tokens listed
  ```bash
  TELEGRAM_BOT_TOKEN=8371069399:... # jen_ea_bot
  # TELEGRAM_BOT_TOKEN=8416140352:... # ken_ea_bot
  # TELEGRAM_BOT_TOKEN=8547541352:... # executive_assistant_ai_bot
  ```

- ⚠️ **AGENTS_NAME BURIED**: `AGENT_NAME=Jen` is hard to find in channel section

### 2. `.env.example` (Template)
**Location:** `docker/.env.example`

**Strengths:**
- ✅ Well-organized with clear sections
- ✅ Good documentation
- ✅ No actual secrets (all placeholders)

**Issues Found:**
- ⚠️ **OUTDATED**: References removed SearXNG
  ```bash
  # Web Search (SearXNG) - only needed if SEARCH_PROVIDER=searxng
  SEARXNG_HOST=https://your-searxng-instance.com
  ```

- ⚠️ **INCOMPLETE DOCUMENTATION**: Missing some config.yaml options
  - No mention of `config.yaml` structure
  - No guidance on when to use .env vs config.yaml

### 3. `config.yaml` (Application Defaults)
**Location:** `docker/config.yaml`

**Strengths:**
- ✅ Excellent hierarchical structure
- ✅ Comprehensive documentation
- ✅ Good separation of concerns (llm, storage, middleware, etc.)
- ✅ Clear comments explaining token counts and ratios

**Issues Found:**
- ⚠️ **INCONSISTENT NAMING**: Mix of snake_case and kebab-case
  ```yaml
  storage:
    checkpoint: postgres        # snake_case
    shared_root: "./data/shared" # snake_case

  vector_store:                 # section name is snake_case
    embedding_model: "..."

  # But then:
  storage_paths:                # snake_case
    admins_root: ./data/admins  # snake_case
  ```

  Actually, this is consistent - but there's `groups_root` mentioned that doesn't match the code (code uses `admins_root`)

- ⚠️ **OBSOLETE REFERENCE**: `groups_root` in paths (line 59) - code uses `admins_root` only
  ```yaml
  paths:
    shared_root: "./data/shared"
    groups_root: "./data/groups"  # ❌ NOT USED in code
    users_root: "./data/users"
  ```

- ⚠️ **MISSING VALUE**: `max_file_size_mb: 10` but code defaults to 10MB, should be explicit
- ⚠️ **DUPLICATE CONFIGURATION**: Storage paths in both `storage.paths` and top-level `storage_paths`

---

## Industry Best Practices

### Python Applications

**Standard pattern:**
```
myapp/
├── config/
│   ├── __init__.py
│   ├── default.yaml          # Application defaults
│   ├── development.yaml       # Dev-specific overrides
│   ├── production.yaml        # Prod-specific overrides
│   └── test.yaml             # Test-specific overrides
├── .env.example              # Template (committed)
├── .env                      # Actual secrets (NOT committed)
├── .env.local                # Local overrides (NOT committed)
└── .gitignore                # Excludes .env and .env.local
```

**Best practices:**
1. ✅ **12-Factor App**: Environment-specific config in environment variables
2. ✅ **Layered configuration**: defaults → config files → env vars
3. ✅ **Validation**: Pydantic settings with clear error messages
4. ✅ **Documentation**: `.env.example` with all possible variables
5. ✅ **Security**: Never commit `.env` or `.env.local`

### Docker/Containerized Apps

**Standard pattern:**
```
docker/
├── Dockerfile
├── docker-compose.yml
├── .env.example              # Template (committed)
├── .env                      # Actual secrets (NOT committed)
└── config/
    ├── app.yaml              # Application config
    ├── development.yaml
    └── production.yaml
```

**Best practices:**
1. ✅ **Secret management**: Use Docker secrets or external vault (not .env in prod)
2. ✅ **Environment-specific compose files**: `docker-compose.dev.yml`, `docker-compose.prod.yml`
3. ✅ **Configuration as Code**: Version control all config files except secrets

---

## Recommendations

### Priority 1: Security (CRITICAL)

**Issue:** Real API keys exposed in `.env` file in version control

**Recommendation:**
1. **Immediately rotate all exposed API keys:**
   - Anthropic API key
   - OpenAI API key
   - Zhipu AI API key
   - Ollama Cloud API key
   - All Telegram bot tokens

2. **Remove `.env` from git history:**
   ```bash
   # Remove from history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch docker/.env" HEAD

   # Or use BFG Repo-Cleaner
   # Force push to all remotes
   ```

3. **Add to `.gitignore`:**
   ```gitignore
   # Environment variables
   docker/.env
   docker/.env.local
   docker/.env.*.local
   .env
   .env.local
   ```

### Priority 2: Clean Up (HIGH)

**1. Remove obsolete SearXNG references:**

From `.env`:
```bash
# REMOVE:
SEARXNG_HOST=https://searxng.research-stack.gongchatea.com.au
```

From `.env.example`:
```bash
# REMOVE:
# Web Search (SearXNG) - only needed if SEARCH_PROVIDER=searxng
SEARXNG_HOST=https://your-searxng-instance.com
```

**2. Remove unused `groups_root` from config.yaml:**

```yaml
storage:
  paths:
    shared_root: "./data/shared"
    # groups_root: "./data/groups"  # ❌ REMOVE THIS
    users_root: "./data/users"
```

**3. Consolidate storage paths:**

Either keep in `storage.paths` OR top-level `storage_paths`, not both.

**Recommendation:** Keep in `storage.paths` for consistency.

### Priority 3: Organization (MEDIUM)

**1. Standardize file structure:**

```
executive_assistant/
├── config/
│   ├── __init__.py
│   ├── default.yaml          # From docker/config.yaml
│   ├── development.yaml       # New (optional)
│   └── production.yaml        # New (optional)
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example          # Keep here
│   └── .env.production       # Production template (optional)
└── .gitignore                # Add .env rules
```

**2. Improve `.env.example` structure:**

**Current:** Good but can be better

**Proposed:**
```bash
# ============================================================================
# Executive Assistant Environment Variables
# ============================================================================
# Copy this file to .env and fill in your values.
# DO NOT commit .env to version control!
#
# Configuration Priority (higher overrides lower):
# 1. Environment variables (.env)
# 2. config.yaml (docker/config.yaml)
# 3. Python defaults (settings.py)
# ============================================================================

# ============================================================================
# REQUIRED: LLM Provider
# ============================================================================
# Choose your LLM provider: anthropic, openai, zhipu, ollama
DEFAULT_LLM_PROVIDER=openai

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-xxx

# OpenAI
# OPENAI_API_KEY=sk-xxx

# Zhipu AI
# ZHIPUAI_API_KEY=xxx

# Ollama (cloud or local)
# OLLAMA_MODE=cloud
# OLLAMA_CLOUD_API_KEY=xxx
# OLLAMA_LOCAL_URL=http://localhost:11434

# ============================================================================
# REQUIRED: Channels
# ============================================================================
EXECUTIVE_ASSISTANT_CHANNELS=telegram,http

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token-here
# TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
# TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# ============================================================================
# REQUIRED: Database
# ============================================================================
POSTGRES_PASSWORD=your-secure-password-here
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_USER=executive_assistant
# POSTGRES_DB=executive_assistant_db

# ============================================================================
# REQUIRED: External Services
# ============================================================================
# Firecrawl (web scraping + search)
FIRECRAWL_API_KEY=fc-your-key-here
# FIRECRAWL_API_URL=https://api.firecrawl.dev

# ============================================================================
# OPTIONAL: Overrides
# ============================================================================
# Override config.yaml values if needed

# Agent name
# AGENT_NAME=Executive Assistant

# Log level
# LOG_LEVEL=DEBUG

# Time zone
# TZ=UTC

# Storage paths (for custom deployments)
# USERS_ROOT=./data/users
# SHARED_ROOT=./data/shared
# ADMINS_ROOT=./data/admins
```

**3. Add validation in settings.py:**

Already using Pydantic - ✅ Good!

**Add explicit warnings for missing required keys:**

```python
@field_validator("FIRECRAWL_API_KEY")
@classmethod
def check_firecrawl_key(cls, v):
    if not v:
        raise ValueError(
            "FIRECRAWL_API_KEY is required. "
            "Set it in .env or get one from https://firecrawl.dev"
        )
    return v
```

### Priority 4: Documentation (LOW)

**1. Add CONFIGURATION.md:**

Create `docs/CONFIGURATION.md` with:
- Overview of configuration system
- How to set up `.env`
- How to customize `config.yaml`
- Environment-specific configs (dev/staging/prod)
- Common configuration scenarios

**2. Update README.md:**

Add clear section on configuration:
```markdown
## Configuration

Executive Assistant uses a layered configuration system:

1. **Environment Variables** (`.env`) - Secrets and overrides
2. **Config File** (`config.yaml`) - Application defaults
3. **Code Defaults** - Fallback values

### Quick Start

1. Copy example environment:
   ```bash
   cp docker/.env.example docker/.env
   ```

2. Edit `docker/.env` and add your API keys

3. (Optional) Customize `docker/config.yaml`

### Required Variables

- `FIRECRAWL_API_KEY` - Web search/scraping
- `TELEGRAM_BOT_TOKEN` - Telegram channel
- One LLM provider API key (Anthropic/OpenAI/Zhipu/Ollama)
```

**3. Add schema validation:**

Generate JSON schema from Pydantic settings for IDE autocomplete:
```python
# In settings.py
if __name__ == "__main__":
    import json
    from executive_assistant.config.settings import Settings
    schema = Settings.model_json_schema()
    with open("config-schema.json", "w") as f:
        json.dump(schema, f, indent=2)
```

---

## Proposed Implementation Plan

### Phase 1: Security Fixes (IMMEDIATE)
- [ ] Rotate all exposed API keys
- [ ] Remove `.env` from git history
- [ ] Add `.env` to `.gitignore`
- [ ] Commit cleanup

### Phase 2: Cleanup (HIGH PRIORITY)
- [ ] Remove SearXNG references from `.env` and `.env.example`
- [ ] Remove `groups_root` from `config.yaml`
- [ ] Consolidate storage paths in `config.yaml`
- [ ] Clean up duplicate bot tokens in `.env`

### Phase 3: Organization (MEDIUM PRIORITY)
- [ ] Reorganize files into `config/` directory
- [ ] Improve `.env.example` structure
- [ ] Add validation for required keys
- [ ] Add `.env.production.example` template

### Phase 4: Documentation (LOW PRIORITY)
- [ ] Create `docs/CONFIGURATION.md`
- [ ] Update README with configuration section
- [ ] Add config schema generation script
- [ ] Add environment-specific config examples

---

## Alternative: Minimal Changes

If you want a simpler approach, **minimum recommended changes:**

1. **Security only:**
   - Rotate API keys
   - Remove `.env` from git history
   - Add to `.gitignore`

2. **Cleanup only:**
   - Remove SearXNG references
   - Remove `groups_root`
   - Clean up duplicate tokens

3. **Documentation only:**
   - Update `.env.example`
   - Add CONFIGURATION guide

---

## Risk Assessment

| Change | Risk | Impact | Effort |
|--------|------|--------|--------|
| Rotate API keys | Medium | High security | Medium |
| Reorganize files | Low | Better organization | High |
| Consolidate paths | Low | Less confusion | Low |
| Improve docs | None | Better DX | Medium |
| Add validation | Low | Better error messages | Low |

---

## Tools That Could Help

1. **Configuration management:**
   - `python-dotenv` (already using) ✅
   - `pydantic-settings` (already using) ✅
   - `dynaconf` (optional - for more complex configs)

2. **Secret management:**
   - Docker secrets (for production)
   - HashiCorp Vault (enterprise)
   - AWS Secrets Manager (cloud)
   - 1Password Secrets Automation (developer-friendly)

3. **Validation:**
   - Pydantic (already using) ✅
   - `python-env-schema` (optional)

---

## Questions for User

1. **Secret Management:**
   - Do you want to use Docker secrets in production?
   - Or stick with `.env` files (easier for development)?

2. **File Organization:**
   - Should we move to `config/` directory structure?
   - Or keep current structure with just improvements?

3. **Environment-Specific Configs:**
   - Do you need separate configs for dev/staging/production?
   - Or is single environment sufficient?

4. **Validation Strictness:**
   - Should app fail to start if required keys missing?
   - Or provide helpful warnings and continue with defaults?

5. **Documentation:**
   - How detailed should CONFIGURATION.md be?
   - Quick reference vs comprehensive guide?

---

## Next Steps

**Waiting for user decision on:**
1. Implementation approach (minimal vs comprehensive)
2. Secret management strategy
3. Whether to reorganize file structure

**Once approved:**
1. Create implementation plan based on chosen approach
2. Implement changes incrementally
3. Test each phase
4. Update documentation
