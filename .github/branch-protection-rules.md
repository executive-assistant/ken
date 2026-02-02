# Branch Protection Rules

This document describes the branch protection policies for the Executive Assistant repository.

## Protected Branches

### `main` Branch

**Status:** 🔒 Protected

**Rules:**
- ✅ Require pull request before merging
  - Allow: Maintainers only
- ✅ Require status checks to pass before merging
  - All required checks must pass
- ✅ Require branches to be up to date before merging
  - Branch must be syncronized with main
- ❌ Restrict pushes
  - Force pushes are blocked
  - Deletions are blocked
  - Tag creation is restricted

**Who can push:** Maintainers and Admins only

### `develop` Branch (if used)

**Status:** 🔒 Protected (same rules as main)

## Feature Branches

### Naming Conventions

Allowed patterns:
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring
- `test/*` - Test improvements
- `hotfix/*` - Urgent production fixes

**Examples:**
- ✅ `feature/add-llm-support`
- ✅ `fix/summarization-trigger`
- ✅ `docs/api-documentation`
- ✅ `refactor/database-layer`
- ❌ `random-branch-name` (unclear purpose)

### Lifecycle

1. **Creation:** Contributor creates branch from `main`
2. **Development:** Commits made during development
3. **PR Opening:** Pull request opened for review
4. **Merge:** PR merged to `main`
5. **Auto-Deletion:** GitHub automatically deletes branch

### Stale Branch Cleanup

Branches are considered stale if:
- No activity for 90+ days
- PR has been closed without merge for 30+ days
- Author has been unresponsive to review requests

**Cleanup Process:**
1. Maintainer creates issue commenting stale branches
2. 7-day grace period for contributors to respond
3. Maintainer closes stale PRs and deletes branches
4. Contributors can always reopen if needed

## Enforcement

### GitHub Settings

These rules are enforced through GitHub branch protection settings.

### Local Development

Prevent accidental pushes to protected branches:

```bash
# Configure Git to prevent force pushes
git config --global push.default current

# Pre-commit hooks (optional)
# .git/hooks/pre-push
#!/bin/bash
protected_branches=("main" "develop")
current_branch=$(git symbolic-ref --short HEAD)

if [[ " ${protected_branches[@]} " =~ " ${current_branch} " ]]; then
    echo "ERROR: Cannot force-push to protected branch: $current_branch"
    exit 1
fi
```

## For Maintainers

### Reviewing PRs

Before merging:
1. Ensure code follows style guidelines
2. All tests pass
3. Documentation is updated
4. No merge conflicts
5. At least one approval from maintainer

### Merging PRs

1. Squash and merge for clean history
2. Delete branch after merge (automatic)
3. Add `merged` label
4. Close related issues

### Post-Merge

```bash
# Periodic maintenance (monthly)
git fetch --prune
git remote prune origin

# Review active branches
git branch -r | grep -v main
```

## Exceptions

### When to Disable Protection

Temporary protection bypass requires:
- Consensus from 2+ maintainers
- Document reason in issue
- Re-enable protection immediately after

### Hotfixes

For urgent production fixes:
1. Create `hotfix/*` branch
2. Open PR
3. Fast-track review
4. Merge after approval
5. Tag release
6. Delete branch

## Questions?

If you have questions about branch policies or need an exception, open an issue or contact maintainers.

---

**Last Updated:** 2026-01-30
**Maintainer:** @executive-assistant
