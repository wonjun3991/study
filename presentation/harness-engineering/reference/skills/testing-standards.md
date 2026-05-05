# Testing Standards for OaaSIS TMS

This skill provides comprehensive testing standards and patterns for the OaaSIS TMS project.

## Test Categories

### 1. Unit Tests
**Location**: `src/test/java/{package}/domain/` or `src/test/java/{package}/application/`

**Purpose**: Test business logic in isolation

**Characteristics**:
- Fast execution (no Spring context, no database)
- Mock all dependencies
- Focus on domain services and use cases
- Test edge cases and validation logic

**Example**:
```java
@ExtendWith(MockitoExtension.class)
class ProcessOrderServiceTest {

  @Mock
  private OrderRepository orderRepository;

  @InjectMocks
  private ProcessOrderService service;

  @Test
  @DisplayName("Should validate order before processing")
  void shouldValidateOrder() {
    // given
    Order invalidOrder = Order.builder()
        .status(OrderStatus.CANCELLED)
        .build();

    // when / then
    assertThrows(IllegalStateException.class,
        () -> service.process(invalidOrder));
  }
}
```

### 2. Integration Tests (REST API)
**Location**: `src/test/java/{package}/adapter/in/rest/`

**Purpose**: Test REST endpoints end-to-end

**Characteristics**:
- Uses `@SpringBootTest` with `@AutoConfigureMockMvc`
- H2 in-memory database
- Real Spring context
- Tests request/response mapping
- Tests authentication/authorization
- Tests validation errors

**Example**:
```java
@SpringBootTest
@AutoConfigureMockMvc
class OrderV3ApiImplTest {

  @Autowired
  private MockMvc mockMvc;

  @Autowired
  private ObjectMapper objectMapper;

  @Test
  @WithMockUser(roles = "ADMIN")
  @DisplayName("POST /api/v3/orders should create order")
  void shouldCreateOrder() throws Exception {
    // given
    CreateOrderRequest request = new CreateOrderRequest()
        .orderNumber("ORD-001")
        .customerId(UUID.randomUUID());

    // when / then
    mockMvc.perform(post("/api/v3/orders")
        .contentType(MediaType.APPLICATION_JSON)
        .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.orderId").exists())
        .andExpect(jsonPath("$.orderNumber").value("ORD-001"));
  }

  @Test
  @WithMockUser(roles = "USER")
  @DisplayName("GET /api/v3/orders should return only user's orders")
  void shouldFilterByOwner() throws Exception {
    // Test multi-tenancy filtering
    mockMvc.perform(get("/api/v3/orders"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray());
  }
}
```

### 3. Repository Tests
**Location**: `src/test/java/{package}/adapter/out/persistence/jpa/`

**Purpose**: Test JPA queries and specifications

**Characteristics**:
- Uses `@DataJpaTest` (lighter than `@SpringBootTest`)
- H2 in-memory database
- Tests custom queries (`@Query`, QueryDSL, Specifications)
- Tests soft delete filtering
- Tests multi-tenancy filtering
- Tests pagination

**Example**:
```java
@DataJpaTest
class OrderJpaRepositoryTest {

  @Autowired
  private OrderSpringDataJpaRepository repository;

  @Autowired
  private TestEntityManager entityManager;

  @Test
  @DisplayName("findByExternalId should filter soft-deleted records")
  void shouldExcludeSoftDeleted() {
    // given
    OrderJpaEntity activeOrder = createOrder();
    OrderJpaEntity deletedOrder = createOrder();
    deletedOrder.setDeletedAt(Instant.now());

    entityManager.persist(activeOrder);
    entityManager.persist(deletedOrder);
    entityManager.flush();

    // when
    Optional<OrderJpaEntity> result = repository
        .findByExternalIdAndTenantId(
            activeOrder.getExternalId(),
            activeOrder.getTenantId());

    // then
    assertThat(result).isPresent();
    assertThat(result.get().getDeletedAt()).isNull();
  }

  @Test
  @DisplayName("Should respect tenant isolation")
  void shouldFilterByTenant() {
    // Test cross-tenant isolation
    UUID tenant1 = UUID.randomUUID();
    UUID tenant2 = UUID.randomUUID();

    OrderJpaEntity order1 = createOrder(tenant1);
    OrderJpaEntity order2 = createOrder(tenant2);

    entityManager.persist(order1);
    entityManager.persist(order2);
    entityManager.flush();

    // when
    List<OrderJpaEntity> tenant1Orders = repository
        .findByTenantId(tenant1);

    // then
    assertThat(tenant1Orders).hasSize(1);
    assertThat(tenant1Orders.get(0).getTenantId()).isEqualTo(tenant1);
  }
}
```

