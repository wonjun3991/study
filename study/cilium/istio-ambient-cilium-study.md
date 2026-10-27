# Istio에서 Cilium까지 — Kubernetes 네트워크 데이터 플레인 심화 스터디

## 핵심 메시지

> **Istio는 애플리케이션 통신 문제를 프록시 계층(Envoy)에서 해결했고, Istio Ambient는 그 프록시 비용을 L4/L7로 계층화했다. Cilium은 Kubernetes 네트워크 자체를 eBPF 데이터 플레인으로 재설계하면서 네트워킹·보안·관측·일부 서비스 메시 기능을 하나로 통합한다.**
>
> **따라서 Cilium을 공부한다는 것은 새로운 서비스 메시 하나를 배우는 것이 아니라, "Pod의 패킷이 어떻게 노드를 나가고, Service IP가 어떻게 Pod로 변환되며, DNS·kube-proxy·프록시가 어디에서 무엇을 하는지" 즉 현대 Kubernetes 네트워킹의 동작 방식 전체를 공부하는 것이다.**

이 노트는 두 부분으로 구성된다.

- **Part I~II**: 왜 Istio가 등장했고, Envoy 사이드카가 실제로 **어떻게 뜨고 어떻게 트래픽을 가로채는가**.
- **Part III~VI**: Pod가 네트워크를 얻는 법(CNI)부터 CoreDNS·kube-proxy·Ingress·Egress가 어떻게 동작하며, **Cilium이 이 모든 것을 eBPF로 어떻게 대체·통합하는가**.

---

# Part I. 배경 — 왜 서비스 메시이고, 왜 Cilium인가

## 1. Istio는 왜 등장했는가

### Kubernetes가 기본으로 해결하는 것

- Pod 간 네트워크 연결 (CNI)
- Service를 통한 서비스 디스커버리와 로드밸런싱 (kube-proxy)
- Deployment/ReplicaSet을 통한 배포
- NetworkPolicy를 통한 기본 L3/L4 접근 통제

하지만 Kubernetes Service가 제공하는 것은 **L3/L4 수준의 연결과 로드밸런싱**까지다. 다음은 애플리케이션이나 별도 인프라가 직접 처리해야 했다.

- 요청 재시도 / 타임아웃 / 서킷 브레이커
- 카나리·A/B를 위한 트래픽 분배
- 서비스 간 mTLS, 호출자 신원 기반 인가
- 서비스 간 요청 추적(tracing), HTTP 경로·헤더 기반 라우팅

마이크로서비스가 많아질수록 모든 서비스가 이 기능들을 **언어·프레임워크마다 제각각** 반복 구현하게 되고, 정책을 일관되게 적용하기 어려워진다.

```text
주문 서비스                     결제 서비스
 ├─ retry                       ├─ retry
 ├─ timeout                     ├─ timeout
 ├─ circuit breaker             ├─ circuit breaker
 ├─ TLS 인증서 관리             ├─ TLS 인증서 관리
 ├─ tracing                     └─ tracing
 └─ metrics
        └── 언어·프레임워크마다 구현이 다름 → 정책 일관성 붕괴
```

### Istio의 해법: 공통 기능을 인프라 계층으로

Istio는 이 공통 기능을 애플리케이션에서 분리해 **Envoy 프록시**로 옮겼다. 각 Pod에 Envoy를 사이드카로 함께 실행하고, 애플리케이션 트래픽이 반드시 Envoy를 통과하게 만든다.

```text
┌──────────── Pod A ────────────┐        ┌──────────── Pod B ────────────┐
│  App A  ──▶  Envoy(A)         │──mTLS──▶│  Envoy(B)  ──▶  App B         │
└───────────────────────────────┘        └───────────────────────────────┘
        코드 수정 없이 retry/timeout/mTLS/tracing/라우팅 주입
```

> **Istio의 등장 이유: 마이크로서비스마다 반복 구현하던 통신 안정성·보안·관측 기능을, 애플리케이션 밖의 공통 인프라 계층(Envoy)으로 분리하기 위해서.**

## 2. 기존 Sidecar 방식의 문제점

범용 L7 프록시를 **모든 Pod에** 넣는 구조는 새로운 비용을 만들었다.

- **Pod마다 Envoy**: App 1,000개면 Envoy도 ~1,000개. CPU·메모리 증가, Pod 시작 지연, 노드당 수용 Pod 감소, Envoy 설정 배포량·버전 관리 부담 증가. mTLS·단순 L4만 필요한 서비스에도 HTTP 라우팅까지 가능한 범용 Envoy가 붙는 **과잉 구조**.
- **생명주기 결합**: 프록시 업그레이드, 사이드카 설정·리소스 변경, injection 변경, 인증서 초기화 문제가 애플리케이션 Pod 재시작을 유발.
- **장애 분석 경로 증가**: `App → Client Envoy → iptables → 네트워크 → Server Envoy → App`. 문제 위치를 App / Envoy 설정 / Istiod 배포 설정 / 인증서 / AuthorizationPolicy / VirtualService / DestinationRule / 트래픽 캡처 / K8s 네트워크 중에서 골라내야 함.

### Envoy 사이드카가 실제로 요구하는 자원 (Istio 공식)

가장 큰 비용은 "Pod마다 Envoy"의 **곱셈**이다. Istio 공식 *Performance and Scalability* 문서 기준:

| 항목 | 값 | 비고 |
|---|---|---|
| 처리량당 (구버전) | **0.35 vCPU + 40 MB / 1,000 rps** | Istio 1.8.3, 프록시를 통과하는 초당 요청 1,000건당 |
| 처리량당 (최신) | **~0.20 vCPU + 60 MB / 1,000 rps** | Istio 1.24, worker 2개·1 KB payload. CPU는 개선, 메모리는 소폭 증가 |
| 기본 requests | **CPU 100m · Memory 128Mi** | 모든 사이드카에 적용되는 차트 기본값 |
| 기본 limits | **CPU 2000m · Memory 1024Mi** | 〃 |

- 메모리는 프록시가 들고 있는 **config state(listener·cluster·route·endpoint)에 비례**한다. 서비스가 많을수록 각 Envoy 메모리도 커짐 → `Sidecar` 리소스로 프록시가 아는 범위를 좁혀 줄일 수 있다.
- **CPU limit을 너무 낮게 잡으면** 트래픽 스파이크 때 스로틀링 → 애플리케이션 지연으로 전가된다(프록시 concurrency는 CPU limit에서 결정). 그래서 limit은 높게 두거나 unset 권장.
- 오버라이드: 전역은 `IstioOperator`의 `values.global.proxy.resources`, 개별 Pod는 애노테이션 `sidecar.istio.io/proxyCPU`·`proxyMemory`·`proxyCPULimit`·`proxyMemoryLimit`.

> **규모 감각:** Pod 1,000개면 사이드카 requests만 **CPU 100 vCPU + 메모리 ~125 GiB**(=1000×128Mi), limits 기준으론 **~2,000 vCPU + ~1 TiB**가 예약 대상이 된다. 애플리케이션이 아니라 **프록시 계층에만** 드는 비용 — Ambient·eBPF가 이 곱셈을 없애려는 이유다.

