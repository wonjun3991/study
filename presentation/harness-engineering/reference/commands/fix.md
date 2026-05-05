---
description: Fix a bug with structured investigation workflow. Branch creation, root cause analysis, fix, test, and commit.
---

# Bug Fix Workflow

Fix a bug using a structured investigation-first approach.

## Input

{{USER_INPUT}}

## Workflow

### Phase 1: Understand the Bug

1. **Parse the input**: Jira ticket (TMS-XXX), error message, or description
2. **If Jira ticket provided**: Fetch details with `mcp__atlassian__getJiraIssue`
3. **Reproduce understanding**: Identify the expected behavior vs actual behavior
4. **Scope the impact**: Which domain aggregate, API version, or layer is affected?

### Phase 2: Branch Setup

1. Check current branch with `git branch --show-current`
2. If on a protected branch (main, master, production, v3, v3-base):
   - Create and switch to fix branch: `fix/<ticket-id>` or `fix/<short-description>`
3. If already on a feature/fix branch: proceed on current branch

### Phase 3: Investigate Root Cause

**Do NOT jump to fixing code. Investigate first.**

1. **Search for the affected code**:
   - Use Grep/Glob to find relevant classes, methods, and tests
   - Read the code surrounding the bug location
2. **Trace the execution path**:
   - From API endpoint → Controller → Service → Repository (for request bugs)
   - From Entity → Mapper → DTO (for data mapping bugs)
   - From test setup → test assertion (for test failures)
3. **Identify the root cause**:
   - State the root cause clearly before proceeding to fix
   - If multiple potential causes exist, list them ranked by likelihood
4. **Check for related code**:
   - Are there similar patterns elsewhere that have the same bug?
   - Will the fix break any existing behavior?

### Phase 4: Implement the Fix

1. **Make the minimal change** that fixes the root cause
2. **Do NOT refactor surrounding code** — only fix the bug
3. **Follow project rules**:
   - Check `.claude/rules/code-review-checklist.md` for safety rules
   - No entity mutation in `@Transactional(readOnly = true)`
   - Add both EN and KO i18n keys if creating new message keys
4. **If the fix touches multiple files**, group logically related changes

### Phase 5: Verify the Fix

1. **Run existing tests** related to the changed code:
   ```bash
   ./gradlew test --tests "com.omelet.oaasis.domain.<AffectedAggregate>.*"
   ```
2. **Add or update tests** if:
   - The bug was not covered by existing tests (add regression test)
   - The fix changes behavior that existing tests assert
3. **Run full test suite** if the change is cross-cutting:
   ```bash
   ./gradlew test
   ```
4. **Compile check** to catch any downstream breakage:
   ```bash
   ./gradlew compileJava compileTestJava
   ```

### Phase 6: Commit

1. Stage only the files related to this fix
2. Create commit following project conventions:
   ```
   fix(<ticket-or-scope>): <concise description of what was fixed>

   - Root cause: <brief explanation>
   - Fix: <what was changed and why>
   ```
3. Verify the commit: `git log -1 --stat`

## Key Principles

- **Investigation over guessing**: Spend time understanding before changing code
- **Minimal change**: Fix the bug, don't improve nearby code
- **Regression test**: Every bug fix should add a test that would have caught the bug
- **One concern per fix**: Don't bundle unrelated fixes in one commit

## Examples

```
/fix TMS-480
/fix "Route reorder returns 500 when vehicle is null"
/fix "UpdateRouteService throws NPE on missing driver"
```
