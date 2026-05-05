---
paths:
  - "src/main/resources/db/**/*"
---

# Database Migration Rules

> Detailed patterns: see `liquibase-patterns` skill. Update both when changing rules.

## Liquibase for DDL
- All schema changes (CREATE, ALTER, DROP) **must** use Liquibase changesets in `src/main/resources/db/changelog/`

## One-time Data Migration Scripts
- **DO NOT commit** one-time data migration scripts (UPDATE, INSERT for existing data) to the repository
- Provide them as **PR comments** for immediate execution after deployment
- Examples: Setting initial values for new columns, migrating data between structures

## Repeatable Seed Data
- Test/seed data that may be re-executed can be kept in `src/main/resources/db/data.sql`

## Workflow
1. Create Liquibase changeset: `20251229-01.xml` (adds new column with default value)
2. Write one-time migration script to set correct values based on existing data
3. Add migration script as **PR comment**, not as a file in the repository
4. After deployment, DBA executes the script from PR comment
