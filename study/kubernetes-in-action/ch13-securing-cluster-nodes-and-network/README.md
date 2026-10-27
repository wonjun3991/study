---
tags: [kubernetes, ch13, security, podsecurity, networkpolicy, hostnamespace, securitycontext]
---

# Chapter 13: Securing cluster nodes and the network

> Pod이 노드의 자원·네임스페이스에 어디까지 접근할 수 있는지 제어(SecurityContext, PodSecurityPolicy)하고, Pod 간/외부 네트워크 트래픽을 어떻게 격리하는지(NetworkPolicy)를 다룬다. ch12가 "API에 누가 접근하는가"였다면 ch13은 "Pod이 노드/네트워크에서 무엇을 할 수 있는가".

## 핵심 한 줄 요약

- **ch12 = 컨트롤 플레인 보안 / ch13 = 데이터 플레인 보안**.
- **호스트 네임스페이스(hostNetwork/hostPID/hostIPC)는 시스템 Pod 전용** — 일반 워크로드에 절대 금지.
- **SecurityContext 황금조합**: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`.
- **PSP는 죽었다, PSA가 표준**. namespace 라벨 한 줄로 baseline/restricted 강제.
- **NetworkPolicy는 default deny가 아니다** — 정책이 적용되는 Pod에 한해 명시 안 된 트래픽만 차단. 진짜 default-deny는 별도로 만들어야 한다.
- **NetworkPolicy는 CNI가 지원해야 동작** — Calico/Cilium ✅, 기본 Flannel ❌ (조용히 무시됨, 매우 위험).

## Key Concepts

### 1. 호스트 네임스페이스 사용 (Pod이 노드 자원 직접 접근)

기본적으로 Pod은 자기만의 네임스페이스(network, PID, IPC, mount, UTS)를 가진다. 노드의 것을 쓰려면 명시적으로 활성화:

```yaml
spec:
  hostNetwork: true     # 노드의 네트워크 네임스페이스 사용 (호스트 IP/포트 그대로)
  hostPID: true         # 노드의 PID 네임스페이스 — ps로 호스트 프로세스 보임
  hostIPC: true         # 노드의 IPC 네임스페이스
  containers:
  - name: ...
    ports:
    - containerPort: 9090
      hostPort: 9090    # 컨테이너 포트를 노드 포트에 직접 매핑 (hostNetwork 안 써도 됨)
```

용도: 시스템 에이전트(노드 모니터링, CNI, kube-proxy 같은 시스템 Pod). **일반 워크로드에는 절대 쓰지 말 것**.

### 2. SecurityContext — 컨테이너 권한 제어

Pod 또는 Container 레벨에서 보안 옵션을 지정한다. Container 레벨이 Pod 레벨을 override.

```yaml
spec:
  securityContext:           # Pod 레벨
    runAsUser: 1000
    runAsNonRoot: true
    fsGroup: 2000
  containers:
  - name: app
    securityContext:         # Container 레벨
      runAsUser: 1001
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
        add: ["NET_BIND_SERVICE"]
      privileged: false
