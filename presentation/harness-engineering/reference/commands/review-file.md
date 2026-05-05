---
description: Review a specific file or class for quality, architecture, and security
---

# Review File/Class

Deep review of a specific file or class across all quality dimensions.

## File to Review

{{USER_INPUT}}

## Review Process

### 1. Identify File Type and Context

**Determine:**
- File location (domain, application, adapter)
- File type (entity, service, repository, controller)
- Related files (tests, interfaces, implementations)
- Recent changes (git log)

### 2. Invoke Appropriate Agents

**Domain Files** → **hexagonal-architect**
- Check business logic placement
- Verify no framework dependencies
- Review domain model design

**Repository Files** → **jpa-guardian** + **security-auditor**
- Validate query compliance
- Check soft delete filters
- Verify authorization specs

**Controller Files** → **openapi-generator** + **security-auditor**
- Verify API contract compliance
- Check authentication/authorization
- Review error handling

**Service Files** → **hexagonal-architect**
- Check layer responsibilities
- Verify port usage
- Review business logic

**Test Files** → **test-runner**
- Verify test coverage
- Check test quality
- Review test scenarios

### 3. Comprehensive Analysis

#### Architecture Review
- [ ] File in correct directory?
- [ ] Follows Hexagonal Architecture?
- [ ] Proper layer separation?
- [ ] Dependencies flow correctly?
- [ ] Port interfaces used properly?

#### Code Quality
- [ ] Follows Google Java Style Guide?
- [ ] Appropriate complexity?
- [ ] Good naming conventions?
- [ ] Proper error handling?
- [ ] No code duplication?

#### Security Review
- [ ] Authorization checks present?
- [ ] Soft delete filtering?
- [ ] Multi-tenancy enforcement?
- [ ] No SQL injection risk?
- [ ] No data leakage?

#### Database Review (if applicable)
- [ ] Queries optimized?
- [ ] No N+1 queries?
- [ ] Proper indexing?
- [ ] Entity design correct?
- [ ] Authorization specs?

#### Test Coverage
- [ ] Tests exist for this file?
- [ ] Coverage percentage?
- [ ] Edge cases tested?
- [ ] Integration tests?
- [ ] Authorization tested?

### 4. Detailed Analysis

**For each method/function:**
- Purpose and responsibility
- Input validation
- Error handling
- Business logic correctness
- Performance considerations
- Security implications

## Review Output Format

Use this structure for the report:

```markdown
# File Review Report
File: `<file path>`
Type: <Domain Service | Repository | Controller | Entity | etc.>

## Overall Assessment
Status: <✅ GOOD | ⚠️ NEEDS IMPROVEMENT | ❌ CRITICAL ISSUES> (Score: X/100)

### Scores by Dimension
- Architecture: X/100
- Security: X/100
- Code Quality: X/100
- Test Coverage: X/100

## Critical Issues (must fix)
### 1. <Issue Title> (Line N)
**Issue**: <description>
**Impact**: <why it matters>
**Fix**: <code snippet or description>

## High Priority Issues (should fix)
### 1. <Issue Title> (Lines N-M)
**Recommendation**: <description>

## Medium Priority Issues (nice to fix)
### 1. <Issue Title>
**Recommendation**: <description>

## Positive Aspects
- <What the code does well>

## Action Plan
- [ ] Fix critical issues
- [ ] Improve tests to 80%+ coverage
- [ ] Refactor complex methods
- [ ] Re-run review to verify fixes
```

## Usage Scenarios

### Review Specific File
```bash
/review-file CreateOrderService.java
/review-file the order repository
/review-file src/main/java/com/.../OrderV3ApiImpl.java
```

### Review After Changes
```bash
# Make changes
# ...

# Review the changed file
/review-file the file I just modified
```

### Deep Dive on Complex Class
```bash
/review-file RouteOptimizationService for complexity and performance
```

### Before Refactoring
```bash
# Get baseline assessment
/review-file the class I want to refactor

# Do refactoring
# ...

# Compare results
/review-file the same class
```

## Smart Context Detection

The command automatically:
- Detects file type and purpose
- Invokes appropriate agents
- Analyzes related files (tests, interfaces)
- Checks git history
- Finds usage patterns
- Identifies dependencies

## Integration with Workflow

**When to use:**
1. **Before refactoring** - Understand current state
2. **After changes** - Verify improvements
3. **Code review** - Deep analysis of specific files
4. **Learning** - Understand complex classes
5. **Quality improvement** - Identify enhancement opportunities
