---
tags: [kubernetes, ch11, internals, control-plane, etcd, networking]
---

# Chapter 11: Understanding Kubernetes internals

> 클러스터 내부에서 컨트롤 플레인과 워커 노드의 컴포넌트들이 실제로 어떻게 협력하는지, Pod이 만들어지고 네트워킹/서비스가 작동하기까지 어떤 일이 일어나는지를 다룬다.

## 핵심 한 줄 요약

- **컴포넌트 간 직접 통신 없음** — 모두 API Server를 경유. API Server만이 etcd와 대화.
- **컨트롤러는 reconcile loop** — Watch API로 변경 구독, desired vs actual 비교, 차이를 메운다.
- **Scheduler는 Pod을 실행하지 않는다** — `spec.nodeName`만 채워 넣는다. 실행은 kubelet.
- **Service는 가상 IP** — 실제 인터페이스 없음. kube-proxy가 iptables/IPVS NAT 규칙으로 구현.
- **HA 패턴**: etcd/API Server는 multi-active, Controller Manager/Scheduler는 leader election으로 active-passive.

## Key Concepts

### 1. 클러스터 아키텍처 한눈에 보기

Kubernetes는 크게 **Control Plane**과 **Worker Node**로 나뉜다.

| 구분 | 컴포넌트 | 역할 |
|------|----------|------|
| Control Plane | **etcd** | 클러스터의 모든 상태를 저장하는 분산 KV 스토어 (단일 진실의 원천) |
| Control Plane | **API Server** (`kube-apiserver`) | 모든 컴포넌트가 통신하는 유일한 게이트웨이. etcd와 직접 대화하는 유일한 컴포넌트 |
| Control Plane | **Scheduler** (`kube-scheduler`) | Pod을 어떤 Node에 배치할지 결정 |
| Control Plane | **Controller Manager** (`kube-controller-manager`) | 다양한 컨트롤러(Replication, Deployment, Node, Endpoints 등)를 한 프로세스에서 실행 |
| Worker Node | **kubelet** | 노드 위 컨테이너 라이프사이클 관리. API Server에 자기 노드 상태 보고 |
| Worker Node | **kube-proxy** | Service의 가상 IP를 노드 위 iptables/IPVS 규칙으로 변환 |
| Worker Node | **Container Runtime** | Docker / containerd / CRI-O 등 |
| Add-on | **CoreDNS, Dashboard, Ingress controller, CNI plugin** | 부가 기능 |

핵심 원칙: **컴포넌트 간 직접 통신은 없다. 모두 API Server를 거친다.**

### 2. etcd — 단일 진실의 원천

- 분산 KV 스토어. **API Server만이 etcd에 직접 접근**한다 (다른 컴포넌트는 모두 API Server 경유).
- Raft 합의 알고리즘으로 일관성 보장. 홀수 개(3/5/7)의 인스턴스를 권장 — 과반수(quorum)가 살아 있어야 쓰기 가능.
- 짝수 개(예: 4)는 split-brain 위험과 가용성 측면에서 홀수보다 나쁘다. 4대 클러스터는 2대 장애 시 quorum이 깨지지만, 3대 클러스터도 마찬가지로 1대까지만 견딘다 → 비용만 더 든다.
- 모든 리소스(Pod, Service, ConfigMap …)는 etcd에 JSON/Protobuf 형태로 직렬화되어 저장된다.

### 3. API Server의 역할

1. **인증(Authentication)** — 클라이언트가 누구인가? (인증서, 토큰, OIDC 등)
2. **인가(Authorization)** — 그 클라이언트가 이 작업을 해도 되는가? (RBAC 등, ch12에서 자세히)
3. **Admission Control** — 요청을 변형/검증 (LimitRanger, ResourceQuota, MutatingWebhook 등)
4. **유효성 검증 후 etcd에 저장**
5. **변경 이벤트 통지** — Watch 메커니즘으로 컨트롤러/스케줄러/kubelet에 알림

