# Spring Boot 3 Patterns and Best Practices for OaaSIS TMS

This skill provides comprehensive Spring Boot 3 patterns, configuration examples, and best practices for the OaaSIS TMS project.

## Project Setup

- **Spring Boot Version**: 3.2.x
- **Java Version**: 21 with preview features enabled (`--enable-preview`)
- **Build System**: Gradle
- **Architecture**: Multi-module project with Hexagonal Architecture

## Key Dependencies

```gradle
spring-boot-starter-web
spring-boot-starter-data-jpa
spring-boot-starter-security
spring-boot-starter-validation
springdoc-openapi-starter-webmvc-ui
liquibase-core
mapstruct
```

## 1. Dependency Injection Patterns

### Service Layer (Domain Services)

```java
@Service
@RequiredArgsConstructor  // Lombok constructor injection
public class CreateOrderService implements CreateOrderUseCase {

  // Inject ports, not implementations
  private final OrderRepository orderRepository;
  private final ModifyStopPort modifyStopPort;

  @Override
  @PreAuthorize("hasAuthority('TMS_OPERATOR') or hasAuthority('TMS_ORG_ADMIN')")
  public Order createOrder(CreateOrderCommand command) {
    // Business logic
  }
}
```

### Repository Adapters

```java
@Component
@RequiredArgsConstructor
public class OrderJpaAdapter implements OrderRepository {

  private final OrderSpringDataJpaRepository jpaRepository;
  private final OrderMapper mapper;

  @Override
  public Order save(User user, Order order) {
    // Adapter implementation
  }
}
```

### Configuration Classes

```java
@Configuration
public class SecurityConfig {

  @Bean
  public SecurityFilterChain filterChain(HttpSecurity http) {
    // Security configuration
  }
}
```

---

## 2. Transaction Management

### Service Layer Transactions

```java
@Service
@RequiredArgsConstructor
public class ModifyRouteScenarioService implements ModifyRouteScenarioUseCase {

  // Transactions at service layer, NOT adapter layer
  @Override
  @Transactional  // Spring manages transaction
  @PreAuthorize("hasAuthority('TMS_OPERATOR')")
  public RouteScenario planRouteScenario(UUID scenarioId, PlanRouteScenarioCommand command) {
    // Multiple repository calls within single transaction
    RouteScenario scenario = routeScenarioRepository.findByExternalId(user, scenarioId)
        .orElseThrow();

    RouteCandidate candidate = routeCandidateRepository.findById(user, command.routeCandidateId())
        .orElseThrow();

    // Business logic

    return routeScenarioRepository.save(user, scenario);
  }
}
```

### Read-Only Transactions

```java
@Transactional(readOnly = true)  // Optimization for queries
public List<Order> listOrders(ListOrdersQuery query) {
  return orderRepository.listOrders(/* ... */);
}
```

### CRITICAL: Entity Mutation in `readOnly` Transactions

**NEVER modify entity fields inside `@Transactional(readOnly = true)`.**

Hibernate's dirty checking may still flush changes depending on the provider. Even if it doesn't flush in your current setup, it violates the contract and may break on upgrades.

```java
// BAD: entity may be flushed despite readOnly
@Transactional(readOnly = true)
public RouteDetailDto preview(UUID routeId) {
  Route route = routeRepository.findById(user, routeId).orElseThrow();
  route.setEstimatedMetrics(newMetrics);  // DANGER: dirty checking
  return buildDto(route);
}

// GOOD: use toBuilder() to create a detached copy
@Transactional(readOnly = true)
public RouteDetailDto preview(UUID routeId) {
  Route route = routeRepository.findById(user, routeId).orElseThrow();
  Route detached = route.toBuilder().build();
  detached.setEstimatedMetrics(newMetrics);  // safe — not JPA-managed
  return buildDto(detached);
}
```

### Transaction Propagation

```java
// Default: REQUIRED (join existing or create new)
@Transactional

// Create new transaction always
@Transactional(propagation = Propagation.REQUIRES_NEW)

// No transaction
@Transactional(propagation = Propagation.NOT_SUPPORTED)
```

---

## 3. Spring Security Integration

### Method-Level Security