## 3. Istio Ambient는 무엇을 바꿨는가

Ambient는 사이드카를 없애는 대신 서비스 메시 기능을 **두 계층으로 분리**했다.

```text
┌──────────────────────────────────────┐
│ L7: Waypoint Proxy (Envoy)           │  HTTP 라우팅·L7 authz·retry
└──────────────────────────────────────┘  ← 필요한 워크로드에만 (선택)
────────────────────────────────────────
┌──────────────────────────────────────┐
│ L4: ztunnel (노드당 1개, DaemonSet)  │  mTLS·identity·L4 authz·telemetry·HBONE
└──────────────────────────────────────┘  ← 기본
```

- **ztunnel** (배포 형태 = **DaemonSet**, 노드당 1개): 경량 L4 프록시. 워크로드 간 mTLS, 신원 확인, L4 AuthorizationPolicy, L4 텔레메트리, HBONE 터널 처리. **HTTP 헤더·URL을 파싱하지 않는다** — 의도적으로 L3/L4에 집중.
- **Waypoint Proxy** (배포 형태 = **Deployment**, DaemonSet 아님): L7 기능이 필요할 때 **네임스페이스 또는 서비스어카운트 단위**로 배포하는 Envoy 프록시. `istioctl waypoint apply`로 생성되며 자체 ServiceAccount·SPIFFE identity를 가진다. 애플리케이션 Pod 밖의 **독립 컴포넌트**라서 앱과 별개로 배포·업그레이드·스케일(HPA)된다.

> **Ambient의 핵심: 모든 Pod에 범용 L7 프록시를 넣지 않고, 기본 보안은 공유 L4 프록시(ztunnel)로 제공하며 필요한 워크로드에만 L7 프록시(Waypoint)를 추가한다.**

다만 Ambient도 결국 **Istio의 서비스 메시 모델**이다(Istiod 제어 플레인 + ztunnel L4 + Waypoint L7, 워크로드 신원·mTLS 중심). 여전히 기존 Kubernetes 네트워크 **위에** 메시 계층을 얹는다.

---

# Part II. Envoy Sidecar는 어떻게 뜨고 어떻게 프록시하는가

한 문장 요약: **Mutating Webhook이 Pod 스펙에 컨테이너를 주입 → istio-init이 iptables로 트래픽을 Envoy로 강제 우회 → Envoy가 15006(inbound)/15001(outbound)에서 받아 프록시 → istiod가 xDS로 Envoy 설정을 실시간 배포.**

### 먼저: Envoy란 무엇인가

Envoy는 Istio가 데이터 플레인으로 쓰는 **고성능 L4/L7 프록시**다(원래 Lyft가 만들었고 현재 CNCF 졸업 프로젝트, C++로 작성). "프록시"란 애플리케이션 대신 네트워크 연결을 받고/내보내며 그 사이에서 정책을 적용하는 중개자다.

- **L4/L7 모두 처리**: 단순 TCP뿐 아니라 HTTP/1.1·HTTP/2·gRPC를 이해해서 경로·헤더 기반 라우팅, 재시도·타임아웃·서킷 브레이커, TLS 종료/개시(mTLS)를 수행.
- **동적 설정(xDS)**: 재시작 없이 API로 리스너·라우트·클러스터·엔드포인트를 받아 실시간 반영한다. 이 "프로그래밍 가능함" 덕분에 istiod 같은 제어 플레인이 수천 개의 Envoy를 중앙에서 조종할 수 있다 → 서비스 메시의 데이터 플레인으로 적합.
- **풍부한 관측**: 상세 통계(metrics)·분산 트레이싱·액세스 로그를 기본 제공.

요청이 Envoy를 지나는 길(설정 모델):

```text
Listener(수신 지점, 예: 15006/15001)
  └ Filter Chain(TLS·HTTP 커넥션 매니저 등)
      └ Route(host·path 매칭 → 어느 Cluster로)
          └ Cluster(논리적 upstream = 목적지 서비스)
              └ Endpoint(실제 백엔드 Pod IP:port)
```

각 계층이 뒤에서 다룰 xDS(LDS/RDS/CDS/EDS, 9장)에 그대로 대응한다. 즉 **Envoy = 트래픽을 실제로 나르고 정책을 집행하는 데이터 플레인**이고, istiod가 그 설정을 배포하는 제어 플레인이다. Istio Sidecar·Ambient Waypoint, 그리고 Cilium의 L7 처리까지 — "L7 프록시가 필요하다"고 할 때 그 프록시는 대부분 이 Envoy다.

## 4. 사이드카 주입 (Sidecar Injection)

### Mutating Admission Webhook

Pod 생성 요청이 API Server에 들어오면, `istio-sidecar-injector`라는 **MutatingAdmissionWebhook**이 요청을 가로채 Pod 스펙을 수정한다. 네임스페이스에 `istio-injection=enabled` 라벨(또는 Pod에 `sidecar.istio.io/inject: "true"`)이 있으면 대상이 된다.

주입 후 Pod에는 두 개의 컨테이너가 추가된다.

```text
apiVersion: v1
kind: Pod
spec:
  initContainers:
    - name: istio-init          # ① iptables 규칙을 세팅하고 종료
      args: [istio-iptables, -p, "15001", -z, "15006", -u, "1337", -m, REDIRECT, ...]
  containers:
    - name: my-app              # 원래 애플리케이션
    - name: istio-proxy         # ② pilot-agent + Envoy (사이드카)
      # pilot-agent가 Envoy 부트스트랩 설정을 만들고 Envoy 프로세스를 실행
```

- **istio-init (initContainer)**: 애플리케이션보다 **먼저** 실행되어 Pod 네트워크 네임스페이스에 iptables 규칙을 심고 종료한다. `NET_ADMIN` 권한 필요. (CNI 플러그인 방식이면 initContainer 대신 Cilium/Istio CNI가 규칙을 대신 설정)
- **istio-proxy (sidecar)**: 내부에서 `pilot-agent`(=istio-agent)가 Envoy 부트스트랩 config를 생성하고 Envoy 프로세스를 띄운다. 또한 istiod와 연결해 인증서(SDS)와 설정(xDS)을 받아 Envoy에 전달한다.

## 5. istio-init — iptables로 트래픽을 "투명하게" 가로채기

애플리케이션은 자기 트래픽이 Envoy를 지난다는 사실을 모른다. 이 "투명 가로채기(transparent hijacking)"를 만드는 것이 istio-init이 심는 iptables `nat` 테이블 규칙이다.

istio-init 인자 `-p 15001 -z 15006 -u 1337 -m REDIRECT`의 의미:

| 인자 | 의미 |
|---|---|
| `-p 15001` | outbound 트래픽을 Envoy 15001로 REDIRECT |
| `-z 15006` | inbound 트래픽을 Envoy 15006으로 REDIRECT |
| `-u 1337` | Envoy 프로세스의 UID. 이 UID에서 나온 패킷은 재우회하지 않음(루프 방지) |
| `-m REDIRECT` | 캡처 모드 (기본 REDIRECT, 또는 TPROXY) |

