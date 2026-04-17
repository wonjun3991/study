---
tags: [kubernetes, ch01]
---
# Chapter 1: 쿠버네티스 소개

## 1.1 쿠버네티스와 같은 시스템이 필요한 이유

### 모놀리스에서 마이크로서비스로

```mermaid
graph LR
    subgraph Monolith
        A[UI + Business Logic + DB Access]
    end
    subgraph Microservices
        B[User Service]
        C[Order Service]
        D[Payment Service]
        E[Inventory Service]
    end
    Monolith -->|분리| Microservices
    B <-->|API| C
    C <-->|API| D
    C <-->|API| E
```

- 모놀리스와 달리 마이크로서비스는 개별적으로 개발, 배포가 가능하다.
- 하지만 새로운 문제가 발생한다:
    - 상호 종속성 수가 높아지므로 배포 관련 결정이 어려워진다
    - 서로를 찾아 통신해야 하는 과정에서 구성이 어렵다 (서비스 디스커버리)
    - 서로 다른 버전의 라이브러리를 필요로 하는 경우가 발생한다
- 스케일링 차이
    - **모놀리스**: 수직 스케일링(비용↑, 한계) 또는 수평 스케일링(전체 복제 필요)
    - **마이크로서비스**: 필요한 서비스만 독립적으로 스케일링 가능

### 일관된 환경 제공

- 마이크로서비스가 동일 OS에서 **서로 다른 버전의 라이브러리**를 필요로 하면 충돌 발생
- "내 로컬에서는 되는데" 문제 → 개발/스테이징/프로덕션 환경 차이
- **컨테이너**가 각 서비스를 자체 환경과 함께 패키징하여 해결

### 데브옵스와 NoOps

- **DevOps**: 개발 팀이 애플리케이션을 배포하고 관리
- **NoOps**: 쿠버네티스가 인프라를 추상화하여 개발자가 운영 없이 배포 가능
- 시스템 관리자는 개별 앱 대신 쿠버네티스 인프라 자체를 관리

---

## 1.2 컨테이너 기술 소개

### 컨테이너 vs 가상머신

```mermaid
graph TB
    subgraph VM["가상머신 방식"]
        HW1[Hardware]
        HOS1[Host OS]
        HYP[Hypervisor]
        subgraph VM1[VM 1]
            GOS1[Guest OS] --> APP1[App A]
        end
        subgraph VM2[VM 2]
            GOS2[Guest OS] --> APP2[App B]
        end
        HW1 --> HOS1 --> HYP --> VM1 & VM2
    end

    subgraph CT["컨테이너 방식"]
        HW2[Hardware]
        HOS2[Host OS]
        CRT[Container Runtime]
        subgraph C1[Container 1]
            APP3[App A]
        end
        subgraph C2[Container 2]
            APP4[App B]
        end
        subgraph C3[Container 3]
            APP5[App C]
        end
        HW2 --> HOS2 --> CRT --> C1 & C2 & C3
    end
```

| 비교 항목 | 가상머신 | 컨테이너 |
|-----------|---------|---------|
| 격리 수준 | 완벽 (별도 커널) | 프로세스 수준 (커널 공유) |
| 오버헤드 | GB 단위 RAM | MB 단위 |
| 시작 시간 | 분 단위 | 초 단위 |
| 밀도 | 낮음 | 높음 |
| 보안 | 강함 | 커널 공유로 인한 리스크 |

- 하이퍼바이저 유형:
    - **Type 1** (Bare-metal): 호스트 OS 불필요 (ESXi, Hyper-V)
    - **Type 2** (Hosted): 호스트 OS 위에서 동작 (VirtualBox, VMware Workstation)

### 컨테이너 격리 메커니즘

- **Linux Namespaces**: 프로세스별 독립된 시스템 뷰 제공
    - Mount, PID, Network, IPC, UTS(hostname), User ID
- **Linux cgroups**: 프로세스의 리소스 사용량 제한 (CPU, 메모리, 디스크 I/O, 네트워크)