API Server는 RESTful이며, **모든 컴포넌트는 Watch API로 변경을 구독**한다 (polling 아님).

### 4. Controller Manager — 컨트롤러 루프

각 컨트롤러는 다음 패턴을 반복한다:

```
1. Watch API로 자기 담당 리소스 변경 감지
2. 현재 상태(actual state)와 원하는 상태(desired state) 비교
3. 차이가 있으면 API Server에 변경 요청
4. → 다시 1번으로
```

대표 컨트롤러:

- **Replication Manager** (RC), **ReplicaSet/Deployment/DaemonSet/StatefulSet/Job/CronJob Controller**
- **Node Controller** — 노드 상태 모니터링, NotReady 시 Pod 축출(eviction)
- **Service Controller, Endpoints Controller** — Service ↔ Pod 매핑 관리
- **Namespace Controller, ServiceAccount Controller, PersistentVolume Controller** 등

### 5. Scheduler — Pod 배치 결정

`spec.nodeName`이 비어 있는 Pod을 찾아 적절한 노드를 골라 채워 넣는다. **직접 Pod을 실행하지는 않는다** (kubelet이 함). 두 단계:

1. **Filtering(Predicates)** — 후보 노드 거르기
   - 자원 충분한가 (CPU/Memory)
   - nodeSelector, nodeAffinity, taints/tolerations 만족하는가
   - hostPort 충돌 없는가
   - PV 접근 가능한가
2. **Scoring(Priorities)** — 남은 노드에 점수 매기기
   - 자원 밸런스, 이미지 캐시 보유 여부, Pod anti-affinity 등
3. 최고 점수 노드에 `Pod.spec.nodeName` 업데이트

여러 스케줄러를 동시에 운영 가능 (`spec.schedulerName`으로 지정).

### 6. Pod이 생성되기까지의 전체 흐름

`kubectl create -f deployment.yaml` 한 번으로 일어나는 일:

```
[kubectl] → [API Server] → [etcd]: Deployment 객체 저장
                ↓ Watch 이벤트
[Deployment Controller] → ReplicaSet 생성 → API Server → etcd
                ↓ Watch 이벤트
[ReplicaSet Controller] → Pod(들) 생성 (nodeName 비어 있음) → API Server → etcd
                ↓ Watch 이벤트
[Scheduler] → 노드 결정 → Pod.spec.nodeName 업데이트 → API Server → etcd
                ↓ Watch 이벤트 (해당 노드 kubelet만)
[kubelet] → 컨테이너 런타임에 컨테이너 실행 지시 → 상태 보고 → API Server → etcd
```

이 모든 단계가 **이벤트 기반(event-driven)** 으로 비동기로 진행된다.

### 7. 컨트롤러의 고가용성

- API Server는 stateless이므로 여러 인스턴스를 active-active로 운영 가능 (앞에 LB).
- Controller Manager / Scheduler는 **leader election**으로 active-passive 구성 → 동시에 두 컨트롤러가 같은 리소스를 조작해 race condition이 나는 것을 방지. (etcd `Endpoints`/`Lease` 객체에 lock)

### 8. 노드 간 네트워킹 — CNI

Kubernetes 네트워크 모델 3대 요구사항:

1. 모든 Pod은 **NAT 없이** 서로 통신할 수 있어야 한다.
2. 모든 노드는 NAT 없이 모든 Pod과 통신할 수 있어야 한다.
3. Pod이 보는 자기 IP = 다른 Pod이 보는 그 Pod의 IP (IP가 변환되지 않는다).

이 요구를 만족시키는 구현이 **CNI 플러그인**: Flannel(VXLAN), Calico(BGP/IPIP), Weave, Cilium(eBPF) 등. kubelet은 Pod이 뜨기 직전 CNI 바이너리를 호출해 네트워크 네임스페이스에 인터페이스를 꽂는다.

