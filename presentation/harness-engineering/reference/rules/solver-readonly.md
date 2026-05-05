---
paths:
  - "clients/oaasis-tms-solver/**/*"
---

# CRITICAL: Solver API Specification - READ ONLY

**DO NOT MODIFY** `clients/oaasis-tms-solver/openapi/solver-api-v2.yaml`

- This OpenAPI specification is **managed by the engine team**
- Changes must come from the engine team's repository
- **Never** add, remove, or modify fields in `solver-api-v2.yaml` directly

## When the engine team updates their API:
1. Manually copy the updated specification from the engine repository
2. Regenerate: `./gradlew :clients:oaasis-tms-solver:cleanGenerated :clients:oaasis-tms-solver:openApiGenerate -x :clients:oaasis-tms-solver:test`
3. Update mappers in `src/main/java/com/omelet/oaasis/adapter/out/service/solver/mapper/` if needed

**Violation of this rule can cause integration failures with the optimization engine.**