```

주요 필드:

| 필드 | 의미 |
|------|------|
| `runAsUser` | 컨테이너 프로세스 UID (Dockerfile USER override) |
| `runAsNonRoot` | true면 root(UID 0)로 시작하는 이미지 실행 거부 |
| `fsGroup` | 마운트된 볼륨에 적용될 GID |
| `privileged` | true면 호스트의 거의 모든 권한 (privileged 컨테이너 — 매우 위험) |
| `allowPrivilegeEscalation` | suid 등으로 권한 상승 가능 여부 (false 권장) |
| `readOnlyRootFilesystem` | 컨테이너 루트 fs를 read-only로 (쓰기는 emptyDir 등으로) |
| `capabilities.add/drop` | Linux capability 추가/삭제. **`drop: ["ALL"]` + 필요한 것만 add가 정석** |
| `seLinuxOptions`, `seccompProfile`, `apparmorProfile` | 추가적인 커널 보안 모듈 |

### 3. Linux Capabilities

루트 권한을 잘게 쪼갠 단위. 예시:

- `NET_BIND_SERVICE` — 1024 미만 포트 바인딩
- `NET_ADMIN` — 네트워크 인터페이스/iptables 조작
- `SYS_ADMIN` — 거의 root 수준 (가급적 피하기)
- `CHOWN`, `KILL`, `SETUID`, `SETGID` 등

기본 컨테이너는 일부 capability를 이미 가진다 → **명시적으로 다 drop하고 필요한 것만 add**.

### 4. PodSecurityPolicy (PSP) — *deprecated*

> ⚠️ **PSP는 Kubernetes 1.21에서 deprecated, 1.25에서 제거됨.** 책 1판(2018)에는 PSP로 설명되어 있지만, 현재(2024+)는 다음 중 하나로 대체:
>
> - **Pod Security Admission (PSA)** — k8s 빌트인. namespace 라벨로 `privileged`/`baseline`/`restricted` 모드 적용 (가장 표준적)
> - **OPA Gatekeeper / Kyverno** — 정책 엔진. PSP보다 훨씬 풍부한 정책 표현 가능

PSP의 개념은 이해해 둘 가치가 있다 — 클러스터 차원에서 어떤 SecurityContext 조합을 허용/금지할지 정의하는 admission controller였다. 정의 → ServiceAccount/Role에 use 권한 부여 → 해당 SA로 만들어진 Pod에 적용.

### 5. Pod Security Admission (현행 표준)

namespace에 라벨을 붙여 한 줄로 보안 수준 적용:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    pod-security.kubernetes.io/enforce: restricted   # 위반 시 거부
    pod-security.kubernetes.io/audit:   restricted   # audit log
    pod-security.kubernetes.io/warn:    restricted   # kubectl warning
```

3가지 프로파일:

| 프로파일 | 의미 |
|---------|------|
| `privileged` | 제한 없음 (시스템 컴포넌트용) |
| `baseline` | 알려진 권한 상승 차단 (호스트 네임스페이스/privileged/위험한 capability 금지) |
| `restricted` | baseline + 강한 제약 (runAsNonRoot 강제, capability 거의 다 drop, seccomp RuntimeDefault) |

### 6. NetworkPolicy — Pod 간 네트워크 격리

Pod은 기본적으로 **모두에게 모든 포트가 열려 있다**. NetworkPolicy로 ingress/egress 트래픽을 제어한다. **CNI 플러그인이 NetworkPolicy를 지원해야** 동작한다 (Calico, Cilium ✅ / 기본 Flannel ❌).

기본 동작: namespace에 NetworkPolicy가 **하나라도 적용되는 순간**, podSelector가 매칭하는 Pod에 대해 그 정책에 명시되지 않은 트래픽은 모두 차단된다 ("default deny" 효과).

### 7. NetworkPolicy 예시 1 — namespace 내 모든 ingress 차단

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: foo
spec:
  podSelector: {}          # namespace의 모든 Pod
  policyTypes: ["Ingress"]
  # ingress 규칙 없음 → 모두 거부
```

### 8. NetworkPolicy 예시 2 — 특정 Pod에서만 접근 허용

`role=db` Pod은 `app=web` Pod에서 5432번 포트만 받는다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-allow-web
  namespace: foo
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes: ["Ingress"]
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 5432
```

### 9. NetworkPolicy의 from/to 셀렉터 종류

`ingress.from` 또는 `egress.to`에 올 수 있는 것:

| 셀렉터 | 의미 |
|--------|------|
| `podSelector` | 같은 namespace의 라벨 매칭 Pod |
| `namespaceSelector` | 라벨 매칭되는 namespace의 모든 Pod |
| `podSelector` + `namespaceSelector` (같은 from 항목) | 둘 다 만족(AND) |
| `ipBlock` | CIDR 기반 (외부 IP 허용/제외) — `cidr` + `except` |