istio-init이 만드는 주요 체인:

```text
[Inbound 방향]  PREROUTING
   └─ ISTIO_INBOUND        : 들어오는 TCP를 대상으로. 단 Envoy 내부용 포트
   │                          (15008 HBONE, 15090 metrics, 15021 health, 15020 stats 등)은 제외
   └─ ISTIO_IN_REDIRECT    : REDIRECT → 15006 (Envoy inbound listener)

[Outbound 방향]  OUTPUT
   └─ ISTIO_OUTPUT         : 나가는 TCP를 대상으로.
   │    ├─ UID/GID 1337 발(發)  → RETURN  (Envoy 자신의 트래픽은 재우회 안 함 = 루프 방지)
   │    ├─ 목적지 127.0.0.1     → RETURN  (loopback은 그대로)
   │    └─ 그 외                → ISTIO_REDIRECT
   └─ ISTIO_REDIRECT       : REDIRECT → 15001 (Envoy outbound listener)
```

**UID 1337이 핵심**: Envoy가 목적지로 보내는 패킷도 OUTPUT을 지나는데, 이것마저 15001로 되돌리면 무한 루프가 된다. iptables는 패킷의 소유자 UID를 검사해 1337(=Envoy)에서 나온 것은 `RETURN`으로 그냥 통과시킨다.

## 6. Envoy 프로세스와 포트 구성

istio-proxy 컨테이너 안에서 `pilot-agent`가 Envoy를 부트스트랩한다. Envoy가 사용하는 고정 포트:

| 포트 | 역할 |
|---|---|
| **15001** | Envoy **outbound** listener — 앱이 밖으로 보내는 트래픽이 iptables로 여기에 도착 |
| **15006** | Envoy **inbound** listener — 밖에서 이 Pod로 오는 트래픽이 iptables로 여기에 도착 |
| **15000** | Envoy admin API (config_dump, 통계 등 디버깅용) |
| **15020** | istio-agent가 노출하는 병합 텔레메트리 + health check 집계 |
| **15021** | health check 엔드포인트 (`/healthz/ready`, kubelet readiness probe 대상) |
| **15090** | Envoy Prometheus 메트릭 (pilot-agent가 스크레이프) |
| **15053** | (옵션) 로컬 DNS proxy |

이 포트들이 iptables 캡처에서 제외되는 이유는, health check·metrics 스크레이프·admin 접근이 Envoy 자신을 통해 다시 우회되면 안 되기 때문이다.

## 7. Inbound 흐름 — 트래픽이 "들어오는" 것

다른 Pod(또는 Ingress)가 이 Pod의 IP:포트로 요청을 보낼 때:

```text
   원격 클라이언트 (다른 Pod의 Envoy)
        │  목적지 = ThisPodIP:8080
        ▼
 ┌───────────────── This Pod netns ─────────────────┐
 │ PREROUTING → ISTIO_INBOUND → ISTIO_IN_REDIRECT    │
 │        └─ REDIRECT → 127.0.0.1:15006              │
 │                        │                          │
 │                        ▼                          │
 │              Envoy(inbound listener)              │
 │        - mTLS 종료(서버측), L7 정책/authz 적용     │
 │        - 접근 로그·메트릭·트레이싱 수집            │
 │                        │  127.0.0.1:8080          │
 │                        ▼                          │
 │                  Application (8080)               │
 └───────────────────────────────────────────────────┘
```

즉 애플리케이션은 항상 **localhost로 들어온 요청**만 본다. mTLS 검증·L7 인가·관측은 앱이 받기 전에 Envoy가 끝낸다.

## 8. Outbound 흐름 — 트래픽이 "나가는" 것

애플리케이션이 다른 서비스(`payment:8080` 같은 ClusterIP)를 호출할 때:

```text
 ┌───────────────── This Pod netns ─────────────────┐
 │  Application  ── connect(payment ClusterIP:8080) ─┤
 │        │                                          │
 │  OUTPUT → ISTIO_OUTPUT → ISTIO_REDIRECT           │
 │        └─ REDIRECT → 127.0.0.1:15001              │
 │                        │                          │
 │                        ▼                          │
 │              Envoy(outbound listener)             │
 │   - 목적지 서비스 식별(원래 dst는 소켓 opt로 보존) │
 │   - 라우팅/재시도/타임아웃/서킷브레이커 적용        │
 │   - 대상 워크로드로 mTLS 개시(클라이언트측)        │
 │        │  (UID 1337 발 → iptables RETURN, 루프 X) │
 │        ▼                                          │
 └────────┼──────────────────────────────────────────┘
          ▼
   상대 Pod의 Envoy(15006) → 상대 App
```

핵심: 앱은 평범하게 `payment` ClusterIP로 connect했을 뿐인데, iptables가 그 소켓을 15001로 돌리고 Envoy가 실제 엔드포인트 선택·mTLS·정책을 대신 수행한다. Envoy가 실제로 밖으로 내보내는 패킷은 UID 1337이라 다시 잡히지 않는다.

## 9. 제어 플레인: istiod ↔ Envoy (xDS)

Envoy는 "무엇을 어디로 어떻게 보낼지"를 스스로 모른다. **istiod**가 Kubernetes API(Service·Endpoint·Istio CR)를 watch해서 Envoy 설정을 만들고, **xDS 프로토콜(gRPC 스트림)**로 각 Envoy에 실시간 푸시한다.

xDS는 istiod가 Envoy에 설정을 내려주는 **API 묶음**이다(x = L/R/C/E/S, DS = Discovery Service). 종류별로 "무엇을" 알려주는지가 다르다.

- **LDS (Listener Discovery Service)** — *Envoy가 어떤 포트에서 트래픽을 받을지.* 예) `15001`=outbound(앱이 밖으로 내보내는 트래픽을 받는 리스너), `15006`=inbound(밖에서 앱으로 들어오는 트래픽을 받는 리스너). 즉 "이 포트로 들어오는 트래픽을 받아 이런 필터 체인으로 처리해라"를 내려준다.
- **RDS (Route Discovery Service)** — *HTTP 요청을 어디로 보낼지(L7 라우팅 규칙).* Istio `VirtualService`와 연결된다. 예) `reviews`로 가는 요청 중 `/v1`→reviews-v1, `/v2`→reviews-v2, 또는 "90%는 v1·10%는 v2". host·path·header·method를 보고 어느 upstream(=Cluster)으로 보낼지 결정.
- **CDS (Cluster Discovery Service)** — *Envoy 관점의 upstream 서비스 묶음.* 여기서 "cluster"는 쿠버네티스 클러스터가 아니라 **"Envoy가 트래픽을 보낼 수 있는 백엔드 그룹"**이다. 예) `outbound|9080||reviews.default.svc.cluster.local`. Istio `DestinationRule`(로드밸런싱·TLS·커넥션 정책)과 연결.
- **EDS (Endpoint Discovery Service)** — *그 Cluster 안의 실제 Pod IP 목록.* CDS가 "서비스 묶음"이라면 EDS는 그 안의 진짜 목적지다. 예) `reviews...` → `10.244.1.12:9080`, `10.244.2.33:9080`, … Pod가 죽거나 새로 뜨면 이 목록이 실시간 갱신된다.
- **SDS (Secret Discovery Service)** — *인증서·private key·CA bundle.* Istio mTLS에서 Envoy가 쓸 workload identity 인증서를 동적으로 내려준다. istio-agent가 인증서를 받아와 주기적으로 **rotate(회전)**한다 — mTLS의 핵심.

