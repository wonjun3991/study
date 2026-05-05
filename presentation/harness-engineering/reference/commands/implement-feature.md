---
description: Implement a complete feature from Jira ticket (e.g., TMS-320) or requirements. Orchestrates all agents to deliver production-ready code.
---

# Implement Feature from Requirements

**🤖 CRITICAL: You MUST invoke the feature-implementer agent using the Task tool. The workflow depends on your current mode.**

## Workflow Based on Mode

### If NOT in Plan Mode (Default)

**Immediately invoke feature-implementer agent**:

1. **Call the Task tool** with `subagent_type: feature-implementer`
2. **Pass the user's requirements** in the prompt parameter
3. **Let the agent handle everything** - planning, implementation, testing, commits

### If IN Plan Mode

**Two-step process**:

1. **Create a comprehensive plan** showing:
   - What the feature-implementer agent will do
   - Which specialist agents will be coordinated
   - What files will be modified
   - What tests will be written
   - What commits will be created

2. **After plan approval, invoke the agent**:
   - Use ExitPlanMode tool to present the plan
   - Wait for user approval
   - Then invoke feature-implementer agent with Task tool

**Important**: DO NOT implement code yourself. Always let the feature-implementer agent handle the actual implementation, even in Plan mode.

## Usage

```
/implement-feature TMS-320
/implement-feature https://omelet.atlassian.net/browse/TMS-320
/implement-feature "Add shipment tracking API"
```

## How This Works

### Normal Mode (Immediate Execution)

This command **immediately invokes** the feature-implementer agent using the Task tool:

```
User: /implement-feature "Add stop_id to solver API"
     ↓
Claude: [Invokes feature-implementer agent]
     ↓
Agent: [Analyzes → Implements → Tests → Commits]
     ↓
Result: Production-ready code with commits
```

### Plan Mode (Two-Step Process)

When in Plan mode, the workflow is different:

```
User: /implement-feature "Add stop_id to solver API"
     ↓
Claude: [Creates comprehensive plan]
     ↓
User: [Reviews and approves plan]
     ↓
Claude: [Invokes feature-implementer agent]
     ↓
Agent: [Executes the approved plan]
     ↓
Result: Production-ready code with commits
```

**Key Difference**: In Plan mode, you get to review the plan before agent execution.

The agent will:
- Read your requirements (Jira ticket or description)
- Coordinate all specialist agents
- Implement code across all layers
- **Create phase-based commits automatically**
- Validate the complete implementation

You don't need to manually call the agent or create commits.

## Automated Branch Management

**CRITICAL**: The agent automatically checks your current branch before starting work:

1. **If on protected branch** (main, master, production, v3, v3-base):
   - Automatically creates feature branch: `feature/<ticket-id>` or `feature/<descriptive-name>`
   - Switches to new branch
   - Proceeds with implementation

2. **If already on feature branch**:
   - Proceeds with implementation on current branch

**Protected Branches**: `main`, `master`, `production`, `v3`, `v3-base`

This ensures you **never accidentally commit directly to protected branches**.

## What This Command Does

The feature-implementer orchestrator will:

1. **Check Current Branch** and create feature branch if on protected branch
2. **Fetch Requirements** from Jira (if ticket provided)
3. **Analyze** requirements and related ADR documents
4. **Plan** the implementation across all layers
4. **Coordinate Agents**:
   - liquibase-manager: Database schema
   - jpa-guardian: JPA entities and repositories
   - hexagonal-architect: Domain model and services
   - spring-boot-expert: Spring configuration
   - openapi-generator: REST API
   - code-quality-guardian: Clean code (SRP)
   - multi-tenant-guardian: Data isolation and authorization
   - test-runner: **Write comprehensive tests** (unit + integration)
5. **Write Tests** - MANDATORY:
   - Unit tests for domain logic and services
   - Integration tests for API endpoints
   - Repository tests for JPA queries
   - Mapper tests for data transformations
   - Target: >80% code coverage
6. **Create Commits** - AUTOMATIC:
   - Commit after each phase completion
   - Follow phase-based commit strategy
   - Use conventional commit messages
7. **Validate** the complete implementation
8. **Deliver** production-ready code with clean git history

## Requirements

Please implement the following feature:

{{USER_INPUT}}

The feature-implementer agent will analyze these requirements and implement accordingly.

## Expected Deliverables

- ✅ Database: Liquibase changesets applied
- ✅ Domain: Business logic implemented
- ✅ API: REST endpoints created
- ✅ **Tests: MANDATORY - >80% coverage, all passing**
  - Unit tests for domain logic
  - Integration tests for REST APIs
  - Repository tests for database queries
  - Mapper tests for DTO conversions
- ✅ **Code Quality: MANDATORY - All violations fixed before commits** 🔍
  - No SRP violations (single responsibility per class/method)
  - No DRY violations (no duplicate code/constants/logic)
  - Methods <30 lines, Classes <300 lines
  - Clear, descriptive naming
  - High cohesion, low coupling
  - Proper abstraction levels
- ✅ Security: Authorization configured
- ✅ Multi-tenancy: Data isolation verified
- ✅ Architecture: Hexagonal Architecture compliant

