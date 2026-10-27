---
tags: [kubernetes, ch12, security, rbac, serviceaccount, authentication, authorization, aws, eks, iam, irsa, pod-identity]
---

# Chapter 12: Securing the Kubernetes API server

> API Server에 도착한 요청이 **누구**인지 식별하고(Authentication), **무엇을 할 수 있는지** 결정하며(Authorization), Pod 안에서 실행되는 앱이 어떻게 API에 안전하게 접근하는지(ServiceAccount + RBAC)를 다룬다.

## 핵심 한 줄 요약

- **요청 파이프라인**: Authentication → Authorization → Admission → etcd. 모두 통과해야 한다.
- **User는 외부, ServiceAccount는 내부**. SA만 K8s API 객체이며 namespace에 속한다.
- **RBAC은 deny가 없다**. 기본은 deny, allow만 추가하는 모델.
- **Role/RoleBinding은 namespace 범위, ClusterRole/ClusterRoleBinding은 cluster 범위**. ClusterRole + RoleBinding은 권한 템플릿 재사용 패턴.
- **SA ≠ IAM**. K8s RBAC은 K8s API용, IAM Role(IRSA/Pod Identity)은 AWS API용. 두 축을 분리해서 생각.

## Key Concepts

### 1. API 요청 처리 파이프라인

모든 API 요청은 다음 3단계를 통과해야 한다:

```
요청 ─▶ [Authentication] ─▶ [Authorization] ─▶ [Admission Control] ─▶ etcd
       (누구?)             (해도 되는가?)       (변형/검증)
```

어느 단계에서든 거부되면 요청은 실패한다.

### 2. Authentication (인증) — "당신은 누구입니까?"

API Server는 여러 인증 플러그인을 동시에 돌린다. 하나라도 성공하면 통과.

주요 인증 방식:

| 방식 | 사용처 |
|------|--------|
| **클라이언트 인증서 (x509)** | kubectl, kubelet, controller-manager 등 시스템 컴포넌트 |
| **Static token / password file** | 테스트용 (production 비추천) |
| **Bearer token** | ServiceAccount 토큰 — Pod 안에서 API 접근할 때 |
| **OpenID Connect (OIDC)** | 외부 IdP(Google, Okta, Keycloak 등) 연동 |
| **Webhook token** | 자체 인증 서버로 위임 |
| **Authenticating proxy** | API Server 앞단 인증 프록시 |

인증 결과로 만들어지는 정체성:

- **User** — 사람 사용자. 클러스터 외부에서 정의됨 (인증서 CN 등에서 추출). API 객체 아님.
- **Group** — 사용자 묶음 (인증서 O 필드 등). `system:authenticated`, `system:unauthenticated` 같은 빌트인 그룹도 있음.
- **ServiceAccount** — Pod 안 앱이 사용하는 정체성. **API 객체로 namespace 안에 존재**.

### 3. ServiceAccount

- Pod이 API Server에 접근할 때 쓰는 정체성. 모든 namespace에는 `default` ServiceAccount가 자동 생성.
- Pod에 SA를 명시하지 않으면 `default` SA가 마운트됨.
- 각 SA마다 토큰이 자동 생성되고, Pod 안 `/var/run/secrets/kubernetes.io/serviceaccount/`에 마운트:
  - `token` — Bearer 토큰
  - `ca.crt` — API Server CA 인증서
  - `namespace` — 현재 namespace

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: default
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-app   # ← 여기서 SA 지정
  containers: [...]
```

`automountServiceAccountToken: false`로 마운트 차단 가능 (필요 없는 Pod에서는 끄는 게 보안상 좋다).

### 4. ImagePullSecret with ServiceAccount

private registry 이미지 풀링용 Secret을 SA에 연결하면 그 SA를 쓰는 모든 Pod에 자동 적용된다 — Pod마다 imagePullSecrets를 반복 명시할 필요가 없어진다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
imagePullSecrets:
- name: my-registry-secret
```

### 5. Authorization (인가) — RBAC

**RBAC = Role-Based Access Control**. Kubernetes의 표준 인가 모델. 4가지 객체로 구성된다:

