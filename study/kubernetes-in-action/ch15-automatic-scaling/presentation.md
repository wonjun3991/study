# Chapter 15 발표 정리 — Automatic Scaling

> 부하에 따라 Pod/노드를 자동으로 늘리고 줄이는 법. 핵심 질문: **"누가, 무엇을 보고, 무엇을 조절하는가?"**

## 발표 목차 (진행 순서)

1. **수평 확장 vs 수직 확장 개념** ← (작성 완료)
2. **Pod 단위 스케일링**
   - 수평(HPA): 컨트롤러 위치 / 메트릭 수집 경로(cAdvisor → kubelet → metrics-server → Aggregation Layer) / kubelet 구성요소 / Heapster의 죽음 / 계산식 / behavior
   - 수직(VPA): 3컴포넌트 / updateMode / HPA와 충돌 / 코어 빌트인 아님
3. **Node 단위 스케일링**
   - Cluster Autoscaler: Pending Pod → 노드 추가, 활용률 낮은 노드 제거
   - Karpenter / 책 vs 현실 (Heapster 폐기·idling 미구현·KEDA scale-to-zero)

---

## 1. 수평 확장 vs 수직 확장

### 1.1 일반적인 확장 개념 (인프라/아키텍처 관점)

쿠버네티스 이전에, **모든 시스템(서버·DB)에 공통인** 두 가지 확장 방식이 있다.

#### 수직 확장 (Scale Up / Scale Down) — "기계를 더 키운다"

한 대의 머신에 **자원을 더 붙인다**. CPU 코어 추가, RAM 증설, 더 빠른 디스크.

- 예: DB 서버를 4코어/16GB → 16코어/64GB 인스턴스로 교체. (AWS RDS 인스턴스 클래스 업그레이드)
- **장점**:
  - **단순함** — 애플리케이션 코드/구조를 안 바꿔도 됨.
  - 분산 시스템의 복잡성(데이터 일관성, 네트워크) 없음.
  - **상태 있는(stateful) 시스템·RDB**에 잘 맞음.
- **단점**:
  - **하드웨어 상한(ceiling)** — 한 대가 가질 수 있는 크기에 물리적 한계.
  - **단일 장애점(SPOF)** — 그 한 대가 죽으면 끝.
  - 보통 **업그레이드 시 재부팅/다운타임**.
  - 고사양으로 갈수록 **비용이 비선형적으로 폭증**.

#### 수평 확장 (Scale Out / Scale In) — "기계를 더 늘린다"

같은 역할의 **머신/인스턴스를 여러 대**로 늘리고 앞에 **로드 밸런서**를 둔다.

- 예: 웹 서버 1대 → 10대 + LB. DB는 read replica 추가 / 샤딩.
- **장점**:
  - **거의 선형적 확장** — 상한이 사실상 없음(머신을 계속 추가).
  - **고가용성(HA)** — 한 대 죽어도 나머지가 처리.
  - **저렴한 범용 하드웨어** 여러 대로 가능 (클라우드 친화적).
- **단점**:
  - **애플리케이션이 무상태(stateless)이거나 분산 상태를 다뤄야** 함.
  - 로드 밸런싱, **데이터 일관성/동기화**, 네트워크 오버헤드 등 **복잡성 증가**.

#### 핵심 트레이드오프

| | 수직 확장 (Up) | 수평 확장 (Out) |
|--|----------------|------------------|
| 방식 | 한 대를 키움 | 여러 대로 늘림 |
| 상한 | 하드웨어 한계 있음 | 사실상 무제한 |
| 가용성 | SPOF | HA(분산) |
| 복잡성 | 낮음(코드 그대로) | 높음(분산 설계) |
| 다운타임 | 보통 필요 | 보통 무중단 |
| 적합 | RDB, stateful, 레거시 | stateless 웹/API, MSA |
| 비용 곡선 | 고사양일수록 급증 | 범용 장비로 완만 |

> **업계 흐름**: 클라우드 네이티브는 **수평 확장 선호**(탄력성·HA·범용 장비). 단 **데이터베이스 등 stateful**은 여전히 수직 확장이 1차 수단 → 그래서 쿠버네티스도 둘 다 제공한다.

---

## 2. Pod 단위 스케일링