```text
K8s API (Service/Endpoint/VirtualService/DestinationRule/AuthorizationPolicy)
        │ watch
        ▼
     istiod  ──── xDS(gRPC) ────▶  각 Pod의 Envoy
        │                               ▲
        └─ CA(인증서 서명) ── SDS ───────┘ (istio-agent 경유)
```

> **정리: 주입(webhook) → 가로채기(iptables) → 프록시(Envoy 15006/15001) → 설정 배포(istiod xDS/SDS). 이 네 단계가 "사이드카가 어떻게 뜨고 어떻게 프록시하는가"의 전부다.**

---

# Part III. Pod는 어떻게 네트워크를 얻는가 — CNI

> 지금까지(Part II)는 "이미 IP를 가진 Pod들" 사이의 트래픽 이야기였다. 그런데 **Pod는 애초에 IP와 네트워크 인터페이스를 어떻게 얻는가?** 그 답이 CNI다. kube-proxy·DNS·Ingress는 전부 이 위에서 돈다.

## 10. CNI란 무엇이고 무엇을 책임지나

**CNI(Container Network Interface)**는 컨테이너에 네트워크를 붙이는 방법을 규정한 CNCF 표준 스펙 + 그 스펙을 구현한 플러그인들이다.

> **CNI 자체는 네트워킹을 "제공"하지 않는다.** 컨테이너 런타임이 플러그인을 **어떻게 호출**할지(입출력 규약)만 정의하고, 실제 인터페이스 생성·IP 할당·라우팅은 플러그인(Cilium·Calico·Flannel·AWS VPC CNI 등)이 한다.

CNI 플러그인이 Pod 하나에 대해 책임지는 것:

- **IPAM (IP Address Management)**: Pod에 클러스터에서 **겹치지 않는 IP**를 하나 할당(노드별 Pod CIDR 등).
- **네트워크 인터페이스 생성**: Pod의 network namespace 안에 인터페이스를 만든다. 보통 **veth pair** — 한쪽 끝은 Pod 안의 `eth0`, 다른 쪽 끝은 노드(호스트) namespace에 꽂힌다.
- **라우팅 설정**: 그 Pod가 같은 노드/다른 노드의 Pod, 그리고 외부와 통신할 수 있도록 경로를 넣는다.

이 모두는 **Kubernetes 네트워크 모델**을 만족하기 위한 것이다:

1. 모든 Pod는 **자기 고유 IP**를 가진다.
2. 모든 Pod는 **NAT 없이** 다른 모든 Pod와(노드를 넘어서도) 통신할 수 있다.
3. 노드의 에이전트(kubelet 등)는 그 노드의 모든 Pod와 통신할 수 있다.

**CNI가 하지 않는 것**도 분명히 하자: Service 로드밸런싱(→ kube-proxy, Part IV)이나 DNS(→ CoreDNS)는 CNI의 일이 아니다. CNI는 오직 **Pod에 IP를 주고 L3 연결을 까는 것**까지다. (단 Cilium처럼 eBPF 기반 CNI는 이 위의 기능까지 함께 흡수한다 — Part VI.)

## 11. Pod가 뜰 때 CNI가 호출되는 흐름

Pod가 스케줄되면 **kubelet → 컨테이너 런타임(containerd/CRI-O) → CNI 플러그인** 순으로 네트워크가 세팅된다.

```text
1. 스케줄러가 Pod를 노드에 배치
2. kubelet → CRI: sandbox(pause 컨테이너) 생성 요청
3. 런타임: Pod용 network namespace 생성
4. 런타임 → CNI 플러그인 호출 (CNI_COMMAND=ADD, JSON config를 stdin으로)
       └ 설정: /etc/cni/net.d/*.conflist   플러그인 바이너리: /opt/cni/bin/
5. 플러그인: IP 할당(IPAM) → veth 생성(Pod eth0 ↔ 호스트) → 라우팅 세팅
6. 플러그인 → 런타임: 할당된 IP·인터페이스 결과 반환
7. Pod가 IP를 갖고, 앱 컨테이너들이 그 netns를 공유하며 시작
   (Pod 삭제 시엔 CNI_COMMAND=DEL로 IP 회수·정리)
```

플러그인이 구현해야 하는 명령은 **ADD / DEL / CHECK** 세 가지다. ADD는 sandbox 생성 시(IP 할당·인터페이스·라우팅), DEL은 teardown 시(IP 반납·인터페이스/라우팅/iptables 정리).

### 노드를 넘는 Pod 간 통신 — 두 가지 datapath

Pod IP는 노드 내부 주소가 아니라 **클러스터 전역**이라, 다른 노드의 Pod로 보내려면 CNI가 노드 간 경로를 만들어야 한다. 크게 두 방식:

- **오버레이(Overlay)**: **VXLAN/Geneve**로 Pod 패킷을 노드 IP 헤더로 **캡슐화**해 노드 사이를 건넌다. 하부 네트워크가 Pod CIDR을 몰라도 되어 이식성이 좋지만 캡슐화 오버헤드가 있다. (예: Flannel VXLAN, Cilium VXLAN 모드)
- **네이티브 라우팅(Direct routing)**: 캡슐화 없이 **BGP나 클라우드 라우트 테이블**로 Pod CIDR 경로를 직접 광고한다. 성능이 좋지만 하부 네트워크(라우터/클라우드 VPC) 지원이 필요하다. (예: Calico BGP, Cilium native routing)

> **Cilium과의 연결:** Cilium은 CNI 플러그인이면서, veth·iptables 기반 전통 datapath 대신 **veth·호스트 경로에 eBPF 프로그램(tc/XDP)을 붙여** 패킷을 처리한다. 그래서 "Pod에 IP를 주는 CNI 역할"과 "Service LB·NetworkPolicy·관측"을 **같은 eBPF 데이터 플레인에서** 함께 해낸다 — 이것이 Part VI에서 Cilium이 kube-proxy까지 대체할 수 있는 근본 이유다.

---

# Part IV. Kubernetes 기본 네트워크 — CoreDNS와 kube-proxy

> 이 파트의 목표: CoreDNS와 kube-proxy가 각각 **어떤 형태로 배포**되고, Pod의 통신(특히 DNS 질의)이 이들을 거쳐 **어떻게 흐르는지** 처음부터 정리한다.

## 12. 배포 형태부터 정확히 — 무엇이 DaemonSet이고 무엇이 Deployment인가

