---
marp: true
theme: default
paginate: true
backgroundColor: #1a1a2e
color: #e0e0e0
style: |
  section {
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    background-color: #1a1a2e;
  }
  h1 {
    color: #00d4ff;
    border-bottom: 2px solid #00d4ff;
    padding-bottom: 10px;
  }
  h2 {
    color: #00d4ff;
  }
  h3 {
    color: #7fdbff;
  }
  strong {
    color: #ffd700;
  }
  code {
    background-color: #16213e;
    color: #00ff88;
  }
  pre {
    background-color: #0d1117 !important;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
  }
  pre code {
    background-color: transparent !important;
    color: #e6edf3;
    font-size: 0.75em;
  }
  table {
    font-size: 0.7em;
    margin: 0 auto;
  }
  th {
    background-color: #16213e;
    color: #00d4ff;
  }
  td {
    background-color: #0f3460;
  }
  blockquote {
    border-left: 4px solid #ffd700;
    background-color: #16213e;
    padding: 10px 20px;
    font-style: normal;
  }
  section.lead h1 {
    text-align: center;
    font-size: 2.5em;
    border: none;
  }
  section.lead p {
    text-align: center;
    font-size: 1.2em;
  }
---

<!-- _class: lead -->

# Chapter 8
## Accessing Pod Metadata
## & Other Resources

Pod 안의 앱이 자기 자신과 클러스터를 아는 법

<!--
이 챕터의 핵심 질문 두 가지로 시작:
1. Pod 안의 앱이 "내가 어느 Pod이지?"를 어떻게 아는가?
2. "클러스터에 뭐가 있지?"는 어떻게 조회하는가?

답: Downward API + Kubernetes API 직접 접근.
이 두 가지는 완전히 다른 메커니즘이고, 각각 사용 시점도 다름.
청중에게 "본인이 만든 앱이 Pod 이름을 알아야 했던 적 있나요?" 라고 물으며 시작.
-->

---

# 오늘의 두 축

| 알고 싶은 것 | 메커니즘 |
|---|---|
| **자기 자신**의 메타데이터<br>(Pod name, IP, labels…) | **Downward API**<br>env / volume 주입 |
| **다른 리소스**<br>(Pod 목록, Service…) | **API 서버 직접 호출**<br>ServiceAccount 토큰 |

> 핵심 차이: Downward API는 **외부 통신 없음**, API 호출은 **HTTPS 통신**.

<!--
이 챕터에서 다룰 두 가지 주제를 한 슬라이드에 명확히 분리.
- 자기 정보 = Downward API (kubelet이 주입)
- 남의 정보 = API Server 호출 (네트워크 + 인증)
이 둘을 헷갈리는 사람이 많은데, "외부 통신 여부"가 결정적 차이라고 강조.
30초 안에 이 표만 머리에 남으면 됨.
-->

---

<!-- _class: lead -->

# 1. Downward API
## Pod가 자기 자신을 아는 법

<!--
첫 번째 주제 진입.
"앱이 자기 Pod 이름을 어떻게 알까?"라는 단순한 질문에서 출발.
이걸 해결하는 게 Downward API.
"왜 필요한가" → "어떻게 쓰는가" → "함정" 순으로 진행.
-->

---

# 왜 Downward API가 필요한가?

```
[로깅] "POST /order" 요청 처리 - 어느 Pod이 처리했지?
[메트릭] 이 컨테이너의 CPU limit은 얼마지?
[클러스터링] 내 IP는 뭐고, 같이 떠있는 Pod IP들은?
```

- 앱 코드는 `metadata.name`을 **모른다**
- k8s API 호출하기엔 **너무 무거움**
- → **kubelet이 알려준다** (env 또는 파일로 주입)

<!--
구체적인 시나리오 3개로 필요성을 어필:
1. 로깅에 Pod 이름 찍기 (가장 흔한 케이스)
2. JVM 같은 곳에서 메모리 limit 인식 (Heap 자동 설정)
3. 분산 앱의 자기 IP 인식

핵심: "k8s API 호출은 무거워. 자기 정보 정도는 가볍게 받자"는 동기.
앱이 k8s에 결합되지 않는다는 점도 중요 — 환경변수로만 받으면
나중에 다른 환경에서도 같은 코드로 동작.
-->

