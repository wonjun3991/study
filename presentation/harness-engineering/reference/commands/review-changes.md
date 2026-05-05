---
description: Review uncommitted changes (git diff) across all quality dimensions
---

# Review Current Changes

Review all uncommitted changes in your working directory across architecture, security, queries, and test quality.

## Changes to Review

{{USER_INPUT}}

## Review Process

### 1. Identify Changes
```bash
git status
git diff
git diff --staged
```

List all modified, added, and deleted files.

### 2. Architecture Review
Invoke **hexagonal-architect** agent for changed files:

**Check:**
- Are new files in correct directories?
- Does code follow Hexagonal Architecture?
- Are layers properly separated?
- Are dependencies flowing correctly?
- Are new domain services properly designed?

**Questions:**
- Should this logic be in domain vs adapter?
- Are port interfaces defined?
- Is framework code isolated?

### 3. Security Review
Invoke **security-auditor** agent for changed files:

**Check:**
- Do new queries filter `deletedAt IS NULL`?
- Is multi-tenancy filtering added?
- Are authorization specs implemented?
- Do new endpoints check user permissions?
- Any potential data leakage?

**Questions:**
- Can users access other tenants' data?
- Are deleted records properly hidden?
- Is authorization enforced?

### 4. Query Review (if database code changed)
Invoke **jpa-guardian** agent for repository changes:

**Check:**
- All new queries have soft delete filter?
- Authorization specs properly implemented?
- No N+1 queries introduced?
- Proper indexing for new columns?
- Entity design follows standards?

**Questions:**
- Will this query perform well at scale?
- Are all filters in place?
- Is pagination needed?

### 5. Code Quality Review (SRP)
Invoke **code-quality-guardian** agent for service/domain changes:

**Check:**
- Do new methods follow Single Responsibility Principle?
- No mixing of retrieval + save in same method?
- Are orchestration methods properly delegating?
- Do method names match their implementation?
- No methods doing 3+ different concerns?

**Questions:**
- Should this method be split?
- Is the responsibility clear?
- Can this logic be tested in isolation?

### 6. Test Review
Invoke **test-runner** agent:

**Check:**
- Are tests added for new functionality?
- Do existing tests still pass?
- Is coverage maintained/improved?
- Are authorization scenarios tested?
- Are edge cases covered?

**Questions:**
- What scenarios are missing tests?
- Are tests comprehensive enough?
- Do tests validate business rules?

### 6. Code Quality Review

**Check:**
- Google Java Style Guide compliance
- No TODO without tickets
- No commented code
- Appropriate error handling
- No hardcoded values

## Review Output Format

```markdown
# Code Review Report
Date: YYYY-MM-DD
Branch: feature/xyz
Files Changed: 12 files (+450, -120)

## Summary
Overall Status: ⚠️ NEEDS WORK (3 critical issues)

## Critical Issues (Must Fix) 🚫
1. **Missing soft delete filter** in OrderRepository.findByStatus()
   - File: `adapter/out/persistence/jpa/order/OrderJpaRepository.java:145`
   - Issue: Query doesn't filter `deletedAt IS NULL`
   - Fix: Add `.and(cb.isNull(root.get("deletedAt")))`

2. **Authorization missing** in OrderV3ApiImpl.assignDriver()
   - File: `adapter/in/rest/v3/order/OrderV3ApiImpl.java:89`
   - Issue: No check if user can assign drivers
   - Fix: Add authorization check before assignment

3. **Layer violation** in CreateOrderService
   - File: `domain/order/CreateOrderService.java:67`
   - Issue: Direct dependency on JPA entity
   - Fix: Use domain model, let adapter handle conversion

## High Priority (Should Fix) ⚠️
1. **Test coverage** for new assignDriver method
   - Missing tests for unauthorized users
   - Missing tests for cross-tenant assignment

2. **N+1 query** potential in Order -> Shipments
   - Consider adding `@EntityGraph` or JOIN FETCH

## Medium Priority (Nice to Fix) 💡
1. **Code duplication** in validation logic
2. **Missing JavaDoc** on public methods

## Low Priority (Optional) ℹ️
1. Variable naming could be more descriptive
2. Consider extracting helper method

## Recommendations

### Immediate Actions (Before Commit)
1. Fix 3 critical issues (30 min)
2. Add missing authorization tests (20 min)
3. Fix soft delete filter (5 min)

### Before PR
1. Run `/pre-pr` to verify all fixes
2. Add integration tests
3. Update documentation if needed

## Files Review Detail

### Modified Files
- ✅ `domain/order/Order.java` - Good, pure domain logic
- ⚠️ `domain/order/CreateOrderService.java` - Layer violation (line 67)
- ❌ `adapter/out/persistence/jpa/order/OrderJpaRepository.java` - Missing soft delete
- ⚠️ `adapter/in/rest/v3/order/OrderV3ApiImpl.java` - Missing auth check
- ✅ `adapter/mapper/order/OrderMapper.java` - Good

### New Files
- ✅ `application/port/in/order/AssignDriverUseCase.java` - Well defined port
- ❌ `adapter/in/rest/v3/order/DriverAssignmentV3ApiImpl.java` - No auth

### Test Files
- ⚠️ Coverage: 75% (target 80%)
- Missing: Authorization test scenarios
- Missing: Cross-tenant isolation tests

## Next Steps
1. Fix critical issues
2. Run `/run-tests` to verify
3. Run `/check-queries` on OrderRepository
4. Run `/review-changes` again to confirm
```

## Usage Patterns

### After Coding Session
```bash
# Review what you just built
/review-changes

# Fix issues
# ... make fixes ...

# Review again
/review-changes
```

### Before Git Commit
```bash
# Final review before commit
/review-changes

# If all clear, commit
git add .
git commit -m "message"
```

### Continuous Development
```bash
# Review changes periodically
/review-changes

# Catch issues early
# Fix immediately
# Continue coding
```

## Smart Review Scope

If you specify a path or module:
```
/review-changes in order module
/review-changes the repository layer only
/review-changes my controller changes
```

The review will focus on that scope only.

## Integration with Workflow

**Best Practice:**
1. Code for 30-60 minutes
2. Run `/review-changes`
3. Fix critical issues immediately
4. Continue coding
5. Before commit: `/review-changes` + `/run-tests`
6. Before PR: `/pre-pr`

This catches issues early when they're easiest to fix!
