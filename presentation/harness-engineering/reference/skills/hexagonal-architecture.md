# Hexagonal Architecture (Ports & Adapters) for OaaSIS TMS

This skill provides comprehensive guidance on Hexagonal Architecture principles for the OaaSIS TMS project.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Adapter Layer                        │
│  (REST Controllers, JPA Repositories, External Services)│
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Application Layer                       │
│      (Ports: Use Case Interfaces, Repository Interfaces)│
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Domain Layer                           │
│     (Domain Models, Domain Services, Business Logic)    │
└─────────────────────────────────────────────────────────┘
```

## The Three Layers

### 1. Domain Layer (`src/main/java/.../domain/`)

**Purpose**: Contains pure business logic with ZERO external dependencies

**What Belongs Here**:
- ✅ Domain models (aggregate roots, entities, value objects)
- ✅ Domain services (business logic)
- ✅ Domain events
- ✅ Domain exceptions
- ✅ Business rules and validation

**What DOES NOT Belong Here**:
- ❌ Framework annotations (Spring, JPA, Jackson)
- ❌ Database concerns
- ❌ HTTP/REST concerns
- ❌ External service calls
- ❌ Infrastructure dependencies

**Example**:
```java
// domain/order/Order.java
public class Order {
  private UUID externalId;
  private String orderNumber;
  private OrderStatus status;
  private List<OrderItem> items;

  // Rich behavior, NOT anemic model
  public void changeStatusToAssigned(UUID driverId) {
    if (this.status != OrderStatus.IN_SCENARIO) {
      throw new IllegalStateException(
        "Order must be IN_SCENARIO to be assigned");
    }
    this.status = OrderStatus.ASSIGNED;
    this.assignedDriverId = driverId;
  }

  public Money calculateTotal() {
    return items.stream()
        .map(OrderItem::getPrice)
        .reduce(Money.ZERO, Money::add);
  }
}

// domain/order/ProcessOrderService.java
@RequiredArgsConstructor
public class ProcessOrderService {

  // Domain service implementing business logic
  public Order processOrder(Order order, User user) {
    // Business rules
    if (order.isEmpty()) {
      throw new EmptyOrderException();
    }

    order.validate();
    order.changeStatus(OrderStatus.PROCESSING);

    return order;
  }
}
```

### 2. Application Layer (`src/main/java/.../application/`)

**Purpose**: Defines ports (interfaces) and orchestrates domain logic

**Structure**:
```
application/
├── port/
│   ├── in/              # Inbound ports (Use Cases)
│   │   └── order/
│   │       ├── CreateOrderUseCase.java
│   │       ├── UpdateOrderUseCase.java
│   │       └── FindOrderUseCase.java
│   └── out/             # Outbound ports (Repositories, Services)
│       ├── order/
│       │   └── OrderRepository.java
│       └── notification/
│           └── NotificationService.java
└── service/             # Use case implementations (optional)
    └── order/
        └── OrderApplicationService.java
```

**Inbound Ports** (Use Cases):
```java
// application/port/in/order/CreateOrderUseCase.java
public interface CreateOrderUseCase {

  Order createOrder(CreateOrderCommand command, User user);

  @Value
  @Builder
  class CreateOrderCommand {
    String orderNumber;
    UUID customerId;
    List<OrderItemDto> items;
  }
}
```

**Outbound Ports** (Dependencies):
```java
// application/port/out/order/OrderRepository.java
public interface OrderRepository {

  Optional<Order> findById(User user, UUID orderId);

  List<Order> findByStatus(User user, OrderStatus status);

  Order save(User user, Order order);

  void delete(User user, UUID orderId);
}
```

**Use Case Implementation**:
```java
// application/service/order/OrderApplicationService.java
@Service
@RequiredArgsConstructor
@Transactional
public class OrderApplicationService implements CreateOrderUseCase {

  // Depend on PORTS, not implementations
  private final OrderRepository orderRepository;
  private final ProcessOrderService processOrderService;
  private final NotificationService notificationService;

