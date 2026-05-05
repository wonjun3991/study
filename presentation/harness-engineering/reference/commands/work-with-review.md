---
name: work-with-review
description: Work on a task with real-time review and guidance from agents. Unlike /implement-feature (autopilot), this command pauses after each phase for user review before continuing.
---

# /work-with-review

Work on a task while receiving continuous review at each phase boundary.

## Task

{{USER_INPUT}}

## Key Difference from /implement-feature

| | `/implement-feature` | `/work-with-review` |
|---|---|---|
| **Mode** | Autopilot | Interactive (pause per phase) |
| **User involvement** | Start → wait → done | Review & approve each phase |
| **When to use** | Trusted, well-defined tasks | Complex tasks, learning, need control |

## Execution

**CRITICAL: You MUST invoke the `feature-implementer` agent using the Task tool, but with phase-by-phase user review.**

### Step 1: Worktree Setup (MANDATORY)

Derive task key from ticket/feature and create a dedicated worktree:

```bash
WT_PATH="$(scripts/worktree-start.sh TMS-123 origin/v3 work)"
cd "$WT_PATH"
```

### Step 2: Requirements Analysis (Phase 1 only)

Invoke `feature-implementer` agent with instructions to **STOP after Phase 1** (Requirements Analysis):

```
1. Call the Task tool with `subagent_type: feature-implementer`
2. In the prompt, include: "STOP after Phase 1 and report your plan. Do NOT proceed to Phase 2."
3. Present the plan to the user for review
```

### Step 3: Phase-by-Phase Execution with Review

For each remaining phase (2 through 8):

1. **Present** what the next phase will do (scope, files, agents involved)
2. **Wait for user approval** before proceeding
3. **Invoke** `feature-implementer` using `session_id` to continue from where it left off:
   - Prompt: "Proceed with Phase N only. STOP after Phase N completion."
4. **Report results** to user (changes made, commit created, any issues)
5. **Wait for user feedback** before moving to next phase

### Review Checkpoints

After each phase, present to user:

```
Phase N: [Phase Name] Complete
----------------------------------------
Changes:
- [file1] - [what changed]
- [file2] - [what changed]

Commit: feat(TMS-XXX): [message]

Issues Found: [none / list]
Next Phase: [Phase N+1 description]

Proceed? [Y/n/adjust]
```

### User Controls

At each checkpoint, the user can:
- **Proceed** → Continue to next phase
- **Adjust** → Modify the approach before continuing
- **Skip** → Skip a phase (e.g., no DB changes needed)
- **Stop** → Pause implementation (can resume later with session_id)

## Phase Sequence

1. **Phase 1**: Requirements Analysis → Present plan
2. **Phase 2**: Database Layer (Liquibase + JPA entities)
3. **Phase 3**: Domain Layer (domain models + services)
4. **Phase 4**: Application Layer (use cases + ports)
5. **Phase 5**: Adapter Layer (REST controllers + OpenAPI + mappers)
6. **Phase 6**: Testing (unit + integration + E2E)
7. **Phase 6.5**: Code Quality Validation (SRP, DRY, multi-tenancy)
8. **Phase 7**: Final Validation (architecture + Spring Boot + tests pass)
9. **Phase 8**: Self-Review Loop

## Session Continuity (CRITICAL)

Use `session_id` from the first `feature-implementer` invocation for ALL subsequent phase calls. This preserves the agent's full context — no repeated file reads, no re-analysis.

```
# Phase 1
result = task(subagent_type="feature-implementer", prompt="Analyze TMS-320. STOP after Phase 1.")
# → session_id = "ses_abc123"

# [User reviews and approves]

# Phase 2
task(session_id="ses_abc123", prompt="Proceed with Phase 2 only. STOP after completion.")

# [User reviews and approves]

# Phase 3
task(session_id="ses_abc123", prompt="Proceed with Phase 3 only. STOP after completion.")

# ... and so on
```

## Parallel Worktree Pattern

For parallel execution across independent tasks, create one worktree per task key:

```bash
# task A
scripts/worktree-start.sh TMS-701 origin/v3 work

# task B
scripts/worktree-start.sh TMS-702 origin/v3 work
```

Never run two unrelated implementations in the same worktree.

## Error Handling

If a phase fails:
1. Report the failure with full context to user
2. Ask user how to proceed: fix, retry, skip, or abort
3. Use `session_id` to continue the agent with the fix instructions

## Resume

If interrupted, use the same `session_id` to resume:
```
task(session_id="ses_abc123", prompt="Resume from Phase N.")
```

The feature-implementer tracks progress in `.claude/progress/{TICKET-ID}.md`.