이 구분이 이후 전체 이해의 기반이 되므로 정확히 짚는다.

| 컴포넌트 | 배포 형태 | 노드 분포 | 역할 |
|---|---|---|---|
| **kube-proxy** | **DaemonSet** | **노드마다 1개** | Service → Pod 로드밸런싱 규칙(iptables/IPVS)을 각 노드 커널에 프로그래밍 |
| **CoreDNS** | **Deployment** (기본) | **노드마다 있는 게 아님** (기본 2 replica, 스케줄러가 배치) | 클러스터 DNS 서버. `kube-dns` Service(ClusterIP)로 프론트됨 |
| (참고) NodeLocal DNSCache | DaemonSet | 노드마다 1개 | 노드 로컬 DNS 캐시. **선택적** 애드온 |

**즉 CoreDNS는 기본적으로 DaemonSet이 아니라 Deployment다.** (원하면 DaemonSet으로 바꿀 수 있고, HA/지연 최적화를 위해 NodeLocal DNSCache를 노드별로 깔 수는 있다.) 노드별로 확실히 하나씩 도는 것은 **kube-proxy**다.

그래서 이어서 다룰 것은 두 가지다:
1. 노드마다 도는 **kube-proxy**가 하는 일은 무엇인가?
2. Pod가 서비스 이름을 부를 때, DNS 질의가 **어떻게 CoreDNS Pod까지 도달**하는가? (← 이 경로에서 kube-proxy가 등장한다)

## 13. kube-proxy는 무엇을 하는가

kube-proxy는 트래픽을 직접 프록시하지 **않는다**(이름과 달리). API Server를 watch하다가 Service/EndpointSlice가 바뀌면, 그 노드의 **커널 규칙(iptables 또는 IPVS)**을 갱신하는 **규칙 프로그래머**다. 실제 패킷 변환(DNAT)은 커널이 한다.

iptables 모드의 규칙 계층(nat 테이블):

```text
KUBE-SERVICES        # 진입점: 목적지 = <ClusterIP>:<port> 매칭
   └─ KUBE-SVC-XXXX  # 그 서비스의 "가상 로드밸런서". 확률(random)로 SEP 하나 선택
        ├─ KUBE-SEP-A  (33%) → DNAT to PodA_IP:port
        ├─ KUBE-SEP-B  (33%) → DNAT to PodB_IP:port
        └─ KUBE-SEP-C  (34%) → DNAT to PodC_IP:port
```

- ClusterIP는 **가상 IP** — 어떤 인터페이스에도 붙어있지 않다. 커널이 KUBE-SERVICES 규칙으로 목적지를 실제 Pod IP로 **DNAT** 할 뿐이다.
- 엔드포인트가 N개면 KUBE-SEP-*도 N개. 선택은 확률 기반(iptables) 또는 해시/RR(IPVS).
- 이 규칙은 **모든 노드에 동일하게** 존재한다(그래서 kube-proxy가 DaemonSet). 어느 노드의 Pod에서 ClusterIP를 불러도 같은 로드밸런싱이 적용된다.
- DNAT 후 패킷은 목적지 Pod IP로 향하고, **노드 간 라우팅은 CNI**가 담당(overlay VXLAN 또는 native routing).

## 14. Pod의 DNS 조회 — end-to-end 경로

여기서 CoreDNS와 kube-proxy가 **어떻게 통신하는지**가 드러난다. 둘은 직접 대화하지 않는다. Pod의 DNS 질의가 **Service(kube-dns) → kube-proxy가 심은 DNAT 규칙 → CoreDNS Pod** 순으로 흐른다.

### (1) Pod의 /etc/resolv.conf

kubelet이 Pod마다 이 파일을 세팅한다:

```text
nameserver 10.96.0.10                 # kube-dns Service의 ClusterIP (가상 IP)
search myns.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

- `nameserver`는 CoreDNS Pod IP가 아니라 **kube-dns Service의 ClusterIP**다. Pod가 바뀌어도 이 IP는 불변.
- `ndots:5`: 점(`.`)이 5개 미만인 이름은 **먼저 search 도메인을 붙여** 순차 시도한다. 예를 들어 `payment`는 `payment.myns.svc.cluster.local` → `payment.svc.cluster.local` → ... 순으로 질의. 외부 도메인(`api.github.com`, 점 2개)도 search 도메인부터 붙이므로 **불필요한 질의가 여러 번** 발생 → 외부 트래픽 많은 앱은 `dnsConfig`로 ndots를 낮추는 것이 성능 튜닝 포인트.

### (2) 질의가 CoreDNS까지 도달하는 경로

```text
 App: getaddrinfo("payment") → resolv.conf 읽음 → UDP 53, dst=10.96.0.10 (kube-dns ClusterIP)
        │
        ▼  (Pod 밖으로 나가는 패킷, 노드 커널 진입)
 노드 커널 iptables (kube-proxy가 심음)
   KUBE-SERVICES → KUBE-SVC-<kube-dns> → KUBE-SEP-<coredns-pod>
        └─ DNAT: dst 10.96.0.10  →  실제 CoreDNS Pod IP (예: 10.244.2.7:53)
        │
        ▼  (CoreDNS Pod가 다른 노드면 CNI가 노드 간 라우팅)
 CoreDNS Pod
   - kubernetes 플러그인: *.svc.cluster.local → 해당 Service의 ClusterIP 응답
   - forward 플러그인: 클러스터 외부 도메인 → 업스트림 DNS로 전달
        │
        ▼  응답이 역경로로 App까지 (conntrack이 DNAT 역변환)
 App: payment = <payment Service ClusterIP> 획득
```

그다음 App이 그 ClusterIP로 실제 요청을 보내면, **다시 kube-proxy DNAT**(13장)를 거쳐 payment Pod로 로드밸런싱된다.

> **핵심: "CoreDNS와 kube-proxy가 어떻게 통신하는가"의 답 — 직접 통신하지 않는다. CoreDNS는 `kube-dns`라는 Service 뒤에 있는 평범한 Pod이고, kube-proxy가 각 노드에 심은 Service DNAT 규칙 덕분에 Pod의 DNS 질의가 CoreDNS Pod로 로드밸런싱되어 도달한다. 즉 kube-proxy는 DNS 트래픽에도 다른 Service와 똑같은 규칙을 적용할 뿐이다.**

---

# Part V. Ingress와 Egress는 어떻게 관리되는가

먼저 방향 용어를 정리한다.

```text
        클러스터 외부(인터넷/사내망)
             ▲            │
   Egress    │            │   Ingress
 (나가는 것)  │            ▼  (들어오는 것)
        ┌──────── Cluster ────────┐
        │  Pod ◀──East-West──▶ Pod │   ← Service/메시가 담당
        └──────────────────────────┘
