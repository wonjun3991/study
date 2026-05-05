# Implementation Safety Rules

These rules **must be followed during code writing**, not just at review time. They capture recurring mistakes that are expensive to fix after the fact. **Apply every rule as you write code.**

## 1. JPA `readOnly` Transaction — Do NOT Mutate Entities

In `@Transactional(readOnly = true)`, **never modify entity fields**. Hibernate may flush dirty state to the database depending on the provider, causing unintended writes.

```java
// BAD: Mutating entity inside readOnly transaction
@Transactional(readOnly = true)
public RouteDetailDto preview(UUID routeId) {
  Route route = routeRepository.findById(user, routeId).orElseThrow();
  route.setEstimatedMetrics(newMetrics);  // DANGER: dirty checking may flush this
  return buildDto(route);
}

// GOOD: Use a detached copy via toBuilder()
@Transactional(readOnly = true)
public RouteDetailDto preview(UUID routeId) {
  Route route = routeRepository.findById(user, routeId).orElseThrow();
  Route previewRoute = route.toBuilder().build();  // detached copy
  previewRoute.setEstimatedMetrics(newMetrics);    // safe
  return buildDto(previewRoute);
}
```

## 2. Input Validation — Duplicate and Set Equality Checks

When accepting a list of IDs from the client, always validate:
1. **No duplicates** in the input list
2. **Exact match** between input set and expected set

```java
private void validateOrderIds(List<UUID> orderIds, Map<UUID, Order> orderById) {
  // Step 1: Reject duplicates
  Set<UUID> uniqueIds = new HashSet<>(orderIds);
  if (uniqueIds.size() != orderIds.size()) {
    throw new LocalizedOaasisProblem("route.reorder.duplicateOrders.message");
  }
  // Step 2: Exact set match (no missing, no extra)
  if (!uniqueIds.equals(orderById.keySet())) {
    throw new LocalizedOaasisProblem("route.reorder.missingOrders.message");
  }
}
```

## 3. DRY — Extract Shared Validation into Components

When two or more services share identical validation steps (e.g., driver ownership, status checks), extract them into a shared `@Component`.

```java
@Component
@RequiredArgsConstructor
public class RouteDriverValidator {
  public Driver validateDriverOwnership(User user, Route route) { ... }
  public void validateRouteStatus(Route route) { ... }
  public void validateRouteScenarioApprovedStatus(User user, UUID depotRouteId) { ... }
}
```

Do NOT copy-paste validation logic between services.

## 4. Null Guards — Check the Right Condition

When a value is guaranteed non-null by earlier validation, do not add redundant null checks that obscure intent. Conversely, check the correct variable:

```java
// BAD: driver is guaranteed non-null by validateDriverOwnership, vehicle may be null
if (driver != null && vehicle != null) { ... }

// GOOD: only check what can actually be null
if (vehicle != null) { ... }
```

## 5. Fallback Chains for Time/Config Values

Never fall back directly to `Instant.now()`. Always try existing configuration first:

```java
private Instant resolveDeliveryStartTime(Route route, RouteOptimizationOptions options) {
  // 1. Original optimization options
  if (options != null && options.getTimeOptions() != null
      && options.getTimeOptions().getDeliveryStartTime() != null) {
    return options.getTimeOptions().getDeliveryStartTime();
  }
  // 2. Route's planned delivery time
  if (route.getPlannedDeliveryTimeWindow() != null
      && route.getPlannedDeliveryTimeWindow().startTime() != null) {
    return route.getPlannedDeliveryTimeWindow().startTime();
  }
  // 3. Last resort
  return Instant.now();
}
```

## 6. Redundant Queries — Reuse Fetched Entities

If a method fetches an entity (e.g., `DepotRoute`), pass it to downstream methods instead of re-querying.

```java
// BAD: Fetch DepotRoute twice
DepotRoute depotRoute = recalculateDepotRouteMetrics(user, depotRouteId);
// ... buildRouteDetailDto re-fetches depotRoute internally

// GOOD: Pass the already-fetched entity
DepotRoute depotRoute = recalculateDepotRouteMetrics(user, depotRouteId);
return buildRouteDetailDto(user, savedRoute, depotRoute);
```

## 7. i18n Message Key Management

- **No duplicate keys** across `messages.properties` and `messages_ko.properties`
- **Always add both EN and KO** when creating a new key
- **Use specific prefixes**: `{domain}.{action}.{detail}.message`
- **Before adding a key**, search existing keys to avoid duplicates:
  ```
  route.find.notFound.message       (unified — do NOT create route.notFound.message)
  route.reorder.duplicateOrders.message
  route.reorder.missingOrders.message
  ```

## 8. Tests Are Mandatory

Every new service class MUST have a corresponding test class. Tests must cover:
- **Happy path** (success scenarios)
- **All validation error paths** (each thrown exception)
- **Edge cases** (null vehicle, empty lists, etc.)
- **Side effect verification** (`verify(repo, never()).save()` for preview mode)

Use the existing test patterns:
- `@ExtendWith(MockitoExtension.class)` + `@Mock` + `@InjectMocks`
- `@Nested` classes for grouping
- `SecurityTestUtils.setAuthenticatedDriver()` in `@BeforeEach`
- `assertThatThrownBy()` for exception tests
- `ArgumentCaptor` for verifying saved entities

## Implementation Checklist (Apply While Writing Code)

Before considering any service method complete, verify:

```
- [ ] No entity mutation in `@Transactional(readOnly = true)` — use `toBuilder().build()`
- [ ] Input list validated: no duplicates + exact set match
- [ ] No copy-pasted validation logic — shared `@Component` extracted
- [ ] Null checks match actual nullability (no redundant guards)
- [ ] Time/config values use fallback chains, not raw `Instant.now()`
- [ ] No redundant DB queries — reuse fetched entities via parameters
- [ ] i18n keys: searched existing keys first, both EN + KO added
- [ ] Unit tests written for all new service classes
- [ ] Tests cover happy path + all validation error paths + edge cases
```