Pod 자체를 조절하는 두 방향: **수평(HPA, 개수)** 과 **수직(VPA, 크기)**.

---

### 2.1 수평 — HPA (Horizontal Pod Autoscaler)

#### 2.1.1 HPA 컨트롤러는 컨트롤 플레인 어디에 있나

- HPA는 **별도 데몬/Pod이 아니다.** **`kube-controller-manager`** 안에서 도는 **컨트롤 루프 하나**.
- 주기적으로(기본 **15초**, `--horizontal-pod-autoscaler-sync-period`) 돌면서:
  1. 메트릭 조회 → 2. 목표와 비교해 원하는 replica 계산 → 3. 대상의 **scale 서브리소스**(Deployment/ReplicaSet/StatefulSet) 업데이트.
- HPA **API**(`autoscaling/v1`, `v2`)는 kube-apiserver가 직접 서빙하는 **built-in API**.

```
[kube-controller-manager]
  └─ HPA 컨트롤 루프 (15초마다)
       조회 → 계산 → Deployment.spec.replicas 수정
```

#### 2.1.2 Pod 메트릭은 어떻게 수집되나 (원천)

자원 사용량의 **원천은 노드의 커널 cgroup**. 이게 위로 올라오는 경로:

```
컨테이너 실행
  └─ 커널이 cgroup에 CPU/메모리 사용량 기록
       └─ cAdvisor (kubelet에 내장) 가 cgroup 통계를 컨테이너별로 읽음
            └─ kubelet 이 노출: /metrics/resource (또는 /stats/summary)
```

- **cAdvisor**: 컨테이너 자원 사용량을 수집·집계·노출하는 데몬. **kubelet에 내장**돼 있다(별도 설치 X).
- 리눅스에선 **cgroup** 기반, 그 외엔 런타임의 CRI Container Metrics 사용.

#### 2.1.3 kubelet 구성요소

> kubelet은 단일 프로그램이 아니라 **여러 매니저의 묶음**이다. cAdvisor는 그중 "메트릭 수집" 담당 하나일 뿐. (오늘 메트릭 경로에서 보는 건 cAdvisor지만, "왜 메트릭 엔드포인트가 kubelet에 붙어 있나?"의 답이 여기 있다.)

**메트릭 관련 (오늘 주제)**

| 구성요소 | 역할 |
|----------|------|
| **cAdvisor** (내장) | 컨테이너별 CPU/메모리/네트워크/디스크 사용량 수집 |
| **Summary API** (`/stats/summary`) | 노드·Pod·컨테이너 사용량 요약(JSON) |
| **`/metrics/resource`** | 리소스 메트릭(Prometheus 포맷) — metrics-server v0.6+ 가 긁는 곳 |

**그 외 kubelet이 하는 일 (참고 — 메트릭과 별개)**

| 구성요소 | 역할 |
|----------|------|
| **SyncLoop** | kubelet 메인 루프 — "원하는 Pod 상태 ↔ 실제 상태"를 계속 일치시킴 |
| **PLEG** (Pod Lifecycle Event Generator) | 런타임을 폴링해 컨테이너 생성·종료 이벤트를 SyncLoop에 전달 |
| **CRI 클라이언트** | gRPC로 containerd/CRI-O에 컨테이너 기동 명령 (kubelet이 직접 안 띄움) |
| **Volume Manager** | PV/ConfigMap/Secret 등 볼륨 mount·unmount |
| **Image Manager** | 이미지 pull + 디스크 부족 시 GC |
| **Probe Manager** | liveness/readiness/startup probe 실행 |
| **Status Manager** | Pod 상태를 apiserver에 보고 |
| **Eviction Manager** | 노드 자원 압박(메모리/디스크) 시 Pod 축출 |
| **Node Lease** | apiserver에 주기적 heartbeat (노드 살아있음 표시) |

→ 즉 **kubelet = 노드 위 컨테이너의 생사·상태·자원·볼륨을 책임지는 에이전트**, cAdvisor는 그 안의 자원 측정 모듈.

#### 2.1.4 Heapster의 죽음 → 지금의 파이프라인