```

- **Ingress (North-South, 인바운드)**: 외부 → 클러스터 내부 서비스로의 진입.
- **Egress (North-South, 아웃바운드)**: 클러스터 Pod → 외부(서드파티 API·DB·인터넷)로의 유출.
- **East-West**: Pod 간 내부 통신 (Service·서비스 메시가 담당, Part II·IV).

## 15. Ingress — 외부 트래픽을 안으로 들이기

Kubernetes 자체 Service만으로는 L7(HTTP 경로·호스트 기반) 라우팅과 단일 진입점을 만들기 어렵다. 그래서 다음 계층이 있다.

- **Ingress 리소스 + Ingress Controller**: `Ingress` 오브젝트에 "host/path → Service" 규칙을 선언하면, 클러스터에 배치된 **Ingress Controller(예: nginx, Envoy 기반)**가 이를 실제 L7 프록시 설정으로 구현. 외부 진입은 보통 `LoadBalancer` 타입 Service(클라우드 LB) 또는 NodePort로 노출.
- **Gateway API**: Ingress의 후속 표준. `GatewayClass` / `Gateway`(리스너·인프라) / `HTTPRoute`(라우팅 규칙)로 역할을 분리해 더 표현력 있고 멀티테넌시에 적합.
- **Istio의 Ingress**: `istio-ingressgateway`(독립 Envoy Deployment)가 클러스터 입구에서 외부 트래픽을 받아 `Gateway` + `VirtualService` 규칙으로 내부 메시로 전달.

```text
인터넷 → 클라우드 LB → [Ingress/Gateway Controller = L7 프록시]
                          │  host/path 매칭
                          ▼
                     내부 Service(ClusterIP) → kube-proxy DNAT → Pod
```

## 16. Egress — 밖으로 나가는 트래픽 통제

기본적으로 Kubernetes는 **모든 egress를 허용**한다. 통제하려면:

- **NetworkPolicy (egress)**: L3/L4 규칙으로 "이 Pod는 이 CIDR/포트로만 나갈 수 있다"를 선언. 단 표준 NetworkPolicy는 **IP/포트 기반**이라 `api.github.com` 같은 도메인 통제는 어렵다(외부 IP가 자주 바뀜).
- **DNS/FQDN 기반 정책**: 도메인 단위 egress 통제. 표준 NetworkPolicy로는 불가 → Cilium `toFQDNs`(Part VI) 같은 확장이 필요.
- **Egress Gateway (고정 출구 IP)**: 특정 Pod의 외부 트래픽을 지정된 게이트웨이 노드로 몰아 **예측 가능한 소스 IP로 SNAT**. 외부 방화벽이 "이 IP만 허용"으로 잠긴 레거시 연동에 필수.
- **Istio의 Egress**: `ServiceEntry`로 외부 서비스를 메시에 등록하고, 선택적으로 `istio-egressgateway`를 통해 모든 외부 트래픽을 한 지점으로 모아 정책·관측·mTLS를 적용.

```text
Pod ──(egress)──▶ [정책 지점]
                    ├─ NetworkPolicy: dst CIDR/포트 allow/deny
                    ├─ FQDN 정책: 허용 도메인만 (DNS 관찰 필요)
                    └─ Egress Gateway: 고정 IP로 SNAT 후 외부로
```

---

# Part VI. Cilium은 이 모든 것을 어떻게 바꾸는가

여기서 Part II~V의 조각들(Envoy 사이드카·iptables·kube-proxy·DNS·Ingress·Egress)이 하나로 모인다. Cilium은 이 기능들을 **eBPF 데이터 플레인**으로 재구현해 통합한다.

## 17. 출발점의 차이

Istio는 **서비스 메시**에서 출발했고, Cilium은 **Kubernetes 네트워킹·보안(CNI)**에서 출발했다.

```text
Cilium의 책임 범위:
  Pod networking(CNI) + Service LB + kube-proxy 대체
  + NetworkPolicy + Observability(Hubble)
  + Ingress/Gateway API + 일부 Service Mesh(mTLS/L7)
```

철학: **커널에서 eBPF로 처리할 수 있는 것은 커널에서(L3/L4), 프로토콜 해석이 필요할 때만 Envoy를(L7).**

```text
일반 L3/L4:   Pod ── eBPF ──────────▶ Pod      (프록시 없음)
L7 정책 필요:  Pod ── eBPF ─▶ Envoy ─▶ Pod      (필요할 때만 Envoy)
```

## 18. kube-proxy 대체 — 소켓 레벨 로드밸런싱

Cilium `kubeProxyReplacement`를 켜면 kube-proxy DaemonSet과 iptables Service 규칙(13장)이 **사라진다**. 대신:

- **Socket LB (connect-time 변환)**: Pod가 ClusterIP로 `connect()`하는 **바로 그 순간**, cgroup에 붙은 eBPF 프로그램(`cgroup/connect`, `cgroup/sendmsg`)이 목적지 주소를 **실제 백엔드 Pod IP로 직접 치환**한다. 패킷이 네트워크 스택을 타기 **전에** 끝나므로 per-packet DNAT·conntrack 오버헤드가 없다.
- **eBPF Service Map (O(1))**: Service→백엔드 매핑을 eBPF 해시맵으로 조회. 서비스·엔드포인트 수가 늘어도 조회 비용 일정. iptables 모드는 규칙이 선형으로 늘어 대규모에서 성능·지연이 나빠지는데, 이를 해소.
- 외부에서 들어와 소켓 LB를 못 쓰는 트래픽(NodePort 등)은 TC/XDP 훅에서 eBPF가 처리.

```text
[iptables 모드]  connect → 커널 KUBE-SERVICES 선형 매칭 → DNAT → conntrack → 전송
[Cilium 소켓LB]  connect → cgroup eBPF가 즉시 백엔드IP로 치환 → 바로 전송 (스택 우회)
```

DNS 서버 자체(CoreDNS)는 Cilium이 대체하지 않는다. 다만 Pod→kube-dns ClusterIP 질의도 위 소켓 LB로 CoreDNS Pod에 도달하므로, **DNS 경로에서 iptables가 빠진다.**

## 19. DNS 처리 — Cilium DNS Proxy와 FQDN 정책

16장에서 표준 NetworkPolicy로는 도메인 기반 egress가 어렵다고 했다. Cilium은 이를 **DNS proxy**로 푼다.

- Pod의 DNS 질의를 eBPF가 cilium-agent 내부의 **DNS proxy(Go L7 프록시)**로 리다이렉트한다.
- proxy는 질의를 정책으로 필터링(허용 도메인만)하고 **응답을 관찰**한다. `toFQDNs: api.github.com` 정책이 있으면, 그 도메인의 응답 IP를 TTL 동안 자동으로 "허용 IP"로 데이터패스에 등록한다.
- 이후 그 IP로의 L3 연결만 허용 → **도메인 단위 egress 통제**가 가능해진다.

```text
Pod ── DNS 질의 ──▶ eBPF redirect ──▶ Cilium DNS proxy
                                        ├─ 정책 위반 도메인 → 거부
                                        ├─ 허용 → CoreDNS/업스트림으로 forward
                                        └─ 응답 IP를 toFQDNs 허용목록에 등록(TTL)