## Example Output

```
✅ Phase 1: Requirements analyzed from TMS-320

✅ Phase 2: Database layer complete
   📝 Committed: feat(TMS-320): add requested_date column to orders table

✅ Phase 3: Domain layer complete
   📝 Committed: feat(TMS-320): implement RequestedDate domain logic

✅ Phase 4: Application layer complete
   📝 Committed: feat(TMS-320): add RequestedDate to order use cases

✅ Phase 5: Adapter layer complete
   📝 Committed: feat(TMS-320): expose requested_date in Order API v3

✅ Phase 6: Tests complete (85% coverage)
   📝 Committed: test(TMS-320): add tests for requested_date feature

✅ Phase 6.5: Code Quality Review 🔍
   🔍 Checking for SRP violations... None found
   🔍 Checking for DRY violations... Found 2 violations
      ↳ Duplicate date formatters in ExcelCellParser
      ↳ Refactoring... Extracted constants
   🔍 Checking method lengths... All methods <30 lines ✓
   🔍 Checking class sizes... All classes <300 lines ✓
   🔍 Checking naming conventions... All clear ✓
   ✅ All code quality checks passed

✅ Phase 7: All validations passed

📦 Implementation Complete
   - Files changed: 12
   - Tests added: 5
   - Commits created: 5
   - Code quality: 100% compliant
   - All standards met
   - Ready for PR
```

## Error Handling

### If Implementation Fails

1. **Jira Fetch Failure**:
   - Verify ticket ID format (e.g., TMS-320)
   - Check Jira API connection: `curl -s -o /dev/null -w "%{http_code}" -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_BASE_URL/rest/api/2/myself"`
   - Verify environment variables: `echo $JIRA_BASE_URL $JIRA_EMAIL`

2. **Agent Coordination Failure**:
   - Review error message to identify failing phase
   - Fix the specific issue (e.g., compile error, missing dependency)
   - Re-run `/implement-feature` or continue manually from failed phase

3. **Test Failure**:
   - Agent will report failing tests
   - Use `/fix-test` to resolve specific test failures
   - Or fix manually and re-run tests

4. **Validation Failure**:
   - Review specific validation errors (architecture, multi-tenancy, security)
   - Fix issues and re-run validation
   - Use specific commands: `/arch-validate`, `/check-auth`

### Partial Completion & Resume

The feature-implementer tracks progress in `.claude/progress/{TICKET-ID}.md`. This file records which phases are completed along with their git commit hashes.

**If implementation stops mid-way**:
- **Already committed phases**: Safe. Commit hashes are recorded in the progress file.
- **Uncommitted changes**: Review with `git status`, decide to commit or discard.

**To resume from where you left off**:
```bash
# Simply re-run the same command
/implement-feature TMS-320
```
The agent will:
1. Detect the existing progress file
2. Verify completed phases by checking git log for commit hashes
3. Load cached requirements (no Jira re-fetch needed)
4. Resume from the first incomplete phase

**To start completely fresh**:
```bash
# Delete the progress file first
rm .claude/progress/TMS-320.md

# Then re-run
/implement-feature TMS-320
```

**Note**: The progress file is in `.claude/` which is gitignored, so it persists locally but is never committed.

## Automated Git Workflow

**IMPORTANT**: The feature-implementer agent **MUST create commits** after completing each implementation phase.

⛔ **This is a HARD REQUIREMENT, not optional.**

### Agent's Commit Process (MANDATORY)

The agent MUST follow this process using Bash tool:

```
Phase Complete → git status → git add <files> → git commit → git log -1 --oneline → Next Phase
```

**Each step MUST be executed via Bash tool**:
1. `git status` - verify changes exist
2. `git add <specific-files>` - stage files for this phase
3. `git commit -m "type(TICKET): description"` - create commit
4. `git log -1 --oneline` - verify commit was created

**Violation Consequence**:
- If agent skips `git commit` → Implementation FAILED
- If agent claims "commit created" without Bash tool → FALSE REPORTING
- If no commits after implementation → Implementation INCOMPLETE

### Expected Commit History

⛔ **AGENT MUST VERIFY**: After implementation, run `git log --oneline -10` to verify commits exist.

**Expected output** (4-6 commits):

```bash
$ git log --oneline -10
a1b2c3d test(TMS-320): add tests for requested_date feature
d4e5f6g feat(TMS-320): expose requested_date in Order API v3
h7i8j9k feat(TMS-320): add RequestedDate to order use cases
l0m1n2o feat(TMS-320): implement RequestedDate domain logic
p3q4r5s feat(TMS-320): add requested_date column to orders table
```

**Verification Command for Agent**:
```bash
# Agent MUST run this at the end
git log --oneline -10

# Verify:
# - At least 4 commits for this feature
# - Each commit follows pattern: type(TICKET): description
# - Commits in correct phase order (database → domain → application → adapter → test)
```

**If fewer than 4 commits exist → Implementation FAILED**

### Commit Message Pattern