| 객체 | 범위 | 무엇을 정의하나 |
|------|------|----------------|
| **Role** | namespace | "이 namespace에서 어떤 동사(verb)로 어떤 리소스에 접근할 수 있는가" |
| **ClusterRole** | cluster-wide | namespace에 묶이지 않는 권한 (Node, PV, …) 또는 모든 namespace에 재사용 가능한 템플릿 |
| **RoleBinding** | namespace | Role(또는 ClusterRole)을 특정 User/Group/SA에 연결 |
| **ClusterRoleBinding** | cluster-wide | ClusterRole을 cluster 범위로 User/Group/SA에 연결 |

핵심 규칙:

- **Role에 정의 → RoleBinding으로 연결 → 비로소 권한 발생**. Role 자체로는 아무 권한도 안 준다.
- ClusterRole + **RoleBinding** 조합: 특정 namespace에서만 그 ClusterRole을 적용. 권한 템플릿 재사용 패턴.
- ClusterRole + **ClusterRoleBinding** 조합: 모든 namespace + cluster 자원에 적용.

### 6. Role 예시

namespace 안 Service를 read-only로 보고 싶다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: foo
  name: service-reader
rules:
- apiGroups: [""]            # core API group
  verbs: ["get", "list"]
  resources: ["services"]
```

이걸 SA `default/foo`에 바인딩:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-services
  namespace: foo
subjects:
- kind: ServiceAccount
  name: default
  namespace: foo
roleRef:
  kind: Role
  name: service-reader
  apiGroup: rbac.authorization.k8s.io
```

verb 종류: `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`, `deletecollection`. 모든 권한은 `["*"]`.

### 7. 빌트인 ClusterRole (반드시 알아둘 것)

| ClusterRole | 권한 |
|-------------|------|
| `view` | 대부분 리소스 read-only (Secret 제외) |
| `edit` | view + 객체 수정 가능 (RBAC, Quota는 제외) |
| `admin` | edit + RBAC 객체 수정 (namespace 한정) |
| `cluster-admin` | 모든 권한, 모든 namespace, 모든 리소스 |

또한 시스템용 ClusterRole이 많다 (`system:*` prefix). 직접 수정하지 말 것.

### 8. ClusterRole + RoleBinding 패턴

자주 쓰이는 트릭: ClusterRole로 권한 템플릿을 정의하고, namespace 단위로 RoleBinding 해서 적용 범위를 좁힌다.

```yaml
# cluster 범위 템플릿
kind: ClusterRole
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  verbs: ["get", "list"]
  resources: ["pods"]
---
# foo namespace의 SA에만 적용
kind: RoleBinding
metadata:
  namespace: foo
  name: read-pods-in-foo
subjects:
- kind: ServiceAccount
  name: my-app
  namespace: foo
roleRef:
  kind: ClusterRole          # ← ClusterRole 참조
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### 9. 인가 플러그인 종류

API Server는 RBAC 외에도 여러 인가 모드를 동시에 활성화할 수 있다 (`--authorization-mode`):

- **Node** — kubelet의 권한을 자기 노드의 Pod 관련 객체로 제한 (반드시 켜야 함)
- **RBAC** — 표준 인가
- **ABAC** — 정책 파일 기반 (deprecated, 비추천)
- **Webhook** — 외부 인가 서버에 위임
- **AlwaysAllow / AlwaysDeny** — 테스트용

여러 개 활성화 시 **하나라도 허용하면 통과**.

### 10. 보안 베스트 프랙티스 요약

1. 모든 Pod에 **명시적인 SA**를 부여하라 (default SA에 권한 묶지 마라).
2. SA에는 **최소 권한(least privilege)** 만 부여 — 필요한 verb/resource만 허용.
3. API 호출이 필요 없는 Pod은 `automountServiceAccountToken: false`.
4. `cluster-admin` 바인딩은 사람/시스템 한 명에게만, 그것도 운영 계정과 분리해서.
5. RBAC을 코드(YAML)로 관리하고 git으로 추적하라 (drift 감지).
6. anonymous 인증(`system:anonymous`, `system:unauthenticated` 그룹) 권한 최소화.
7. ServiceAccount 토큰은 Secret으로 자동 생성되므로 외부로 새지 않게 주의 (로그/덤프).

## 책 vs 현실 차이점

| 책(2018, k8s 1.9 시점) | 현재(2024+) |
|------------------------|-------------|
| ABAC도 흔히 언급 | 사실상 **RBAC + Webhook**만 운영. ABAC는 deprecated. |
| SA 토큰 = **무기한 JWT, Secret 객체로 자동 생성** 후 Pod에 마운트 | **Projected SA Token** (v1.22+ default). 시간제한(기본 1h), audience 지정 가능, Pod 바인딩 → Pod 삭제 시 즉시 무효. |
| 새 SA 만들면 `default-token-xxxxx` Secret 자동 생성 | **v1.24+ 자동 생성 안 함**. 필요하면 `kubernetes.io/service-account-token` 타입 Secret을 명시적으로 만들어야 한다. |
| `--insecure-port=8080` 평문 접근 가능 | **v1.20에서 코드 제거, v1.24에서 플래그 제거**. HTTPS 6443만. |
| Admission Controller는 컴파일 인 | **Mutating/Validating Webhook** (v1.9+ stable) — 외부 서비스로 동적 admission. Kyverno/Gatekeeper가 표준. |
| Pod Security Policy (PSP) | **PSP는 v1.25에서 제거**. **Pod Security Admission (PSA)** 표준 (ch13에서 자세히). |
| ImagePullSecret을 Pod마다 명시 | SA에 묶어 자동 적용 (이건 책 시점에도 가능했음, 그러나 책은 강조 안 함) |

## Deep dives

### A. Projected ServiceAccount Token (v1.22+)

기존 SA 토큰의 문제: **무기한 + 노출 시 회수 불가**. Projected token으로 해결.

```yaml
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: my-app
  containers:
  - name: app
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: my-token
          audience: my-api          # 토큰을 받을 대상 명시
          expirationSeconds: 3600   # 1시간 만료
