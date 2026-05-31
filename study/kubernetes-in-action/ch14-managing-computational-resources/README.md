---
tags: [kubernetes, ch14, resources, requests, limits, qos, limitrange, resourcequota, scheduling]
---

# Chapter 14: Managing pods' computational resources

> 컨테이너에 CPU/메모리를 얼마나 **요청(requests)**하고 얼마나까지 **제한(limits)**할지 지정하는 법, 이 값들이 **스케줄링**과 **QoS 등급(축출 우선순위)**에 어떻게 영향을 주는지, 그리고 namespace 차원에서 기본값(LimitRange)과 총량(ResourceQuota)을 어떻게 강제하는지를 다룬다.

## 핵심 한 줄 요약

- **requests = 스케줄링 기준 + 보장량**, **limits = 상한선(넘으면 throttle/kill)**. 둘은 완전히 다른 목적.
- **스케줄러는 requests의 합만 본다** — 노드의 실제 사용량이 아니라 "예약된 양"으로 배치 결정.
- **CPU는 압축 가능(compressible) 자원** → limit 초과 시 throttle(느려짐). **메모리는 비압축(incompressible)** → limit 초과 시 **OOMKill**.
- **QoS 3등급**: `Guaranteed`(requests==limits) > `Burstable`(일부만 설정) > `BestEffort`(아무것도 안 함). 노드 메모리 부족 시 **BestEffort부터 축출**.
- **LimitRange = Pod 단위 기본값/최대·최소**, **ResourceQuota = namespace 총량**. 둘은 admission 단계에서 동작.
- **ResourceQuota가 있으면 모든 Pod에 requests/limits를 명시해야** 한다 (또는 LimitRange로 기본값 제공).

## Key Concepts

### 1. requests vs limits

```yaml
spec:
  containers:
  - name: app
    resources:
      requests:           # 스케줄링·보장에 쓰임
        cpu: "200m"       # 0.2 코어 (200 millicore)
        memory: "128Mi"
      limits:             # 상한선
        cpu: "500m"
        memory: "256Mi"
```

| 구분 | requests | limits |
|------|----------|--------|
| 목적 | 스케줄러가 배치할 노드 결정 + **최소 보장** | 컨테이너가 쓸 수 있는 **상한** |
| 안 쓰면 | 스케줄러가 0으로 간주 (아무 노드나) | 무제한 (노드 자원 다 먹을 수 있음) |
| CPU 초과 시 | — | **throttle** (CPU 시간 제한, 느려짐) |
| 메모리 초과 시 | — | **OOMKill** (컨테이너 강제 종료 후 재시작) |

### 2. CPU 단위 (millicore)

- `1` = `1000m` = 1 vCPU/코어.
- `200m` = 0.2 코어 = 한 코어의 20% CPU 시간.
- CPU requests는 커널 **CFS(Completely Fair Scheduler)의 cpu.shares**로 변환 → 경합 시 비율대로 분배.
- CPU limits는 **cpu.cfs_quota_us / cfs_period_us** 로 변환 → 절대 상한(throttle).

### 3. 메모리 단위

- `Mi`(Mebibyte=2^20), `Gi`(2^30) — 이진 단위 (권장).
- `M`(Megabyte=10^6), `G`(10^9) — 십진 단위.
- `128Mi` ≈ 134MB. 헷갈리면 항상 `Mi/Gi` 사용.

### 4. 압축 가능(compressible) vs 비압축(incompressible) 자원

| 자원 | 압축성 | limit 초과 시 동작 |
|------|--------|-------------------|
| CPU | 압축 가능 | **throttle** — 컨테이너를 죽이지 않고 CPU 시간만 깎음 (느려질 뿐) |
| 메모리 | 비압축 | **OOMKill** — 회수 불가하므로 컨테이너를 죽임 |

이 차이가 운영의 핵심: **메모리 limit은 신중히** (너무 낮으면 OOMKill 루프), **CPU limit은 throttle만** (애플리케이션 지연으로 나타남).