---

# 노출 방법 두 가지

| 방식 | 어디에 정의 | 특징 |
|---|---|---|
| **환경 변수** | `containers[].env[].valueFrom` | 시작 시 1회 설정, 변경 시 재시작 필요 |
| **`downwardAPI` 볼륨** | `volumes[].downwardAPI.items[]` | 파일 1개 = 필드 1개, **런타임 갱신 가능** |

> 주요 차이: **변경 반영 시점**과 **표현 가능한 범위**.

<!--
두 가지 방식을 표로 정리.
환경변수 → 간단, 1회성. 컨테이너 재시작해야 갱신.
볼륨 → 파일 형태. 일부 필드는 런타임에 자동 갱신. 더 풍부한 표현.

"언제 뭘 쓰지?"에 대한 답:
- 단순 식별자 (Pod name): env로 충분
- 라벨/어노테이션 전체, 자주 바뀌는 정보: volume
다음 슬라이드에서 구체적 차이 설명.
-->

---

# fieldRef: 노출 가능한 필드

**둘 다 가능 (env / volume):**
- `metadata.name`, `metadata.namespace`, `metadata.uid`
- `metadata.labels['<KEY>']`, `metadata.annotations['<KEY>']` (단일 키)

**env 전용** (volume `fieldRef` 불가):
- `spec.serviceAccountName`, `spec.nodeName`
- `status.hostIP`, `status.hostIPs`, `status.podIP`, `status.podIPs`

**volume 전용** (env 불가):
- `metadata.labels` (전체), `metadata.annotations` (전체)

<!--
공식 문서를 직접 보면서 헷갈렸던 포인트:
- "labels는 env 불가" 라고 책에서는 적혀있지만,
  사실 **전체** labels만 env 불가, 단일 키는 env 가능.
- env 전용 필드들이 의외로 많음 (nodeName, podIP 등)
- volume 전용은 단 두 개: 전체 labels, 전체 annotations

이 슬라이드는 외울 필요 없음. "필요할 때 찾을 수 있다"는 인지만.
"왜 전체 labels는 env 불가?" → multi-line 값이라 env에 못 넣음.
-->

---

# resourceFieldRef: 컨테이너 리소스

```yaml
env:
- name: CPU_REQUEST_MILLICORES
  valueFrom:
    resourceFieldRef:
      resource: requests.cpu
      divisor: 1m              # "100m" → "100"
- name: MEMORY_LIMIT_MIB
  valueFrom:
    resourceFieldRef:
      resource: limits.memory
      divisor: 1Mi
```

가능한 리소스: `cpu`, `memory`, `ephemeral-storage`, `hugepages-*`
(각각 `requests` / `limits`)

<!--
JVM 앱에서 "내 메모리 limit은?"을 알면 Heap 사이즈를 자동 설정 가능.
divisor가 핵심:
- 1m → 밀리코어 단위로 변환
- 1Mi → MiB 단위
- 생략 시 raw 값 (반올림 동작 주의)

면접 질문 단골: "limits.cpu = 100m을 divisor 없이 받으면?" → "0.1"
실제로는 정수만 받고 싶어서 divisor 1m 권장.

hugepages-*는 DPDK나 JVM Large Pages 쓰는 경우. 일반적으로 불필요.
-->

---

# env로 주입하는 예시

```yaml
env:
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_IP
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
- name: NODE_NAME
  valueFrom:
    fieldRef:
      fieldPath: spec.nodeName
```

→ 컨테이너 안: `echo $POD_NAME` → `kubia-abc123`

<!--
가장 흔한 패턴 3개를 한 번에 보여줌:
- POD_NAME: 로깅용
- POD_IP: 자기 IP 인식 (분산 시스템)
- NODE_NAME: 어느 노드에 떠있나 (디버깅)

valueFrom + fieldRef + fieldPath의 3-tier 구조.
이 패턴은 외워두면 좋음.
실제 데모에서는 `kubectl exec`로 들어가서 env 확인하는 게 임팩트.
-->

---

# 볼륨으로 주입 (multi-line 노출)