```

- kubelet이 `TokenRequest` API로 만료시간 있는 JWT를 받아 파일로 주입.
- **만료 시간의 80% 시점에 자동 갱신** (파일 교체).
- audience를 분리하면 한 SA가 여러 backend에 각각 다른 토큰을 받을 수 있음 (audience 검증 강제).
- v1.22+ 부터는 기본 SA 토큰 마운트도 projected 방식 — `/var/run/secrets/kubernetes.io/serviceaccount/token`이 1시간 만료짜리 자동 갱신 토큰.

기존 코드는 토큰을 한 번 읽고 메모리에 캐싱하는 경우가 많다 → **파일에서 매번 다시 읽어야** 자동 갱신을 따라간다. client-go는 기본적으로 이걸 처리한다.

### B. TokenRequest API

```
POST /api/v1/namespaces/<ns>/serviceaccounts/<sa>/token
{
  "spec": {
    "audiences": ["my-api"],
    "expirationSeconds": 3600,
    "boundObjectRef": {
      "kind": "Pod",
      "name": "my-pod",
      "uid": "..."
    }
  }
}
```

- `boundObjectRef` — 토큰을 특정 Pod에 바인딩. Pod이 삭제되면 토큰 검증 실패.
- 외부 서비스가 토큰을 검증할 때 `TokenReview` API를 사용:
  ```
  POST /apis/authentication.k8s.io/v1/tokenreviews
  ```
  → API Server가 서명/만료/바인딩을 검증해 username, groups, audiences를 응답.

### C. OIDC Authentication

API Server를 외부 IdP(Google, Okta, Keycloak, Dex 등)와 연동:

```
kube-apiserver \
  --oidc-issuer-url=https://accounts.google.com \
  --oidc-client-id=<my-app-id> \
  --oidc-username-claim=email \
  --oidc-groups-claim=groups \
  --oidc-username-prefix="oidc:" \
  --oidc-groups-prefix="oidc:"
```

흐름:
1. 사용자가 IdP에 로그인 → ID Token (JWT) 받음.
2. `kubectl`이 Authorization 헤더에 `Bearer <id-token>`을 붙여 호출.
3. API Server가 IdP의 JWKS로 서명 검증.
4. claims에서 username/groups 추출 → 이후 단계로.

EKS의 IRSA가 정확히 이 메커니즘을 **거꾸로** 활용한다 — API Server는 OIDC issuer이고, AWS STS가 검증자.

### D. Webhook Authentication / Authorization

```
--authentication-token-webhook-config-file=...
--authorization-webhook-config-file=...
```

API Server가 외부 HTTPS 서버에 인증/인가를 위임. 흐름:

```
API Server → 외부 webhook (TokenReview / SubjectAccessReview JSON 전송)
              ↓
            응답: {"status": {"authenticated": true, "user": {...}}}
                  or {"status": {"allowed": true/false}}
