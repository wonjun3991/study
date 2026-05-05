---
paths:
  - "src/main/resources/openapi/**/*.yml"
  - "src/main/resources/openapi/**/*.yaml"
---

# OpenAPI Specification Guidelines

## Reusable Parameter Objects

**All API parameters MUST be defined as reusable objects** in the `components/parameters` section and referenced via `$ref`. Do NOT define parameters inline in path operations.

**Naming Convention**: `{ConceptName}Param` (e.g., `UserIdParam`, `RouteIdParam`, `PageParam`)

**Parameter Structure**:
```yaml
components:
  parameters:
    ExampleParam:
      in: query|path|header
      name: example_name
      required: true|false
      description: Description
      schema:
        $ref: '#/components/schemas/SchemaType'
```

**Usage in Paths**:
```yaml
paths:
  /api/resources/{resource_id}:
    get:
      parameters:
        - $ref: '#/components/parameters/ResourceIdParam'    # Correct
        - $ref: '#/components/parameters/PageParam'
      # NEVER define parameters inline
```

**Variants for Same Concept**:
- Path parameter: `UserIdParam` (in: path)
- Query parameter: `UserIdQueryParam` (in: query)
- Required variant: `RequiredWarehouseIdParam`
- Optional variant: `WarehouseIdParam`

**Array Parameters** (comma-separated values):
```yaml
RouteIdsParam:
  in: query
  name: route_ids
  description: List of Route identifiers (comma separated)
  style: form
  explode: false
  schema:
    type: array
    items:
      $ref: '#/components/schemas/UUID'
    example: 'uuid1,uuid2,uuid3'
```
