# Restarting Cassey

**Important:** When restarting Cassey, always restart the entire system:

```bash
# 1. Stop everything
docker compose down
pkill -f "python.*cassey"

# 2. Start docker (waits for postgres to be ready)
docker compose up -d

# 3. Run any new migrations
psql postgresql://cassey:cassey_password@localhost:5432/cassey_db -f migrations/XXX_new_migration.sql

# 4. Start cassey
nohup uv run python -m cassey.main > cassey.log 2>&1 &
```

**Why?** The database, scheduler, and workers are all interconnected. A full restart ensures clean state.

**To verify:**
```bash
# Check docker
docker compose ps

# Check cassey process
ps aux | grep "cassey.main"

# Check logs
tail -f cassey.log
```