**중요한 함정**: 같은 `from:` 리스트 항목 안에 `podSelector`와 `namespaceSelector`를 같이 쓰면 **AND**, 항목을 분리하면 **OR**.

```yaml
# AND: ns가 prod이고 동시에 Pod이 role=client
ingress:
- from:
  - namespaceSelector: { matchLabels: { ns: prod } }
    podSelector:       { matchLabels: { role: client } }

# OR: ns가 prod이거나 또는 Pod이 role=client
ingress:
- from:
  - namespaceSelector: { matchLabels: { ns: prod } }
  - podSelector:       { matchLabels: { role: client } }
```

### 10. Egress 정책 — 외부 통신 제한

Pod이 외부로 어디까지 나갈 수 있는지 제어. 데이터 유출 방지에 중요.

```yaml
spec:
  podSelector:
    matchLabels: { app: my-app }
  policyTypes: ["Egress"]
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8       # 내부망만 허용
        except: [10.5.0.0/16]  # 단 이 대역은 제외
    ports:
    - protocol: TCP
      port: 443
  # DNS는 별도 허용 필요 (안 그러면 이름 해석 불가!)
  - to:
    - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
      podSelector:       { matchLabels: { k8s-app: kube-dns } }
    ports:
    - protocol: UDP
      port: 53
```

흔한 함정: egress를 막을 때 DNS(53/UDP) 허용을 빼먹으면 모든 도메인 호출이 실패한다.

### 11. 보안 베스트 프랙티스 요약

1. **호스트 네임스페이스 금지** — `hostNetwork/hostPID/hostIPC` 안 씀, `hostPath` 마운트 최소화.
2. **non-root로 실행** — `runAsNonRoot: true`, `runAsUser: 10000` 같은 임의 UID.
3. **capability 전부 drop, 필요한 것만 add**.
4. **`readOnlyRootFilesystem: true`** + 쓰기 필요 영역만 emptyDir.
5. **`allowPrivilegeEscalation: false`**, **`privileged: false`**.
6. **Pod Security Admission `restricted`** 를 default namespace 정책으로.
7. **NetworkPolicy default-deny** 로 시작하고 필요한 통신만 명시적으로 허용.
8. egress 정책에서 DNS(53/UDP) 허용 잊지 않기.
9. NetworkPolicy를 지원하는 CNI 사용 (Calico/Cilium 등).
10. 시크릿/토큰을 환경변수보다 파일 마운트로 (덤프 노출 위험 줄이기).

## 책 vs 현실 차이점

| 책(2018, k8s 1.9) | 현재(2024+) |
|--------------------|-------------|
| **PodSecurityPolicy** (PSP) 가 정책 강제의 표준 | **v1.21 deprecated, v1.25 제거**. 대체: **Pod Security Admission (PSA)** + 정책엔진 (Kyverno/Gatekeeper) |
| PSP는 SA의 `use` 권한으로 활성화 — RBAC와 얽혀 헷갈림 | PSA는 namespace 라벨 한 줄. 단순/명시적 |
| seccomp는 annotation으로 (`seccomp.security.alpha.kubernetes.io/pod`) | **v1.19+ 정식 필드** (`spec.securityContext.seccompProfile`). annotation은 deprecated |
| AppArmor도 annotation | **v1.30+ 정식 필드** (`spec.securityContext.appArmorProfile`) |
| NetworkPolicy는 Ingress만 | **v1.8+ Egress 지원**. v1.21+ **endPort** 필드로 포트 범위 지원 |
| ipBlock에 외부 LB IP가 어떻게 매칭되는지 모호 | 명확화: kube-proxy가 SNAT 안 하면 client IP 그대로 보임 (`externalTrafficPolicy: Local`) |
| L7 정책 없음 | **Cilium / Calico Enterprise** 가 HTTP method, gRPC, Kafka 등 L7 정책 지원 (CRD로) |
| 정책을 yaml로 손수 작성 | **AdminNetworkPolicy** (v1.29+ alpha) — cluster-admin이 NetworkPolicy를 override하는 상위 계층 도입 중 |

