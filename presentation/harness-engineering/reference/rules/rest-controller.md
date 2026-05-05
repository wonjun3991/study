---
paths:
  - "src/main/java/**/adapter/in/rest/**/*.java"
---

# REST Controller Rules (Thin Layer)

> Detailed patterns: see `hexagonal-architecture` skill. Update both when changing rules.

Controllers are **thin layers** that ONLY handle HTTP concerns. They must NOT contain business logic.

## Controllers MUST do:
- HTTP request/response handling
- Extract authentication context (User from SecurityContext)
- Map DTO -> Command (using Mapper)
- Call UseCase method (single call preferred)
- Map Domain -> DTO (using Mapper)
- Return appropriate HTTP status

## Controllers MUST NOT do:
- Entity lookups (e.g., `findDriverByUserId()`, `findOrderById()`)
- Business rule validation
- Multiple service/repository calls orchestration
- Data transformation beyond simple DTO mapping
- Transaction management logic
- Any logic that might be reused by other adapters (batch, events, etc.)

## Multi-Version API Support

The application maintains two API versions (v2 and v3) simultaneously:
- **API Definitions**: `src/main/resources/openapi/tms-api-v2.yml` and `tms-api-v3.yml`
- **Generated Code**: `src/generated/java/com/omelet/oaasis/adapter/in/rest/v2` and `v3`
- **Controller Implementations**: `src/main/java/com/omelet/oaasis/adapter/in/rest/v2` and `v3`