> Docker 자체가 격리를 제공하는 것이 아니라, 리눅스 커널의 Namespace + cgroups를 쉽게 사용할 수 있게 해주는 플랫폼이다.

### Docker

- 컨테이너를 여러 시스템에 쉽게 이식 가능하게 하는 최초의 컨테이너 시스템
- 핵심 개념:
    - **이미지**: 애플리케이션 + 환경을 레이어로 패키지화
    - **레지스트리**: 이미지 저장소 (Docker Hub 등)
    - **컨테이너**: 이미지의 실행 인스턴스 (격리된 프로세스)
- 이미지 레이어: 여러 이미지가 동일 레이어를 공유 → 저장 공간/전송 효율
- 제한: 리눅스 커널 기반이므로 특정 커널 기능이 필요하면 해당 환경에서만 동작

### 도커의 대안: rkt

- OCI(Open Container Initiative) 표준 준수
- 보안, 조합성 강조
- 현재는 deprecated (2018년 당시 대안으로 소개)

---

## 1.3 쿠버네티스 소개

### 기원

- Google이 내부에서 수십만 개의 작업을 관리하던 **Borg** → **Omega** 시스템의 경험을 바탕으로
- 2014년 오픈소스로 공개, 개발자 경험에 더 집중

### 쿠버네티스 아키텍처

```mermaid
graph TB
    User([kubectl / API Client])

    subgraph ControlPlane["Control Plane (Master Node)"]
        API[API Server]
        SCHED[Scheduler]
        CM[Controller Manager]
        ETCD[(etcd)]
        API <--> ETCD
        API --> SCHED
        API --> CM
    end

    subgraph Worker1["Worker Node 1"]
        KL1[kubelet]
        KP1[kube-proxy]
        subgraph Pods1["Pods"]
            P1[Pod A]
            P2[Pod B]
        end
        KL1 --> Pods1
    end

    subgraph Worker2["Worker Node 2"]
        KL2[kubelet]
        KP2[kube-proxy]
        subgraph Pods2["Pods"]
            P3[Pod C]
            P4[Pod D]
        end
        KL2 --> Pods2
    end

    User --> API
    API --> KL1
    API --> KL2
```

**컨트롤 플레인 (마스터 노드)**
- **API Server**: 모든 통신의 중심 허브
- **etcd**: 클러스터 전체 상태를 저장하는 분산 KV 스토어
- **Scheduler**: 리소스 요구사항에 따라 Pod를 워커 노드에 배치
- **Controller Manager**: 복제본 관리, 노드 추적, 장애 처리

**워커 노드**
- **kubelet**: API 서버와 통신, 해당 노드의 컨테이너 관리
- **kube-proxy**: Service에 대한 네트워크 트래픽을 로드밸런싱 (iptables/IPVS)

### 애플리케이션 실행 흐름

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Reg as Container Registry
    participant API as API Server
    participant Sched as Scheduler
    participant KL as kubelet
    participant RT as Container Runtime

    Dev->>Reg: 1. docker push (이미지 업로드)
    Dev->>API: 2. kubectl apply (매니페스트 게시)
    API->>Sched: 3. 새 Pod 스케줄링 요청
    Sched->>API: 4. 워커 노드 할당 결정
    API->>KL: 5. Pod 실행 지시
    KL->>RT: 6. 이미지 pull & 컨테이너 실행
    loop 지속적 모니터링
        KL->>API: 상태 보고
        API->>KL: 디스크립션과 불일치 시 재시작/재스케줄링
    end