그 후: Pod ── 그 IP로 연결 ──▶ 데이터패스가 "허용된 FQDN IP"만 통과
```

## 20. Ingress / Gateway API — per-node Envoy

Cilium은 Ingress·Gateway API를 **네이티브로** 지원한다. L7 라우팅이 필요할 때 별도 Ingress Controller Deployment 대신, Cilium이 관리하는 **노드 단위 Envoy**(cilium-agent에 내장 또는 전용 Envoy DaemonSet)가 처리한다. 즉 L3/L4는 eBPF, L7 HTTP 라우팅만 Envoy로 위임 — Part II의 "필요할 때만 Envoy" 철학이 Ingress에도 적용된다.

## 21. Egress Gateway — 고정 출구 IP

16장의 Egress Gateway를 Cilium은 eBPF로 구현한다. 특정 Pod(라벨 기준)에서 특정 외부 CIDR로 나가는 트래픽을 지정된 **게이트웨이 노드**로 라우팅하고, 그 노드의 **고정 IP로 SNAT(마스커레이드)**한다. 외부 방화벽 allowlist·레거시 연동에 사용. (전제: BPF masquerade + kube-proxy replacement 활성화 필요.)

## 22. Envoy는 Cilium에서 언제 쓰이나

- **안 쓰는 경우(대부분)**: L3/L4 라우팅·Service LB·NetworkPolicy·마스커레이드 → 전부 eBPF(커널).
- **쓰는 경우(L7만)**: HTTP/gRPC/Kafka L7 정책, Ingress/Gateway L7 라우팅, L7 관측/메시 기능 → 노드 단위 Envoy로 위임.

> 참고: 위 L7 경로(HTTP 경로 라우팅·정교한 L7 authz 등)를 **깊게 쓰는 경우는 실무에서 많지 않다.** 대다수 트래픽은 L4·mTLS·기본 정책·관측 수준에서 처리되므로, Envoy가 실제로 관여하는 비중은 생각보다 작다.

## 23. 대응표 — 기존 구성 요소 → Cilium

| 기존 Kubernetes/Istio | Cilium에서 | 계층 |
|---|---|---|
| CNI 플러그인 | Cilium CNI (eBPF datapath) | L3 |
| kube-proxy (iptables DNAT) | eBPF socket LB + Service map | L4 |
| NetworkPolicy (L3/L4) | eBPF 정책 (identity 기반) | L3/L4 |
| 도메인 egress (표준으론 불가) | DNS proxy + `toFQDNs` | L7-aware |
| 고정 출구 IP (별도 장비) | Egress Gateway (eBPF SNAT) | L3 |
| Ingress Controller | Cilium Ingress/Gateway (Envoy) | L7 |
| 메트릭·트레이싱·flow 가시성 | Hubble | 관측 |
| Envoy 사이드카(모든 Pod) | 노드 단위 Envoy (L7 필요 시만) | L7 |

## 24. Cilium과 Istio Ambient — 핵심 차이

둘 다 "Pod마다 Envoy 사이드카를 넣지 않는다"는 공통점이 있지만 출발점과 범위가 다르다.

| 항목 | Istio Ambient | Cilium |
|---|---|---|
| 출발점 | 서비스 메시 | CNI·Kubernetes 네트워킹 |
| 기본 데이터 플레인 | ztunnel(L4 프록시, 노드당) | eBPF 커널 데이터패스 |
| L7 처리 | Waypoint(Envoy) | Cilium Envoy(노드당) |
| Pod 네트워크 | 별도 CNI 필요 | Cilium 자체가 CNI |
| Service 라우팅 | 기존 CNI·kube-proxy 위에 메시 | kube-proxy까지 대체 |
| 기본 보안 단위 | 워크로드 identity·mTLS | security identity·NetworkPolicy |
| 관측 | Istio telemetry | Hubble |
| 강점 | 성숙한 mTLS·풍부한 L7 메시 | 네트워크·정책·관측 통합 |
| mTLS 성숙도 | 핵심 기능, 성숙 | 버전별 성숙도 확인 필요 |

구조적으로:

```text
[Istio Ambient]  App → ztunnel(L4) → (필요시 Waypoint L7) → K8s 네트워크 → CNI/kube-proxy
                  = 기존 네트워크 "위에" 메시 계층을 추가

[Cilium]         App → eBPF datapath ┬ Service LB
                                     ├ NetworkPolicy
                                     ├ Observability(Hubble)
                                     └ (필요시 Envoy L7)
                  = 네트워크 "자체"에 들어가 통합