Each commit follows conventional commits format:
- **Database**: `feat(TMS-XXX): add/modify [table/column] for [purpose]`
- **Domain**: `feat(TMS-XXX): implement [DomainConcept] logic`
- **Application**: `feat(TMS-XXX): add [UseCase] to [aggregate]`
- **Adapter**: `feat(TMS-XXX): expose [feature] in [API/persistence]`
- **Tests**: `test(TMS-XXX): add tests for [feature]`

### After Implementation

```bash
# 1. Review commits created by agent
git log --oneline -10

# 2. Review changes in each commit
git show HEAD~4  # Database phase
git show HEAD~3  # Domain phase
git show HEAD~2  # Application phase
git show HEAD~1  # Adapter phase
git show HEAD    # Tests phase

# 3. If satisfied, push to remote
git push origin feature/TMS-320

# 4. Create PR
gh pr create --base v3 --title "feat(TMS-320): Add requested_date to Order"
```

### Manual Override

If you prefer to create commits manually:
- Stop the agent before commit step
- Use `/smart-commit` command with `commit-strategy` skill
- Follow phase-based patterns manually

**→ See `.claude/skills/commit-strategy.md` for detailed commit guidelines**

## Notes

- Provide either Jira ticket ID (TMS-XXX) or feature description
- Agent will ask for clarification if requirements are unclear
- Agent coordinates all specialist agents automatically
- **Test writing is MANDATORY** - implementation is NOT complete without tests
- Full validation ensures production readiness

## Test Requirements

**IMPORTANT**: Every feature implementation MUST include tests:

1. **Unit Tests** (`src/test/java/.../domain/`):
   - Test domain models and business logic
   - Test validation rules and constraints
   - Mock external dependencies

2. **Integration Tests** (`src/test/java/.../adapter/in/rest/`):
   - Test REST API endpoints with MockMvc
   - Test request/response mapping
   - Test error handling and validation

3. **Repository Tests** (`src/test/java/.../adapter/out/persistence/jpa/`):
   - Test JPA queries and specifications
   - Test soft delete filtering
   - Test multi-tenancy isolation

4. **Mapper Tests** (`src/test/java/.../adapter/mapper/`):
   - Test MapStruct mappers
   - Test DTO ↔ Domain conversions
   - Test edge cases and null handling

**Coverage Target**: Minimum 80% line coverage for new code

---

## Plan Mode

In Plan Mode, Claude creates an implementation plan **before** executing. The workflow:

1. **Plan Creation**: Claude analyzes the feature and creates a plan showing phases, files to modify, expected commits, and agent workflow
2. **Plan Approval**: User reviews and approves (or adjusts) the plan
3. **Agent Execution**: feature-implementer follows the approved plan
4. **Completion**: Agent delivers results matching the plan

**Use Plan Mode when**: Critical features, learning the workflow, need to review scope, team review needed.
**Skip Plan Mode when**: Urgent fixes, simple/well-understood changes, want fastest execution.

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Normal** | Immediate agent execution | Fast, trusted workflows |
| **Plan** | Plan → Approval → Execution | Learning, critical features |

## Final Self-Review Loop (MANDATORY)

After completing all implementation phases, the feature-implementer agent performs a **holistic final self-review**.

### Phase 8: Final Self-Review

```bash
# Review all feature commits
git log --oneline -10
git diff HEAD~N...HEAD  # Review all changes in this feature
```

**Self-Assessment Checklist:**
- [ ] All Jira acceptance criteria satisfied?
- [ ] Architecture clean and hexagonal pattern respected?
- [ ] Tests meaningful (edge cases, not just happy paths)?
- [ ] No technical debt introduced?
- [ ] Code quality meets all standards (SRP, DRY, naming)?
- [ ] Multi-tenancy properly secured?
- [ ] Jira ticket updated with implementation notes?

### Verdict

**SATISFIED** → Mark implementation complete, present final summary

**NOT SATISFIED** → Loop back:
1. Identify which phase needs improvement (e.g., "Phase 6 tests are insufficient")
2. Find the relevant commit: `git log --oneline`
3. Fix the specific issue (do NOT redo the entire implementation)
4. Re-execute only the failing phase
5. Return to Phase 8 review

**Maximum review cycles**: 2 loops. After 2 unsatisfied reviews:
- Document remaining concerns explicitly
- Mark as "complete with known issues"
- Present issues to user for decision

### Review Output Format

```
🔍 Phase 8: Final Self-Review
══════════════════════════════

Reviewing all changes for TMS-XXX...

✅ Acceptance Criteria: All 5 criteria satisfied
✅ Architecture: Hexagonal pattern respected
⚠️ Tests: Integration test for error case missing
✅ Code Quality: All methods <30 lines, no SRP violations
✅ Multi-tenancy: All queries filter by tenantId

Verdict: NOT SATISFIED
Reason: Missing error case test in Phase 6

→ Looping back to Phase 6...
```

OR:

```
🔍 Phase 8: Final Self-Review
══════════════════════════════

✅ All acceptance criteria satisfied
✅ Architecture clean
✅ Tests comprehensive (85% coverage)
✅ Code quality: 100% compliant
✅ Multi-tenancy: Secure

Verdict: SATISFIED ✅

📦 Implementation Complete for TMS-XXX
```