### 9. Service의 동작 — kube-proxy

Service의 ClusterIP는 **실제 인터페이스가 없는 가상 IP**. 동작 방식:

- **userspace mode** (구식, 거의 안 씀): kube-proxy가 직접 프록시.
- **iptables mode** (기본): kube-proxy가 iptables NAT 규칙을 노드에 설치 → 패킷이 ClusterIP로 가면 커널이 무작위 Pod IP로 DNAT.
- **IPVS mode**: iptables보다 빠른 룰셋, 라운드로빈 등 다양한 LB 알고리즘 지원.

Endpoints/EndpointSlice 객체가 "이 Service는 이 Pod IP들로 부하분산해라"를 정의하고, kube-proxy가 이를 Watch해서 노드 규칙을 갱신한다.

### 10. 고가용성 클러스터 정리

- **etcd**: 3/5/7개 인스턴스, 별도 노드 권장
- **API Server**: 여러 개 + 앞단 L4 LB
- **Controller Manager / Scheduler**: leader election (여러 개 띄워도 한 번에 하나만 active)
- **워커 노드**: 여러 개, Pod replica를 spread (anti-affinity, topologySpreadConstraints)

## 책 vs 현실 차이점

| 책(2018, k8s ~1.9) | 현재(2024+) |
|---------------------|-------------|
| Scheduler가 직접 점수 매기는 predicates/priorities | **Scheduler Framework** (v1.19+ stable) — 확장 포인트(QueueSort, Filter, Score, Bind 등)에 플러그인 끼우는 방식 |
| DaemonSet Pod은 **DaemonSet controller가 직접 노드 지정** (Scheduler 우회) | v1.12+ **기본 스케줄러 경유**. nodeAffinity로 강제 (`spec.affinity.nodeAffinity`) |
| Endpoints 객체 하나가 Service의 모든 Pod IP를 포함 | **EndpointSlice** (v1.21+ default) — Endpoints를 샤딩 (~100 endpoint/slice). 대규모 Service 성능 개선 |
| iptables / userspace 두 가지 모드 | **IPVS** (v1.11+ stable) + **nftables** (v1.31+ alpha) 추가. iptables는 여전히 default |
| controller-manager 안 leader election은 Endpoints 객체 lock | **Lease 객체** (`coordination.k8s.io/v1`) 기본 — Endpoints lock은 deprecated |
| etcd v2 호환 (Kubernetes 1.5까지) | **etcd v3 전용** (v1.6부터). MVCC, gRPC 기반 |
| CNI는 옵션 | 사실상 필수. kubenet은 거의 안 쓰임 |

## Deep dives

### A. Watch API 메커니즘

Watch는 polling이 아니라 **long-lived HTTP 연결로 chunked transfer**. 흐름:

```
GET /api/v1/pods?watch=true&resourceVersion=12345
  → HTTP/1.1 200 OK
    Transfer-Encoding: chunked
    [chunk] {"type":"ADDED","object":{...}}
    [chunk] {"type":"MODIFIED","object":{...}}
    [chunk] {"type":"DELETED","object":{...}}
    ...
```

- `resourceVersion` — etcd revision. 클라이언트가 마지막으로 본 버전을 알려주면 그 이후 이벤트만 받는다.
- 연결이 끊기면 클라이언트는 마지막 RV로 재연결. RV가 너무 오래되면 `410 Gone` → **relist** 필요.
- `client-go`의 **Informer**가 이걸 추상화: List + Watch + 로컬 캐시(`Indexer`) + 이벤트 핸들러.

### B. Raft와 etcd 클러스터 크기

etcd는 Raft 합의로 일관성을 보장한다. **과반수(quorum) = ⌊N/2⌋+1**.

