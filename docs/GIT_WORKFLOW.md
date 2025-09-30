# Git Workflow and Commit Conventions

**Version**: 1.0
**Date**: 2025-09-29
**Project**: NANDA Adapter v2.0 Refactoring

---

## Branching Strategy

### Main Branch

- `main` - Production-ready code, current v1.x
- Protected: No direct commits
- All changes via Pull Requests

### Feature Branches

**Naming Convention**: `feature/<scope>-<brief-description>`

**Examples**:
```bash
feature/local-registry           # Day 1: File-based registry
feature/protocol-loop-prevention # Day 2: Protocol module
feature/router-depth-tracking    # Day 3: Router module
feature/simple-nanda-entry       # Day 4-5: SimpleNANDA class
feature/testing-integration      # Integration tests
feature/docs-readme-rewrite      # Documentation updates
```

### Creating Feature Branches

```bash
# Start from main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/local-registry

# Work on feature...
# Commit regularly (see commit guidelines below)

# Push to remote
git push -u origin feature/local-registry
```

---

## Commit Guidelines

### Frequency

**Commit when**:
- ✅ Completing a logical unit of work (function, class, test suite)
- ✅ Finishing a file or module
- ✅ Before switching to a different task
- ✅ Code is in working state (tests pass)
- ✅ End of work session

**Don't commit**:
- ❌ After every line change (too granular)
- ❌ With failing tests (unless explicitly WIP)
- ❌ Mixed concerns in single commit

**Rule of thumb**: Commit every 30-60 minutes of focused work, or when completing a feature component.

### Commit Message Format

**Structure**:
```
<type>: <subject>

<body (optional)>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring (no behavior change)
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Build, dependencies, tooling

**Subject Line**:
- ✅ Imperative mood ("Add registry", not "Added registry")
- ✅ Lowercase start
- ✅ No period at end
- ✅ Max 72 characters
- ✅ Describe WHAT, not HOW

**Body (optional)**:
- Why the change was made
- What problem it solves
- Any important context
- Breaking changes

---

## Commit Examples

### Good Commits

```bash
# Simple, clear
git commit -m "feat: add file-based local registry"

# With context
git commit -m "feat: add LocalRegistry class

Implements file-based registry using JSON for local development.
Supports register, lookup, list, and unregister operations.
Data persists to .nanda_registry.json file."

# Bug fix
git commit -m "fix: validate API key before creating Anthropic client

Previously, client was created at module import time even if not needed.
Now uses lazy initialization to only create when required."

# Test addition
git commit -m "test: add unit tests for LocalRegistry

Covers all CRUD operations plus file persistence."

# Refactoring
git commit -m "refactor: extract protocol parsing to separate module

Moves format_a2a_message and parse_a2a_message from agent_bridge
to new protocol.py module. No behavior changes."

# Documentation
git commit -m "docs: update README with curl testing examples"
```

### Bad Commits (Avoid)

```bash
# Too vague
git commit -m "update code"
git commit -m "fixes"
git commit -m "changes"

# Past tense
git commit -m "Added registry"  # Use "add" not "added"

# Too granular
git commit -m "add comma"
git commit -m "fix typo"

# Mixed concerns
git commit -m "add registry, fix bug, update docs"  # Should be 3 commits
```

---

## Workflow Example: Day 1 (Local Registry)

```bash
# Start feature
git checkout -b feature/local-registry

# Create registry interface
# ... write code ...
git add nanda_adapter/core/registry_interface.py
git commit -m "feat: add RegistryInterface abstract base class"

# Implement LocalRegistry
# ... write code ...
git add nanda_adapter/core/local_registry.py
git commit -m "feat: implement LocalRegistry with file persistence

Uses JSON file (.nanda_registry.json) to store agent registrations.
Supports register, lookup, list, unregister, and clear operations."

# Add tests
# ... write tests ...
git add tests/unit/test_local_registry.py
git commit -m "test: add unit tests for LocalRegistry

Covers all CRUD operations, file persistence, and error cases."

# Run tests, fix issues
# ... fix bugs ...
git add nanda_adapter/core/local_registry.py
git commit -m "fix: handle missing registry file on first load"

# Day complete, push
git push -u origin feature/local-registry
```

**Result**: 4 clean, focused commits

---

## Workflow Example: Day 3 (Router Module)

```bash
git checkout -b feature/router-depth-tracking

# Implement router class
git add nanda_adapter/core/router.py
git commit -m "feat: add MessageRouter with depth tracking

Routes @agent_id, /query, and /help commands.
Includes depth parameter to prevent message loops."

# Add loop prevention logic
git add nanda_adapter/core/router.py
git commit -m "feat: implement depth limit check in router