```yaml
volumeMounts:
- name: downward
  mountPath: /etc/downward
volumes:
- name: downward
  downwardAPI:
    items:
    - path: podName
      fieldRef:
        fieldPath: metadata.name
    - path: labels                 # ← env로는 불가
      fieldRef:
        fieldPath: metadata.labels
```

→ `/etc/downward/podName`, `/etc/downward/labels` 파일 생성

<!--
볼륨의 핵심 use case는 "전체 labels/annotations 노출".
env로는 못 하는 일.

파일 포맷:
labels 파일 안에는
  app="kubia"
  env="prod"
한 줄에 하나씩, key="value" 형식으로 자동 포맷됨.

앱은 이 파일을 watch하면 라벨 변경을 감지 가능 (다음 슬라이드).
-->

---

# 핵심 차이: 런타임 갱신

| 방식 | labels 변경 시 | 리소스 리사이즈 시 |
|---|---|---|
| **env** | 갱신 안 됨 (재시작 필요) | 갱신 안 됨 (재시작 필요) |
| **volume** | **자동 갱신** ✅ | **자동 갱신** ✅ (k8s 1.35+ stable) |

```bash
# 실험: labels 추가
kubectl label pod kubia env=production

# 컨테이너 안에서 5초 후
$ cat /etc/downward/labels
env="production"
app="kubia"
```

<!--
이 슬라이드가 ch08의 가장 실용적인 인사이트.
**볼륨은 살아있는 파일이다** — k8s가 백그라운드에서 갱신해줌.

실습에서 검증한 내용:
- kubectl label 후 약 5초 안에 파일 변경 확인
- env는 영원히 그대로

v1.35 stable의 in-place resize:
- 컨테이너 재시작 없이 CPU/메모리 변경 가능
- 이때 volume의 resourceFieldRef 파일은 자동 갱신
- env는 stale 상태 유지 → **JVM 앱이 limits 보고 Heap 설정한다면 volume으로 받아야**
-->

---

# Limits 미설정 시 함정

```yaml
# Pod에 limits를 설정 안 했는데
env:
- name: MEMORY_LIMIT
  valueFrom:
    resourceFieldRef:
      resource: limits.memory
      divisor: 1
```

→ kubelet이 **node allocatable 최대값**으로 채움
→ 32GB 노드라면 → `MEMORY_LIMIT="34359738368"` (32GiB)
→ 의도치 않은 큰 값 주의 ⚠️

<!--
공식 문서에서만 명확히 설명된 함정:
"limits 없으면 0이겠지?" → 아님. node allocatable 최대값.

JVM에서:
- `-XX:MaxRAMPercentage=75` 사용
- limits 없는 Pod에서 동작하면
- node가 32GB일 때 Heap = 24GB로 잡혀버림
- 다른 Pod 메모리까지 침범 → OOMKilled 연쇄

해결: 항상 limits를 명시하거나, divisor 가드 코드 추가.
이건 책에 없는 내용 — 공식 문서를 직접 본 사람만 아는 함정.
-->

---

<!-- _class: lead -->

# 2. Kubernetes API 직접 접근
## 클러스터 안의 다른 리소스 조회

<!--
두 번째 주제로 전환.
"Downward API는 자기 자신만." → "다른 Pod 목록 조회하려면?"
이때부터는 API Server와 통신해야 하고,
인증/인가 문제가 등장.
-->

---

# 왜 API 서버 직접 호출?

```
Downward API: 자기 자신의 메타데이터만 ✅

질문:
- 같은 Service의 다른 Pod IP는?  ❌
- 클러스터의 모든 Service 목록은?  ❌
- 최근 발생한 이벤트는?  ❌

→ 모두 API Server에 쿼리 필요
```

<!--
한계 명확히 짚기:
Downward API는 "셀프 서비스" — 자기 정보만.
다른 정보는 "API 호출"이 필요.

대표 use case:
- Cassandra/Kafka 같은 분산 DB의 peer discovery
- 운영 자동화 도구 (cluster autoscaler 등)
- Operator 패턴

이 부분은 쓸 일이 적지만, 한 번 쓰면 반드시 알아야 할 인증 흐름.
-->

---

# 접근 경로

```
       Pod
        │
        │ HTTPS (Bearer token)
        ▼
kubernetes.default.svc.cluster.local
        │
        ▼
     apiserver
```