```

- 매니페스트에는 컨테이너 이미지, 복제본 수, 통신 방법, 리소스 요구량 등이 포함
- 쿠버네티스가 배포 상태와 디스크립션의 일치를 주기적으로 확인 (**선언적 모델**)
- 노드 장애 시 다른 노드에서 자동 재실행
- kube-proxy 덕분에 Pod가 이동해도 네트워크 연결 유지

### 쿠버네티스 사용의 장점

- **배포 단순화**: 어느 노드에서 실행 중인지 신경 쓸 필요 없음
- **하드웨어 활용도**: 남는 노드로 자동 이동하여 리소스 활용도 극대화
- **상태 확인과 자가 치유**: 실패한 컨테이너 자동 재시작
- **오토스케일링**: 메트릭 기반 자동 확장/축소
- **개발 단순화**: 서비스 디스커버리, 리더 선출 등을 플랫폼이 제공

---

## 1.4 Deep Dive: 서비스 디스커버리의 필요성과 진화

> 마이크로서비스에서 가장 근본적인 문제: **"상대 서비스가 어디에 있는가?"**

### 왜 서비스 디스커버리가 필요한가?

모놀리스에서는 함수 호출이면 끝이지만, 마이크로서비스에서는 **네트워크 호출**이다. 상대의 IP:Port를 알아야 한다. 클라우드 환경에서 IP는 동적이다 — 오토스케일링, 롤링 배포, 장애 복구 시 IP가 계속 바뀐다. 이 문제를 해결하는 접근법이 시대별로 진화해왔다.

```mermaid
graph LR
    A["정적 설정<br/>(IP 하드코딩)"] -->|"스케일 불가"| B["DNS<br/>(A 레코드)"]
    B -->|"캐시 문제"| C["Client-Side<br/>(Eureka+Ribbon)"]
    C -->|"JVM 종속"| D["Server-Side<br/>(Consul+LB)"]
    D -->|"LB가 SPOF"| E["Platform<br/>(K8s Service)"]
    E -->|"L4만 지원"| F["Service Mesh<br/>(Istio/Linkerd)"]
```

---

### Stage 1: 정적 설정 — IP 하드코딩

```properties
# application.properties
payment-service.host=10.0.1.42
payment-service.port=8080
```

- 서버 3대면 동작하지만, 100대면 **운영 불가능**
- 서버 교체/스케일링할 때마다 **모든 호출자의 설정을 수동 변경 후 재배포**

---

### Stage 2: DNS 기반 디스커버리 — 왜 실패하는가

`payment-service.internal` → DNS A 레코드로 IP 목록 반환. 얼핏 충분해 보이지만:

#### 문제 1: DNS 캐시가 4중으로 쌓인다

```mermaid
graph TB
    APP[Application] --> JVM["JVM InetAddress Cache<br/>기본: ∞ (SecurityManager 시)"]
    JVM --> OS["OS Cache (nscd)<br/>기본: 3,600s"]
    OS --> RESOLVER["Corporate DNS Resolver<br/>TTL만큼 캐시"]
    RESOLVER --> AUTH["Authoritative DNS<br/>레코드 변경"]
    
    style JVM fill:#ff634730,stroke:#ff6347
    style OS fill:#ff634720,stroke:#ff6347
```

| 캐시 레이어 | 기본 캐시 시간 | 비고 |
|------------|---------------|------|
| **JVM InetAddress** | **∞ (영원히)** | SecurityManager 있을 때 `-1`. 한번 resolve하면 JVM 재시작까지 안 바뀜 |
| OS (nscd) | 3,600s ~ 86,400s | 리눅스 1시간, Windows 24시간 |
| Corporate Resolver | TTL 값 (30~3600s) | 일부 ISP는 TTL 무시하고 자체 캐시 |
| 브라우저 | 60s (하드코딩) | Chrome/Firefox DNS TTL 무시, 자체 60초 고정 |

> DNS TTL을 5초로 설정해도, JVM이 영원히 캐싱하면 **의미 없다**.
> AWS 공식 문서에서도 [JVM TTL을 5초로 설정하라고 권고](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/jvm-ttl-dns.html)한다.

```java
// JVM DNS 캐시 설정 — 주의: -D 시스템 프로퍼티로는 안 됨!
// WRONG:
java -Dnetworkaddress.cache.ttl=30 -jar app.jar  // 무효

