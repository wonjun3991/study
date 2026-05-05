---
description: Pre-PR validation - check code quality before creating pull request
---

# Pre-Pull Request Validation

Validate your code changes before creating a pull request.

## Changes Description

{{USER_INPUT}}

## Validation Sequence

### 1. Architecture Review
Invoke **hexagonal-architect** agent to validate:
- New code follows Hexagonal Architecture
- Files in correct directories
- Proper layer separation maintained
- Dependencies flow correctly
- Ports and adapters properly used

**Questions to answer:**
- Are new features in the right layers?
- Is domain logic in domain services?
- Are controllers using use cases?
- Are repositories behind port interfaces?

### 2. Security Review
Invoke **security-auditor** agent to check:
- New queries have soft delete filters
- Multi-tenancy properly enforced
- Authorization specs for new repositories
- API endpoints check user permissions
- No security regressions

**Questions to answer:**
- Can users access other tenants' data?
- Are soft-deleted records hidden?
- Is authorization enforced at every level?
- Are there any IDOR vulnerabilities?

### 3. Query Review
Invoke **jpa-guardian** agent to verify:
- New entities follow standards
- Queries include deletedAt IS NULL
- Authorization specs implemented
- No N+1 queries introduced
- Proper indexes defined

**Questions to answer:**
- Do all new queries filter soft deletes?
- Is multi-tenancy filtering working?
- Are there performance issues?
- Are indexes needed?

### 4. Test Coverage
Invoke **test-runner** agent to ensure:
- Tests for new functionality exist
- All tests pass
- Coverage meets threshold (80%+)
- Integration tests included
- Authorization scenarios tested

**Questions to answer:**
- Are all new public methods tested?
- Do tests cover error cases?
- Are different user roles tested?
- Is multi-tenancy tested?

### 5. API Changes (if applicable)
Invoke **openapi-generator** agent to verify:
- OpenAPI spec updated
- Code regenerated
- Controllers implemented
- No breaking changes in v2
- Proper API versioning

**Questions to answer:**
- Is the OpenAPI spec current?
- Are DTOs generated correctly?
- Are breaking changes documented?
- Is backward compatibility maintained?

### 6. Common Mistake Review
Check for recurring issues (ref: `.claude/rules/code-review-checklist.md`):

- [ ] No entity mutation in `@Transactional(readOnly = true)` — use `toBuilder().build()` for detached copies
- [ ] Input list validation: duplicate check (`HashSet` size) + exact set match (`equals(keySet())`)
- [ ] No copy-pasted validation logic — extract shared `@Component` (e.g., `RouteDriverValidator`)
- [ ] Null guards match actual nullability — no redundant checks on guaranteed non-null values
- [ ] Time/config fallback chain (options → route → `Instant.now()`) — never raw `Instant.now()` as first choice
- [ ] No redundant DB queries — pass fetched entities to downstream methods
- [ ] i18n keys: search for duplicates before adding, both EN + KO added, consistent naming
- [ ] Unit tests exist for ALL new service classes, covering happy path + all error paths

### 7. i18n Validation
Verify i18n message management:
- Search `messages.properties` for duplicate keys before adding new ones
- Every key must exist in both `messages.properties` (EN) and `messages_ko.properties` (KO)
- Naming convention: `{domain}.{action}.{detail}.message`

## Automated Checks

Run before creating PR:
```bash
# Format code
./gradlew spotlessApply

# Run tests
./gradlew test

# Build
./gradlew build

# Verify compilation
./gradlew compileJava
```