### 5. 스케줄러는 requests의 합으로 결정

스케줄러는 노드의 **실제 사용량이 아니라 이미 스케줄된 Pod들의 requests 합**을 본다.

- 노드 CPU 4코어, 이미 requests 합 3.5코어 → 0.5코어 미만 요청하는 Pod만 배치 가능.
- 실제 사용량이 1코어뿐이어도, **requests 기준으로 꽉 찼다고 판단**.
- → requests를 너무 크게 잡으면 노드가 "예약상" 가득 차서 실사용은 낮은데 새 Pod이 못 들어감 (낭비). 반대로 너무 작으면 과밀 배치로 실제 자원 부족.

### 6. QoS 클래스 (Quality of Service)

노드 메모리 부족 시 **어느 Pod을 먼저 축출(evict)할지** 결정하는 등급. Pod의 requests/limits 설정으로 **자동 부여**된다.

| QoS 클래스 | 조건 | 축출 우선순위 |
|-----------|------|--------------|
| `Guaranteed` | 모든 컨테이너가 CPU·메모리 모두 requests==limits | **가장 나중** (제일 안전) |
| `Burstable` | 최소 하나의 컨테이너가 requests 설정, 단 Guaranteed 조건 미달 | 중간 |
| `BestEffort` | 어떤 컨테이너도 requests/limits 없음 | **가장 먼저 축출** |

```bash
kubectl get pod my-pod -o jsonpath='{.status.qosClass}'
```

### 7. 노드 압박(node pressure)과 축출 순서

노드 메모리가 부족하면 kubelet이 Pod을 축출한다. 순서:

1. **BestEffort** Pod 먼저.
2. 그다음 **Burstable** 중 **requests를 초과해서 쓰는** Pod (초과량이 큰 순).
3. **Guaranteed**는 시스템이 정말 한계일 때만 (거의 마지막).

같은 등급 안에서는 **OOM score**(requests 대비 실제 사용 초과 비율)로 결정.

### 8. LimitRange — Pod/컨테이너 단위 정책

namespace 안에서 컨테이너별 **기본값/최소/최대**를 정의. admission 단계에서 적용.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
  namespace: foo
spec:
  limits:
  - type: Container
    default:              # limits 안 쓰면 이 값 적용
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:       # requests 안 쓰면 이 값 적용
      cpu: "100m"
      memory: "128Mi"
    max:                  # 컨테이너가 넘을 수 없는 상한
      cpu: "1"
      memory: "1Gi"
    min:                  # 최소
      cpu: "50m"
      memory: "64Mi"
    maxLimitRequestRatio: # limit/request 비율 상한
      cpu: "4"
  - type: Pod             # Pod 전체 합 제한도 가능
    max:
      cpu: "2"
  - type: PersistentVolumeClaim
    max:
      storage: 10Gi
```

핵심: **requests/limits를 명시하지 않은 Pod에 기본값을 자동 주입**한다. ResourceQuota와 짝으로 자주 쓴다.

### 9. ResourceQuota — namespace 총량 정책

namespace 전체에서 쓸 수 있는 **자원 총합**과 **오브젝트 개수**를 제한.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
  namespace: foo
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "10"
    services.loadbalancers: "2"
    persistentvolumeclaims: "20"
    requests.storage: 500Gi
    count/deployments.apps: "20"
```

**중요한 함정**: ResourceQuota가 CPU/메모리에 걸려 있으면, 그 namespace의 **모든 Pod은 해당 자원의 requests/limits를 반드시 명시**해야 한다. 안 하면 Pod 생성이 거부된다 → **LimitRange로 기본값을 함께 제공**하는 게 정석.

### 10. ResourceQuota의 scope

특정 QoS나 우선순위에만 quota를 적용할 수 있다.