```

- 자체 SSO/감사 시스템과 통합 시 사용.
- 모든 요청이 webhook을 거치므로 **latency가 critical**. 캐시 권장.

### E. Audit Logging

요청 파이프라인 전체에서 audit event를 생성한다. Policy로 어디까지 기록할지 제어:

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata           # 요청 메타데이터만
  resources:
  - group: ""
    resources: ["secrets"]
- level: RequestResponse    # 요청과 응답 본문까지
  resources:
  - group: ""
    resources: ["pods"]
    verbs: ["create", "delete"]
- level: None               # 무시
  users: ["system:kube-proxy"]
```

레벨: `None`, `Metadata`, `Request`, `RequestResponse`.

```
--audit-policy-file=audit-policy.yaml
--audit-log-path=/var/log/audit.log
--audit-log-maxage=30
--audit-log-maxbackup=10
--audit-log-maxsize=100
```

EKS에서는 audit log를 CloudWatch Logs로 자동 전송 (control plane logging 활성화).

### F. RBAC 디버깅 워크플로

권한 문제 진단 순서:

```bash
# 1) 이 요청을 누가 보낸 셈인가?
kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa>

# 2) SA가 어떤 binding에 묶여 있는가?
kubectl get rolebinding,clusterrolebinding -A \
  -o jsonpath='{range .items[?(@.subjects[*].name=="<sa-name>")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'

# 3) 그 binding의 Role 내용
kubectl describe role <role-name> -n <ns>

# 4) API Server 로그에서 인가 거부 이유 추적
kubectl logs -n kube-system kube-apiserver-<node> | grep "Forbidden"
```

## 면접 예상 질문

1. **User와 ServiceAccount의 차이는?**
   - User는 K8s 외부 정체성(인증서 CN, OIDC claim 등). K8s API 객체가 아님. SA는 namespace 안의 K8s 객체로, Pod이 사용.
2. **default ServiceAccount에 권한을 주는 게 왜 위험한가?**
   - namespace 내 SA를 명시하지 않은 모든 Pod이 자동으로 default를 쓴다 → 의도하지 않은 Pod에 권한이 줄 줄 새기 쉽다.
3. **`automountServiceAccountToken: false`는 언제?**
   - 그 Pod이 K8s API에 접근할 필요가 없을 때. 토큰 노출 표면을 줄임.
4. **Role과 ClusterRole 중 무엇을 만들어야 하나?**
   - Node/PV같은 cluster-scope 리소스 → ClusterRole 필수. namespace 안에서만 → Role. 권한 템플릿 재사용은 ClusterRole + RoleBinding.
5. **RBAC에 deny rule이 없는데 특정 권한만 빼고 싶다면?**
   - 빼고 싶은 verb/resource를 처음부터 안 넣는다. 또는 admission webhook(Kyverno/Gatekeeper)으로 추가 제약.
6. **`cluster-admin` ClusterRoleBinding을 만들지 말아야 할 대상은?**
   - 사람/CI/외부 시스템 모두. 운영 계정과 명확히 분리하고 break-glass 용도로만.
7. **OIDC로 인증한 사용자에게 그룹을 매핑하는 법?**
   - IdP의 ID Token에 `groups` claim을 넣고 API Server에 `--oidc-groups-claim=groups`. RBAC binding의 subject에 `kind: Group`.
8. **SA 토큰이 노출되면?**
   - **v1.22 이전 (legacy)**: Secret 객체 삭제 + 재생성 + Pod 재시작 — 그런데 이전 토큰은 만료가 없어서 무효화 불가.
   - **v1.22+ (projected)**: 기본 1시간 만료라 자연 회수. 즉시 무효화하려면 SA 삭제(연관 토큰 전부 reject).
9. **IRSA와 Pod Identity 중 무엇을 골라야 하나?**
   - Linux EC2 노드 + 단일 EKS 클러스터 + 단일 AWS 계정 → Pod Identity. Fargate / EKS Anywhere / 멀티클라우드 → IRSA.
10. **`kubectl auth can-i`는 어떻게 동작하나?**
    - SelfSubjectAccessReview API를 호출. API Server가 인증된 신원으로 인가 단계만 시뮬레이션해서 yes/no 응답.

## Notes

- 인증과 인가는 **완전히 별개의 단계**. 인증을 통과해도 인가에서 막힐 수 있다.
- `kubectl auth can-i` 명령으로 권한 확인 가능:
  ```
  kubectl auth can-i create deployments --as system:serviceaccount:foo:default
  ```