```

**완전한 대체재가 아니다**: Cilium은 CNI·kube-proxy 대체·L3/L4 정책·DNS/FQDN·flow 가시성에서 강하고, Istio Ambient는 성숙한 서비스 간 mTLS·identity 중심 Zero Trust·복잡한 L7 트래픽 관리(fault injection·정교한 authz)에서 앞선다. 실제로 **Cilium을 CNI/데이터패스로 깔고 그 위에 Istio Ambient를 얹는** 조합도 쓰인다.

### 실무 관점 — 왜 Cilium을 먼저 고려하는가

위 차이에도 불구하고, **일반적인 서비스 운영에서 깊은 L7 트래픽 관리(정교한 경로 라우팅·fault injection·복잡한 L7 authz)를 실제로 쓰는 경우는 많지 않다.** 대부분의 워크로드가 필요로 하는 것은 L4 연결·mTLS·기본 접근 정책·관측 수준이다. 이 지점에서 Cilium의 장점이 두드러진다.

- **Service Mesh와 CNI를 한 곳에서 관리**: 별도 CNI + 별도 메시(각자의 제어 플레인·업그레이드·트러블슈팅)를 두 스택으로 운영하는 대신, Pod 네트워킹부터 Service LB·NetworkPolicy·L7 정책까지 **하나의 eBPF 데이터 플레인**으로 통합해 운영 표면을 줄인다.
- **Hubble 네트워크 옵저버빌리티**: 데이터 플레인이 커널에 있으므로 allow/drop·source/destination identity·DNS·L3/L4 flow(및 일부 L7)를 **추가 사이드카 없이** 흐름 단위로 관찰할 수 있다. 장애를 "어느 계층에서 끊겼나" 기준으로 바로 추적 가능.
- **L7 심층 기능 의존이 낮은 환경**이라면, Ambient가 앞서는 영역(성숙한 L7 메시)의 이점이 상대적으로 작아진다.

> **판단:** L7을 깊게 다루지 않는 대다수 환경에서는, **네트워킹·정책·관측을 단일 데이터 플레인으로 묶는 Cilium을 Istio Ambient보다 먼저 도입하는 편이 낫다.** 단, 서비스 간 mTLS·identity 기반 Zero Trust나 정교한 L7 트래픽 관리가 핵심 요구라면 Ambient(또는 Cilium 위에 Ambient 병용)를 함께 검토한다.

### Cilium 장단점 한눈에

| 장점 | 단점 · 주의점 |
|---|---|
| Service Mesh + CNI를 **하나의 eBPF 데이터 플레인**으로 단일 관리 | 서비스 간 **mTLS·Zero Trust 성숙도**는 Istio에 못 미침(버전 확인) |
| **kube-proxy 대체**(socket LB, O(1))로 iptables 제거 | **정교한 L7 트래픽 관리**(fault injection·복잡한 authz)는 Istio가 앞섬 |
| **Hubble**로 사이드카 없이 flow 가시성(관측) | **eBPF·커널 버전 의존**, 러닝커브 존재 |
| **FQDN egress·Egress Gateway** 등 정책이 강력 | 깊은 서비스 메시 기능·생태계는 여전히 Istio가 풍부 |
| 사이드카가 없어 **리소스·지연 절감** | 초기 도입·트러블슈팅에 eBPF 지식 필요 |

---

# Part VII. 정리

## 25. Cilium을 공부해야 하는 이유

1. **Kubernetes 네트워크의 가장 아래 계층을 이해한다.** Istio를 배우면 프록시·L7·mTLS·메시 정책까지지만, Cilium을 배우면 그 아래 — Pod 패킷이 노드를 어떻게 나가는가, CNI가 Pod 네트워크를 어떻게 구성하는가, Service IP가 어떻게 Endpoint로 변환되는가, kube-proxy/iptables가 무엇을 하는가, eBPF가 어떤 훅에서 패킷을 처리하는가, NetworkPolicy가 실제로 어디서 강제되는가 — 까지 내려간다.
2. **네트워크 구성 요소가 통합되는 방향을 이해한다.** CNI·kube-proxy·NetworkPolicy·메트릭·tracing·Ingress·메시로 흩어진 역할이 왜 하나의 eBPF 데이터 플레인으로 수렴하는지, 왜 "분리된 프록시·iptables 중심"에서 "eBPF 통합 데이터패스"로 이동하는지 보인다.
3. **장애를 네트워크 흐름 기준으로 분석한다.** DNS 실패? Service가 Endpoint를 못 골랐나? NetworkPolicy에서 drop? 노드 간 라우팅 실패? L7 authz 거절? — Hubble로 allow/drop, source/destination identity, DNS, L3/L4 flow, 일부 L7을 데이터패스 관점에서 관찰.
4. **Istio Ambient도 더 정확히 이해한다.** ztunnel이 왜 노드 단위 공유 프록시인지, 사이드카를 왜 제거했는지, L4/L7을 왜 분리했는지 — Pod netns·트래픽 리다이렉션·CNI·identity 정책·커널 vs 프록시 데이터패스를 알아야 보인다.

## 26. 발표 흐름 요약

```text
1. K8s는 서비스 "연결"은 주지만, 통신의 신뢰성·보안·관측까진 해결 안 함.
2. Istio는 Envoy 사이드카로 이 공통 기능을 앱 밖으로 분리.
   → 주입(webhook) + 가로채기(iptables 15006/15001) + 프록시(Envoy) + 배포(istiod xDS).
3. 모든 Pod에 범용 L7 프록시 = 리소스·운영 복잡성 급증.
4. Ambient는 L4(ztunnel)/L7(Waypoint)로 계층화해 이를 완화.
5. 그 밑단(CoreDNS=Deployment, kube-proxy=DaemonSet)이 실제로 어떻게 도는지:
   DNS 질의도 결국 kube-dns Service → kube-proxy DNAT → CoreDNS Pod.
6. Ingress/Egress는 별도 컨트롤러·정책·게이트웨이로 관리.
7. Cilium은 이 모두를 eBPF 데이터패스로 재구현·통합.
   kube-proxy(socket LB)·DNS(FQDN proxy)·Ingress·Egress Gateway, L7만 Envoy.
8. 그래서 Cilium 공부 = 특정 제품 사용법이 아니라
   현대 K8s 네트워크가 어떻게 진화하는지를 공부하는 것.
```

## 결론

> **Istio가 서비스 간 통신을 "프록시"로 추상화했다면, Cilium은 Kubernetes 네트워크 "자체"를 프로그래밍 가능한 eBPF 데이터 플레인으로 바꾸고 있다. 사이드카가 어떻게 뜨는지(webhook·iptables·Envoy·xDS), Service·DNS가 어떻게 도는지(kube-proxy DNAT·kube-dns), Ingress·Egress가 어떻게 통제되는지를 알고 나면, Cilium은 그 조각들을 커널로 끌어내려 하나로 합친 결과임이 보인다. 그래서 Cilium을 공부하는 것은 Istio의 대체재를 배우는 것이 아니라, Kubernetes 네트워킹의 다음 단계를 배우는 것이다.**

> **도입 관점 한 줄:** L7을 깊게 쓰지 않는 대다수 환경이라면, **Service Mesh·CNI·관측을 하나로 묶고 Hubble로 흐름을 보는 Cilium을 Istio Ambient보다 먼저 고려**하는 것이 합리적이다.

---

## 참고 자료

- Istio 사이드카 주입·iptables·트래픽 라우팅: Jimmy Song, "Understanding the Sidecar Injection, Traffic Intercepting & Routing Process in Istio" — https://jimmysong.io/blog/sidecar-injection-iptables-and-traffic-routing/
- Istio 컴포넌트 포트 상세: Tetrate, "Istio component ports and functions in detail" — https://tetrate.io/blog/istio-component-ports-and-functions-in-detail
- Istio iptables 스냅샷(체인·UID 1337): istio/istio Wiki, "Understanding IPTables snapshot" — https://github.com/istio/istio/wiki/Understanding-IPTables-snapshot
- Envoy 사이드카 자원(성능·기본 requests/limits): Istio Docs, "Performance and Scalability" — https://istio.io/latest/docs/ops/deployment/performance-and-scalability/
- ztunnel(DaemonSet)·Waypoint(Deployment) 배포 모델: Istio Docs, "Ambient Overview" / "Configure waypoint proxies" — https://istio.io/latest/docs/ambient/overview/
- CoreDNS(Deployment) 서비스 디스커버리: Kubernetes Docs, "Using CoreDNS for Service Discovery" — https://kubernetes.io/docs/tasks/administer-cluster/coredns/
- Service/Pod DNS·resolv.conf·ndots: Kubernetes Docs, "DNS for Services and Pods" — https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/
- kube-proxy 가상 IP·DNAT: Kubernetes Docs, "Virtual IPs and Service Proxies" — https://kubernetes.io/docs/reference/networking/virtual-ips/
- Cilium kube-proxy 대체(socket LB): Cilium Docs, "Kubernetes Without kube-proxy" — https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/
- Cilium DNS/FQDN 정책·DNS proxy: Cilium Docs, "Locking Down External Access with DNS-Based Policies" — https://docs.cilium.io/en/latest/security/dns/
- Cilium Egress Gateway: Cilium Docs, "Egress Gateway" — https://docs.cilium.io/en/stable/network/egress-gateway/egress-gateway/
- CNI 스펙·ADD/DEL·kubelet↔CRI↔플러그인: Kubernetes Docs, "Network Plugins" — https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/
- CNI 규약(스펙 본문): CNI, "Container Network Interface Specification" — https://www.cni.dev/docs/
