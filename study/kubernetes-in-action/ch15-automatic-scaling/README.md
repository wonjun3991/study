---
tags: [kubernetes, ch15, autoscaling, hpa, vpa, cluster-autoscaler, metrics-server, keda]
---

# Chapter 15: Automatic scaling of pods and cluster nodes

> 부하에 따라 Pod 개수를 자동으로 늘리고 줄이는 **HPA(수평)**, 컨테이너의 requests/limits를 자동 조정하는 **VPA(수직)**, 그리고 Pod이 들어갈 노드 자체가 모자라면 노드를 늘리는 **Cluster Autoscaler** — 세 가지 자동 스케일링 축을 다룬다. ch14의 requests/limits 설정이 이 모든 것의 전제다.

## 핵심 한 줄 요약

- **HPA = Pod 개수 조절(수평)**, **VPA = Pod당 자원 조절(수직)**, **Cluster Autoscaler = 노드 개수 조절**. 세 층위가 다르다.
- **HPA 공식**: `원하는 replica = ceil(현재 replica × (현재 메트릭 / 목표 메트릭))`.
- **HPA는 CPU 사용률을 requests 대비로 계산** → ch14에서 **requests를 반드시 설정**해야 HPA가 동작.
- **HPA와 VPA(CPU/메모리)는 같은 메트릭에 동시 사용 금지** — 서로 싸운다. (VPA는 권장값만 주는 모드로 병행)
- **메트릭 파이프라인**: HPA → Metrics Server(리소스 메트릭) / Custom·External Metrics API(커스텀).
- **Cluster Autoscaler는 Pending Pod(스케줄 못 한 Pod)을 보고 노드를 추가**, 활용률 낮은 노드는 비워서 제거.
- **scale-to-zero**는 기본 HPA 불가 → **KEDA**(이벤트 기반) 필요.

## Key Concepts

### 1. 세 가지 자동 스케일링

| 종류 | 무엇을 조절 | 리소스 |
|------|-------------|--------|
| **HPA** (Horizontal Pod Autoscaler) | Pod **개수** (replica) | `HorizontalPodAutoscaler` |
| **VPA** (Vertical Pod Autoscaler) | Pod의 **requests/limits** | `VerticalPodAutoscaler` (애드온) |
| **Cluster Autoscaler** | **노드** 개수 | 클라우드 프로바이더 연동 컴포넌트 |

### 2. HPA 동작 원리

컨트롤 매니저의 HPA 컨트롤러가 **주기적으로(기본 15초)** 메트릭을 조회 → 목표값과 비교 → replica 수 조정.

```
desiredReplicas = ceil( currentReplicas × ( currentMetricValue / desiredMetricValue ) )
```

예: 현재 3 replica, CPU 평균 사용률 90%, 목표 50% → `ceil(3 × 90/50) = ceil(5.4) = 6`.

### 3. HPA 정의 (autoscaling/v2)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization      # requests 대비 %
        averageUtilization: 50
  - type: Resource
    resource:
      name: memory
      target:
        type: AverageValue     # 절대값 기준
        averageValue: 500Mi
```

여러 메트릭을 주면 **각각 계산해서 가장 큰 replica 수를 채택**(안전한 쪽).

### 4. CPU 사용률은 requests 대비

`type: Utilization`의 `averageUtilization: 50`은 **노드 CPU의 50%가 아니라 컨테이너 requests의 50%**.

- 컨테이너 CPU requests `200m`, 실제 사용 `100m` → 사용률 50%.
- → **requests가 없으면 사용률을 계산할 수 없어 HPA가 동작 안 함**. (ch14와 직결)

### 5. 메트릭 종류 3가지

| type | 출처 | 예 |
|------|------|-----|
| `Resource` | Metrics Server | CPU, 메모리 사용률 |
| `Pods` / `Object` | Custom Metrics API (Prometheus Adapter 등) | 초당 요청수, 큐 길이 |
| `External` | External Metrics API | 클라우드 큐(SQS/PubSub) 메시지 수, 외부 시스템 지표 |

```yaml
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  - type: External
    external:
      metric:
        name: queue_messages
      target:
        type: AverageValue
        averageValue: "30"
```

### 6. 스케일링 안정화 (flapping 방지)

급격한 진동(scale up→down 반복)을 막기 위한 안정화 윈도/정책. autoscaling/v2의 `behavior`:

```yaml
spec:
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # 5분간 최댓값 유지 후에야 축소
      policies:
      - type: Percent
        value: 50          # 한 번에 최대 50%까지만 축소
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0      # 확장은 즉시
      policies:
      - type: Pods
        value: 4           # 60초당 최대 4개 추가
        periodSeconds: 60
      selectPolicy: Max