- RBAC은 **deny rule이 없다**. 기본은 deny이고, Role/Binding으로 allow만 추가한다.
- 인증서 회전, OIDC 토큰 갱신 등은 production에서 큰 운영 부담 — 가능하면 외부 IdP로 위임하는 편이 좋다.
- Pod-to-API-Server 통신은 항상 TLS이며, Pod 안 `ca.crt`로 API Server 검증.
- `system:masters` 그룹은 RBAC을 우회한다 (bootstrap용). 절대 일반 사용자에게 주지 말 것.
- audit log는 보안 사고 후 reconstruction의 거의 유일한 단서 — production에서 반드시 켜고 외부 저장소로 송출.

---

## SA ↔ 클라우드 IAM 연동 (AWS EKS 중심)

> 책(2018) 시점에는 다루지 않은 주제. 실제 EKS 운영에서 ServiceAccount는 **K8s 내부 RBAC**(API Server 접근 제어)뿐 아니라 **AWS IAM**(S3, DynamoDB, SQS 같은 AWS 리소스 접근 제어)과도 연동되어야 한다. AWS는 두 가지 메커니즘을 제공한다: **IRSA**(2019~)와 **EKS Pod Identity**(2023~).

### A. 왜 필요한가 — 안티패턴부터 보기

EKS Pod이 S3에 접근해야 한다고 하자. 다음 방식들은 모두 안 좋다:

| 안티패턴 | 문제 |
|----------|------|
| 노드 EC2 인스턴스 IAM Role 사용 | 같은 노드의 **모든 Pod이 같은 권한 공유** → least privilege 깨짐. Pod가 옆 Pod의 권한으로 행동 가능 |
| AWS access key를 Secret으로 마운트 | 키 회전(rotation) 운영 부담, 유출 시 무효화 어려움, GitOps 시 평문 위험 |
| 환경변수에 키 주입 | 프로세스 덤프/로그로 노출 위험 |

→ **Pod 단위로 IAM 권한을 부여**하는 것이 정답. 이를 위해 K8s ServiceAccount를 IAM Role과 연결한다.

### B. IRSA — IAM Roles for Service Accounts (2019~)

OIDC 페더레이션 기반. K8s가 SA 토큰을 OIDC JWT로 발급 → AWS STS가 검증 → 임시 자격증명 발급.

**전체 흐름**:

```
1. EKS 클러스터마다 OIDC Issuer URL이 있다
   (예: https://oidc.eks.<region>.amazonaws.com/id/<id>)
2. 클러스터당 1회: AWS 계정에 IAM OIDC Provider 등록 (이 issuer를 신뢰)
3. IAM Role 생성. 신뢰 정책(trust policy)에 OIDC provider + sub/aud 조건
4. SA에 어노테이션 eks.amazonaws.com/role-arn=<role-arn>
5. Pod 생성 시 EKS의 mutating webhook이 자동 주입:
   - 환경변수 AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
   - projected volume: kubelet이 Bound SA Token (OIDC JWT, audience=sts.amazonaws.com) 발급
6. AWS SDK가 이 토큰으로 sts:AssumeRoleWithWebIdentity 호출 → 임시 자격증명 획득
```

**ServiceAccount + IAM Role 예시**:

```yaml
# 1) ServiceAccount with role-arn annotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: app
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eks-s3-reader
```

**IAM Role Trust Policy** (이 Role을 누가 떠맡을 수 있는지):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/ABCD1234"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.ap-northeast-2.amazonaws.com/id/ABCD1234:aud": "sts.amazonaws.com",
        "oidc.eks.ap-northeast-2.amazonaws.com/id/ABCD1234:sub": "system:serviceaccount:app:s3-reader"
      }
    }
  }]
}
```

핵심:
- `Federated` principal이 OIDC provider ARN.
- `sub` 조건이 **이 SA만** 떠맡을 수 있게 잠금 — `system:serviceaccount:<namespace>:<sa-name>` 형식.
- `aud`는 항상 `sts.amazonaws.com`.
- `StringLike`로 `system:serviceaccount:app:*` 와일드카드도 가능 (namespace 통째로 허용).

**eksctl 한 줄 생성** (실무에서 가장 많이 쓰는 방식):

```bash
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace app \
  --name s3-reader \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

내부적으로 IAM Role 생성 + Trust Policy 작성 + SA 생성 + 어노테이션 부여를 한 번에 한다.