### 4. Mapper Tests
**Location**: `src/test/java/{package}/adapter/mapper/`

**Purpose**: Test MapStruct mappers

**Characteristics**:
- Uses `@SpringBootTest` (needs Spring to inject mappers)
- Tests domain ↔ DTO conversions
- Tests null handling
- Tests nested object mapping
- Tests collection mapping

**Example**:
```java
@SpringBootTest
class OrderMapperTest {

  @Autowired
  private OrderMapper mapper;

  @Test
  @DisplayName("Should map Order to OrderDto correctly")
  void shouldMapToDto() {
    // given
    Order order = Order.builder()
        .externalId(UUID.randomUUID())
        .orderNumber("ORD-001")
        .status(OrderStatus.PENDING)
        .build();

    // when
    OrderDto dto = mapper.toDto(order);

    // then
    assertThat(dto.getOrderId()).isEqualTo(order.getExternalId());
    assertThat(dto.getOrderNumber()).isEqualTo("ORD-001");
    assertThat(dto.getStatus()).isEqualTo(OrderStatusDto.PENDING);
  }

  @Test
  @DisplayName("Should handle null values gracefully")
  void shouldHandleNulls() {
    // given
    Order order = Order.builder()
        .externalId(UUID.randomUUID())
        .orderNumber(null)  // Null field
        .build();

    // when
    OrderDto dto = mapper.toDto(order);

    // then
    assertThat(dto.getOrderNumber()).isNull();
  }
}
```

### 5. Security Tests
**Location**: `src/test/java/{package}/adapter/in/rest/` (mixed with integration tests)

**Purpose**: Test authorization and multi-tenancy

**Characteristics**:
- Uses `@WithMockUser` for different roles
- Tests 403 Forbidden responses
- Tests cross-tenant access prevention
- Tests role-based access control

**Example**:
```java
@SpringBootTest
@AutoConfigureMockMvc
class OrderSecurityTest {

  @Autowired
  private MockMvc mockMvc;

  @Test
  @WithMockUser(roles = "USER")
  @DisplayName("USER should not access other user's orders")
  void shouldPreventCrossTenantAccess() throws Exception {
    // given
    UUID otherUsersOrderId = UUID.randomUUID();

    // when / then
    mockMvc.perform(get("/api/v3/orders/" + otherUsersOrderId))
        .andExpect(status().isForbidden());
  }

  @Test
  @WithAnonymousUser
  @DisplayName("Anonymous user should get 401")
  void shouldRequireAuthentication() throws Exception {
    mockMvc.perform(get("/api/v3/orders"))
        .andExpect(status().isUnauthorized());
  }

  @Test
  @WithMockUser(roles = "ADMIN")
  @DisplayName("ADMIN can access all tenants")
  void adminCanAccessAll() throws Exception {
    mockMvc.perform(get("/api/v3/orders"))
        .andExpect(status().isOk());
  }
}
```

## Coverage Requirements

### Minimum Coverage Targets
- **Overall**: 80% line coverage
- **Domain layer**: 90% (critical business logic)
- **Application layer**: 85% (use cases)
- **Adapter layer**: 75% (infrastructure)
- **Mappers**: 100% (simple transformations)

### What to Test
- ✅ Business logic
- ✅ Validation rules
- ✅ Edge cases and error handling
- ✅ Multi-tenancy isolation
- ✅ Soft delete filtering
- ✅ Authorization checks
- ✅ Null handling
- ✅ Collection operations

### What NOT to Test
- ❌ Getters/setters (covered by coverage tools)
- ❌ Framework code (Spring, JPA)
- ❌ Generated code (MapStruct implementations, OpenAPI)
- ❌ Simple DTOs with no logic
- ❌ Configuration classes

## Test Data Management

### Test User Fixtures
```java
public class TestUserFixtures {

  public static User systemAdmin() {
    return User.builder()
        .externalId(UUID.randomUUID())
        .tenantId(UUID.randomUUID())
        .roles(Set.of(UserRoleType.TMS_SYSTEM_ADMIN))
        .build();
  }

  public static User orgAdmin(UUID tenantId) {
    return User.builder()
        .externalId(UUID.randomUUID())
        .tenantId(tenantId)
        .roles(Set.of(UserRoleType.TMS_ORGANIZATION_ADMIN))
        .build();
  }

  public static User regularUser(UUID tenantId, UUID ownerId) {
    return User.builder()
        .externalId(ownerId)
        .tenantId(tenantId)
        .roles(Set.of(UserRoleType.TMS_USER))
        .build();
  }
}
```