- `kubernetes.default.svc` Service는 **모든 클러스터에 항상 존재**
- ClusterIP는 클러스터마다 다르지만 DNS는 동일
- 모든 Pod에서 자동으로 도달 가능

<!--
"어디로 호출하지?" → 정해진 DNS가 있다.
이건 K8s가 부트스트랩할 때 자동으로 만드는 Service.

Pod 안에서:
$ curl https://kubernetes.default.svc/api/v1
→ 401 Unauthorized (인증 없이는 거부)

다음 슬라이드에서 인증.
-->

---

# 인증: ServiceAccount

모든 Pod에 **자동 마운트**되는 경로:

```
/var/run/secrets/kubernetes.io/serviceaccount/
├── ca.crt        # apiserver TLS 검증용 CA 인증서
├── namespace     # 현재 네임스페이스
└── token         # JWT Bearer token
```

- 명시 안 하면 `default` ServiceAccount 사용
- 별도 SA 만들어 권한 분리 권장

<!--
"3종 세트"가 핵심:
- token: 너 누구야? (인증)
- ca.crt: 진짜 apiserver 맞아? (TLS 검증)
- namespace: 어느 네임스페이스에 속해? (편의)

이 마운트는 ServiceAccount admission controller가 자동으로 해줌.
명시적으로 끄려면: spec.automountServiceAccountToken: false

요즘 (k8s 1.21+) Projected Token 방식: 시간 제한 + 감사 가능.
책 시점의 영구 토큰과 다름.
-->

---

# 호출 예시

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
NS=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

curl --cacert $CACERT \
  -H "Authorization: Bearer $TOKEN" \
  https://kubernetes.default.svc/api/v1/namespaces/$NS/pods
```

→ 인증은 통과! 하지만…

```json
{ "kind": "Status", "status": "Failure",
  "message": "pods is forbidden: ...", "code": 403 }
```

<!--
호출 패턴 한 번에 다 보여주기. 실습할 때 그대로 쓸 수 있음.

- --cacert: TLS 검증
- Bearer 헤더: 인증
- /api/v1/namespaces/$NS/pods: 네임스페이스 내 Pod 목록

"인증은 됐는데 forbidden? 왜?" → RBAC 등장.
이게 책 시점과 가장 큰 차이.
-->

---

# RBAC 벽 (k8s 1.6+ 기본 활성)

```
default ServiceAccount의 권한: ❌ 없음
```

해결: Role + RoleBinding으로 권한 부여

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { name: pod-reader }
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: { name: pod-reader-binding }
subjects:
- kind: ServiceAccount
  name: default
roleRef: { kind: Role, name: pod-reader, apiGroup: rbac.authorization.k8s.io }
```

<!--
RBAC = Role-Based Access Control.
구성: Role(권한 정의) + RoleBinding(누구에게 부여)

핵심:
- apiGroups: [""] → core API group
- resources: ["pods"] → Pod만 허용
- verbs: ["get","list"] → 읽기만

실습에서 검증:
- pods Role만 부여 → pods는 OK, services는 여전히 forbidden
- 즉 권한이 정확히 그 자원에만 적용됨 (과허용 없음)

ClusterRole/ClusterRoleBinding은 클러스터 전역. Role/RoleBinding은 네임스페이스 한정.
-->

---

# 실습: 5단계 검증 시나리오

1. SA 토큰이 마운트되었는지 확인
2. **인증 없이** 호출 → 401 거부
3. **토큰으로** 호출 → 401 통과, 그러나 403 forbidden (RBAC)
4. **Role + RoleBinding** 부여 → pods 허용 ✅
5. 같은 토큰으로 services 호출 → **여전히 403** (Role 범위 밖)

> 5단계의 의미: **권한이 정확히 부여된 리소스에만 적용된다**. 과허용 없음.

<!--
실습에서 직접 확인한 5단계.
가장 중요한 학습 포인트는 마지막:
"Role에 pods만 줬으면, services 호출은 여전히 막힌다"
이건 보안의 기본 원칙 (Least Privilege).