// CORRECT:
java.security.Security.setProperty("networkaddress.cache.ttl", "30");
```

#### 문제 2: 커넥션 풀이 DNS를 완전히 무시한다

Apache HttpClient, OkHttp 등의 커넥션 풀은 한번 TCP 연결이 맺어지면 **DNS를 다시 조회하지 않는다:**

```
1. payment-service → DNS → 10.0.1.5 (연결 성공, 풀에 저장)
2. 10.0.1.5 인스턴스 종료, DNS가 10.0.1.7로 변경
3. 커넥션 풀에 10.0.1.5 연결이 살아있음 → DNS 재조회 안 함
4. 계속 10.0.1.5로 요청 → 연결 실패
5. 커넥션 풀 TTL 만료 후에야 (기본: 무한) DNS 재조회
```

실질적 stale routing window = `max(JVM TTL, 커넥션 풀 TTL)` = **분 ~ 무한대**

#### 문제 3: DNS Round-Robin은 로드밸런싱이 아니다

- **glibc가 응답 순서를 재정렬** (RFC 6724) → 같은 서브넷 클라이언트는 항상 같은 IP
- 기업 DNS resolver 1대가 10,000 클라이언트에 **동일한 캐시 IP** 제공 → 특정 인스턴스 편중
- **건강 체크 없음** — 인스턴스가 죽어도 DNS 레코드에 남아있음

#### 문제 4: SRV 레코드도 답이 아니다

DNS SRV 레코드는 포트, 가중치, 우선순위를 제공하지만:
- RFC 2782가 **HTTP에 SRV 사용을 금지** → 모든 HTTP 클라이언트(curl, HttpClient, OkHttp 등) 미지원
- HTTP/2 워킹 그룹도 [SRV 지원을 명시적으로 거부](https://lists.w3.org/Archives/Public/ietf-http-wg/2015AprJun/0674.html)

---

### Stage 3: Client-Side Discovery — Eureka + Ribbon

Netflix가 2012년 크리스마스 이브 AWS ELB 장애를 겪은 후, "중앙 LB를 거치지 않는 구조"를 만들기 위해 개발.

```mermaid
graph TB
    subgraph EurekaCluster["Eureka Server Cluster (AP)"]
        E1[Eureka 1]
        E2[Eureka 2]
        E3[Eureka 3]
        E1 <-.->|peer replication| E2
        E2 <-.->|peer replication| E3
    end
    
    subgraph Service["Order Service (JVM)"]
        APP[비즈니스 로직]
        EC[Eureka Client<br/>30s 주기 heartbeat]
        RIB[Ribbon<br/>로컬 인스턴스 캐시]
        EC -->|register/renew| E1
        E1 -->|인스턴스 목록| RIB
        APP --> RIB
    end
    
    RIB -->|direct call| PAY[Payment Pod]
```

**장점**: 프록시 hop 없음, 레지스트리 다운 시 로컬 캐시로 기존 서비스 통신 유지

#### Eureka의 치명적 문제들

**1) Self-Preservation Mode — 좀비 인스턴스**

heartbeat 수신이 전체의 85% 미만이면 **모든 인스턴스 제거를 중단**한다:

```
인스턴스 10개 중 2개 죽음 → heartbeat 80% < 85% threshold
→ Self-preservation 발동
→ 죽은 2개 인스턴스가 레지스트리에 영구 유지 (좀비)
→ 트래픽이 좀비에게 계속 전달
→ 수동 개입 없이는 복구 안 됨
```

> 작은 클러스터일수록 더 심각: 인스턴스 3개 중 1개 죽으면 → 66% < 85% → 즉시 발동

**2) 죽은 인스턴스 제거까지 worst-case 5분 30초**

Eureka 소스 코드의 `renew()` 메서드에 **알려진 버그**가 있어서 lease 만료가 2배로 걸린다:

```java
// Lease.java — Netflix/eureka 소스
public void renew() {
    lastUpdateTimestamp = System.currentTimeMillis() + duration;
    // ↑ 버그: now + duration으로 설정해서 isExpired()에서 2×duration 후에야 만료
}
```

```
T+0s     인스턴스 ungraceful 종료
T+180s   Lease 만료 (90s × 2 = 180s, renew 버그)
T+240s   EvictionTask 실행 (최대 60s 간격)
T+270s   서버 response 캐시 갱신 (30s)
T+300s   클라이언트 레지스트리 fetch (30s)
T+330s   Ribbon ServerList 갱신 (30s)
─────────────────────────────────────
총 worst-case: ~5분 30초 동안 죽은 인스턴스로 트래픽 전송
```

**3) Eureka 전체 장애 시**

| 영향 | 상세 |
|------|------|
| 기존 서비스 통신 | 로컬 캐시로 **유지됨** (즉시 전사 장애는 아님) |
| 새 배포 | **불가** — 새 인스턴스가 등록 못 함 → 트래픽 0 |
| 죽은 인스턴스 | **제거 불가** — 좀비 상태로 계속 트래픽 수신 |
| 캐시 stale | Ribbon 캐시가 마지막 상태로 고정 → 부분 장애 확산 |

**4) 캐시 체인 — 5중 캐시**

```
Eureka Server Registry
  → Server Response Cache (30s)
    → Eureka Client Cache (30s)
      → Ribbon ServerList Cache (30s)
        → HTTP Connection Pool (∞)
