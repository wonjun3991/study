# Execution Tracking: Progress File & Resume Protocol

This skill defines how the feature-implementer orchestrator tracks progress across phases, enabling resume after interruption.

## Progress File

**Location**: `.claude/progress/{TICKET-ID}.md`
**Owner**: feature-implementer orchestrator only (sub-agents do NOT touch this file)
**Lifecycle**: Created at Phase 1 start, updated after each phase, marked COMPLETED at end

### Format

```markdown
# Progress: {TICKET-ID}

**Status**: IN_PROGRESS | COMPLETED | FAILED
**Branch**: feature/{TICKET-ID}
**Started**: {ISO-8601 timestamp}
**Last Updated**: {ISO-8601 timestamp}

## Requirements

- **Summary**: {one-line summary from Jira}
- **Jira**: {TICKET-ID}
- **ADRs**: {comma-separated ADR references, or "None"}
- **Scope**: {affected aggregates}
- **Acceptance Criteria**:
  - AC1: {criterion}
  - AC2: {criterion}

## Phases

### Phase 1: Requirements Analysis
- **Status**: PENDING | DONE | IN_PROGRESS | SKIPPED | FAILED
- **Completed**: {timestamp, only if DONE}

### Phase 2: Database Layer
- **Status**: PENDING | DONE | SKIPPED
- **Commit**: {short hash, only if DONE}
- **Files**:
  - {list of significant files}

### Phase 3: Domain Layer
- **Status**: PENDING | DONE | SKIPPED
- **Commit**: {short hash}
- **Files**:
  - {list of files}

### Phase 4: Application Layer
- **Status**: PENDING | DONE | SKIPPED
- **Commit**: {short hash}
- **Files**:
  - {list of files}

### Phase 5: Adapter Layer
- **Status**: PENDING | DONE | SKIPPED
- **Commit**: {short hash}
- **Files**:
  - {list of files}

### Phase 6: Testing
- **Status**: PENDING | DONE
- **Commit**: {short hash}
- **Files**:
  - {list of files}

### Phase 6.5: Code Quality Review
- **Status**: PENDING | DONE

### Phase 6.6: Specialist Agent Validation
- **Status**: PENDING | DONE

### Phase 7: Validation
- **Status**: PENDING | DONE
```

## Resume Protocol (Phase 0)

Before starting Phase 1, the orchestrator MUST run this check:

### Step 1: Check for existing progress

```
Read .claude/progress/{TICKET-ID}.md
```

- **File does NOT exist** -> Create initial progress file (all phases PENDING) -> proceed to Phase 1
- **File exists** -> Continue to Step 2

### Step 2: Verify completed phases

For each phase marked DONE that has a **Commit** hash:

```bash
git log --oneline | grep {hash}
```

- If commit hash is found -> phase is genuinely DONE
- If commit hash is NOT found -> mark phase as PENDING (commit was lost, e.g., branch reset)

### Step 3: Resume from first incomplete phase

Find the first phase whose status is NOT `DONE` and NOT `SKIPPED`:

- Use the cached **Requirements** section from the progress file (skip Jira re-fetch)
- Print resume summary to user:

```
Resuming {TICKET-ID} from Phase {N}: {Phase Name}
Phases 1-{N-1} already completed.
Requirements loaded from progress file.
```

### Step 4: If all phases are DONE

- Mark status as COMPLETED
- Print: "All phases already completed for {TICKET-ID}. Delete .claude/progress/{TICKET-ID}.md to start fresh."

## Per-Phase Update Rules

After each phase completes successfully, the orchestrator MUST:

1. **Read** the current progress file (to avoid stale writes)
2. **Update** the completed phase:
   - Set `**Status**:` to `DONE`
   - Set `**Completed**:` to current timestamp
   - Set `**Commit**:` to output of `git log -1 --format=%h` (for phases that create commits)
   - Set `**Files**:` to list of significant files created/modified in that phase
3. **Update** `**Last Updated**:` timestamp at the top
4. **Write** the updated progress file back

### When to skip per-phase update

- Phase 1 (Requirements Analysis): Update after writing the Requirements section
- Phase 6.5 / 6.6 / 7: These phases don't produce commits, just set status to DONE

## Output Summary Format

At the end of execution, include a summary section:

```markdown
## Execution Summary

### Agents Invoked:
| Agent | Phase | Task | Status |
|-------|-------|------|--------|
| liquibase-manager | 2 | Create changeset | Invoked |
| jpa-guardian | 2 | Implement repository | Invoked |
| test-runner | 6 | Write tests | Invoked |

### Skills Referenced:
| Skill | Purpose |
|-------|---------|
| hexagonal-architecture | Layer separation |
| testing-standards | Test patterns |

### Summary:
- **Agents**: X invoked / Y skipped
- **Skills**: N referenced
- **Files modified**: Z
- **Tests written**: T (coverage%)
- **Commits created**: C
- **Progress file**: .claude/progress/{TICKET-ID}.md
```

## Guidelines

1. **Only the orchestrator writes** the progress file - never sub-agents
2. **Always re-read before writing** to avoid overwriting concurrent changes
3. **Be honest** - only mark DONE after verifying the phase actually completed
4. **Include commit hashes** - they are the source of truth for resume verification
5. **Keep the Requirements section complete** - it replaces Jira re-fetch on resume
