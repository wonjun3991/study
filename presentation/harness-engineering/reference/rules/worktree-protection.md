# Main Worktree Protection

## Problem

The main worktree (original git checkout at the repository root) accumulates unstaged changes from multiple features when agents edit files directly in it instead of using dedicated worktrees. This causes:

- Unrelated changes bleeding into other branches
- Chronic `git stash` accumulation (35+ stashes observed)
- Confusion about which changes belong to which feature

## Rules

### Rule 1: NEVER Edit Source Code in the Main Worktree

The main worktree (`/Users/wonjunchoi/IdeaProjects/oaasis-tms-be`) is **read-only for source code**.

- **NEVER** modify files under `src/` in the main worktree
- **NEVER** run `git checkout <feature-branch>` in the main worktree to do feature work
- The main worktree should stay on `dev` (or a stable base branch) and remain clean

**Allowed in main worktree**: Reading files, running `git worktree` commands, modifying project-level configs (AGENTS.md, CLAUDE.md, .gitignore).

### Rule 2: ALWAYS Create a Dedicated Worktree for Code Changes

Before modifying any source file, create a worktree:

```bash
# From the main worktree
git worktree add .worktree/fix/TMS-XXX -b fix/TMS-XXX dev
```

Then perform ALL edits, commits, and pushes from that worktree path.

### Rule 3: Dirty Main Worktree = Stop and Fix

If `git status` in the main worktree shows modified source files:

1. **STOP** — do not proceed with any other work
2. **Report** the dirty state to the user
3. **Propose** moving changes to a dedicated worktree or stashing them
4. **Never** silently ignore or discard uncommitted changes

### Rule 4: Verify Working Directory Before Editing

Before any `edit()` or `write()` call on a source file, verify:

```
Is the file path inside a worktree (.worktree/) or the main worktree?
If main worktree → REFUSE and create a worktree first.
```

### Rule 5: No Feature Branches on Main Worktree

The main worktree branch should always be `dev` or `main`. If you find it on a feature branch:

1. Check if the working tree is clean (`git status`)
2. If clean → switch back to `dev` (`git checkout dev`)
3. If dirty → follow Rule 3 (stop and report)

## Pre-Flight Check (Before Any Code Change)

```
1. Am I in a worktree (.worktree/*)? → ✅ Proceed
2. Am I in the main worktree? → ❌ Create worktree first
3. Is the main worktree clean? → If dirty, report to user
4. Is the worktree on the correct branch? → Verify before editing
```