```

각 레이어마다 30초씩 지연이 누적된다.

---

### Stage 4: Server-Side Discovery — Consul + LB

- Consul = **CP 모델** (Raft 합의) → 일관된 레지스트리, 좀비 없음
- HAProxy/NGINX가 Consul을 watch → 동적 백엔드 풀 업데이트
- **장점**: 언어 무관, 중앙 정책 관리
- **문제**: LB가 새로운 **SPOF & 병목**, Raft 리더 선출 시 **30~120초 불가용**

| | Eureka (AP) | Consul (CP) | ZooKeeper (CP) |
|---|---|---|---|
| 파티션 시 | 항상 가용, stale 데이터 | 쓰기 불가 (쿼럼 필요) | 전체 불가 (쿼럼 필요) |
| 좀비 인스턴스 | Self-preservation으로 가능 | 없음 (건강체크 즉시 제거) | 세션 만료로 제거 |
| 리더 선출 | 없음 (P2P) | Raft (30~120초) | ZAB (30~120초) |
| Split-brain | **가능** (divergent registry) | Raft가 방지 | ZAB가 방지 |

---

### Stage 5: K8s가 해결한 방법

#### DNS 문제 해결: ClusterIP (가상 IP)

K8s는 DNS를 "인스턴스 IP 목록 반환"이 아니라 **"안정된 가상 IP 1개 반환"**으로 바꿨다:

```
CoreDNS: payment-service → 10.96.100.1 (ClusterIP, 고정)
                                 │
                          kube-proxy (커널)
                           iptables/IPVS
                          ┌──────┼──────┐
                          ▼      ▼      ▼
                       Pod A   Pod B   Pod C
                     (실제 IP는 수시로 변경)
```

- 앱은 **ClusterIP 하나만** 알면 됨 → DNS 캐시가 stale해도 ClusterIP는 안 바뀜
- **커넥션 풀 문제 해소**: ClusterIP로 연결하면 커널이 매 패킷마다 실제 Pod로 라우팅
- JVM DNS 캐시 문제도 사실상 무관 — ClusterIP가 변하지 않으므로

#### 레지스트리 SPOF 해결: 별도 레지스트리 없음

```
Eureka 방식: App → Eureka Client → Eureka Server (별도 프로세스) → IP 목록
K8s 방식:    App → DNS → ClusterIP → kube-proxy (모든 노드에 존재) → Pod
```

- etcd에 상태가 내장, 별도 레지스트리 프로세스가 없음
- kube-proxy가 **모든 Worker Node에** DaemonSet으로 실행 → 단일 장애점 없음
- Endpoint Controller가 API Server를 **watch**하여 변경 즉시 반영

#### Stale 인스턴스 해결: Readiness Probe + 즉시 제거

| 시나리오 | Eureka | K8s |
|---------|--------|-----|
| Graceful 종료 | 30~330초 (heartbeat + 캐시 체인) | **~2-5초** (endpoint `ready=false` 즉시) |
| Ungraceful 종료 | 180~330초 (renew 버그 + 캐시 체인) | **~30초** (readiness probe 3회 실패) |
| 좀비 인스턴스 | Self-preservation으로 무한 유지 가능 | **불가능** (readiness probe가 지속 검증) |
| 새 인스턴스 가시성 | 30~60초 (등록 + 캐시 전파) | **~5-10초** (Pod Ready → EndpointSlice) |

#### K8s의 3-state 모델 (Eureka에 없는 것)

```yaml
# EndpointSlice conditions (K8s v1.26+)
conditions:
  ready: false        # ← 로드밸런서가 트래픽 중단
  serving: true       # ← 진행 중인 요청은 계속 처리
  terminating: true   # ← graceful shutdown 중
