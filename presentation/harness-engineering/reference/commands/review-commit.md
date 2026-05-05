---
description: Review a specific commit or range of commits
---

# Review Commit(s)

Review code changes in a specific commit or commit range.

## Commit to Review

{{USER_INPUT}}

## Review Process

### 1. Identify Commit Changes
```bash
# Single commit
git show <commit-hash>
git show <commit-hash> --stat

# Commit range
git diff <commit1>..<commit2>
git log <commit1>..<commit2> --oneline

# Recent commits
git log -n 5 --oneline
git diff HEAD~5..HEAD
```

### 2. Multi-Agent Review

Invoke agents based on changed files:

**If domain code changed** → **hexagonal-architect**
**If repository code changed** → **jpa-guardian** + **security-auditor**
**If controller code changed** → **openapi-generator** + **security-auditor**
**If test code changed** → **test-runner**

### 3. Review Dimensions

#### Architecture Compliance
- File placement correct?
- Layer separation maintained?
- No circular dependencies introduced?
- Domain logic properly isolated?

#### Security & Authorization
- Queries filter soft deletes?
- Multi-tenancy enforced?
- Authorization checks present?
- No data leakage possible?

#### Code Quality
- Follows style guide?
- Tests included?
- Documentation updated?
- No regressions?

#### Database Changes
- Queries optimized?
- Indexes defined?
- No N+1 queries?
- Entity design correct?

## Review Output

```markdown
# Commit Review Report

## Commit Details
- **Hash**: abc123def
- **Author**: John Doe
- **Date**: 2025-12-27
- **Message**: "Add driver assignment feature"
- **Files Changed**: 8 (+320, -45)

## Overall Assessment
Status: ⚠️ NEEDS IMPROVEMENT (2 issues)

## Issues Found

### Critical 🚫
None

### High Priority ⚠️
1. **Missing Authorization Check**
   - Location: `OrderV3ApiImpl.assignDriver()` line 92
   - Impact: Users could assign drivers to any order
   - Fix: Add `authorizationService.checkOrderAccess(user, orderId)`

2. **Soft Delete Not Filtered**
   - Location: `DriverRepository.findAvailable()` line 156
   - Impact: Could return soft-deleted drivers
   - Fix: Add `AND d.deletedAt IS NULL` to query

### Medium Priority 💡
1. Missing integration tests for new feature
2. No error handling for invalid driver assignment

## Positive Aspects ✅
- Good layer separation
- Domain logic properly encapsulated
- Mapper correctly separates concerns
- Commit message is clear

## Recommendations

1. **Immediate**: Fix 2 high priority issues
2. **Before Merge**: Add integration tests
3. **Consider**: Add more detailed error messages

## Diff Summary

### Added Files
- `application/port/in/order/AssignDriverUseCase.java` ✅
- `domain/order/DriverAssignment.java` ✅

### Modified Files
- `adapter/in/rest/v3/order/OrderV3ApiImpl.java` ⚠️
- `adapter/out/persistence/jpa/driver/DriverJpaRepository.java` ⚠️

### Architectural Impact
- No violations introduced
- Follows Hexagonal Architecture
- Proper use of ports and adapters

## Action Items
1. [ ] Fix authorization check
2. [ ] Add soft delete filter
3. [ ] Write integration tests
4. [ ] Re-review with `/review-commit abc123def`
```

## Usage Scenarios

### Review Last Commit
```bash
/review-commit HEAD
/review-commit the last commit
```

### Review Specific Commit
```bash
/review-commit abc123def
/review-commit commit abc123
```

### Review Commit Range
```bash
/review-commit from abc123 to def456
/review-commit last 5 commits
```

### Review Before Push
```bash
# Review commits not yet pushed
/review-commit origin/main..HEAD

# Fix issues
# Push when clean
```

### Review Someone Else's Commit
```bash
# Code review in PR
/review-commit commit by John in PR #123
```

## Integration with PR Review

**Workflow:**
1. Reviewer runs `/review-commit` on PR commits
2. Gets automated analysis
3. Adds human judgment
4. Provides comprehensive feedback
5. Author fixes issues
6. Re-review with same command

## Comparison with Other Commands

| Command | Scope | When to Use |
|---------|-------|-------------|
| `/review-changes` | Uncommitted changes | During development |
| `/review-commit` | Specific commit(s) | After commit, during review |
| `/pre-pr` | All changes vs base | Before creating PR |
| `/pre-deploy` | Current branch state | Before deployment |

## Smart Detection

The command automatically detects:
- Type of changes (domain, adapter, test)
- Which agents to invoke
- Priority of issues
- Related files to check
- Test coverage impact