```java
@PreAuthorize("hasAuthority('TMS_SYSTEM_ADMIN') or " +
             "hasAuthority('TMS_ORG_ADMIN') or " +
             "hasAuthority('TMS_OPERATOR')")
public Order updateOrder(UUID orderId, UpdateOrderCommand command) {
  // Only accessible to specific roles
}
```

### Role Hierarchy

```
SYSTEM_ADMIN > ORG_ADMIN > OPERATOR > USER > DRIVER
```

### SecurityContext Usage

```java
// Get current user
User user = UserDetailsUtil.getCurrentUserDetails().getUser();

// Check roles programmatically
if (SecurityUtils.hasRole("TMS_ADMIN")) {
  // Admin-only logic
}
```

---

## 4. Spring Data JPA Patterns

### Interface-Based Repositories

```java
public interface OrderSpringDataJpaRepository extends JpaRepository<OrderJpaEntity, Long>,
    JpaSpecificationExecutor<OrderJpaEntity> {

  // Query methods
  Optional<OrderJpaEntity> findByExternalIdAndTenantIdAndDeletedAtIsNull(
      UUID externalId, UUID tenantId);

  // Custom queries
  @Query("SELECT DISTINCT o FROM OrderJpaEntity o " +
         "JOIN FETCH o.shipments s " +
         "WHERE o.tenantId = :tenantId AND o.deletedAt IS NULL")
  List<OrderJpaEntity> findAllByTenantId(@Param("tenantId") UUID tenantId);
}
```

### Specifications (Dynamic Queries)

```java
public class OrderSpecifications {

  public static Specification<OrderJpaEntity> hasStatus(OrderStatus status) {
    return (root, query, cb) ->
        cb.equal(root.get("status"), status);
  }

  public static Specification<OrderJpaEntity> notDeleted() {
    return (root, query, cb) ->
        cb.isNull(root.get("deletedAt"));
  }
}
```

---

## 5. Configuration Management

### application.yml Structure

```yaml
spring:
  application:
    name: oaasis-tms-be
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:local}

  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/oaasis_tms}
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}

  jpa:
    hibernate:
      ddl-auto: validate  # Use Liquibase, not Hibernate DDL
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true

  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.xml
```

### Profile-Specific Configs

- `application-local.yml`: Local development
- `application-test.yml`: Test environment (H2)
- `application-dev.yml`: Dev server
- `application-prod.yml`: Production

### @ConfigurationProperties

```java
@ConfigurationProperties(prefix = "oaasis.solver")
@ConstructorBinding
public record SolverConfig(
    String baseUrl,
    int timeoutSeconds,
    int maxRetries
) {}
```

---

## 6. Exception Handling

### Global Exception Handler

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(LocalizedOaasisProblem.class)
  public ResponseEntity<ProblemDetail> handleOaasisProblem(LocalizedOaasisProblem ex) {
    // Convert to RFC 7807 Problem Details
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(
        HttpStatus.BAD_REQUEST,
        messageSource.getMessage(ex.getMessageKey(), /* ... */)
    );
    return ResponseEntity.of(problem).build();
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  public ResponseEntity<ProblemDetail> handleValidationError(MethodArgumentNotValidException ex) {
    // Handle @Valid validation errors
  }
}
```

### Domain Exceptions

```java
public class LocalizedOaasisProblem extends RuntimeException {
  private final String messageKey;  // i18n key
  private final Map<String, String> fieldErrors;
}
```

---

## 7. Validation

### DTO Validation

```java
public record CreateOrderRequest(
    @NotNull(message = "{order.customer.required}")
    String customerName,

    @NotBlank(message = "{order.address.required}")
    @Size(max = 500)
    String destAddress,

    @DecimalMin(value = "0.0", inclusive = false)
    BigDecimal volumeCbm
) {}
```

### Service Layer Validation

```java
@Service
public class CreateOrderService {

  public Order createOrder(@Valid CreateOrderCommand command) {
    // @Valid triggers validation

    // Business rule validation
    if (command.preferredDate().isBefore(LocalDate.now())) {
      throw new LocalizedOaasisProblem("order.preferredDate.past");
    }
  }
}
```

---

## 8. Async Processing

### @Async Methods

```java
@Service
public class NotificationService {