## Deep dives

### A. PSA 3가지 프로파일 상세

PSA는 **namespace 라벨** 3종(`enforce`/`audit`/`warn`)으로 동작 모드 지정. 각 라벨 값은 3 프로파일 중 하나.

```yaml
labels:
  pod-security.kubernetes.io/enforce: restricted
  pod-security.kubernetes.io/enforce-version: v1.29
  pod-security.kubernetes.io/audit: restricted
  pod-security.kubernetes.io/warn: restricted
```

| 프로파일 | 핵심 제약 | 사용처 |
|---------|-----------|--------|
| `privileged` | 사실상 무제한 | kube-system, CNI, CSI 등 시스템 namespace |
| `baseline` | hostNetwork/PID/IPC 금지, privileged 금지, host paths 제한, capability `NET_RAW` 등 위험한 것 금지 | 대다수 일반 워크로드의 최저선 |
| `restricted` | baseline + `runAsNonRoot` 강제, `allowPrivilegeEscalation: false` 강제, `capabilities.drop: ["ALL"]` 강제, seccomp `RuntimeDefault` 강제, volume 종류 제한 (configMap/secret/emptyDir/PVC만) | 보안이 중요한 워크로드/멀티 테넌트 |

3 모드:
- **enforce**: 위반 시 Pod 생성 거부.
- **audit**: 위반해도 생성은 됨, audit log에 기록.
- **warn**: kubectl에 경고 메시지 표시.

마이그레이션 패턴: `warn: restricted` → 로그 확인 → 워크로드 수정 → `enforce: restricted`.

### B. NetworkPolicy의 "default deny"는 사실 없다

`NetworkPolicy`는 **명시적으로 default deny 모드가 없다**. 동작 모델:

1. Pod이 어떤 NetworkPolicy의 `podSelector`에도 매칭되지 않으면 → **모든 트래픽 허용**.
2. Pod이 하나라도 매칭되면 → 그 정책에 명시된 것만 허용, 나머지 차단.

따라서 진짜 default-deny를 만들려면 **모든 Pod에 매칭되지만 아무 ingress/egress도 허용하지 않는** 정책을 만든다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: my-ns
spec:
  podSelector: {}              # 모든 Pod
  policyTypes: ["Ingress", "Egress"]
  # ingress/egress 규칙 없음 → 모두 차단
```

이후 필요한 통신은 별도 정책으로 추가. **이 default-deny가 없으면 다른 정책들이 의미 없다** — 새 Pod이 정책 매칭되지 않으면 그대로 뚫림.

### C. NetworkPolicy AND vs OR 함정 (재강조)

```yaml
ingress:
# AND — 같은 항목 안의 두 셀렉터
- from:
  - namespaceSelector: { matchLabels: { ns: prod } }
    podSelector:       { matchLabels: { role: client } }

# OR — 항목을 나눠서
- from:
  - namespaceSelector: { matchLabels: { ns: prod } }
  - podSelector:       { matchLabels: { role: client } }
```

리스트 들여쓰기 한 칸 차이로 의미가 정반대. 실수의 단골.

### D. Egress + DNS 함정

Pod이 `https://api.example.com`을 호출하려면:
1. DNS 질의로 IP 받기 (UDP/53 → CoreDNS Pod).
2. 그 IP로 HTTPS (TCP/443).

Egress 정책에 1번을 빼면 모든 도메인 호출이 실패. 표준 처방:

```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: kube-system
    podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
  - protocol: TCP
    port: 53          # 큰 응답은 TCP fallback
- to: ...             # 그 외 필요한 egress
```