```

Eureka는 UP/DOWN 이진 상태만 있지만, K8s는 **ready/serving/terminating** 3가지 상태로 **Zero-downtime 롤링 업데이트**를 가능하게 한다.

---

### Stage 6: Service Mesh — 그 다음 단계

K8s Service는 **L4 (TCP/UDP)** — HTTP 헤더, gRPC 메타데이터를 모름:

| | K8s Service | Service Mesh (Istio/Linkerd) |
|---|---|---|
| mTLS | ❌ | ✅ 자동, 코드 변경 없음 |
| Retry/Timeout | ❌ | ✅ 선언적 정책 |
| Circuit Breaking | ❌ | ✅ outlier detection |
| Canary 배포 | ❌ | ✅ 트래픽 % 분할 |
| 분산 추적 | ❌ | ✅ 자동 span 전파 |

> Service Mesh는 sidecar 프록시(Envoy)가 모든 트래픽을 가로채서 L7 기능을 제공한다.
> Trade-off: 레이턴시 +1~3ms/hop, 메모리 200~400MB/pod, 운영 복잡도 증가.

---

## 1.5 Traditional MSA vs Kubernetes (종합 비교)

> 쿠버네티스 이전에 마이크로서비스 아키텍처는 어떻게 구축되었고, 쿠버네티스가 어떻게 개선했는가?

### 전체 아키텍처 비교

```mermaid
graph TB
    subgraph Before["기존 MSA (Spring Cloud Netflix)"]
        EU[Eureka Server<br/>서비스 레지스트리]
        CFG[Config Server<br/>설정 관리]
        ZU[Zuul Gateway<br/>API 게이트웨이]
        
        subgraph SVC1["Order Service (JVM)"]
            S1APP[비즈니스 로직]
            S1RIB[Ribbon<br/>클라이언트 LB]
            S1EUR[Eureka Client]
            S1HYS[Hystrix<br/>서킷 브레이커]
        end
        
        subgraph SVC2["Payment Service (JVM)"]
            S2APP[비즈니스 로직]
            S2RIB[Ribbon]
            S2EUR[Eureka Client]
            S2HYS[Hystrix]
        end
        
        EU <-.->|heartbeat| S1EUR & S2EUR
        ZU -->|라우팅| SVC1 & SVC2
        CFG -->|설정 배포| SVC1 & SVC2
    end

    subgraph After["Kubernetes MSA"]
        KDNS[CoreDNS]
        KCM[ConfigMap / Secret]
        KING[Ingress Controller]
        
        subgraph POD1["Order Service Pod"]
            P1APP[비즈니스 로직<br/>순수 앱 코드만]
        end
        
        subgraph POD2["Payment Service Pod"]
            P2APP[비즈니스 로직<br/>순수 앱 코드만]
        end
        
        KSV1[Service<br/>ClusterIP]
        KSV2[Service<br/>ClusterIP]
        
        KING --> KSV1 & KSV2
        KSV1 --> POD1
        KSV2 --> POD2
        KDNS -.->|DNS 자동 등록| KSV1 & KSV2
        KCM -.->|env/volume 주입| POD1 & POD2
    end