```

기본값: **scale-down은 5분 안정화**(보수적), **scale-up은 즉시**(빠른 대응).

### 7. VPA (Vertical Pod Autoscaler)

컨테이너의 requests/limits를 **실제 사용량에 맞춰 자동 추천/조정**. 빌트인 아님 — 별도 애드온 설치.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: web-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  updatePolicy:
    updateMode: "Auto"   # Off | Initial | Recreate | Auto
  resourcePolicy:
    containerPolicies:
    - containerName: "*"
      minAllowed: { cpu: "100m", memory: "128Mi" }
      maxAllowed: { cpu: "2",    memory: "2Gi" }
```

updateMode:
- `Off`: 추천만 (실제 변경 X) — 가장 안전.
- `Initial`: Pod 생성 시점에만 적용.
- `Recreate`: Pod을 죽이고 새 값으로 재생성.
- `Auto`: Recreate와 동일 (향후 In-place resize 결합 예정).

구성요소: **Recommender**(사용량 분석), **Updater**(낡은 Pod 축출), **Admission Controller**(새 Pod에 값 주입).

### 8. HPA vs VPA 동시 사용 금지

**같은 자원(CPU/메모리)에 HPA와 VPA를 동시에 걸면 안 된다.**

- HPA: CPU 높으면 → replica 늘림 → Pod당 부하 ↓ → CPU 사용률 ↓.
- VPA: CPU 높으면 → requests 늘림.
- 둘이 같은 신호에 반대로 반응 → 진동/충돌.

허용 조합:
- HPA(CPU/메모리) + VPA(`updateMode: Off`, 추천만).
- HPA(커스텀 메트릭, 예: QPS) + VPA(CPU/메모리).

### 9. Cluster Autoscaler

노드 레벨 스케일링. 클라우드 프로바이더(AWS ASG, GKE node pool 등)와 연동.

**Scale up**: Pod이 자원 부족으로 **Pending**(스케줄 실패)이면 → 노드 그룹에 노드 추가.
**Scale down**: 노드 활용률이 낮고(기본 50% 미만) 그 위 Pod들을 다른 노드로 옮길 수 있으면 → 노드 비우고(drain) 제거.

```
HPA가 replica 늘림 → Pod이 Pending(노드 부족) → Cluster Autoscaler가 노드 추가 → Pod 스케줄됨
```

축소를 막는 요소: PodDisruptionBudget, local storage 사용 Pod, `safe-to-evict: false` 어노테이션, system Pod 등.

### 10. Metrics Server (전제 조건)

`kubectl top`과 HPA의 Resource 메트릭 모두 **Metrics Server**가 제공. 책의 **Heapster는 deprecated/제거**.

```bash
kubectl top pod
kubectl get hpa            # 현재/목표 메트릭, replica 확인
kubectl describe hpa web-hpa   # 스케일링 이벤트/사유
```

HPA가 `<unknown>` 메트릭을 보이면 보통 **Metrics Server 미설치** 또는 **requests 미설정**.

## 책 vs 현실 차이점

| 책(2018, k8s 1.9) | 현재(2024+) |
|--------------------|-------------|
| HPA는 `autoscaling/v1` (CPU만) | **`autoscaling/v2`** 표준 — 메모리·커스텀·External 메트릭, `behavior` 스케일링 정책 |
| 메트릭은 **Heapster** | **Heapster 제거**. Metrics Server(리소스) + **Prometheus Adapter**(커스텀) + External Metrics API |
| VPA는 거의 언급 없음/초기 | VPA가 성숙 — Recommender/Updater/Admission 구조. **In-place resize(v1.27+)** 와 결합 진행 |
| 스케일링 진동 제어 미흡 | `behavior.stabilizationWindowSeconds` + 정책으로 정밀 제어 |
| scale-to-zero 불가 | **KEDA**(CNCF)로 이벤트 기반 + **0까지 축소** 가능 (Kafka, SQS, cron 등 60+ scaler) |
| Cluster Autoscaler만 | **Karpenter**(AWS, 노드그룹 없이 즉시 적합한 인스턴스 프로비저닝)가 대안으로 부상 |
| 커스텀 메트릭 파이프라인 복잡 | Prometheus Adapter / **KEDA**가 표준화. DataDog/CloudWatch 어댑터도 |
| HPA 동기화 주기 고정 | `--horizontal-pod-autoscaler-sync-period`(기본 15s) 등 튜닝 가능 |

## Deep dives