`kubernetes.io/metadata.name` 라벨은 **v1.22+에서 모든 namespace에 자동 부착** — 이전엔 직접 라벨링했어야 했다.

### E. SecurityContext가 실제로 컨테이너에 어떻게 적용되나

- `runAsUser`/`runAsGroup` → 컨테이너 프로세스의 UID/GID. Dockerfile `USER`보다 우선.
- `runAsNonRoot: true` → 컨테이너가 root로 시작하려 하면 kubelet이 **시작 자체를 거부** (`CreateContainerConfigError`). 이미지의 USER가 UID 0이거나 비어 있으면 실패.
- `fsGroup` → 마운트된 볼륨의 ownership을 그 GID로 **recursive chown** (큰 볼륨은 시작이 느려질 수 있음). `fsGroupChangePolicy: OnRootMismatch`로 최적화.
- `capabilities.drop: ["ALL"]` + `capabilities.add: ["NET_BIND_SERVICE"]` — 컨테이너 시작 시 커널의 capability bounding set을 제한.
- `readOnlyRootFilesystem: true` → containerd가 overlay fs를 ro로 마운트. 쓰기 필요 영역은 `emptyDir`로 마운트해서 우회.

### F. seccomp / AppArmor

**seccomp**: 시스템콜 필터링.
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault    # containerd/cri-o 기본 프로파일 (대부분 안전)
    # 또는 type: Localhost, localhostProfile: "profiles/my-profile.json"
```
PSA `restricted`는 `RuntimeDefault`를 강제한다.

**AppArmor**: MAC(Mandatory Access Control) 파일/네트워크 제어.
```yaml
securityContext:
  appArmorProfile:
    type: RuntimeDefault