```

> 핵심 변화: 기존 MSA는 인프라 관심사를 **애플리케이션 라이브러리**(Ribbon, Eureka Client, Hystrix)에 넣었지만, K8s는 이를 **플랫폼 계층**으로 이동시켰다.

### 영역별 상세 비교

#### 1) 서비스 디스커버리

```mermaid
graph LR
    subgraph Before["기존: Eureka"]
        SVC_A[Service A<br/>+ Eureka Client<br/>+ Ribbon] -->|getInstances| EUR[Eureka Server]
        EUR -->|인스턴스 목록| SVC_A
        SVC_A -->|Client-side LB| SVC_B[Service B]
    end

    subgraph After["K8s: CoreDNS + Service"]
        POD_A[Pod A<br/>순수 앱 코드] -->|"http://svc-b:8080"| KSVC[Service<br/>ClusterIP<br/>10.96.x.x]
        KSVC -->|iptables/IPVS| POD_B1[Pod B-1]
        KSVC -->|iptables/IPVS| POD_B2[Pod B-2]
        DNS[CoreDNS] -.->|svc-b → 10.96.x.x| POD_A
    end
```

| | Eureka + Ribbon | K8s Service + CoreDNS |
|---|---|---|
| 레지스트리 | 별도 Eureka Server 운영 필요 | 컨트롤 플레인에 내장 |
| 언어 지원 | JVM 중심 (Eureka Client) | **언어 무관 (DNS)** |
| Stale 엔트리 | 최대 90초 (heartbeat 3회 미수신) | **Endpoint Controller가 즉시 갱신** |
| 앱 코드 결합 | `DiscoveryClient` 코드 필요 | **제로 — DNS 이름만 사용** |

#### 2) 내부 통신 & 로드 밸런싱

| | Ribbon + Feign | kube-proxy (iptables/IPVS) |
|---|---|---|
| LB 위치 | 앱 프로세스 내부 (in-process) | **커널 레벨** |
| 인스턴스 캐시 | Eureka 전파 지연으로 stale 가능 | API Server 직접 watch |
| IPVS 모드 | - | **O(1) 조회** (10k+ 서비스에서 유리) |
| L7 라우팅 | Zuul/Spring Cloud Gateway | Ingress + Istio (서비스 메시) |

#### 3) 설정 관리

| | Spring Cloud Config Server | ConfigMap + Secret |
|---|---|---|
| 별도 서비스 | Config Server 운영 필요 | **불필요** |
| 언어 지원 | Spring 전용 | **언어 무관** |
| 변경 반영 | Spring Cloud Bus (RabbitMQ) | Reloader 또는 Spring Cloud K8s |
| 감사 추적 | 커스텀 로깅 | **Git 히스토리 (GitOps)** |

#### 4) 상태 확인 & 자가 치유

| | Actuator + Eureka 제거 (90s) | K8s Probes |
|---|---|---|
| 감지 → 조치 | 수동 모니터링 + 스크립트 | **kubelet이 자동으로 재시작** |
| 부분 장애 | 구분 없음 (죽거나 살거나) | **Liveness vs Readiness 구분** |
| Readiness | 없음 | 트래픽 제거만 (재시작 안 함) — 일시적 장애에 적합 |

> **핵심**: Readiness probe 실패 시 Service에서 제외만 하고 재시작하지 않는다. DB 일시 장애 같은 상황에서 불필요한 재시작을 방지.

#### 5) 스케일링

| | VM 기반 (ASG) | K8s HPA/VPA/KEDA |
|---|---|---|
| 단위 | VM (분 단위 프로비저닝) | **Pod (초 단위)** |
| 트리거 | CPU만 (CloudWatch) | CPU, 메모리, 커스텀 메트릭, 이벤트 |
| Scale-to-zero | 불가능 | **KEDA로 가능** |
| 세분성 | VM 단위 (서비스 단위 불가) | **서비스(Pod) 단위** |

#### 6) 배포 전략

| | Spinnaker / Jenkins 스크립트 | K8s Deployment + Argo |
|---|---|---|
| Rolling Update | 커스텀 파이프라인 | **내장, 선언적** |
| 운영 비용 | Spinnaker 8+ 서비스 운영 | Argo Rollouts = CRD 1개 |
| 선언적 | 아니오 (명령형 파이프라인) | **YAML 매니페스트 in Git** |
| Drift 감지 | 없음 | **ArgoCD 지속 동기화** |

### 종합: 인프라 관심사의 이동

```mermaid
graph TB
    subgraph AppLayer["애플리케이션 계층"]
        BIZ[비즈니스 로직]
    end
    
    subgraph LibLayer["기존 MSA: 라이브러리 계층<br/>(앱 안에 내장)"]
        RIB[Ribbon<br/>LB]
        EURC[Eureka Client<br/>Discovery]
        HYS[Hystrix<br/>Circuit Breaker]
        ARC[Archaius<br/>Config]
    end
    
    subgraph PlatLayer["K8s: 플랫폼 계층<br/>(앱 바깥)"]
        SVC[Service + kube-proxy<br/>LB & Discovery]
        PROBE[Probes<br/>Health & Recovery]
        CM[ConfigMap/Secret<br/>Config]
        HPA[HPA/VPA<br/>Scaling]
    end
    
    BIZ -->|기존| LibLayer
    BIZ -->|K8s| PlatLayer
    
    style LibLayer fill:#ff634720,stroke:#ff6347
    style PlatLayer fill:#3cb37120,stroke:#3cb371