  @Async("taskExecutor")  // Use named executor
  public CompletableFuture<Void> sendOrderCreatedNotification(Order order) {
    // Async notification
    return CompletableFuture.completedFuture(null);
  }
}
```

### Task Executor Configuration

```java
@Configuration
@EnableAsync
public class AsyncConfig {

  @Bean(name = "taskExecutor")
  public Executor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(2);
    executor.setMaxPoolSize(5);
    executor.setQueueCapacity(100);
    executor.setThreadNamePrefix("async-");
    executor.initialize();
    return executor;
  }
}
```

---

## 9. Event-Driven Architecture

### Domain Events

```java
// Event
public record OrderCreatedEvent(UUID orderId, UUID tenantId) {}

// Publisher (in domain service)
@Service
@RequiredArgsConstructor
public class CreateOrderService {

  private final ApplicationEventPublisher eventPublisher;

  public Order createOrder(CreateOrderCommand command) {
    Order order = // ... create order

    // Publish event
    eventPublisher.publishEvent(new OrderCreatedEvent(
        order.getExternalId(),
        order.getTenantId()
    ));

    return order;
  }
}

// Listener
@Component
public class OrderEventListener {

  @EventListener
  @Async
  public void handleOrderCreated(OrderCreatedEvent event) {
    // Handle event asynchronously
  }
}
```

---

## 10. Testing Support

### Test Configuration

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class OrderServiceTest {

  @Autowired
  private MockMvc mockMvc;

  @Autowired
  private ObjectMapper objectMapper;

  @Test
  void testCreateOrder() {
    SecurityTestUtils.setAuthenticatedUser();
    // Test logic
  }
}
```

### Test Slicing

```java
// Repository test
@DataJpaTest
class OrderRepositoryTest { }

// Web layer test
@WebMvcTest(OrderController.class)
class OrderControllerTest { }

// Service test with mocks
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
  @Mock
  private OrderRepository orderRepository;

  @InjectMocks
  private CreateOrderService createOrderService;
}
```

---

## 11. Project-Specific Patterns

### Multi-Tenancy with Spring

```java
@Service
@RequiredArgsConstructor
public class TenantAwareService {

  public List<Order> getOrders() {
    // Always get current user from SecurityContext
    User user = UserDetailsUtil.getCurrentUserDetails().getUser();

    // Pass user to repository (adapter handles filtering)
    return orderRepository.findByTenantId(user.getTenantId());
  }
}
```

### Soft Delete with Spring Data

```java
// Custom repository base
public interface SoftDeleteRepository<T, ID> extends JpaRepository<T, ID> {

  @Override
  @Query("SELECT e FROM #{#entityName} e WHERE e.deletedAt IS NULL")
  List<T> findAll();

  @Modifying
  @Query("UPDATE #{#entityName} e SET e.deletedAt = CURRENT_TIMESTAMP WHERE e.id = :id")
  void softDelete(@Param("id") ID id);
}
```

---

## Critical Rules

### ✅ ALWAYS

1. **Use Constructor Injection** (via `@RequiredArgsConstructor`)
   - Enables immutability
   - Makes dependencies explicit
   - Supports testing

2. **@Transactional at Service Layer**
   - NOT at repository/adapter layer
   - Service methods define transaction boundaries

3. **@PreAuthorize for Method Security**
   - Check roles/permissions at service layer
   - Don't rely only on controller-level security

4. **Profile-Specific Configuration**
   - Use `application-{profile}.yml`
   - Environment variables for secrets

5. **Liquibase for Schema Changes**
   - NEVER use `hibernate.ddl-auto=update`
   - Always `ddl-auto=validate`

### ❌ NEVER

1. **Field Injection** (`@Autowired` on fields)
   - Hard to test
   - Hides dependencies

2. **@Transactional on Adapters**
   - Transactions belong to business logic layer
   - Adapters should be transaction-agnostic

3. **Mixing Framework Annotations in Domain**
   - Domain should be pure Java
   - Framework concerns belong in adapters

4. **Hardcoding Configuration**
   - Use `application.yml` or `@ConfigurationProperties`
   - Externalize environment-specific values

5. **Swallowing Exceptions**
   - Let exceptions bubble up
   - Use global exception handler

---

**This skill should be invoked whenever**:
- Implementing Spring Boot services
- Configuring Spring features
- Setting up transactions or security
- Creating test infrastructure
- Reviewing Spring Boot code