```yaml
spec:
  hard:
    pods: "10"
  scopeSelector:
    matchExpressions:
    - operator: In
      scopeName: PriorityClass
      values: ["high"]
  # scopes: ["BestEffort", "NotBestEffort", "Terminating", "NotTerminating"]
```

### 11. 사용량 모니터링

```bash
kubectl top node           # 노드별 실제 CPU/메모리 사용량
kubectl top pod            # Pod별 실제 사용량
kubectl describe node X    # Allocatable / Allocated(requests,limits) 비교
```

- `kubectl top`은 **Metrics Server**가 설치돼 있어야 동작 (책의 Heapster는 deprecated).
- `describe node`의 "Allocated resources"가 **requests 기준 예약률** — 스케줄링 여유를 본다.

## 책 vs 현실 차이점

| 책(2018, k8s 1.9) | 현재(2024+) |
|--------------------|-------------|
| 메트릭 수집은 **Heapster** | **Heapster 제거됨**. `kubectl top`은 **Metrics Server** 사용. 장기 저장은 Prometheus |
| QoS 등급 3종 설명 | 동일하지만 **Pod Priority/Preemption**(우선순위 기반 축출)이 추가되어 QoS와 별개 축으로 작동 |
| 메모리 OOMKill 설명 | **cgroup v2**(v1.25+ 기본)로 메모리 관리 방식 변화. `memory.high`로 soft limit 가능 (MemoryQoS 알파) |
| CPU throttle 단순 설명 | **CFS throttle 버그/CPU limit 논쟁** 부각 — limit 때문에 멀쩡한 앱이 throttle되는 이슈. 일부 조직은 **CPU limit을 아예 안 건다** |
| `requests/limits`만 | **VPA**(Vertical Pod Autoscaler)로 자동 추천/조정 가능 (ch15) |
| 정적 LimitRange/Quota | **In-place Pod Resize**(v1.27+ 알파, v1.33 베타) — 재시작 없이 requests/limits 변경 |
| 메모리/CPU 두 자원만 | **Ephemeral storage**, **HugePages**, **확장 자원(GPU 등 `nvidia.com/gpu`)** 도 requests/limits로 관리 |
| Quota는 자원 총량 위주 | **count/`<resource>.<group>`** 로 임의 오브젝트 개수 제한 가능 |

## Deep dives

### A. CPU requests가 cpu.shares로 변환되는 원리

- CPU requests `value(m)` → cgroup `cpu.shares = value * 1024 / 1000`. 즉 `1000m`(1코어) = 1024 shares.
- shares는 **상대값** — 경합이 있을 때만 의미. 노드에 여유가 있으면 requests보다 더 쓸 수 있다(Burstable).
- 두 컨테이너가 각각 500m, 1000m requests면 경합 시 CPU를 1:2로 분배.
- → CPU requests는 "최소 보장 비율"이지 "상한"이 아니다. 상한은 limits.

### B. CPU limit과 CFS throttling 함정

CPU limit은 `cfs_period_us`(기본 100ms) 동안 쓸 수 있는 `cfs_quota_us`로 변환된다.

- limit `200m` → 100ms마다 20ms의 CPU 시간만 허용.
- **함정**: 멀티스레드 앱이 짧은 순간 버스트로 quota를 다 쓰면 **남은 period 동안 강제로 멈춤** → p99 레이턴시 급증. 평균 사용률은 낮은데도 throttle 발생.
- 그래서 많은 SRE가 **CPU requests는 설정하되 CPU limits는 생략**(혹은 넉넉히)하는 전략을 쓴다. 메모리 limit은 OOM 보호를 위해 유지.

### C. 메모리는 왜 OOMKill인가