### A. HPA 계산의 디테일 (tolerance, ready 무시)

- **tolerance**: 비율이 0.9~1.1(기본 10%) 안이면 스케일 안 함 — 미세 진동 방지.
- **Not-Ready/막 시작한 Pod**: 메트릭이 아직 불안정한 Pod은 계산에서 **보수적으로 제외/할인**(과대 스케일 방지).
- **missing metrics**: 일부 Pod 메트릭이 없으면 scale-up 시엔 0%로(보수적), scale-down 시엔 100%로 가정.

이 보정들 때문에 "공식대로면 6개여야 하는데 5개"인 상황이 정상일 수 있다.

### B. 왜 requests가 HPA의 전제인가

`type: Utilization`은 `사용량 / requests × 100`. requests가 없으면 분모가 없어 **사용률 계산 불가** → HPA가 `<unknown>`. 그래서:

- HPA를 쓸 거면 **반드시 CPU(혹은 대상 자원) requests 설정**.
- requests를 너무 크게 잡으면 사용률이 낮게 나와 **scale-up이 늦음**. 너무 작으면 과민 반응.
- → ch14의 requests 튜닝이 HPA 품질을 좌우.

### C. 커스텀 메트릭 파이프라인 (Prometheus Adapter)

```
앱(메트릭 노출) → Prometheus(수집) → Prometheus Adapter(custom.metrics.k8s.io API로 변환) → HPA
```

- `type: Pods` 메트릭(예: `http_requests_per_second`)은 Prometheus Adapter의 룰로 PromQL → k8s 메트릭 API로 매핑.
- 장점: CPU보다 **비즈니스 신호(QPS, 큐 길이, p99)** 로 스케일 → 더 정확.

### D. KEDA — 이벤트 기반 + scale-to-zero

기본 HPA는 `minReplicas: 1` 이하로 못 내려간다(0 불가). **KEDA**는:

- `ScaledObject` CRD로 60+ 이벤트 소스(Kafka lag, SQS depth, RabbitMQ, cron, Prometheus 등)를 트리거로.
- 이벤트 없으면 **0으로 축소**, 이벤트 오면 1+로 깨우고 이후는 HPA에 위임.
- 서버리스/배치성 워크로드 비용 절감의 핵심.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: { name: consumer }
spec:
  scaleTargetRef: { name: consumer-deploy }
  minReplicaCount: 0
  maxReplicaCount: 50
  triggers:
  - type: kafka
    metadata:
      topic: orders
      lagThreshold: "100"
```

### E. Cluster Autoscaler vs Karpenter

| | Cluster Autoscaler | Karpenter |
|--|--------------------|-----------|
| 단위 | 미리 정의된 **노드 그룹/ASG** 안에서 +/- | 노드 그룹 없이 **Pending Pod에 딱 맞는 인스턴스 타입을 즉석 선택** |
| 속도 | 상대적으로 느림(ASG 경유) | 빠름(직접 프로비저닝) |
| 비용 최적화 | 그룹 단위 한계 | spot/타입 혼합으로 비용 최적 |
| 범위 | 모든 클라우드/온프렘 | 주로 AWS(타 클라우드 확산 중) |

### F. 스케일링 충돌/경합 정리

1. **HPA × VPA 동일 자원** → 금지(진동). VPA는 추천 모드로.
2. **HPA × Cluster Autoscaler** → 협력 관계(HPA가 Pod↑ → Pending → CA가 노드↑). 정상.
3. **여러 HPA가 같은 Deployment** → 금지. 하나만.
4. **수동 `kubectl scale` × HPA** → HPA가 곧 덮어씀. 수동 조절 무의미.

### G. PodDisruptionBudget과 스케일 다운

Cluster Autoscaler가 노드를 비울 때 PDB를 존중한다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2        # 또는 maxUnavailable
  selector:
    matchLabels: { app: web }
```

PDB가 너무 빡빡하면(예: `minAvailable`이 replica와 같음) **노드를 영영 못 비워** scale-down이 막힌다 — 비용 누수의 흔한 원인.

### H. HPA가 안 움직일 때 체크리스트

1. **Metrics Server 설치?** (`kubectl top pod` 되는지)
2. **컨테이너에 requests 있나?** (없으면 `<unknown>`)
3. `kubectl describe hpa` 의 이벤트/조건(`AbleToScale`, `ScalingActive`) 확인.
4. `minReplicas`/`maxReplicas` 범위에 갇혀 있지 않은지.
5. behavior의 `stabilizationWindow`로 축소가 지연되는 중인지.
6. 커스텀 메트릭이면 Adapter가 메트릭 API를 제대로 서빙하는지(`kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1`).