| 클러스터 크기 | quorum | 허용 장애 | 비고 |
|--------------|--------|-----------|------|
| 1 | 1 | 0 | 단일 장애점 |
| 3 | 2 | 1 | 권장 최소 |
| 4 | 3 | 1 | 3보다 가용성 동일, 비용만 ↑ → **나쁨** |
| 5 | 3 | 2 | 대규모 권장 |
| 7 | 4 | 3 | 매우 큰 클러스터 |

짝수가 나쁜 이유: 4대 클러스터가 2대 잃으면 quorum 깨짐(2 < 3). 3대 클러스터도 2대 잃으면 깨짐. 둘 다 1대까지만 견디는데 4대는 비용만 더 든다. 또한 split-brain 위험에서 짝수는 동수(tie) 분할 가능성이 있다.

### C. Scheduler Framework 확장 포인트 (v1.19+)

```
PreEnqueue → QueueSort → PreFilter → Filter → PostFilter
                                       ↓
                              PreScore → Score → NormalizeScore
                                       ↓
                              Reserve → Permit → PreBind → Bind → PostBind
```

각 포인트에 플러그인을 끼울 수 있다. 예: `NodeResourcesFit`(Filter), `ImageLocality`(Score), `VolumeBinding`(PreBind). 커스텀 스케줄러는 이 프레임워크 위에 빌드.

### D. kube-proxy iptables 규칙 모양

ClusterIP `10.96.5.10:80` → Pod `10.244.1.5:8080`, `10.244.2.7:8080` 두 개로 분산할 때 노드에 생기는 규칙(요약):

```
# 1) 서비스 IP/포트 매칭 → KUBE-SVC-XXX 체인으로 점프
-A KUBE-SERVICES -d 10.96.5.10/32 -p tcp --dport 80 -j KUBE-SVC-XXX

# 2) 50% 확률로 첫 번째 endpoint, 나머지는 두 번째
-A KUBE-SVC-XXX -m statistic --mode random --probability 0.5 -j KUBE-SEP-A
-A KUBE-SVC-XXX -j KUBE-SEP-B

# 3) 실제 Pod IP로 DNAT
-A KUBE-SEP-A -p tcp -j DNAT --to-destination 10.244.1.5:8080
-A KUBE-SEP-B -p tcp -j DNAT --to-destination 10.244.2.7:8080
```

→ Endpoint 수가 많아지면 iptables 규칙도 선형 증가 → 룰 평가 시간 ↑. 그래서 대규모 클러스터는 **IPVS**로 전환 (해시 테이블 기반 O(1)).

### E. Leader election (Lease 기반)

```yaml
apiVersion: coordination.k8s.io/v1
kind: Lease
metadata:
  name: kube-controller-manager
  namespace: kube-system
spec:
  holderIdentity: controller-manager-node1_<uuid>
  leaseDurationSeconds: 15
  renewTime: "2024-..."
  acquireTime: "2024-..."
```

- 각 컨트롤러 인스턴스가 주기적으로 (`renewDeadline` 안에) `renewTime`을 갱신.
- 갱신 실패 시 leader 자리 비움 → 다른 인스턴스가 `acquire` 시도.
- 기본 fail-over latency = `leaseDuration` (~15초) + 후보의 backoff 정도.

`kubectl get lease -A`로 현재 leader 확인 가능.

### F. DaemonSet이 Scheduler를 거치게 된 이유

이전: DaemonSet controller가 `spec.nodeName`을 직접 채움 → Scheduler가 모르는 Pod 존재 → 자원 회계 어긋남.

현재: DaemonSet controller가 Pod에 **`nodeAffinity` (hard, 그 노드 강제)** 와 **toleration**(모든 taint)을 넣어 만들고 Scheduler에 맡김. 결과적으로 그 노드에 정확히 한 개씩 배치됨. Scheduler가 자원을 올바르게 추적하게 됨.

## 면접 예상 질문