- 메모리는 회수가 불가능한 자원 — 한번 할당된 페이지를 강제로 뺏을 수 없다.
- limit 초과 시 커널 OOM killer가 **컨테이너 프로세스(주로 PID 1)** 를 죽임 → 컨테이너 재시작(`OOMKilled` 상태).
- 반복되면 `CrashLoopBackOff`. `kubectl describe pod`의 `Last State: Terminated, Reason: OOMKilled`로 확인.
- JVM 등은 **컨테이너 인지(`-XX:+UseContainerSupport`, 기본 ON in JDK 10+)** 가 안 되면 노드 전체 메모리를 보고 힙을 잡아 OOM. cgroup 기준으로 잡도록 설정 필요.

### D. Guaranteed QoS를 만드는 정확한 조건

**모든 컨테이너**(init 포함)가:
- CPU requests == CPU limits, **그리고**
- 메모리 requests == 메모리 limits.

limits만 설정하면 쿠버네티스가 requests를 limits와 같게 자동 설정 → Guaranteed가 된다 (편법).

```yaml
resources:
  limits:            # requests 생략 → requests=limits 자동 → Guaranteed
    cpu: "500m"
    memory: "256Mi"
```

### E. 축출(eviction) vs OOMKill 의 차이

| | OOMKill | kubelet Eviction |
|--|---------|------------------|
| 주체 | 리눅스 커널 OOM killer | kubelet (노드 압박 감지) |
| 범위 | 컨테이너 하나 | Pod 전체를 노드에서 축출 |
| 트리거 | 컨테이너가 메모리 limit 초과 | 노드 전체 가용 메모리/디스크가 임계치 이하 |
| QoS 반영 | OOM score로 | QoS 등급 + requests 초과량으로 |
| 결과 | 컨테이너 재시작(같은 노드) | Pod 삭제 → 컨트롤러가 다른 노드에 재생성 |

kubelet eviction threshold: `--eviction-hard=memory.available<100Mi,nodefs.available<10%` 등으로 설정.

### F. Allocatable — 노드 자원의 실제 가용량

노드의 전체 자원 ≠ Pod이 쓸 수 있는 양.

```
Node Capacity
 = Allocatable (Pod이 쓸 수 있는 양)
 + kube-reserved (kubelet, 컨테이너 런타임용)
 + system-reserved (OS, sshd 등)
 + eviction-threshold (축출 버퍼)
```

스케줄러는 **Allocatable** 기준으로 requests 합을 계산. `kubectl describe node`에서 Capacity vs Allocatable 차이 확인.

### G. 확장 자원 (GPU 등)

CPU/메모리 외의 자원도 requests/limits로 관리한다. 단 **확장 자원은 requests==limits를 강제**(부분 할당 불가).

```yaml
resources:
  limits:
    nvidia.com/gpu: 1        # GPU 1장 (device plugin이 노드에 advertise)
    hugepages-2Mi: 512Mi
  requests:
    ephemeral-storage: 2Gi   # 컨테이너 쓰기 가능 레이어 + emptyDir
```

GPU는 **device plugin**(NVIDIA k8s-device-plugin)이 노드에 자원을 광고해야 스케줄 가능.

### H. In-place Pod Resize (신기능)

전통적으로 requests/limits 변경은 **Pod 재생성**이 필요했다. v1.27+ 알파 → v1.33 베타로 **재시작 없이** 변경 가능:

```yaml
spec:
  containers:
  - name: app
    resizePolicy:
    - resourceName: cpu
      restartPolicy: NotRequired   # CPU는 재시작 없이
    - resourceName: memory
      restartPolicy: RestartContainer  # 메모리는 컨테이너 재시작
```

VPA가 이 기능과 결합되면 **무중단 수직 스케일링**이 가능해진다.

## 면접 예상 질문

1. **requests와 limits의 차이는?**
   - requests는 스케줄링 기준이자 최소 보장량, limits는 상한선. requests로 노드 배치가 결정되고, limits 초과 시 CPU는 throttle, 메모리는 OOMKill.
2. **CPU limit과 메모리 limit의 초과 동작이 왜 다른가?**
   - CPU는 압축 가능 자원이라 시간만 깎으면(throttle) 되지만, 메모리는 회수 불가라 죽이는(OOMKill) 수밖에 없다.
