---
tags: [kubernetes, ch08, downward-api, serviceaccount, rbac]
---

# Chapter 8: Accessing pod metadata and other resources from applications

> Pod 안의 앱이 "내가 어느 Pod이지?", "어떤 노드에 떠있지?", "클러스터에 뭐가 있지?"를 알아야 하는 상황의 해법.

## 핵심 한 줄 요약

- **Downward API**: Pod 자기 자신의 메타데이터를 env 또는 파일로 노출 (외부 통신 없이)
- **Kubernetes API 접근**: 클러스터의 다른 리소스를 알고 싶으면 apiserver에 직접 쿼리 (ServiceAccount 토큰 사용)

---

## 1. Downward API — Pod가 자기 자신을 아는 법

### 1.1 왜 필요?

앱이 로깅/메트릭에 "어느 Pod에서 온 요청인지" 찍고 싶다면? 앱 코드는 `metadata.name`을 모름.
→ **k8s가 알려줌**. 환경변수 또는 파일로 주입.

### 1.2 노출 가능한 필드

| 방식 | 가능한 값 |
|------|-----------|
| `fieldRef` | `metadata.name`, `metadata.namespace`, `metadata.uid`, `metadata.labels`, `metadata.annotations`, `status.podIP`, `status.podIPs`, `status.hostIP`, `status.hostIPs`, `spec.nodeName`, `spec.serviceAccountName` |
| `resourceFieldRef` | `requests.cpu`, `requests.memory`, `limits.cpu`, `limits.memory`, `requests.ephemeral-storage`, `limits.ephemeral-storage`, `requests.hugepages-*`, `limits.hugepages-*` |

⚠️ **`metadata.labels` / `metadata.annotations` 전체 노출은 env 불가, 볼륨만 가능** (multi-line 값이라).
✅ 단, **단일 키 추출**(`metadata.labels['<KEY>']`, `metadata.annotations['<KEY>']`)은 **env로도 가능**.

📌 **`status.podIPs` / `status.hostIPs`**: 듀얼스택(IPv4+IPv6) 환경에서 IP 슬라이스로 받음. 첫 번째 값은 `status.podIP` / `status.hostIP`와 동일.

📌 **`hugepages-*`**: HugePages를 쓰는 워크로드(DPDK, JVM large pages)에서 `requests/limits.hugepages-2Mi`처럼 사용.

📌 **Limits 미설정 시 fallback**: `limits.cpu` / `limits.memory`를 노출하는데 컨테이너에 limits가 없으면 kubelet이 **node allocatable 최대값**으로 채움 (0이 아님 — 의도치 않은 큰 값 주의).

📌 **In-place resize와 downward API** (k8s v1.35 stable): 컨테이너 CPU/메모리 리소스가 런타임에 리사이즈되면
- **볼륨 파일**: 자동 갱신 ✅
- **환경 변수**: 컨테이너 재시작해야 갱신 ⚠️ (stale 위험)
→ 리사이즈 환경에서 리소스 의존 정보는 **반드시 볼륨으로** 받아야 정합성 유지.

### 1.3 env로 주입

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
- name: CONTAINER_CPU_REQUEST_MILLICORES
  valueFrom:
    resourceFieldRef:
      resource: requests.cpu
      divisor: 1m                    # "15m" → "15"
```

### 1.4 볼륨으로 주입 (파일 하나당 필드 하나)

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
    - path: labels
      fieldRef:
        fieldPath: metadata.labels         # env로는 못 했던 이것도 OK
```

→ `/etc/downward/podName`, `/etc/downward/labels` 파일 생성.
multi-line (annotations 등)도 **자동 포맷**되어 쓰여짐.

### 1.5 업데이트 동작

- env: 한 번 설정. Pod 재생성해야 반영.
- 볼륨 labels/annotations: **런타임 업데이트됨** (kubectl label/annotate → 자동 반영)
- 볼륨 nodeName 등 불변 필드: 초기값 고정

---

## 2. Kubernetes API 서버 직접 접근

### 2.1 왜 필요?

Downward API는 **자기 자신의 정보만** 노출. 클러스터 내 **다른 리소스**(다른 Pod 리스트, Service 목록, 최근 이벤트 등)를 알려면 API 서버 호출 필수.