이게 왜 중요? 운영 자동화 도구에 Role 부여할 때
"일단 다 풀어주자"는 유혹이 큰데, 정확히 필요한 것만 줘야 함.
-->

---

<!-- _class: lead -->

# 3. Ambassador 패턴
## 인증 로직을 사이드카에 위임

<!--
실용적인 패턴 소개.
앞에서 본 토큰 읽기, CA cert, Bearer 헤더 — 앱 코드에 다 넣기 귀찮음.
"사이드카가 대신 해준다"는 발상.
-->

---

# 문제: 앱 코드에 인증 로직?

```python
# 앱 코드에 이런 거 다 들어가야 함:
token = open("/var/run/.../token").read()
ca = "/var/run/.../ca.crt"
ns = open("/var/run/.../namespace").read()

requests.get(
  f"https://kubernetes.default.svc/api/v1/namespaces/{ns}/pods",
  headers={"Authorization": f"Bearer {token}"},
  verify=ca
)
```

→ 모든 언어, 모든 앱마다 반복 ❌

<!--
DRY 위반의 예.
6줄짜리 인증 보일러플레이트가 앱 코드에 들어가야 함.
Java/Go/Python/Node.js 다 비슷한 코드.

"이거 한 번만 하면 안 될까?" → Ambassador.
-->

---

# 해법: kubectl proxy 사이드카

```
┌─────────── Pod ───────────┐
│                           │
│  ┌──────┐   HTTP    ┌──────────┐ │
│  │ app  │──────────▶│ kubectl  │ │  HTTPS
│  │      │ localhost │  proxy   │ │ ─────▶ apiserver
│  │      │   :8001   │          │ │  + auth
│  └──────┘            └──────────┘ │
└──────────────────────────────────┘
```

- `app`: `curl localhost:8001/api/...` (plain HTTP)
- `proxy`: 토큰/cert 자동 처리

<!--
사이드카 패턴의 정수.
앱은 plain HTTP만 알면 됨. localhost로 호출.
proxy 컨테이너가 인증을 다 해줌.

이미 잘 알려진 도구(kubectl)를 사이드카로 쓰는 게 핵심.
새로 만들 필요 없이 기성품 활용.
-->

---

# Pod 매니페스트

```yaml
spec:
  containers:
  - name: main
    image: curlimages/curl:latest      # ← tutum/curl 대체
    command: ["sleep", "9999999"]
  - name: ambassador
    image: bitnami/kubectl:latest      # ← luksa/kubectl-proxy:1.6.2 대체
    command: ["kubectl", "proxy", "--port=8001"]
```

→ `main`에서 `curl localhost:8001/api/v1/.../pods` ✅

<!--
실습에서 발견한 이미지 교체:
- 책의 luksa/kubectl-proxy:1.6.2는 2018년 k8s 1.8 기반.
  최신 클러스터(1.30+)에서 호환성 이슈 가능.
- bitnami/kubectl:latest로 교체. 항상 최신 kubectl 포함.
- command를 명시적으로 지정 (entrypoint 의존하지 않게)

curl 이미지도 tutum/curl이 deprecated.
curlimages/curl:latest 권장.
-->

---

# 클라이언트 라이브러리가 더 깔끔

| 언어 | 패키지 |
|---|---|
| Go | `k8s.io/client-go` |
| Python | `kubernetes` (pip) |
| Java | `io.kubernetes:client-java` |
| Node.js | `@kubernetes/client-node` |

- **InClusterConfig**: SA 토큰 자동 로드
- **타입 안전**: Pod struct 등
- **Informer 패턴**: watch + 캐싱 + 이벤트 핸들러
- **재시도/백오프** 내장

<!--
실전에서는 raw curl 안 씀. 라이브러리 사용.

InClusterConfig가 핵심:
- SA 토큰 자동 발견
- CA cert 자동 로드
- API server 주소 자동 설정
- 한 줄로 끝남:
    config := rest.InClusterConfig()
    clientset := kubernetes.NewForConfig(config)

Informer 패턴은 다음 단계 — 이벤트 기반 처리.
Operator 만들 때 필수.
-->

---

<!-- _class: lead -->

# 4. 책 vs 현실

<!--
책이 2018년이라 일부 내용은 outdated.
실습하면서 발견한 차이를 정리.
이 부분이 면접에서도 자주 묻는 포인트.
-->