Prevents infinite loops by enforcing max_depth=1 (request-response only)."

# Add tests
git add tests/unit/test_router.py
git commit -m "test: add unit tests for MessageRouter

Tests routing logic, depth limits, and error handling."

# Integration with protocol
git add nanda_adapter/core/router.py
git commit -m "refactor: integrate protocol module with router

Router now uses format_a2a_message and parse_a2a_message from protocol module."

git push -u origin feature/router-depth-tracking
```

---

## Pull Request Process

### 1. Before Creating PR

```bash
# Ensure all commits are clean
git log --oneline

# Rebase on main (if needed)
git fetch origin main
git rebase origin/main

# Run all tests
pytest

# Push final changes
git push origin feature/local-registry
```

### 2. Create PR

**Title**: Same as feature scope
- `feat: local registry implementation`
- `refactor: extract protocol module`

**Description Template**:
```markdown
## Summary
Brief description of what this PR does.

## Changes
- List of key changes
- Organized by file/module

## Testing
- How to test the changes
- What tests were added

## Related
- Closes #<issue-number> (if applicable)
- Part of: MVP Implementation Plan Day X
```

### 3. PR Review Checklist

- [ ] All tests pass
- [ ] No merge conflicts
- [ ] Commit messages follow conventions
- [ ] No advertising/branding in commits
- [ ] Code follows project style
- [ ] Documentation updated (if needed)

### 4. Merge

**Method**: Squash and merge (preferred for MVP)
- Combines all commits into single commit on main
- Keeps main history clean

**Alternative**: Merge commit (if commits are well-organized)

---

## Commit Amending (Use Sparingly)

**When to amend**:
- Fix typo in last commit
- Add forgotten file to last commit
- **Before pushing** (local only)

```bash
# Fix typo, add to last commit
git add file.py
git commit --amend --no-edit

# Change last commit message
git commit --amend -m "feat: corrected commit message"
```

**NEVER amend**:
- After pushing (breaks history for others)
- Commits that others have based work on

---

## Stashing Changes

**Use case**: Need to switch branches mid-work

```bash
# Save work in progress
git stash push -m "WIP: router depth tracking"

# Switch branches
git checkout main

# Return and restore
git checkout feature/router-depth-tracking
git stash pop
```

---

## Checking Commit History

```bash
# View recent commits
git log --oneline -10

# View commits with diffs
git log -p -2

# View commits by author
git log --author="Your Name"

# Search commit messages
git log --grep="registry"

# View file history
git log --follow -- nanda_adapter/core/registry.py
```

---

## Example: Full Day Workflow

```bash
# Morning: Start fresh
git checkout main
git pull origin main
git checkout -b feature/protocol-loop-prevention

# Work session 1 (9am - 10:30am)
# Implement protocol.py
git add nanda_adapter/core/protocol.py
git commit -m "feat: add A2AMessage dataclass with depth fields"

# Work session 2 (10:30am - 12pm)
# Add format/parse functions
git add nanda_adapter/core/protocol.py
git commit -m "feat: implement format_a2a_message and parse_a2a_message

Handles depth, max_depth, and message_type fields for loop prevention."

# Lunch break

# Work session 3 (1pm - 3pm)
# Write tests
git add tests/unit/test_protocol.py
git commit -m "test: add comprehensive protocol tests

Tests formatting, parsing, round-trip, and depth field handling."

# Work session 4 (3pm - 5pm)
# Fix bugs found in testing
git add nanda_adapter/core/protocol.py
git commit -m "fix: handle missing depth fields in legacy messages

Defaults to depth=0, max_depth=1 for backward compatibility."

# End of day
git push -u origin feature/protocol-loop-prevention
```

**Result**: 4 commits, clean history, logical progression

---

## Emergency: Undo Last Commit

```bash
# Keep changes, undo commit
git reset --soft HEAD~1

# Discard changes, undo commit (DANGEROUS)
git reset --hard HEAD~1

# Already pushed? Create revert commit
git revert HEAD
git push origin feature/branch-name
```

---

## Summary

### Branching
- ✅ One feature branch per MVP day or logical feature
- ✅ Name: `feature/<scope>-<description>`
- ✅ Start from `main`, merge back via PR

### Commits
- ✅ Commit every 30-60 minutes or logical completion
- ✅ Format: `<type>: <subject>`
- ✅ Clear, factual, no advertising
- ✅ Imperative mood, lowercase, no period

### Pull Requests
- ✅ Create when feature complete
- ✅ Descriptive title and description
- ✅ All tests pass
- ✅ Squash and merge to keep main clean

---

**Next**: See [MVP_IMPLEMENTATION_PLAN.md](./MVP_IMPLEMENTATION_PLAN.md) for feature branch breakdown by day.