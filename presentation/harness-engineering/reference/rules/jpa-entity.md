---
paths:
  - "src/main/java/**/domain/**/*.java"
  - "src/main/java/**/adapter/out/persistence/jpa/**/*.java"
---

# JPA Entity & Domain Rules

> Detailed patterns: see `database-standards` skill. Update both when changing rules.

## Entity Design
- **Primary Key**: `id` (Long) is the database PK for all tables
- **External ID (`external_id`)**: UUID, aggregate identifier (DDD). Must always have a unique index
- **Do not use `@ManyToMany`** if the join table has any columns beyond the two FKs. Create a dedicated entity instead
- **`serialVersionUID`**: Required for `Serializable` classes. Do NOT declare for `record` types

## Temporal Types
- **All time-related fields in domain entities MUST use `java.time.Instant`**
- DO NOT use `LocalDateTime` or `ZonedDateTime` in domain entity classes
- **Exception**: `LocalDate` MAY be used for date-only fields (e.g., `requestedDate`)
- API DTOs may use `LocalDate`/`OffsetDateTime`; MapStruct + `DateTimeMapper` handles conversion

## Naming and Schema
- **JPA Naming**: `CamelCaseToUnderscoresNamingStrategy` - avoid redundant `@Column(name = "...")`
- **FK columns (`{xxx}_id`)**: Must have an index on all UUID FK columns
- **Enum Types**: `VARCHAR(32)`
- **Phone Numbers**: `VARCHAR(32)`
- **Timestamps**: `timestamp` data type

## Common Entity Fields (ADR-010)
- All JPA entities extend `BaseEntity` (provides `id`, `externalId`, `tenantId`, `ownerId`, `accessLevel`)
- Audit trail: `@Embedded AuditableEmbeddable` (provides `createdAt`, `createdBy`, `lastModifiedAt`, `lastModifiedBy`)
- Spring Data JPA Auditing manages audit fields automatically

## Route Entity Versioning (ADR-013)
- Routes use composite key: `externalId` + `version`
- `version = 0` = current active state
- Historical versions: `version > 0` (immutable)
- Updates: copy current to new version, then update `version = 0` record