### 2.2 접근 경로

```
Pod 내부
  ↓ (HTTPS)
kubernetes.default.svc.cluster.local  (Service — 항상 존재)
  ↓
apiserver
```

### 2.3 인증 — ServiceAccount

모든 Pod은 기본 ServiceAccount(`default`) 토큰을 자동 마운트:
```
/var/run/secrets/kubernetes.io/serviceaccount/
├── ca.crt       # apiserver의 CA 인증서
├── namespace    # 현재 네임스페이스
└── token        # JWT Bearer token
```

### 2.4 Pod 내부에서 호출하는 curl 예시

```bash
# Variables
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
NS=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# API 호출
curl --cacert $CACERT \
  -H "Authorization: Bearer $TOKEN" \
  https://kubernetes.default.svc/api/v1/namespaces/$NS/pods
```

### 2.5 RBAC 벽 (현대 클러스터의 기본)

위 호출이 **`forbidden` 에러** 나면 정상. k8s 1.6+부터 RBAC 활성화.
`default` ServiceAccount는 아무 권한 없음.

해결:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
subjects:
- kind: ServiceAccount
  name: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## 3. Ambassador 패턴 — 복잡한 인증을 사이드카에 위임

### 3.1 문제

앱 코드에 토큰 읽기, CA cert 검증, Bearer 헤더 붙이기 … 전부 넣기 귀찮음.

### 3.2 해법: `kubectl proxy` 사이드카

```
┌─────────── Pod ───────────┐
│                           │
│  ┌──────┐     ┌────────┐ │
│  │ app  │ --> │ proxy  │ │-──> apiserver
│  │      │ HTTP│ (kubectl│ │ HTTPS + auth
│  └──────┘     │  proxy) │ │
│               └────────┘ │
└───────────────────────────┘
```

- `app` 컨테이너: `curl localhost:8001/api/...` 만 호출 (plain HTTP, 인증 X)
- `proxy` 사이드카: 토큰/cert 읽어서 apiserver로 forward (인증 처리)

### 3.3 Pod 예시

```yaml
containers:
- name: main
  image: tutum/curl
  command: ["sleep", "9999999"]
- name: ambassador
  image: luksa/kubectl-proxy:1.6.2
```

→ `main`에서 `curl localhost:8001/api/v1/namespaces/default/pods` 호출 가능.

### 3.4 책의 이미지 문제
`luksa/kubectl-proxy:1.6.2`는 k8s 1.8 kubectl이라 최신 클러스터와 호환성 주의.
최신 실습은 `bitnami/kubectl:latest`로 대체 가능:
```yaml
- name: ambassador
  image: bitnami/kubectl:latest
  command: ["kubectl", "proxy", "--port=8001"]
```

---

## 4. 클라이언트 라이브러리 (실전)

앱 언어별 공식 클라이언트로 더 깔끔하게:

| 언어 | 패키지 |
|------|--------|
| Go | `k8s.io/client-go` |
| Python | `kubernetes` (pip) |
| Java | `io.kubernetes:client-java` |
| Node.js | `@kubernetes/client-node` |

클라이언트 라이브러리는:
- SA 토큰 자동 로드 (InClusterConfig)
- 타입 안전 (Pod struct 등)
- 재시도, 캐싱, Informer 패턴 지원

→ 책의 raw curl 방식은 **이해용**, 실전은 라이브러리.

---

## 5. 책 vs 현실 차이점

| 책(2018) | 현재(2024+) |
|----------|-------------|
| SA 토큰이 Secret으로 생성되어 자동 마운트 | **Projected ServiceAccount Token** (시간제한, 감사 가능) |
| `luksa/kubectl-proxy:1.6.2` | `bitnami/kubectl` 또는 클라이언트 라이브러리 |
| RBAC는 "선택" | **기본 활성화**. 권한 없으면 거부 |
| Downward API는 Pod 필드만 | 여전히 동일. ConfigMap/Secret과 **Projected Volume**으로 통합 가능 |

---

## 6. 면접 예상 질문

1. **Pod 안에서 자기 Pod 이름을 알려면?**
   - Downward API env (`metadata.name`) 또는 `HOSTNAME` 환경변수 (Pod name과 동일)