### C. EKS Pod Identity (2023~ Nov re:Invent)

OIDC를 거치지 않는 **새 메커니즘**. 더 단순하고 멀티 클러스터 친화적.

**구성 요소**:

1. **eks-pod-identity-agent** DaemonSet — 노드마다 한 개 (애드온으로 설치).
2. **PodIdentityAssociation** — EKS 컨트롤 플레인의 API 객체. SA ↔ IAM Role 매핑을 클러스터 외부에 보관.
3. Pod이 뜨면 EKS가 자동으로 환경변수 주입:
   - `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`
   - `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE=/var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token`
4. AWS SDK는 **Container credential provider**로 `169.254.170.23`(IPv4 link-local) 또는 `[fd00:ec2::23]`(IPv6)에 GET → 노드 위 agent가 EKS Auth API의 `AssumeRoleForPodIdentity`로 토큰 교환 → 임시 자격증명 반환.

**Trust Policy** (IRSA보다 훨씬 간단):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
    "Effect": "Allow",
    "Principal": { "Service": "pods.eks.amazonaws.com" },
    "Action": [
      "sts:AssumeRole",
      "sts:TagSession"
    ]
  }]
}
```

- `Federated` 대신 `Service: pods.eks.amazonaws.com` — OIDC issuer 정보가 없다 → **클러스터에 묶이지 않는다**.
- `sts:TagSession` 필수 — EKS가 cluster-arn / namespace / SA / pod-name 등을 세션 태그로 자동 부착.

**Association 생성**:

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace app \
  --service-account s3-reader \
  --role-arn arn:aws:iam::123456789012:role/eks-s3-reader
```

**중요**: SA에 어노테이션을 붙이지 않는다. 매핑은 EKS 컨트롤 플레인에만 존재.

### D. IRSA vs Pod Identity 비교표

| 항목 | IRSA (2019) | Pod Identity (2023) |
|------|-------------|---------------------|
| 메커니즘 | OIDC + `sts:AssumeRoleWithWebIdentity` | EKS Auth API + `AssumeRoleForPodIdentity` |
| 클러스터당 사전 설정 | IAM OIDC Provider 등록 (1회) | 애드온 설치(`eks-pod-identity-agent`) |
| Trust Policy | OIDC provider별 `Federated` 원리, `sub` 조건 | `Service: pods.eks.amazonaws.com` 한 줄 |
| 매핑 위치 | SA 어노테이션 (`eks.amazonaws.com/role-arn`) | EKS API 객체 (`PodIdentityAssociation`) |
| 멀티 클러스터 Role 재사용 | 어렵다 (OIDC issuer마다 trust policy 갱신) | **쉽다 (trust policy 1회 작성, association만 추가)** |
| STS 호출 위치 | Pod 안 SDK가 직접 STS 호출 | 노드의 agent가 대표로 호출 (STS throttling 회피 유리) |
| 세션 태그 | 직접 추가 어려움 | 자동 부착 (cluster/ns/sa/pod) — ABAC 친화 |
| 토큰 audience | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| 토큰 expiry | 1시간(기본) | 24시간 (agent가 갱신) |
| EKS 외 환경 | EKS, EKS Anywhere, ROSA, self-managed K8s 모두 가능 | **EKS 전용** |
| Fargate | ✅ 지원 | ❌ **미지원** (Linux EC2만) |
| Windows 노드 | ✅ | ❌ |
| GovCloud / China | ✅ | ❌ (GA 시점) |
| 계정당 한도 | OIDC provider 100개/account → 클러스터 100개 상한 | 한도 없음 |
| 크로스 계정 | trust policy로 가능 | 1차 association은 동일 계정만 → role chaining 필요 |

**선택 가이드라인** (2024+):
- 새 EKS 클러스터, 단일 계정, Linux EC2 노드 → **Pod Identity 우선**.
- Fargate를 쓴다 / 자체 K8s나 EKS Anywhere다 / 멀티클라우드 추상화가 필요 → **IRSA**.
- 이미 IRSA로 운영 중 → 마이그레이션 불필수. 두 방식은 **공존 가능**(같은 SA에 둘 다 설정하면 Pod Identity가 우선).

### E. 운영상 함정 (반드시 알아둘 것)