## 면접 예상 질문

1. **HPA, VPA, Cluster Autoscaler의 차이는?**
   - HPA는 Pod 개수(수평), VPA는 Pod당 requests/limits(수직), CA는 노드 개수. 층위가 다르고 HPA↔CA는 협력하지만 HPA↔VPA(동일 자원)는 충돌한다.
2. **HPA가 원하는 replica 수를 어떻게 계산하나?**
   - `ceil(현재 replica × (현재 메트릭 / 목표 메트릭))`. 여러 메트릭이면 각각 계산 후 가장 큰 값 채택, 10% tolerance 안이면 변동 없음.
3. **HPA에 CPU requests가 꼭 필요한 이유?**
   - Utilization은 requests 대비 비율이라 requests가 없으면 분모가 없어 사용률 계산 불가 → `<unknown>`. requests 크기가 scale-up 민감도를 좌우.
4. **HPA와 VPA를 같이 쓰면 안 되는 이유?**
   - 같은 CPU/메모리 신호에 HPA는 replica를, VPA는 requests를 바꿔 서로 반대로 반응→진동. VPA를 추천(Off) 모드로 두거나 HPA는 커스텀 메트릭으로 분리해야 한다.
5. **scale-down이 scale-up보다 보수적인 이유와 제어 방법?**
   - 진동(flapping) 방지. 기본 5분 stabilization window. `behavior.scaleDown`으로 윈도·축소율(Percent/Pods) 조정.
6. **scale-to-zero가 기본 HPA로 안 되는데 어떻게 하나?**
   - KEDA로 이벤트 소스(Kafka lag, 큐 depth 등) 기반 0↔N 스케일. 이벤트 없으면 0, 오면 깨워 이후 HPA에 위임.
7. **Cluster Autoscaler는 무엇을 보고 노드를 추가/제거하나?**
   - 스케줄 실패한 Pending Pod이 있으면 노드 추가, 활용률 낮고 Pod 재배치 가능한 노드는 drain 후 제거. PDB/local storage/시스템 Pod이 축소를 막을 수 있다.
8. **커스텀 메트릭(QPS)으로 HPA를 하려면?**
   - Prometheus + Prometheus Adapter로 custom.metrics.k8s.io API 제공 → HPA `type: Pods/Object`로 참조. 또는 KEDA.
9. **HPA가 전혀 안 움직인다. 어디부터 보나?**
   - Metrics Server 설치 여부 → requests 존재 → `describe hpa`의 conditions → min/max 범위 → 커스텀이면 메트릭 API 서빙 확인.
10. **Karpenter가 Cluster Autoscaler와 다른 점?**
    - 노드 그룹/ASG 없이 Pending Pod 요구사항에 딱 맞는 인스턴스를 즉석 프로비저닝 → 더 빠르고 비용(spot/타입 혼합) 최적. 주로 AWS.

## Notes

- **HPA=가로(개수), VPA=세로(자원), CA=노드** — 이 세 단어만 기억하면 구조가 잡힌다.
- HPA는 ch14의 requests 설정에 **전적으로 의존** — autoscaling 장이지만 사실상 리소스 관리의 연장.
- 실무 표준 조합: **HPA(CPU 또는 QPS) + Cluster Autoscaler(또는 Karpenter) + VPA(추천 모드)**.
- 진동(flapping)은 behavior로, 충돌은 "같은 자원에 HPA·VPA 금지" 규칙으로 막는다.
- 비용 절감/서버리스성 워크로드는 **KEDA scale-to-zero**가 게임 체인저.
- `autoscaling/v1`(CPU만)은 레거시 — 새로 만들면 항상 `autoscaling/v2`.
- HPA 디버깅의 8할은 "Metrics Server 있나 / requests 있나" 두 가지.

## Questions

- [ ] 우리 서비스는 CPU 기반 HPA가 맞나, QPS/큐 길이 같은 커스텀 메트릭이 맞나?
- [ ] VPA를 추천(Off) 모드로 돌려 requests 보정에 활용하고 있는가?
- [ ] Cluster Autoscaler vs Karpenter — 우리 비용/속도 요구에는 어느 쪽인가?
- [ ] PDB가 너무 빡빡해서 노드 scale-down을 막고 있지는 않은가?
- [ ] 배치/이벤트성 워크로드에 KEDA scale-to-zero를 적용하면 비용이 얼마나 줄어드는가?
- [ ] HPA behavior의 stabilization window/정책이 우리 트래픽 패턴에 맞게 튜닝돼 있는가?