```

| 관심사 | 기존 (앱 내 라이브러리) | K8s (플랫폼 계층) |
|--------|------------------------|-------------------|
| 서비스 디스커버리 | Eureka Client + Ribbon | CoreDNS + ClusterIP |
| 로드 밸런싱 | Ribbon (in-process) | iptables/IPVS (kernel) |
| API 게이트웨이 | Zuul / Spring Cloud Gateway | Ingress + Istio |
| 설정 관리 | Spring Cloud Config Server | ConfigMap + Secret |
| 상태 확인 / 복구 | Actuator + Eureka 제거 (90s) | Liveness/Readiness Probes (5s) |
| 스케일링 | 수동 / ASG (VM, 분 단위) | HPA/VPA/KEDA (Pod, 초 단위) |
| 배포 | Spinnaker (8 서비스) / Jenkins | Deployment + Argo Rollouts |

> **Trade-off**: K8s가 앱을 단순화하는 대신, 플랫폼 운영 복잡도가 증가한다. 인프라 팀의 K8s 전문성이 필수적이다.

---

## 1.6 요약

- 모놀리스는 배포가 쉽지만, 유지보수와 스케일링이 어렵다
- 마이크로서비스는 개별 개발이 쉽지만, 하나의 시스템으로 배포/구성하기 어렵다
- 컨테이너는 VM과 유사한 격리를 훨씬 가볍게 제공한다
- Docker는 컨테이너화된 앱의 패키징/배포를 단순화했다
- 쿠버네티스는 전체 데이터센터를 하나의 컴퓨팅 리소스로 추상화한다
- 개발자는 시스템 관리자 없이 K8s를 통해 앱을 배포할 수 있다
- 서비스 디스커버리는 정적 설정 → DNS → Client-Side(Eureka) → Server-Side(Consul) → Platform(K8s) → Service Mesh로 진화했다
    - 각 단계는 이전 단계의 근본 문제를 해결했지만, 새로운 제약을 도입했다
    - K8s는 ClusterIP(고정 가상 IP) + kube-proxy(커널 레벨 라우팅)로 DNS 캐시/커넥션 풀/레지스트리 SPOF 문제를 구조적으로 해결했다
- 기존 MSA의 인프라 관심사(디스커버리, LB, 설정, 복구, 스케일링)를 앱 라이브러리에서 플랫폼 계층으로 이동시켰다