**예전(책, Heapster):**
```
kubelet/cAdvisor → Heapster(긁어 집계, InfluxDB 저장) → HPA가 Heapster를 직접 호출
```
- HPA가 **특정 구현(Heapster)에 직접 의존** → 결합도 높고 무거움.
- Heapster: **1.11(2018) deprecated → 2019 retired**. 지금 쓰면 안 됨.

**지금(metrics-server):**
```
각 노드 kubelet(/metrics/resource)
      │ metrics-server가 15초마다 scrape
      ▼
metrics-server (최근값만 메모리 보관 — 저장 안 함, 경량)
      │ APIService로 metrics.k8s.io 등록
      ▼
Aggregation Layer (kube-apiserver 내장) 가 요청을 프록시
      ▲
      │ HPA 컨트롤러 / kubectl top 이 metrics.k8s.io 조회
[kube-controller-manager] HPA
```

#### 2.1.5 핵심 구조 — 인터페이스 / 소켓 / 구현체

| 역할 | 무엇 | 비유 |
|------|------|------|
| **인터페이스(계약)** | `metrics.k8s.io` API | 콘센트 **규격** |
| **등록·라우팅** | **Aggregation Layer** (kube-apiserver 내장) | 벽에 박힌 **소켓** |
| **구현체** | **metrics-server** (애드온, 직접 설치) | 꽂는 **플러그** |
| **배선** | `APIService` 오브젝트 | "이 플러그를 이 소켓에" |

- **둘의 기본 내장 여부가 다르다:**
  - Aggregation Layer = ✅ kube-apiserver 내장 (단, APIService 등록 전엔 아무 일 안 함)
  - metrics-server = ❌ **애드온, 직접 배포** (안 깔면 `kubectl top`·HPA 둘 다 `<unknown>`)
- **HPA가 core인 이유**: HPA는 **인터페이스(`metrics.k8s.io`)에 의존**하지 구현(metrics-server)에 의존하지 않는다. 컨트롤러·API는 core, 데이터 공급자는 갈아끼우는 확장.

#### 2.1.6 HPA 계산식

```
desiredReplicas = ceil( currentReplicas × ( currentMetric / desiredMetric ) )
```

- 예: 현재 3 replica, CPU 평균 90%, 목표 50% → `ceil(3 × 90/50) = ceil(5.4) = 6`.
- **CPU 사용률은 노드가 아니라 컨테이너 `requests` 대비 %** → **requests 없으면 계산 불가(`<unknown>`)**. (ch14 직결)
- tolerance 10%: 비율이 0.9~1.1이면 변동 없음(미세 진동 방지).

#### 2.1.7 메트릭 종류 3가지

| type | 출처(API) | 예 |
|------|-----------|-----|
| `Resource` | metrics.k8s.io (metrics-server) | CPU, 메모리 |
| `Pods` / `Object` | custom.metrics.k8s.io (Prometheus Adapter) | 초당 요청수, 큐 길이 |
| `External` | external.metrics.k8s.io (어댑터/KEDA) | SQS·PubSub 메시지 수 |

- 여러 메트릭 지정 시 **각각 계산해 가장 큰 replica 채택**(안전).

#### 2.1.8 스케일링 안정화 — flapping 방지 (`behavior`)

```yaml
spec:
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5분 안정화 후 축소(보수적)
      policies: [{ type: Percent, value: 50, periodSeconds: 60 }]
    scaleUp:
      stabilizationWindowSeconds: 0    # 확장은 즉시
      policies: [{ type: Pods, value: 4, periodSeconds: 60 }]
```

- 기본: **scale-up 즉시 / scale-down 5분 보수적** → 진동 방지.

---

### 2.2 수직 — VPA (Vertical Pod Autoscaler)

> HPA가 개수를 늘린다면, VPA는 **Pod 하나의 requests/limits를 실제 사용량에 맞춰 자동 조정**.

#### 2.2.1 코어 빌트인 아님

- **VPA는 코어에 내장되지 않았다.** `kubernetes/autoscaler` 레포의 **별도 애드온** — 직접 설치해야 함. API 그룹도 `autoscaling.k8s.io`.
- 책(2017)이 "계획 중"이라던 기능이 **애드온 형태로 실현**됐을 뿐, HPA처럼 기본 탑재 아님.

#### 2.2.2 3개 컴포넌트