```
노드에 프로파일 사전 배포 필요 (DaemonSet 등으로).

### G. 런타임 보안 (Falco)

NetworkPolicy/SecurityContext는 **사전 차단**이고, 그 사이를 빠져나가는 런타임 이상행위는 **사후 탐지**해야 한다. 표준: **Falco** (CNCF graduated).

- eBPF로 syscall 모니터링.
- 룰 예: "Shell이 컨테이너에서 실행됨", "민감 파일 읽음", "비표준 포트 listen".
- 알람 → 외부 시스템(Slack, SIEM)으로 전송.

### H. CNI별 NetworkPolicy 지원 상태

| CNI | 표준 NP | L7 정책 | 비고 |
|-----|---------|---------|------|
| Calico | ✅ | ✅ (`tier`/`GlobalNetworkPolicy`) | 가장 널리 쓰임. eBPF 모드도 옵션 |
| Cilium | ✅ | ✅ (CiliumNetworkPolicy로 HTTP/gRPC/Kafka) | eBPF native. Hubble 가시화 |
| Flannel | ❌ | ❌ | NetworkPolicy 무시. Calico와 조합(`Canal`)으로 보완 |
| Weave | ✅ (제한적) | ❌ | 유지보수 둔화 |
| AWS VPC CNI | ✅ (v1.14+) | ❌ | enable-network-policy=true. 이전엔 Calico 추가 필요 |

→ **CNI 선택은 NetworkPolicy 전략을 좌우한다**. Flannel-only 클러스터에서 NetworkPolicy yaml을 적용해도 조용히 무시되는 것이 큰 함정.

## 면접 예상 질문

1. **privileged=true와 hostNetwork=true의 차이?**
   - privileged는 capability/디바이스/securityModule을 다 풀어버린 것 (사실상 노드 root). hostNetwork는 네트워크 네임스페이스만 노드 것을 공유. 보통 같이 안 켠다.
2. **PSP가 제거된 이유?**
   - 정책-RBAC가 얽혀 운영 복잡, 정책 표현력 한계, default 동작이 직관적이지 않음. → namespace 라벨 한 줄로 끝나는 PSA로 대체.
3. **PSA `restricted` 도입 시 가장 자주 깨지는 워크로드?**
   - root로 도는 레거시 이미지 (`runAsNonRoot` 위반), Dockerfile에서 setcap 쓰는 컨테이너 (`allowPrivilegeEscalation` 위반), hostPath 마운트하는 모니터링/로깅 사이드카.
4. **NetworkPolicy를 적용했는데 트래픽이 안 막힌다?**
   - (a) CNI가 NetworkPolicy를 지원하지 않을 가능성 (Flannel only), (b) podSelector가 의도와 다르게 매칭, (c) 같은 Pod에 다른 NetworkPolicy가 OR로 허용 중. `kubectl describe netpol`로 매칭 확인.
5. **NetworkPolicy의 from에 ipBlock으로 외부 IP를 명시했는데 안 잡힌다?**
   - 외부 IP가 kube-proxy/CNI에서 SNAT되어 노드 IP로 보일 수 있음. `externalTrafficPolicy: Local`로 client IP 보존.
6. **Egress를 막은 뒤 도메인 호출이 전부 실패한다?**
   - DNS(53/UDP, TCP)를 CoreDNS에 허용 안 함. 표준 처방 적용.
7. **`runAsNonRoot: true`로 설정했는데 컨테이너가 안 뜬다?**
   - 이미지의 USER가 0(root)이거나 비어 있어서 kubelet이 거부. Dockerfile에 `USER 10000` 추가 또는 `runAsUser: 10000`을 spec에 명시.
8. **`readOnlyRootFilesystem: true`로 했더니 앱이 임시 파일 못 쓴다?**
   - `/tmp`나 캐시 디렉토리를 emptyDir로 마운트. 또는 앱 설정으로 디렉토리 변경.
9. **default-deny NetworkPolicy 없이 다른 정책만 만들면?**
   - 그 정책 podSelector에 매칭되지 않는 새 Pod은 그대로 모든 트래픽 허용 → 의도와 다른 누수. 반드시 default-deny가 baseline.
10. **L7(HTTP path 별) 정책을 표준 NetworkPolicy로 만들 수 있나?**
    - 불가능. NetworkPolicy는 L3/L4만. Cilium의 CiliumNetworkPolicy 또는 service mesh(Istio AuthorizationPolicy) 필요.

## Notes

- ch12가 **컨트롤 플레인 보안**(API에 누가 접근하나)이라면, ch13은 **데이터 플레인 보안**(Pod이 무엇을 할 수 있나).
- SecurityContext + NetworkPolicy + PSA 세 축이 같이 가야 의미 있는 격리가 된다.
- `kubectl auth can-i`처럼 NetworkPolicy도 시뮬레이션 도구가 있다 (`np-viewer`, Cilium `network-policy-validator` 등 외부 툴).
- privileged=true 컨테이너는 사실상 노드 root와 같다 — 절대 외부 입력으로 만들어지지 않게.
- 실서비스에서는 보안 정책을 **GitOps + admission controller(Kyverno/Gatekeeper)** 로 강제하는 것이 표준.
- NetworkPolicy는 **클러스터 안 통신만** 다룬다. 외부 LB로 들어오는 트래픽은 별도 방화벽/WAF/Ingress 인증.
- 컨테이너 이미지 보안(취약점 스캔)은 별개 축 — Trivy / Grype 등을 CI/CD에 통합.

## Questions

- [ ] PSA `restricted` 프로파일을 기존 운영 클러스터에 적용하려면 어떤 마이그레이션이 필요한가?
- [ ] Calico vs Cilium NetworkPolicy 차이? (L7 정책, eBPF 등)
- [ ] CNI가 정책을 지원하지 않는 클러스터에서 NetworkPolicy를 적용하면 어떻게 되는가? (조용히 무시됨 — 위험!)
- [ ] seccomp/AppArmor 프로파일은 실제로 어떻게 만들어 배포하는가?
- [ ] sidecar (e.g. Istio proxy)와 NetworkPolicy의 상호작용은?