  @Override
  public Order createOrder(CreateOrderCommand command, User user) {
    // 1. Create domain model
    Order order = Order.create(
        command.getOrderNumber(),
        command.getCustomerId(),
        user.getTenantId(),
        user.getExternalId()
    );

    // 2. Add items
    command.getItems().forEach(item ->
        order.addItem(item.getProductId(), item.getQuantity()));

    // 3. Domain service for business logic
    order = processOrderService.processOrder(order, user);

    // 4. Persist
    order = orderRepository.save(user, order);

    // 5. Side effects
    notificationService.sendOrderCreated(order);

    return order;
  }
}
```

### 3. Adapter Layer (`src/main/java/.../adapter/`)

**Purpose**: Implements ports and connects to external world

**Structure**:
```
adapter/
├── in/                  # Inbound adapters
│   └── rest/
│       ├── v2/
│       │   └── order/
│       │       └── OrderV2ApiImpl.java
│       └── v3/
│           └── order/
│               └── OrderV3ApiImpl.java
├── out/                 # Outbound adapters
│   ├── persistence/jpa/
│   │   └── order/
│   │       ├── OrderJpaEntity.java
│   │       ├── OrderJpaRepository.java
│   │       └── OrderSpringDataJpaRepository.java
│   └── service/
│       ├── solver/      # External solver service
│       ├── notification/# Email/SMS service
│       └── storage/     # File storage (S3)
└── mapper/              # Layer boundary converters
    └── order/
        ├── OrderMapper.java
        └── OrderJpaMapper.java
```

**Inbound Adapter** (REST Controller):
```java
// adapter/in/rest/v3/order/OrderV3ApiImpl.java
@RestController
@RequiredArgsConstructor
public class OrderV3ApiImpl implements OrdersV3Api {

  // Depend on USE CASE (inbound port), not service directly
  private final CreateOrderUseCase createOrderUseCase;
  private final OrderMapper mapper;

  @Override
  public ResponseEntity<OrderDto> createOrder(CreateOrderRequest request) {
    // 1. Get authenticated user (injected by Spring Security)
    User user = UserDetailsUtil.getCurrentUserDetails().getUser();

    // 2. Map DTO to command
    CreateOrderCommand command = mapper.toCommand(request);

    // 3. Invoke use case
    Order order = createOrderUseCase.createOrder(command, user);

    // 4. Map domain to DTO
    OrderDto response = mapper.toDto(order);

    return ResponseEntity.status(HttpStatus.CREATED).body(response);
  }
}
```

**Outbound Adapter** (JPA Repository):
```java
// adapter/out/persistence/jpa/order/OrderJpaRepository.java
@Repository
@RequiredArgsConstructor
public class OrderJpaRepository implements OrderRepository {

  private final OrderSpringDataJpaRepository springDataRepository;
  private final OrderJpaMapper mapper;

  @Override
  public Optional<Order> findById(User user, UUID orderId) {
    // AuthorizationSpecificationFactory filtering (see multi-tenant-guardian agent for rules)
    Specification<OrderJpaEntity> spec =
        AuthorizationSpecificationFactory.forUser(user)
            .and(OrderJpaSpecifications.hasExternalId(orderId));

    return springDataRepository.findOne(spec)
        .map(mapper::toDomain);
  }