| 컴포넌트 | 역할 |
|----------|------|
| **Recommender** | 사용량 분석 → 적정 requests 추천값 계산 |
| **Updater** | 추천값과 동떨어진 기존 Pod을 **축출**(재생성 유도) |
| **Admission Controller** | 새로 뜨는 Pod에 추천값 **주입**(mutating webhook) |

#### 2.2.3 updateMode 4가지

| 모드 | 동작 | 용도 |
|------|------|------|
| `Off` | **추천만**, 변경 X | 가장 안전 / HPA와 병행 |
| `Initial` | 생성 시점에만 주입 | 재시작 부담 최소 |
| `Recreate` | Pod 죽이고 새 값으로 재생성 | 무중단 아님 |
| `Auto` | 현재 Recreate와 동일 | (향후 In-place resize 결합) |

#### 2.2.4 가장 큰 함정 — HPA와 충돌

- **같은 자원(CPU/메모리)에 HPA·VPA 동시 사용 금지.**
  - HPA: CPU↑ → replica↑ → Pod당 부하↓
  - VPA: CPU↑ → requests↑
  - 같은 신호에 반대로 반응 → **진동**.
- **허용 조합**: HPA(CPU) + VPA `Off`(추천만) / 또는 HPA(커스텀 메트릭 QPS) + VPA(CPU·메모리).

#### 2.2.5 무중단 수직 스케일링의 미래

- 전통적 VPA는 requests 변경 = **Pod 재시작**.
- 코어에 추가된 **In-place Pod Resize**(`resizePolicy`, 1.27 alpha → 1.33 beta)와 결합 시 **재시작 없이** 조정 목표.
- → "코어에 들어온 건 VPA가 아니라, 자원을 재시작 없이 바꾸는 In-place Resize."

---

## 3. Node 단위 스케일링

> Pod을 늘렸는데(HPA) **들어갈 노드가 없으면?** 노드 자체를 늘리는 게 이 레이어.

### 3.1 Cluster Autoscaler (CA)

클라우드 프로바이더(AWS ASG, GKE node pool 등)와 연동해 **노드 개수**를 조절.

- **Scale up**: Pod이 자원 부족으로 **Pending**(스케줄 실패)이면 → 노드 그룹에 노드 추가.
- **Scale down**: 노드 활용률이 낮고(기본 50% 미만) 그 위 Pod을 **다른 노드로 옮길 수 있으면** → drain 후 노드 제거.

```
HPA가 replica↑ → Pod이 Pending(노드 부족)
      → Cluster Autoscaler가 노드 추가 → Pod 스케줄됨
```

**축소를 막는 요소**(비용 누수 단골):
- PodDisruptionBudget이 너무 빡빡(`minAvailable`=replica) → 노드를 영영 못 비움.
- local storage 사용 Pod, `safe-to-evict: false` 어노테이션, 시스템 Pod.

### 3.2 Karpenter (대안)

|     | Cluster Autoscaler           | Karpenter                                  |
| --- | ---------------------------- | ------------------------------------------ |
| 단위  | 미리 정의된 **노드 그룹/ASG** 안에서 +/- | 노드 그룹 없이 **Pending Pod에 딱 맞는 인스턴스를 즉석 선택** |
| 속도  | 느림(ASG 경유)                   | 빠름(직접 프로비저닝)                               |
| 비용  | 그룹 단위 한계                     | spot/타입 혼합으로 최적                            |
| 범위  | 모든 클라우드/온프렘                  | 주로 AWS(확산 중)                               |

### 3.3 세 층위의 협력 흐름 (전체 그림)

```
부하 ↑
 └─ HPA: Pod 개수 ↑
      └─ 새 Pod이 노드에 안 들어감 → Pending
           └─ Cluster Autoscaler / Karpenter: 노드 ↑
                └─ Pod 스케줄 성공
부하 ↓ → HPA Pod↓ → 노드 활용률↓ → CA가 노드 비우고 제거
(VPA는 Pod당 requests를 옆에서 보정)
```

- **HPA ↔ CA는 협력**(Pod↑ → Pending → 노드↑). **HPA ↔ VPA(동일 자원)는 충돌**.



---

<!-- 다음: (선택) marp 슬라이드(slides.md) 변환 / 발표 스크립트 분리 -->