3. **QoS 클래스 3종과 결정 기준은?**
   - Guaranteed(모든 컨테이너 requests==limits), Burstable(일부 설정), BestEffort(미설정). 노드 메모리 부족 시 BestEffort → Burstable(초과분 큰 순) → Guaranteed 순으로 축출.
4. **스케줄러는 노드의 실제 사용량을 보고 배치하나?**
   - 아니다. 이미 스케줄된 Pod들의 **requests 합**(예약량)만 본다. 실사용이 낮아도 requests로 꽉 차면 새 Pod이 못 들어간다.
5. **CPU limit을 일부러 안 거는 이유는?**
   - CFS throttling으로 평균 사용률이 낮은데도 버스트 시 강제로 멈춰 p99 레이턴시가 튄다. 메모리 limit은 OOM 보호로 유지하되 CPU limit은 생략하는 전략이 흔하다.
6. **ResourceQuota를 걸었더니 Pod 생성이 거부된다?**
   - quota가 CPU/메모리에 걸리면 모든 Pod이 그 자원의 requests/limits를 명시해야 한다. LimitRange로 기본값을 자동 주입하면 해결.
7. **LimitRange와 ResourceQuota의 차이?**
   - LimitRange는 컨테이너/Pod 단위 기본값·최소·최대, ResourceQuota는 namespace 총량·오브젝트 개수. 둘은 admission에서 함께 동작.
8. **컨테이너가 OOMKilled 되는데 메모리 사용은 limit보다 낮아 보인다?**
   - JVM/Node 등이 cgroup 한계를 인지 못해 노드 전체 메모리 기준 힙을 잡거나, 순간 피크가 잡히지 않은 경우. 컨테이너 인지 옵션과 메모리 limit 재조정 필요.
9. **Guaranteed QoS를 만드는 방법?**
   - 모든 컨테이너에서 CPU·메모리 requests==limits. limits만 쓰면 requests가 자동으로 같아져 Guaranteed가 된다.
10. **GPU 같은 자원은 어떻게 요청하나?**
    - device plugin이 노드에 광고한 확장 자원(`nvidia.com/gpu`)을 requests==limits로 정수 요청. 부분 할당은 불가(MIG/타임슬라이싱은 별도).

## Notes

- requests = "달라고 한 양(보장+스케줄링)", limits = "넘으면 안 되는 선". 이 둘의 구분이 14장 전부.
- **CPU=throttle, 메모리=kill** 한 줄만 기억해도 운영 사고의 절반을 막는다.
- ResourceQuota + LimitRange는 **멀티테넌트 클러스터의 기본 가드레일**.
- QoS는 우리가 직접 지정하는 게 아니라 requests/limits 조합으로 **자동 부여**된다.
- 실무에서는 **VPA로 추천값 받고 → requests 보정 → HPA로 수평 확장**(ch15)이 한 세트.
- `kubectl top`은 Metrics Server 필수. 장기 분석은 Prometheus + Grafana.
- 노드의 Capacity와 Allocatable 차이(시스템 예약분)를 모르면 "노드에 자원 남았는데 왜 스케줄 안 되지?"에 빠진다.

## Questions

- [ ] CPU limit을 거는 것과 안 거는 것, 우리 워크로드에는 어느 쪽이 맞는가? (throttle vs 무제한 버스트)
- [ ] cgroup v1 → v2 전환이 메모리 관리(MemoryQoS)에 어떤 차이를 만드는가?
- [ ] In-place Pod Resize를 VPA와 결합하면 무중단 수직 스케일링이 실제로 되는가?
- [ ] 우리 JVM 워크로드는 cgroup 메모리 한계를 제대로 인지하고 있는가?
- [ ] ResourceQuota를 namespace별로 어떻게 배분할 것인가? (팀별 가드레일 설계)