---

# 책(2018) → 현재(2024+)

| 항목 | 책 | 현재 |
|---|---|---|
| SA 토큰 | Secret 기반 영구 토큰 | **Projected Token** (만료, 감사) |
| RBAC | "선택" | **기본 활성** |
| 이미지 | `luksa/kubectl-proxy:1.6.2` | `bitnami/kubectl:latest` |
| `tutum/curl` | 권장 | deprecated → `curlimages/curl:latest` |
| Downward 필드 | 책 시점 한정 | + `status.podIPs/hostIPs` (듀얼스택)<br>+ `hugepages-*` |
| Resource Resize | 없음 | **v1.35 stable** (volume 자동 갱신) |

<!--
이 표는 면접용 + 실무용 양쪽 다 유용.

특히 강조할 포인트:
1. Projected Token: 보안 강화. 만료 + audit 가능.
2. RBAC 기본 활성: 책은 "RBAC 켜져 있으면 권한 부여" 톤이지만, 지금은 "RBAC 안 켜져 있으면 이상한 클러스터".
3. In-place resize: 큰 변화. JVM 앱에서 리소스 의존 정보는 volume으로 받자.

이 슬라이드는 "내가 책만 보고 있는 게 아니다"를 보여주는 가치도 있음.
-->

---

# 실습 메모: 부딪힌 이슈

- **`memory: 4Mi` 에러**:
  `runc: Minimum memory limit allowed is 6MB` → **8Mi로 수정**
- **이미지 호환성**:
  `luksa/kubectl-proxy:1.6.2` (2018, k8s 1.8) 노후 → `bitnami/kubectl:latest`
- **labels 런타임 갱신 검증**:
  `kubectl label pod kubia env=test` → 5초 내 `/etc/downward/labels` 파일 변경 확인 ✅
- **RBAC 정확성**:
  Role에 pods만 → services 여전히 forbidden (Least Privilege 검증)

<!--
실제 실습하면서 부딪힌 4가지 이슈.
청중에게 "책 그대로 따라하면 안 된다, 환경에 맞춰야 한다"는 메시지.

memory 4Mi 이슈가 가장 흥미로움:
- 책 그대로 적용 → 즉시 실패
- 원인: Docker runc의 cgroup 제약
- 해결: 8Mi로 올림 (큰 차이 없음)

이런 디테일이 실습의 가치. 책만 읽으면 모름.
-->

---

# Key Takeaways

1. **Downward API**: 자기 메타데이터, env/volume 두 방식
2. **labels/annotations 전체**: env 불가, volume만
3. **단일 키** (`labels['app']`): env 가능
4. **API 직접 호출**: SA 토큰 + RBAC + (선택) Ambassador
5. **In-place resize**: env stale, volume 자동 갱신
6. **운영 도구는 Role을 정확히 좁혀** 부여 (Least Privilege)

<!--
정리 슬라이드.
6개 핵심을 다시 각인.

Q&A 시간 유도:
"가장 의외였던 게 뭐였나요?"
대부분 "labels 단일 키는 env 가능" 이거 모름.
또는 "limits 없을 때 node allocatable로 채워짐"도 의외.

다음 챕터(ch09 Deployments) 연결:
"Pod 메타데이터를 다뤘으니, 이제 Pod을 어떻게 굴리는가 — Deployments"
-->

---

<!-- _class: lead -->

# Q & A

면접 예상 질문:
- env로 `metadata.labels` 받으려면?
- limits 없는데 `limits.cpu`를 노출하면?
- in-place resize 후 env / volume 동작 차이?
- Ambassador 패턴 vs 클라이언트 라이브러리?

<!--
예상 질문 4개를 미리 보여주고 답변 준비.
1. 전체 labels는 env 불가. 단일 키만 가능. 전체는 volume.
2. node allocatable 최대값. 32GB 노드면 32GB 들어옴. 함정.
3. volume 자동 갱신, env는 재시작까지 stale.
4. Ambassador = 언어 무관, 가벼움. 라이브러리 = 타입 안전, Informer 등 풍부.

답변할 때 단답형 → 구체적 예시 → trade-off 순으로.
-->