  @Override
  public Order save(User user, Order order) {
    OrderJpaEntity entity = mapper.toEntity(order);
    entity = springDataRepository.save(entity);
    return mapper.toDomain(entity);
  }
}
```

## Dependency Rules

### ✅ Allowed Dependencies

```
Domain       →  Nothing (pure Java)
Application  →  Domain
Adapter      →  Application + Domain + Frameworks
```

### ❌ Forbidden Dependencies

```
Domain       →  Application or Adapter  ❌
Domain       →  Spring, JPA, Jackson    ❌
Application  →  Adapter                 ❌
Application  →  JPA, Jackson            ❌
```

## Ports vs Adapters

### Inbound Port (Driving Port)
- **Definition**: Interface defining what the application CAN DO
- **Location**: `application/port/in/`
- **Examples**: `CreateOrderUseCase`, `FindOrderUseCase`
- **Implemented By**: Application services
- **Called By**: Inbound adapters (controllers)

### Outbound Port (Driven Port)
- **Definition**: Interface defining what the application NEEDS
- **Location**: `application/port/out/`
- **Examples**: `OrderRepository`, `NotificationService`
- **Implemented By**: Outbound adapters (JPA repos, external services)
- **Called By**: Application services

## Layer Separation with Mappers

### Why Mappers?
- Prevent leaking infrastructure details into domain
- Allow domain models to evolve independently
- Enable testing without infrastructure dependencies

### Mapper Types

**1. Domain ↔ DTO Mapper**:
```java
// adapter/mapper/order/OrderMapper.java
@Mapper(componentModel = "spring")
public interface OrderMapper {

  // API DTO → Domain
  Order toDomain(CreateOrderRequest dto);

  // Domain → API DTO
  OrderDto toDto(Order domain);

  // Collection mapping
  List<OrderDto> toDtoList(List<Order> orders);
}
```

**2. Domain ↔ JPA Entity Mapper**:
```java
// adapter/mapper/order/OrderJpaMapper.java
@Mapper(componentModel = "spring")
public interface OrderJpaMapper {

  // Domain → JPA Entity
  OrderJpaEntity toEntity(Order domain);

  // JPA Entity → Domain
  Order toDomain(OrderJpaEntity entity);
}
```

## File Organization Examples

### Example 1: Order Aggregate

```
domain/order/
├── Order.java                    # Aggregate root
├── OrderItem.java                # Entity
├── OrderStatus.java              # Enum
├── ProcessOrderService.java      # Domain service
└── OrderEmptyException.java      # Domain exception

application/port/in/order/
├── CreateOrderUseCase.java
├── UpdateOrderUseCase.java
└── FindOrderUseCase.java

application/port/out/order/
└── OrderRepository.java

application/service/order/
└── OrderApplicationService.java  # Implements use cases

adapter/in/rest/v3/order/
└── OrderV3ApiImpl.java           # REST controller

adapter/out/persistence/jpa/order/
├── OrderJpaEntity.java           # JPA entity
├── OrderJpaRepository.java       # Repository impl
└── OrderSpringDataJpaRepository.java  # Spring Data

adapter/mapper/order/
├── OrderMapper.java              # DTO ↔ Domain
└── OrderJpaMapper.java           # Entity ↔ Domain
```

### Example 2: Route Optimization Aggregate

```
domain/optimization/
├── RouteScenario.java
├── RouteCandidate.java
├── RoutePlan.java
└── OptimizationService.java

application/port/in/optimization/
├── CreateRouteScenarioUseCase.java
└── OptimizeRoutesUseCase.java

application/port/out/optimization/
├── RouteScenarioRepository.java
└── SolverService.java

adapter/out/service/solver/
├── SolverServiceAdapter.java
└── SolverClientMapper.java
```

## Common Violations & Fixes

### Violation 1: JPA Annotations in Domain
```java
// ❌ WRONG: Domain model with JPA
@Entity
@Table(name = "orders")
public class Order {
  @Id
  @GeneratedValue
  private Long id;
}
```

**Fix**: Separate domain and persistence
```java
// ✅ CORRECT: Pure domain model
public class Order {
  private UUID externalId;
  // No JPA annotations
}

