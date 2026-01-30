# Contributing to Executive Assistant

Thank you for your interest in contributing! This document provides guidelines for contributing to the Executive Assistant project.

## Quick Start

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Open a pull request
5. Respond to code review feedback

## Branch Management

### For Contributors

**After your PR is merged:**
```bash
# Switch back to main
git checkout main
git pull upstream main

# Delete your local branch
git branch -d feature/your-feature-name

# Don't delete remote branches - we handle that automatically
```

**Why this approach?**
- Maintainers control remote branch deletion
- GitHub auto-deletes branches when PRs merge
- Your local repository stays clean
- No coordination needed with other contributors

### Branch Naming

Use clear, descriptive branch names:
- `feature/your-feature-name` - New features
- `fix/bug-description` - Bug fixes
- `docs/update-documentation` - Documentation updates
- `refactor/simplify-code` - Code refactoring

### What Happens to Your Branch

1. **During PR Review:** Your branch stays active
2. **After Merge:** GitHub automatically deletes it (we enabled this)
3. **If Abandoned:** Maintainers may close stale PRs and delete branches

## Development Workflow

### 1. Set Up Your Fork

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/executive_assistant.git
cd executive_assistant

# Add upstream remote
git remote add upstream https://github.com/mgmtcnsltng/executive_assistant.git
```

### 2. Create Feature Branch

```bash
# Always start from main
git checkout main
git pull upstream main

# Create your branch
git checkout -b feature/your-feature-name
```

### 3. Make Changes

- Follow the existing code style
- Write clear commit messages
- Test your changes thoroughly
- Update documentation as needed

### 4. Open Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Open PR on GitHub
# Fill in the PR template
# Link any related issues
```

### 5. Code Review

- Maintainers will review your PR
- Respond to feedback within a reasonable time
- Make requested changes
- Keep commits focused (squash if needed)

### 6. After Merge

Once your PR is merged:
```bash
# Update your main branch
git checkout main
git pull upstream main

# Delete your local branch
git branch -d feature/your-feature-name

# The remote branch is auto-deleted by GitHub ✨
```

## Code Style Guidelines

### Python
- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and concise

### Git Commits
- Write clear, descriptive commit messages
- Use present tense: "Add feature" not "Added feature"
- Limit to 50-72 characters for first line
- Add detailed body if needed

Example:
```
Add support for PostgreSQL connection pooling

- Implement connection pool in PostgreSQLStorage
- Add min_size and max_size configuration
- Update tests to verify pool behavior

Fixes #123
```

## Testing

### Before Opening PR
- Run existing tests: `uv run pytest`
- Add tests for new features
- Ensure all tests pass
- Test manually if applicable

### Test Coverage
- Aim for >80% coverage on new code
- Run `uv run pytest --cov` to check

## Questions?

- Check existing issues and discussions
- Read documentation in `docs/`
- Ask questions in your PR if unsure
- Be patient - we'll respond as soon as we can

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build something great together.

---

**Thank you for contributing! 🎉**