**IRSA**:
- OIDC 서명키는 **7일마다 회전**. 외부 OIDC 클라이언트(있다면)는 keys 엔드포인트를 주기적으로 다시 받아야 한다.
- STS 글로벌 엔드포인트 사용 시 `SignatureDoesNotMatch` 에러 가능 → **regional 엔드포인트** 사용 (`AWS_STS_REGIONAL_ENDPOINTS=regional` 또는 SA 어노테이션 `eks.amazonaws.com/sts-regional-endpoints=true`). 신규 EKS는 기본값이 regional.
- 대규모 Pod 환경에서 Pod 마다 STS 호출 → **STS throttling** 우려.
- Trust Policy 크기 한도(2048자) 때문에 한 Role에 묶을 수 있는 신뢰 관계가 제한적.
- 이미 떠 있는 Pod에는 webhook이 작동하지 않는다 → 어노테이션 추가 후 **Pod 재시작 필요**.

**Pod Identity**:
- IPv6 비활성 노드에서 agent가 기본 설정상 시작 실패 → agent 설정에서 IPv6 명시적 비활성화 필요.
- Pod 내부에서 HTTP 프록시를 쓴다면 `NO_PROXY`에 `169.254.170.23`, `[fd00:ec2::23]` 반드시 포함. 안 그러면 자격증명 요청이 프록시로 가서 실패.
- Association 변경은 **eventually consistent** (수 초). 핫 패스에서 만들지/지우지 마라.
- agent가 노드에 죽으면 그 노드의 모든 Pod이 자격증명 갱신 실패 → DaemonSet PDB / 모니터링 필수.

**공통**:
- **K8s RBAC과는 완전히 별개**. SA에 IAM Role을 붙여도 K8s API 접근 권한은 변하지 않는다 (그건 RoleBinding의 영역). 이 둘이 헷갈리지 않게 머릿속에서 분리해 두자.
  ```
  SA ─┬─ K8s RBAC (RoleBinding)        → K8s API에 무엇을 할 수 있나
      └─ IAM Role (IRSA / Pod Identity) → AWS API에 무엇을 할 수 있나
  ```
- AWS SDK 버전이 너무 낮으면 web identity / container credential provider를 모를 수 있다 → SDK 최신화.
- IAM Role의 `MaxSessionDuration` 설정 잘못 → SDK 자동 갱신 사이클과 어긋날 수 있음.

### F. GKE / AKS 한 줄씩 (참고)

같은 문제를 다른 클라우드도 비슷하게 푼다:

- **GKE Workload Identity**: K8s SA(KSA) ↔ Google SA(GSA) 매핑. KSA 어노테이션 `iam.gke.io/gcp-service-account`. GSA에 `roles/iam.workloadIdentityUser` 부여. 최근에는 KSA를 직접 IAM principal로 쓰는 *Workload Identity Federation for GKE*도 있음.
- **AKS Workload Identity**: 2023 GA, Azure AD federated credential 기반. SA 어노테이션 `azure.workload.identity/client-id`로 AAD 앱과 연결. (이전 *Pod Identity*는 deprecated.)

세 클라우드 다 사실상 같은 패턴: **K8s SA의 토큰을 OIDC/페더레이션으로 클라우드 IAM에 신뢰시키고 임시 자격증명을 받는다**. AWS만 OIDC 없는 단축 경로(Pod Identity)를 새로 추가한 셈.

## Questions

- [ ] OIDC 연동을 실제로 구성하려면 API Server 플래그가 어떻게 되는가?
- [ ] Webhook 인가를 직접 구현해야 한다면 OPA/Gatekeeper를 쓰는 게 표준인가?
- [ ] SA 토큰이 노출되었을 때 회수(rotation) 절차는?
- [ ] Audit logging은 어디에 어떻게 켜고, 무엇을 추적해야 하는가? (12장 외 주제이지만 연관)
- [ ] 기존 IRSA 클러스터를 Pod Identity로 마이그레이션하는 실제 절차와 다운타임 영향은?
- [ ] Pod Identity의 세션 태그(`kubernetes-namespace`, `kubernetes-service-account`)를 IAM 정책의 ABAC 조건으로 활용하는 패턴은?
- [ ] 멀티 클러스터/멀티 계정 환경에서 IAM Role 설계 전략 (cross-account assume role chain)?
- [ ] aws-load-balancer-controller, external-dns, cluster-autoscaler 같은 시스템 컴포넌트는 IRSA / Pod Identity 중 무엇을 쓰는가, 그 이유는?