// ✅ Separate JPA entity in adapter layer
@Entity
@Table(name = "orders")
public class OrderJpaEntity {
  @Id
  @GeneratedValue
  private Long id;
}
```

### Violation 2: Business Logic in Controller
```java
// ❌ WRONG: Business logic in adapter
@RestController
public class OrderController {
  public ResponseEntity<?> createOrder(CreateOrderRequest req) {
    if (req.getItems().isEmpty()) {
      throw new EmptyOrderException();  // Business rule!
    }
    // More business logic...
  }
}
```

**Fix**: Move to domain/application layer
```java
// ✅ CORRECT: Business logic in domain
public class Order {
  public void validate() {
    if (items.isEmpty()) {
      throw new EmptyOrderException();
    }
  }
}

@RestController
public class OrderController {
  public ResponseEntity<?> createOrder(CreateOrderRequest req) {
    // Just orchestrate
    Order order = createOrderUseCase.create(toCommand(req), user);
    return ResponseEntity.ok(toDto(order));
  }
}
```

### Violation 3: Controller Calling Repository Directly
```java
// ❌ WRONG: Skip use case layer
@RestController
public class OrderController {
  private final OrderRepository repository;  // Direct dependency!

  public Order getOrder(UUID id) {
    return repository.findById(id);  // No authorization!
  }
}
```

**Fix**: Use use case
```java
// ✅ CORRECT: Go through use case
@RestController
public class OrderController {
  private final FindOrderUseCase findOrderUseCase;

  public Order getOrder(UUID id) {
    User user = getCurrentUser();
    return findOrderUseCase.findById(user, id);
  }
}
```

### Violation 4: Domain Depending on Adapter
```java
// ❌ WRONG: Domain imports adapter
package com.omelet.oaasis.domain.order;

import com.omelet.oaasis.adapter.out.persistence.OrderJpaEntity;  // ❌

public class Order {
  private OrderJpaEntity entity;  // Wrong!
}
```

**Fix**: Dependency inversion
```java
// ✅ CORRECT: Domain defines interface, adapter implements
package com.omelet.oaasis.domain.order;

public class Order {
  // Pure domain, no infrastructure dependency
}

// Adapter implements domain interface
package com.omelet.oaasis.adapter.out.persistence;

public class OrderJpaRepository implements OrderRepository {
  // Adapter depends on domain, not vice versa
}
```

## Benefits of Hexagonal Architecture

### 1. Testability
- Domain logic testable without framework/database
- Use cases testable with mocked repositories
- Each layer testable in isolation

### 2. Flexibility
- Swap REST with GraphQL (change adapter)
- Swap JPA with MongoDB (change adapter)
- Domain remains unchanged

### 3. Maintainability
- Clear separation of concerns
- Business logic centralized in domain
- Easy to locate and modify

### 4. Framework Independence
- Domain not coupled to Spring
- Can migrate frameworks without touching business logic
- Easier to upgrade dependencies

## Quick Reference

### Creating a New Feature

1. **Define Domain Models** (domain/)
   - Aggregate roots, entities, value objects
   - Business rules and validation

2. **Define Ports** (application/port/)
   - Inbound: Use case interfaces
   - Outbound: Repository/service interfaces

3. **Implement Use Cases** (application/service/)
   - Orchestrate domain services
   - Coordinate with repositories

4. **Create Adapters** (adapter/)
   - Inbound: REST controllers
   - Outbound: JPA repositories, external services

5. **Create Mappers** (adapter/mapper/)
   - DTO ↔ Domain
   - Entity ↔ Domain

## Validation Checklist

When implementing a feature:
- [ ] Domain models in domain/ with NO framework dependencies
- [ ] Use case interfaces in application/port/in/
- [ ] Repository interfaces in application/port/out/
- [ ] Controllers in adapter/in/rest/ implementing use cases
- [ ] JPA repos in adapter/out/persistence/jpa/ implementing repo ports
- [ ] Mappers separating layers
- [ ] Dependency direction: Adapter → Application → Domain
- [ ] No business logic in controllers
- [ ] No JPA annotations in domain models
- [ ] No direct repository calls from controllers

---

**This skill should be invoked whenever**:
- Designing new features
- Reviewing architecture compliance
- Refactoring existing code
- Validating layer separation
- Training new developers on the architecture