### Test Data Builders
```java
public class OrderTestBuilder {

  private UUID externalId = UUID.randomUUID();
  private UUID tenantId = UUID.randomUUID();
  private UUID ownerId = UUID.randomUUID();
  private String orderNumber = "ORD-001";
  private OrderStatus status = OrderStatus.PENDING;

  public OrderTestBuilder withExternalId(UUID externalId) {
    this.externalId = externalId;
    return this;
  }

  public OrderTestBuilder withTenant(UUID tenantId) {
    this.tenantId = tenantId;
    return this;
  }

  public Order build() {
    return Order.builder()
        .externalId(externalId)
        .tenantId(tenantId)
        .ownerId(ownerId)
        .orderNumber(orderNumber)
        .status(status)
        .build();
  }
}
```

## Naming Conventions

### Test Class Names
- Unit test: `{ClassName}Test` (e.g., `ProcessOrderServiceTest`)
- Integration test: `{ClassName}IntegrationTest` or `{ApiClassName}Test`
- Repository test: `{RepositoryClassName}Test`

### Test Method Names
**Pattern**: `should{ExpectedBehavior}_when{Condition}`

**Examples**:
- `shouldCreateOrder_whenValidRequest()`
- `shouldThrowException_whenInvalidStatus()`
- `shouldFilterDeleted_whenQueryingOrders()`
- `shouldPreventAccess_whenDifferentTenant()`

### Display Names
Use `@DisplayName` for readable descriptions:
```java
@Test
@DisplayName("Should create order when request is valid")
void shouldCreateOrder_whenValidRequest() {
  // ...
}
```

## Test Profiles

### application-test.yml
```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true
  liquibase:
    enabled: true
    contexts: test

logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql.BasicBinder: TRACE
```

## Test Utilities

### Common Assertions
```java
// Multi-tenancy
assertThat(result.getTenantId()).isEqualTo(user.getTenantId());

// Soft delete
assertThat(result.getDeletedAt()).isNull();

// Authorization
assertThat(result.getOwnerId()).isEqualTo(user.getExternalId());

// Collections
assertThat(results).hasSize(3);
assertThat(results).extracting(Order::getOrderNumber)
    .containsExactly("ORD-001", "ORD-002", "ORD-003");

// Exceptions
assertThrows(IllegalArgumentException.class,
    () -> service.process(invalidOrder));
assertThatThrownBy(() -> service.process(invalidOrder))
    .isInstanceOf(IllegalArgumentException.class)
    .hasMessage("Invalid order status");
```

### MockMvc Helpers
```java
// JSON assertions
mockMvc.perform(get("/api/v3/orders"))
    .andExpect(status().isOk())
    .andExpect(jsonPath("$.content").isArray())
    .andExpect(jsonPath("$.content[0].orderId").exists())
    .andExpect(jsonPath("$.totalElements").value(10));

// Headers
mockMvc.perform(post("/api/v3/orders")
    .header("Authorization", "Bearer " + token)
    .contentType(MediaType.APPLICATION_JSON)
    .content(requestJson))
    .andExpect(header().exists("Location"));
```

## Mandatory Test Scenarios

Every feature MUST include tests for:

### 1. Happy Path
- ✅ Valid request succeeds
- ✅ Returns expected data
- ✅ Side effects occur correctly

### 2. Validation
- ✅ Required fields missing → 400 Bad Request
- ✅ Invalid format → 400 Bad Request
- ✅ Business rule violation → 400 Bad Request

### 3. Authorization
- ✅ USER can access own resources
- ✅ USER cannot access others' resources
- ✅ ADMIN can access all resources
- ✅ Unauthenticated → 401 Unauthorized

### 4. Multi-Tenancy
- ✅ Tenant A cannot see Tenant B's data
- ✅ SystemAdmin sees all tenants
- ✅ OrgAdmin sees only own tenant

### 5. Soft Delete
- ✅ Deleted records not returned
- ✅ Deleted records can be queried explicitly (if needed)
- ✅ Cascading soft delete works

### 6. Edge Cases
- ✅ Empty collections
- ✅ Null values
- ✅ Boundary values
- ✅ Concurrent modifications

## CI/CD Integration

### Running Tests
```bash
# All tests
./gradlew test

# Specific test class
./gradlew test --tests "OrderServiceTest"

# Specific test method
./gradlew test --tests "OrderServiceTest.shouldCreateOrder"

# With coverage
./gradlew test jacocoTestReport

# Skip integration tests (faster)
./gradlew test -x integrationTest
```

### Coverage Reports
**Location**: `build/reports/jacoco/test/html/index.html`

**Excludes** (configured in build.gradle):
- Config classes
- DTOs
- Mappers (MapStruct generated)
- Exceptions
- Generated code

## Mandatory Tests for New Services

**Every new domain service class MUST have a corresponding test class.** This is non-negotiable.