1. **etcd 클러스터를 4대로 운영하면 왜 안 되나요?**
   - quorum이 3이라 1대 장애만 견딘다 (3대 클러스터와 동일). 짝수는 split-brain 동수 분할 위험 + 비용만 ↑.
2. **API Server는 stateless인데 어떻게 Watch를 유지하나요?**
   - 상태는 etcd에. Watch 연결 자체는 메모리에 들고 있지만, 연결이 끊겨도 클라이언트가 `resourceVersion`으로 재연결하면 이어진다.
3. **Controller A와 Controller B가 같은 리소스를 동시에 수정하면?**
   - Controller Manager는 leader election으로 한 번에 하나만 active → 충돌 없음. 다른 종류의 컨트롤러 간에는 optimistic concurrency(`resourceVersion`) 충돌 → retry.
4. **Scheduler가 모든 노드를 거른다(filtering 통과 0)면 Pod은 어떻게 되나요?**
   - `Pending` 상태로 남고 이벤트에 `FailedScheduling` 기록. Scheduler는 주기적으로 재시도 (백오프 큐).
5. **DaemonSet도 Scheduler를 거치나요?**
   - v1.12+ 예. DaemonSet controller가 `nodeAffinity`로 노드를 강제하고 Scheduler가 배치 결정.
6. **Service의 ClusterIP로 ping이 안 되는 이유?**
   - 실제 인터페이스 없음. iptables NAT 규칙이 TCP/UDP 패킷에만 매칭됨 (ICMP는 안 받음).
7. **Pod이 Service를 통해 자기 자신을 호출하면?**
   - kube-proxy 모드/CNI에 따라 다름. iptables 모드 + Linux 커널 기본은 hairpin 활성화 시 작동. 비활성화면 자기 → 자기 패킷이 막힐 수 있음.
8. **Watch가 410 Gone을 받으면?**
   - resourceVersion이 etcd compaction으로 사라짐. Informer는 자동으로 **relist** 후 watch 재개.
9. **Endpoints vs EndpointSlice 차이?**
   - Endpoints는 Service당 1개 객체 → 큰 Service에서 매번 전체 객체가 전파됨(대역폭/처리 비용 ↑). EndpointSlice는 ~100개 endpoint씩 샤딩 → 변경 시 해당 slice만 업데이트.
10. **kubectl create -f deployment.yaml 후 Pod이 노드에 뜨기까지 거치는 컴포넌트 순서?**
    - API Server → etcd → (Deployment Controller → ReplicaSet) → (ReplicaSet Controller → Pod) → Scheduler → kubelet → CRI → 컨테이너 런타임.

## Notes

- "API Server만이 etcd와 대화한다"는 규칙이 디자인의 핵심. 이게 깨지면 일관성/감사성/캐싱 전략이 모두 흔들린다.
- Watch API는 long-polling + chunked response 기반. 컨트롤러들은 절대 polling 하지 않는다.
- 컨트롤러는 reconcile loop이지 transaction이 아니다 → 중간 상태가 잠깐 보일 수 있다 (eventual consistency).
- DaemonSet은 Scheduler를 거치지 않는다 (구버전). 최신 버전은 Scheduler를 거치되 nodeAffinity로 배치 강제.
- `kubectl get events`는 디버깅 첫걸음. 컨트롤러들이 reconcile하면서 남기는 흔적.
- `kubectl get --raw /metrics`로 컴포넌트 내부 메트릭 노출. Scheduler queue depth, etcd request latency 등 디버깅에 유용.

## Questions

- [ ] etcd 백업/복구는 실제로 어떻게 운영하는가? (snapshot 빈도, DR 시나리오)
- [ ] CNI 플러그인을 바꾸려면 어떤 절차가 필요한가? (런타임 교체 가능?)
- [ ] iptables → IPVS로 마이그레이션하는 실제 영향은?
- [ ] leader election에서 leader가 죽었을 때 fail-over latency는 얼마나 되는가?
