---
description: Review code for SRP, DRY, and clean code violations
---

# Code Quality Review

**🔍 Comprehensive code quality review for clean, maintainable, and readable code.**

This command reviews code for:
- **SRP (Single Responsibility Principle)** violations
- **DRY (Don't Repeat Yourself)** violations
- Method/class size violations
- Naming convention issues
- Abstraction level mixing
- God classes and utility dumps
- High cohesion and low coupling

## Usage

```bash
# Review all uncommitted changes
/review-code-quality

# Review specific path
/review-code-quality src/main/java/com/omelet/oaasis/domain/order/

# Review specific file
/review-code-quality src/main/java/com/omelet/oaasis/adapter/in/rest/v3/OrderController.java
```

## What This Command Does

This command will:

1. **Analyze Code** (uncommitted changes or specified path)
2. **Detect Clean Code Violations**:
   - SRP violations (multiple responsibilities)
   - DRY violations (duplicate code/constants/logic)
   - Method length violations (>30 lines)
   - Class size violations (>300 lines)
   - Naming convention violations
   - Mixed abstraction levels
   - God classes
   - Feature envy patterns

3. **Provide Detailed Report**:
   - List all violations found
   - Explain why each is a violation
   - Suggest specific refactoring patterns

4. **Offer Refactoring Solutions**:
   - Extract Method pattern
   - Extract Class pattern
   - Extract Constants pattern
   - Extract Helper Methods pattern
   - Move Method pattern
   - Introduce Parameter Object pattern

5. **Apply Fixes (if requested)**:
   - Automatically refactor code
   - Re-run validation
   - Confirm all violations resolved

## Code Quality Criteria

### ✅ PASS Criteria

- Each class has single, clear responsibility
- No duplicate code, constants, or logic
- Methods ≤30 lines
- Classes ≤300 lines
- Clear, descriptive names (no "Manager", "Handler", "Utils")
- Single level of abstraction per method
- High cohesion within classes
- Low coupling between classes

### ❌ FAIL Criteria

- Multiple responsibilities in one class
- Duplicate code patterns (2+ occurrences)
- Methods >30 lines
- Classes >300 lines
- Generic/vague names ("Manager", "Helper", "Processor")
- Mixed abstraction levels (high + low in same method)
- God classes (doing everything)
- Shotgun surgery (one change affects many classes)

## Example Output

```
🔍 Code Quality Review Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Reviewing: src/main/java/com/omelet/oaasis/adapter/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ VIOLATION 1: DRY Violation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ExcelCellParser.java:45-52

Issue: Duplicate date formatters in multiple methods

Code:
```java
public LocalDateTime parseDateTime(String value) {
  DateTimeFormatter[] formatters = {
      DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
      DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss")
  };
  // ... parsing logic
}

public LocalDateTime parseTime(String value) {
  // DUPLICATE! Same formatters again
  DateTimeFormatter[] formatters = {
      DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
      DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss")
  };
  // ... parsing logic
}
```

📋 Suggested Refactor: Extract Constants
```java
private static final DateTimeFormatter[] DATETIME_FORMATTERS = {
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
    DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss")
};

public LocalDateTime parseDateTime(String value) {
  return tryParse(value, DATETIME_FORMATTERS);
}

public LocalDateTime parseTime(String value) {
  return tryParse(value, DATETIME_FORMATTERS);
}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ VIOLATION 2: SRP Violation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: OrderService.java:120-180

Issue: Method doing too many things (65 lines)

Responsibilities detected:
1. Fetch scenario
2. Validate scenario
3. Fetch candidate
4. Update candidate status
5. Assign drivers to orders (SEPARATE CONCERN!)
6. Update route status
7. Save scenario

📋 Suggested Refactor: Extract Method
```java
public Order planRouteScenario(UUID scenarioId, PlanRouteScenarioCommand command) {
  final User user = UserDetailsUtil.getCurrentUserDetails().getUser();

  final RouteScenario routeScenario = findRouteScenario(user, scenarioId);
  validateNotAlreadyPlanned(routeScenario);

  final RouteCandidate routeCandidate = findRouteCandidate(user, command.routeCandidateId());
  routeCandidate.changeStatusToComplete();

  routeScenario.setRoutePlan(createRoutePlan(routeCandidate));

  assignDriversToOrders(routeCandidate, user);  // Delegated

  return routeScenarioRepository.save(user, routeScenario);
}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PASS: OrderValidator.java
   - Single responsibility ✓
   - Methods <30 lines ✓
   - Clear naming ✓

✅ PASS: RouteOptimizer.java
   - Single responsibility ✓
   - Methods <30 lines ✓
   - Clear naming ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files reviewed: 12
Violations found: 2
  - SRP violations: 1
  - DRY violations: 1
  - Method length violations: 0
  - Class size violations: 0

SRP Score Breakdown:
| Category           | Score   | Weight | Weighted |
|--------------------|---------|--------|----------|
| Method Separation  | 60/100  | 40%    | 24       |
| Naming Clarity     | 75/100  | 20%    | 15       |
| Testability        | 55/100  | 25%    | 13.75    |
| Reusability        | 70/100  | 15%    | 10.5     |
| **Total**          |**65/100**| 100%  | **65**   |

Rating: Needs Improvement (Target: 80+)

⚠️  Code quality: FAIL
    Fix violations before committing code

Would you like me to:
1. Apply suggested refactorings automatically
2. Show more details on specific violations
3. Skip and continue anyway (NOT RECOMMENDED)
```

## Integration with /implement-feature

This command is **automatically invoked** by `/implement-feature` at Phase 6.5 (Code Quality Review).

You can also run it manually:
- During development to check your code
- Before creating commits
- During code review
- After refactoring to validate improvements

## Benefits

### For You (Developer)
- ✅ Learn clean code principles by example
- ✅ Catch quality issues before review
- ✅ Improve code maintainability
- ✅ Reduce technical debt

### For Code Review
- ✅ Less back-and-forth on style issues
- ✅ Focus on business logic, not code quality
- ✅ Faster approval process

### For Codebase
- ✅ Consistent code quality
- ✅ Better readability
- ✅ Easier maintenance
- ✅ Reduced bugs from complexity

## When to Use

**✅ Use this command when**:
- Writing new code
- Refactoring existing code
- Before creating commits
- During code review
- Learning clean code principles

**⏩ Skip this command when**:
- Emergency hotfixes (fix quality later)
- Generated code (OpenAPI, MapStruct)
- Third-party code integration
- Proof-of-concept code (will be rewritten)

## References

- Clean Code Principles: `.claude/skills/clean-code-principles.md`
- SRP violations: Section 1-3
- DRY violations: Section 11
- Refactoring patterns: Section 7

---

**IMPORTANT**: Code with quality violations should NOT be committed to the repository. Always fix violations before creating commits.