### Required Test Coverage for Services

| Scenario | Required? | Example |
|----------|-----------|---------|
| Happy path (success) | **YES** | `reorderRoute_success_previewModeNoDbSave` |
| Every validation error path | **YES** | `reorderRoute_duplicateOrderIds_throwsException` |
| Entity not found | **YES** | `reorderRoute_routeNotFound_throwsException` |
| Authorization/ownership | **YES** | `reorderRoute_driverNotOwner_throwsException` |
| No-save verification (preview) | **YES** if readOnly | `verify(repo, never()).save(any(), any())` |
| Edge cases (null vehicle, etc.) | **YES** | `reorderRoute_noVehicle_success` |
| Side effect verification | **YES** | `assertThat(route.getChangeReason()).isEqualTo(DRIVER_REORDER)` |

### Test Structure Pattern

```java
@ExtendWith(MockitoExtension.class)
class MyServiceTest {

  @Mock private MyRepository myRepository;
  @Mock private MyValidator myValidator;
  @InjectMocks private MyService myService;
  @Captor private ArgumentCaptor<MyEntity> entityCaptor;

  @BeforeEach
  void setUp() {
    SecurityTestUtils.setAuthenticatedDriver();  // or setAuthenticatedOperator()
    user = UserDetailsUtil.getCurrentUserDetails().getUser();
  }

  @Nested @DisplayName("Success Cases")
  class SuccessCases { ... }

  @Nested @DisplayName("Validation Errors")
  class ValidationErrors { ... }

  @Nested @DisplayName("Not Found Cases")
  class NotFoundCases { ... }
}
```

### ArgumentCaptor for Side Effect Verification

Use `ArgumentCaptor` to verify what was saved to the database:

```java
@Captor private ArgumentCaptor<Route> routeCaptor;

when(routeRepository.save(any(), routeCaptor.capture()))
    .thenAnswer(invocation -> invocation.getArgument(1));

// ... call service ...

Route savedRoute = routeCaptor.getValue();
assertThat(savedRoute.getChangeReason()).isEqualTo(RouteChangeReason.DRIVER_REORDER);
assertThat(savedRoute.getStopAssignments()).allMatch(sa -> sa.getStatus() == StopStatus.PLANNED);
```

## Summary Checklist

When implementing a new feature, ensure:
- [ ] Unit tests for domain services (90% coverage)
- [ ] Integration tests for REST endpoints
- [ ] Repository tests for queries (soft delete + tenant filter)
- [ ] Mapper tests for DTO conversions
- [ ] Security tests for authorization
- [ ] Multi-tenancy tests (cross-tenant isolation)
- [ ] Edge cases and error handling tested
- [ ] **Field-mapping tests for ALL hand-written merge/update methods** (see below)
- [ ] Test names follow conventions
- [ ] All tests pass locally
- [ ] Coverage meets minimum targets (80%)

## Field-Mapping Test Requirements (Mandatory)

> ⚠️ **Root Cause**: `Order.mergeFirstOrderItem()` once merged only 3 of 11 fields, silently dropping `category`, `sku`, `quantity`, and 5 others. Tests must prevent this.

Every hand-written field-mapping method **must** have a dedicated test verifying **ALL fields**:

### Scope

| Method Type | Location | Test Type |
|---|---|---|
| Domain merge (`mergeFirstOrderItem()`, `mergeFirstShipment()`) | `domain/order/Order.java` | Domain unit test |
| JPA update (`updateOrderItemFields()`, `updateShipmentFields()`) | `adapter/out/persistence/jpa/` | JPA repository unit test |

### Required Test Cases

1. **All-fields-updated**: Set ALL fields → update with new values → assert EVERY field changed
2. **Null-preservation**: Set ALL fields → update with nulls → assert originals preserved

### Pattern

```java
@Test
@DisplayName("shouldMergeAllOrderItemFields: 모든 OrderItem 필드가 업데이트된다")
void shouldMergeAllOrderItemFields() {
  OrderItem existing = OrderItem.builder()
      .sku("OLD").name("Old").category("OldCat")
      .quantity(1).weightKg(1.0).volumeCbm(0.1)
      .lengthCm(10.0).widthCm(5.0).heightCm(3.0).note("old")
      .build();
  // set up incoming with ALL new values
  // call updateFrom()
  // assert EVERY field updated — no field left behind
}
```

### Field Count Guard

When adding a new field to a domain/entity class:
1. Update the hand-written merge/update method
2. Update the corresponding test to include the new field
3. A test that only verifies a subset of fields is **incomplete**

---

**This skill should be invoked whenever**:
- Writing tests for new features
- Reviewing test coverage
- Debugging test failures
- Validating test quality
- Setting up test infrastructure