2. **Downward API로 `metadata.labels` 받으려면?**
   - **전체** labels: env 불가, **볼륨 마운트만** 가능
   - **단일 키** (`metadata.labels['app']`): env로도 가능
3. **Pod에서 API 서버 호출 시 인증은?**
   - 마운트된 SA 토큰(`/var/run/secrets/.../token`) + Bearer 헤더
4. **RBAC 에러 "forbidden" 해결?**
   - Role + RoleBinding (또는 ClusterRole/ClusterRoleBinding)으로 SA에 권한 부여
5. **Ambassador 패턴 장점?**
   - 앱 코드에 인증 로직 불필요. 사이드카가 인증/암호화 처리
6. **CPU limits=100m을 env로 받으면 값이 뭐?**
   - divisor: 1m이면 "100", divisor: 1이면 "0.1" (반올림 방식 주의)
7. **컨테이너에 limits가 없는데 `limits.cpu`를 downward API로 노출하면?**
   - **node allocatable 최대값**이 들어옴 (0 아님). 노드 스펙에 따라 큰 값으로 주입되는 함정
8. **In-place resize 후 env / volume 동작 차이?**
   - volume: 즉시 갱신. env: 컨테이너 재시작 전까지 stale. → 리소스 의존 로직은 volume 권장
9. **`status.podIPs`와 `status.podIP` 차이?**
   - `podIP`: primary IP 1개 (string). `podIPs`: 듀얼스택 IP 슬라이스 (첫 값은 podIP와 동일)

---

## 실습 체크리스트

- [x] `01-downward-env`: env로 Pod 메타데이터 7개 주입 (`memory: 4Mi` → `8Mi`로 수정 필요)
- [x] `02-downward-volume`: 볼륨 마운트 + labels 런타임 업데이트 반영 실증
- [x] `03-api-direct`: 5단계 시나리오 — SA 마운트 확인 → 인증 없이 거부 → 토큰으로 성공 → RBAC 없이 pods 거부 → RBAC 부여 후 성공 → services는 여전히 거부 (범위 정확성)
- [x] `04-kubectl-proxy`: ambassador 사이드카로 인증 위임 (`bitnami/kubectl:latest`로 대체)

### 실습 관찰 메모 (2026-05-05)

- **Memory limits 4Mi 에러**: `Minimum memory limit allowed is 6MB`. Docker runc 제약. 책 예제의 `4Mi`를 `8Mi`로 올림.
- **Downward API volume labels 런타임 반영**: `kubectl label pod <name> env=test` 후 5초 내 `/etc/downward/labels` 파일 업데이트 확인. env와 달리 Pod 재생성 불필요.
- **RBAC 정확성**: Role에 `resources: ["pods"]`만 넣으면 pods만 허용, services는 여전히 forbidden. 과하게 넓어지지 않음.
- **ambassador 이미지 교체**: `luksa/kubectl-proxy:1.6.2` (2018, k8s 1.8) → `bitnami/kubectl:latest`. 시작 명령도 `ENTRYPOINT` 대신 Pod spec의 `command`에 명시.
- **curl 이미지 교체**: `tutum/curl`(outdated) → `curlimages/curl:latest`.

---

## Key Concepts

- **Downward API**: Pod 자기 자신의 메타데이터 주입 (env, volume)
- **ServiceAccount**: Pod의 identity, 토큰 자동 마운트
- **RBAC**: Role + RoleBinding으로 권한 부여
- **Ambassador 패턴**: 사이드카가 앱의 외부 통신 대리
- **InClusterConfig**: 클라이언트 라이브러리의 자동 토큰 로딩

## Notes

- 예제는 `examples/Chapter08/` 원본 참고
- `luksa/kubectl-proxy:1.6.2` 이미지는 오래됨 — `bitnami/kubectl`로 대체 가능
- RBAC 실습은 추가 리소스(Role, RoleBinding) 필요

## Questions

- Projected ServiceAccount Token vs 기존 Secret 기반 토큰?
- Informer 패턴은 언제 raw API 호출보다 유리?
- Service Account에 `imagePullSecret` 묶어쓰는 관용?
