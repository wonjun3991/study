# Cilium 5주차 — DNS / FQDN / L7 Policy & Envoy 심층 노트

## 핵심 메시지

> **eBPF는 L3/L4까지, L7은 프록시로 — 왜, 그리고 그중 DNS는 왜 Envoy가 아니라 agent 내장 Go 프록시인가.**
>
> Cilium은 "커널에서 처리 가능한 것은 eBPF로, 프로토콜 파싱이 꼭 필요한 경우만 userspace 프록시로" 원칙에 따라 역할을 나눈다. L3/L4 정책·서비스 로드밸런싱·NAT·암호화는 eBPF 커널 경로로 처리한다. HTTP/gRPC L7 정책이 필요한 트래픽만 TPROXY로 노드당 하나의 Envoy 프로세스(`cilium-envoy` DaemonSet)로 우회한다. DNS는 단순 요청-응답 프로토콜이라 `cilium-agent` 안의 Go 싱글톤 프록시로 충분하다 — Envoy를 전혀 쓰지 않는다. 이 구분을 이해하는 것이 5주차의 목표다.

이 노트는 슬라이드의 심화 보충 자료다. 슬라이드가 "무엇"을 소개했다면, 이 문서는 "왜"와 "어떻게"를 파고든다.

- **Part I~II**: OSI 캡슐화와 L3/L4 정책만으로는 왜 부족한가.
- **Part III**: DNS 프록시와 `toFQDNs` — 이름 기반 egress 정책.
- **Part IV**: HTTP/gRPC L7 정책 — 메서드·경로 기반 접근 통제.
- **Part V**: Node-local Envoy — 배포 형태와 eBPF→Envoy 리다이렉트.
- **Part VI**: eBPF vs Envoy 역할 구분 — 왜 HTTP는 eBPF로 불가능한가.
- **Part VII**: 4개 질문 요약과 6주차 예고.

---

# 5주차 목표와 4개 핵심 질문

**목표**: L3/L4 정책을 넘어 L7 Policy가 필요한 이유와 Envoy가 언제 개입하는지 이해한다.

**4개 핵심 질문** (Part VII 표로 답한다):

1. **DNS 기반 정책은 어떻게 가능한가?** — 도메인 이름을 IP로 변환하는 DNS 단계를 가로채는 방법
2. **HTTP 정책은 어떻게 동작하는가?** — 같은 포트, 다른 요청을 구별하는 방법
3. **eBPF만으로 L7이 가능한가?** — per-packet 실행 모델과 verifier 제약이 그어놓은 한계
4. **Envoy는 언제 필요한가?** — 대부분 트래픽은 eBPF fast path, 예외는 어디인가

4주차까지의 `CiliumNetworkPolicy`는 `identity(label)` + `IP/CIDR` + `port`까지만 볼 수 있었다. 오늘은 그 위층으로 올라간다.

---

# Part I. 기초 — 패킷은 L1~L7에서 어떻게 변하는가

## 1. OSI 캡슐화: 껍질을 덧씌우고 벗기는 과정

정책이 "어디까지 볼 수 있나"는 곧 **패킷의 어느 껍질까지 열어보느냐**의 문제다. 애플리케이션이 만든 HTTP 요청은 아래 계층으로 내려가며 각 계층의 헤더가 앞에 붙는다(encapsulation). 수신 측은 정확히 역순으로 껍질을 벗긴다(역캡슐화).

```text
   송신 방향 (캡슐화 — 아래로 내려가며 헤더를 앞에 덧붙임)
 ─────────────────────────────────────────────────────────
 L7  App     │ HTTP: GET /api/orders  {JSON body}
              │   ↓ HTTP 헤더(method·path·host·…) 추가
 L5/6 TLS    │ [TLS record | {HTTP payload}]   암호화·세션
              │   ↓ TCP 헤더(srcPort·dstPort·SEQ·ACK) 추가
 L4  TCP     │ [TCP hdr | {TLS|HTTP}]
              │   ↓ IP 헤더(srcIP·dstIP·TTL·proto) 추가
 L3  IP      │ [IP hdr | {TCP|TLS|HTTP}]
              │   ↓ Ethernet 헤더(srcMAC·dstMAC) + FCS 추가
 L2  Eth     │ [MAC hdr | {IP|…} | FCS]
              │   ↓
 L1  Wire    │ 0101010101…  전기·광 신호
 ─────────────────────────────────────────────────────────
   수신 방향: L1→L2→L3→L4(재조합)→L5/6(복호화)→L7(앱 소비)
   각 계층이 자기 헤더만 벗기고 위 계층에 payload를 전달
```

각 계층은 자기 헤더만 추가하고 위 계층의 내용은 **불투명한 payload**로 취급한다. L2 스위치는 IP 주소를 모르고, L3 라우터는 TCP 포트를 신경 쓰지 않는다.

## 2. 계층별로 "무엇이 보이는가" — 정책 가능 범위

| 계층 | 헤더 단위 | 볼 수 있는 것 | 정책으로 쓰면 |
|---|---|---|---|
| **L3** IP | IP packet | 출발·목적지 **IP**, 프로토콜 번호 | CIDR 허용·차단 |
| **L4** TCP/UDP | segment | **포트**, TCP flags (SYN·FIN·RST) | 포트 기반 정책 |
| **L7** HTTP | 재조합된 스트림 | **method·path·header·host·body** | 경로·메서드 정책 |

- **L3/L4**: 패킷 헤더 앞부분 몇 바이트만 읽으면 된다. eBPF가 패킷 하나 단위로 즉시 판단 — 커널에서 완결, userspace 전환 없음.
- **L7**: payload 안쪽 + 여러 패킷에 걸친 스트림을 **재조합·파싱**해야 한다. 연결 단위 상태가 필요하고, 구현이 훨씬 무겁다.

> **Cilium의 역할 분리는 여기에서 시작한다: L3/L4는 eBPF(커널), L7은 프록시(userspace). 이것이 오늘 전체 내용의 뼈대다.**

---

# Part II. 왜 L3/L4로 부족한가

## 3. 4주차 정책이 보는 것

4주차까지 `CiliumNetworkPolicy`는 이것까지만 볼 수 있었다:

```yaml
# 4주차 L3/L4 정책 — 정책이 보는 정보: identity + IP + port
egress:
- toEndpoints:
  - matchLabels:
      app: payment
  toPorts:
  - ports:
    - port: "8080"
      protocol: TCP
```

정책이 보는 것: **누가(Cilium security identity, label 기반) + 어디로(목적지 IP) + 어느 포트(L4)**. HTTP 경로나 도메인 이름은 개념조차 없다.

## 4. 이것만으로 해결 안 되는 두 문제

### 문제 ①: 외부 도메인의 IP churn

`api.github.com`만 허용하고 싶다. CIDR로 표현하면:

```yaml
egress:
- to:
  - ipBlock:
      cidr: 140.82.121.3/32   # 내일 바뀔 수 있다
```

AWS S3·GitHub API·Stripe·CDN 서비스 등 외부 엔드포인트는 anycast·로드밸런서 교체·CDN 이전으로 **IP가 수시로 변한다**. 정책을 관리자가 수동으로 갱신해야 하며, 범위를 넓히면 과잉 허용이 발생한다. DNS 이름이 서비스의 **안정적 식별자**인데 이를 정책에 반영할 방법이 없다.

### 문제 ②: 같은 포트, 다른 요청

```text
GET  /public  → 허용
POST /admin   → 거부
둘 다 목적지 :80/TCP → L3/L4로는 구별 불가
```

같은 포트로 오는 요청 중 일부만 허용하고 싶다. 포트만 봐서는 HTTP 메서드·경로를 알 수 없다. payload를 열어봐야 한다.

> **① → DNS/FQDN Policy, ② → HTTP L7 Policy. 둘 다 패킷의 더 안쪽(payload)을 봐야 하는 문제다.**

---

# Part III. DNS / FQDN Policy

## 5. DNS와 FQDN 기초 — 이름이 IP가 되는 과정

### DNS: 계층적 이름 해석 시스템

DNS(Domain Name System)는 사람이 읽는 이름(`api.github.com`)을 기계가 쓰는 IP(`140.82.121.3`)로 바꾸는 **전 세계 분산 데이터베이스**다. 흔히 "인터넷의 전화번호부"에 비유된다.

**계층 구조** — 이름은 오른쪽(root)부터 왼쪽으로 권한이 위임된다:

```text
. (root)                 ← 전 세계 root 서버군
└─ com.                  ← TLD (Top-Level Domain) 네임서버
   └─ github.com.        ← authoritative 네임서버 (도메인 소유자 운영)
      └─ api.github.com. ← 실제 호스트 레코드
```

**해석 흐름** — 앱(stub resolver)은 recursive resolver에게 위임하고, recursive resolver가 root→TLD→authoritative를 순회한다:

```text
앱(stub) → recursive resolver → root 서버    ("com 담당은?")
                              → TLD(com) 서버 ("github.com 담당은?")
                              → authoritative ("api.github.com = 140.82.121.3")
         ← 결과를 TTL 동안 캐시 ←
```

**주요 레코드 타입**:

| 타입 | 의미 |
|------|------|
| `A` / `AAAA` | 이름 → IPv4 / IPv6 주소 |
| `CNAME` | 이름 → 다른 이름(별칭). FQDN 정책은 체인을 따라가야 함 |
| `NS` | 도메인을 책임지는 네임서버 |
| `MX` / `TXT` | 메일 서버 / 임의 텍스트(SPF·도메인 검증 등) |

모든 응답에는 **TTL(Time To Live)**이 붙고, resolver는 그 시간 동안 결과를 캐시한다. 이 TTL이 뒤에서 Cilium이 학습한 IP를 **얼마나 오래 허용할지**와 직접 연결된다(§8·§9).

### FQDN: 이름의 완전한 주소

**FQDN(Fully Qualified Domain Name)**은 root부터 host까지 **전부 명시된 절대 이름**이다. 엄밀히는 끝에 root를 나타내는 점(`.`)이 붙지만 일상에서는 생략한다.

```text
api.github.com.
│   │      │  └ root ('.' — 보통 생략)
│   │      └──── TLD  (com)
│   └─────────── SLD  (Second-Level Domain, github)
└─────────────── host / subdomain (api)
```

- **FQDN(절대 이름)**: `api.github.com.` — 어디서 조회해도 같은 결과.
- **상대 이름(PQDN)**: `web`, `web.default` — 그 자체로는 모호. resolv.conf의 **search 도메인**을 붙여 FQDN으로 확장해야 한다.
- **길이 제약**: 각 label ≤ 63자, 전체 FQDN ≤ 253자.

**K8s에서의 확장** — Pod resolv.conf의 `search` + `ndots` 규칙이 상대 이름을 FQDN으로 만든다:

```text
options ndots:5
# 이름의 점 개수 < 5 이면 search 도메인을 먼저 순회
web
  → web.default.svc.cluster.local.   (search[0] 적용)
  → web.svc.cluster.local.           (실패 시 다음)
  → ... → web.                       (마지막에 그대로 시도)
```

> **왜 중요한가**: Cilium FQDN 정책의 `matchName`/`matchPattern`은 바로 이 **FQDN 문자열**과 비교된다(§10). 매칭 단위가 "이름"이므로 이름 해석 과정을 정확히 알아야 정책 디버깅이 가능하다.

### 이름이 IP가 되는 과정 — Cilium이 엿보는 지점

Pod 안의 `/etc/resolv.conf`:

```text
nameserver 10.96.0.10   # kube-dns (CoreDNS) ClusterIP
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

`curl https://api.github.com`을 실행하면:
1. glibc `getaddrinfo()` → UDP/TCP port 53 DNS 질의 → kube-dns
2. kube-dns가 `api.github.com. A 140.82.121.3` 응답
3. 애플리케이션이 **그 IP**로 TCP 연결

**핵심 관찰**: 앱은 항상 이름 → IP 변환을 먼저 한다. 이 DNS 질의를 가로채서
- (a) 어떤 이름을 허용할지 필터하고
- (b) 응답으로 온 IP를 기록해두면

→ 그 IP만 이후에 허용하는 방식으로 **도메인 단위 통제**가 가능하다.

> Cilium FQDN Policy의 핵심 아이디어: *DNS 응답을 엿봐서 "허용된 이름의 IP"를 실시간으로 학습한다.*

## 6. Cilium DNS Proxy — Go 싱글톤, Envoy가 아니다

> **⚠️ 흔한 혼동 — 반드시 구분**: Cilium의 DNS proxy는 `cilium-agent` 내부에 내장된 Go 구현체다. Envoy와 전혀 관계없다.

소스 직접 인용 (`pkg/fqdn/dnsproxy/proxy.go`):

```go
// DNSProxy is a L7 proxy for DNS traffic. It keeps a list of allowed DNS
// lookups that can be regexps and blocks lookups that are not allowed.
// A singleton is always running inside cilium-agent.
type DNSProxy struct { ... }
```

`pkg/fqdn/doc.go`도 명확히 기술한다:

```go
// Package fqdn handles some of the DNS-based policy functions:
//   - A DNS Proxy that applies L7 DNS rules and populates the lookup cache
//     with IPs from allowed/successful DNS lookups.
```

DNS library: `github.com/cilium/dns` (miekg/dns 기반 Go 라이브러리).

L7 기능별 처리 주체 비교:

| L7 기능 | 처리 주체 |
|---------|-----------|
| DNS (`rules: dns`) | **cilium-agent 내 Go DNS proxy** — Envoy 아님 |
| HTTP (`rules: http`) | Envoy (cilium-envoy DaemonSet) |
| gRPC | Envoy |
| Kafka (deprecated, 레거시) | cilium-agent 내 Go proxy |

> `Documentation/security/policy/layer7.rst`의 "Layer 7 policies will proxy traffic through a node-local envoy instance"는 HTTP/gRPC 섹션 설명이다. 같은 문서의 DNS 섹션은 별도로 "DNS Proxy in the agent intercepts egress DNS traffic"이라고 명시한다.

```text
┌────────────────────────────── Worker Node ─────────────────────────────┐
│                                                                         │
│  ┌─────────────────────────── cilium-agent ──────────────────────────┐  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  DNS Proxy (Go singleton)                                    │ │  │
│  │  │  • UDP/TCP listen (IP_TRANSPARENT socket)                    │ │  │
│  │  │  • IP_RECVORIGDSTADDR 로 원래 목적지 추출                    │ │  │
│  │  │  • matchName / matchPattern 필터 적용                        │ │  │
│  │  └─────────────────────────┬────────────────────────────────────┘ │  │
│  │                            │ NotifyOnDNSMsg callback               │  │
│  │  ┌─────────────────────────▼────────────────────────────────────┐ │  │
│  │  │  per-Endpoint DNS Lookup Cache → Global DNS Cache            │ │  │
│  │  └─────────────────────────┬────────────────────────────────────┘ │  │
│  │                            │                                       │  │
│  │  ┌─────────────────────────▼────────────────────────────────────┐ │  │
│  │  │  NameManager                                                  │ │  │
│  │  │  • FQDN Selector → IP 매핑 관리                               │ │  │
│  │  │  • ipcache에 /32 CIDR identity 주입                          │ │  │
│  │  │  • endpoint policy map 갱신                                  │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  eBPF datapath (TC ingress/egress hooks)                                │
│  → TPROXY redirect (또는 --enable-bpf-tproxy 시 sk_assign, 커널 5.7+)  │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7. toFQDNs 정책은 반드시 2단 구성

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-github-api"
spec:
  endpointSelector:
    matchLabels:
      org: empire
      class: mediabot
  egress:
  # ── Part A ── DNS proxy 인터셉트 + kube-dns 접근 허용
  - toEndpoints:
    - matchLabels:
        "k8s:io.kubernetes.pod.namespace": kube-system
        "k8s:k8s-app": kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY       # UDP + TCP 모두
      rules:
        dns:
        - matchPattern: "*"  # 모든 DNS 쿼리를 proxy가 관찰·허용
  # ── Part B ── proxy가 학습한 IP에 대한 L3 연결 허용
  - toFQDNs:
    - matchName: "api.github.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**Part A의 역할**:
1. kube-dns로의 UDP/TCP 53 트래픽을 허용한다
2. `rules: dns:` — DNS proxy에게 "이 이름들의 쿼리를 관찰·허용하라" 지시
3. **이 규칙 없이 Part B만 있으면 동작하지 않는다** — proxy로의 리다이렉트 자체가 발생하지 않아 이름→IP 매핑 수집 불가능

`pkg/fqdn/doc.go`: *"traffic is only redirected to it when a L7 rule includes a DNS section"*

**Part B의 역할**:
- `api.github.com`으로 resolve된 IP들에 대한 TCP 443 연결 허용
- proxy가 DNS 응답에서 추출한 IP가 eBPF policy map에 주입된 후 이 규칙이 매칭됨

## 8. 동적 allowlist 갱신 흐름 (name → IP → ipcache → policy map)

```text
Pod               eBPF TC hook       DNS Proxy (Go)         kube-dns
 │                     │                   │                    │
 │── DNS query ────────▶│                   │                    │
 │   (UDP :53)         │                   │                    │
 │                     │──[TPROXY/sk_assign]▶│                   │
 │                     │                   │                    │
 │                     │           ┌───────▼─────────────┐     │
 │                     │           │ 1. 발신 endpoint 식별 │     │
 │                     │           │ 2. rules:dns 필터    │     │
 │                     │           │ 3. matchName/Pattern │     │
 │                     │           └───────┬─────────────┘     │
 │                     │                   │── forward ────────▶│
 │                     │                   │◀── DNS response ───│
 │                     │           ┌───────▼─────────────┐     │
 │                     │           │ 4. 응답 파싱: name→IP │     │
 │                     │           │ 5. ipcache /32 생성  │     │
 │                     │           │ 6. policy map 갱신   │     │
 │                     │           │ 7. ≤100ms 후 응답전달│     │
 │                     │           └───────┬─────────────┘     │
 │◀── DNS response ────│◀──────────────────│                    │
 │                     │                   │                    │
 │── TCP SYN ──────────▶│                   │                    │
 │   (to resolved IP)  │ [eBPF: IP→identity → ALLOW]           │
 │── 연결 성립 ──────────▶ external service                      │
```

- proxy는 응답을 즉시 Pod에 주지 않고 **최대 100ms** 대기(`--tofqdns-proxy-response-max-delay`, 기본 100ms). 이 시간 안에 eBPF policy map 갱신을 완료한다.
- 갱신 전에 IP를 직접 알고 연결하면(`curl --resolve` 등) **차단**된다 — 보안상 의도된 동작이다.

**TTL 만료와 zombie 메커니즘** (`pkg/fqdn/doc.go` 기반):

```text
DNS 응답 수신 → per-EP Cache에 TTL 적용 저장 (min-ttl로 하한 보정)
TTL 만료
  → IP가 "zombie" 상태로 전환
  → CT GC: 살아있는 연결 있으면 "alive" 마킹 → 유예 연장
  → 연결 없으면 다음 GC 사이클에서 ipcache 제거
     → policy map 갱신 → 새 연결 차단

CT GC 실행 주기: 30s ~ 12h (연결 churn 정도에 따라 자동 조정)
```

## 9. 설정 파라미터 레퍼런스

| 플래그 | 기본값 | 설명 |
|--------|--------|------|
| `--tofqdns-min-ttl` | `3600` (s) | DNS TTL 하한. CDN TTL이 30s여도 이 값으로 override |
| `--tofqdns-proxy-response-max-delay` | `100ms` | eBPF map 갱신 완료 대기 최대 시간 |
| `--tofqdns-idle-connection-grace-period` | `0s` | TTL 만료 후 idle 연결 유예 기간 |
| `--tofqdns-endpoint-max-ip-per-hostname` | `50` | endpoint당 FQDN당 최대 저장 IP 수 |
| `--tofqdns-dns-reject-response-code` | `refused` | 거부 시 반환 코드 (`nameError`=NXDOMAIN으로 변경 가능) |
| `--tofqdns-pre-cache` | `""` | 시작 시 pre-load할 DNS cache 파일 경로 |
| `--dnsproxy-enable-transparent-mode` | `false` | upstream DNS로 요청 시 원래 Pod IP를 source로 사용 |

## 10. matchName vs matchPattern 시맨틱

두 필드는 Part A (`rules: dns:`)와 Part B (`toFQDNs:`) 양쪽에서 같은 문법으로 쓰인다.

| 패턴 | 매칭됨 | 매칭 안됨 |
|------|-------|----------|
| `matchName: "api.github.com"` | `api.github.com` | `sub.api.github.com`, `github.com` |
| `matchPattern: "*.github.com"` | `api.github.com`, `gist.github.com` | `github.com` (`.` 불통과) |
| `matchPattern: "*.*.svc.cluster.local"` | `myapp.default.svc.cluster.local` | `myapp.svc.cluster.local` |
| `matchPattern: "part*ial.com"` | `partial.com`, `part-extra-ial.com` | `par.tial.com` |
| `matchPattern: "*"` | 모든 이름 | — |

**핵심**: `*`는 점(`.`) 경계를 넘지 않는다. `*.github.com`은 `github.com` 자체를 허용하지 않는다. 루트 도메인도 허용하려면 `matchName: "github.com"`을 반드시 추가해야 한다.

Part A와 Part B의 관계:

```text
Part A (rules: dns:)  →  proxy가 관찰·허용할 DNS 쿼리 필터링
Part B (toFQDNs:)     →  관찰된 IP에 대한 L3 연결 허용

Part A에서 허용되지 않은 이름 → DNS 쿼리 자체가 REFUSED
Part A에서 허용됐지만 Part B에 없는 이름 → DNS 성공, TCP 연결 차단
```

## 11. 운영 주의사항 (Gotchas)

| 함정 | 증상 및 해결 |
|------|-------------|
| **Part A 누락** | `toFQDNs`가 조용히 동작하지 않음. DNS 규칙 먼저 확인 |
| **musl/Alpine 이미지** | proxy가 `REFUSED` 반환 시 musl이 search list 순회를 멈춤 → `--tofqdns-dns-reject-response-code=nameError` (NXDOMAIN으로 변경) |
| **클러스터 내부 IP** | `toFQDNs`는 in-cluster IP 처리 불가 (ipcache identity 충돌). `toEndpoints` / `toServices` 사용 |
| **짧은 TTL** | CDN TTL 30s → 잦은 갱신 → `--tofqdns-min-ttl=3600` (기본값)으로 하한 설정 |
| **agent 재시작** | 캐시 미보유 이름 일시 차단 → Standalone DNS Proxy (alpha)로 완화 가능 |
| **DNS bypass** | `curl --resolve`처럼 DNS 없이 IP 직접 사용하면 이름→IP 매핑 없어 차단 |

- **캐시는 노드 로컬**: `pkg/fqdn/doc.go`: *"DNS data is tracked per-endpoint but collected globally in each cilium-agent"*. Node A의 학습 결과는 Node A에만 존재. 각 노드가 독립적으로 학습해야 한다.
- **Standalone DNS Proxy (alpha)**: 별도 DaemonSet으로 실행 가능. agent 다운 중에도 기존 캐시 기반으로 동작하지만, 다운 중 처음 조회되는 새 도메인은 identity 할당 불가.

## 12. Hubble에서 DNS 가시성

DNS proxy는 모든 처리에 대해 L7 cilium-monitor 이벤트를 emit한다.

```text
# hubble observe --protocol dns -f 출력 예시
default/app:36657 -> kube-system/coredns:53
    L3-L4 REDIRECTED (UDP)            ← eBPF가 proxy로 우회
    to-proxy FORWARDED (UDP)

default/app:36657 -> kube-system/coredns:53
    dns-request FORWARDED             ← L7 이벤트
        (DNS Query api.github.com. A)

default/app:36657 <- kube-system/coredns:53
    dns-response FORWARDED            ← 응답 + IP
        (DNS Answer "140.82.121.3" TTL: 30 (Proxy api.github.com. A))

default/app:44754 -> api.github.com:443
    L3-Only FORWARDED (TCP Flags: SYN)  ← 학습된 IP로 연결 허용
```

```bash
# DNS 질의/응답 실시간 관찰
hubble observe --protocol dns -f
# L7 이벤트만
hubble observe --protocol dns --type l7 -f
# agent가 알고 있는 이름→IP 캐시 직접 조회
kubectl exec -n kube-system ds/cilium -- cilium fqdn cache list
```

---

# Part IV. HTTP / gRPC L7 Policy

## 13. toPorts + rules:http 구조

`toPorts` 안에 `rules:` 블록을 추가하면 해당 포트 트래픽이 **L7-aware**가 된다. L7 규칙이 있는 포트의 트래픽은 TC eBPF가 TPROXY로 노드 로컬 Envoy에 우회하고, Envoy가 파싱·정책 평가를 수행한다.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "http-allow-get-public"
spec:
  endpointSelector:
    matchLabels:
      app: service
  ingress:
  - fromEndpoints:
    - matchLabels:
        env: prod
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/public$"    # ⚠️ 앵커 필수 — 부분 매칭이므로 /public$이 아니면 /public-admin도 통과
        # POST /public, GET /admin 등은 모두 HTTP 403 반환
```

**HTTP 매칭 필드**:

| 필드 | 설명 | 생략 시 |
|------|------|---------|
| `method` | Extended POSIX regex (`GET`, `POST\|PUT`) | 모든 method 허용 |
| `path` | POSIX regex, `/`로 시작, **부분 매칭** | 모든 path 허용 |
| `host` | Host 헤더 기준 regex | host 무시 |
| `headers` | 반드시 존재해야 하는 헤더 목록 | 헤더 무관 |

> **⚠️ path는 부분 매칭이다.** `/public`은 `/public-admin`도 매칭한다. 보안 정책에서는 반드시 `/public$` 또는 `^/public$`로 앵커를 달아야 한다.

## 14. gRPC 정책 — HTTP/2 위의 http 규칙

gRPC는 전송 계층으로 HTTP/2를 사용한다. 각 RPC 메서드 호출은 HTTP/2 요청으로 매핑된다:

```text
HTTP Method : POST
Path        : /<package>.<Service>/<Method>
Content-Type: application/grpc
```

따라서 **별도 `rules: grpc:` 필드 없이** `rules: http:`에 `method: POST` + path로 gRPC 메서드를 필터링한다.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "grpc-door-policy"
spec:
  endpointSelector:
    matchLabels:
      app: cc-door-mgr
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: public-terminal
    toPorts:
    - ports:
      - port: "50051"
        protocol: TCP
      rules:
        http:                 # gRPC도 http 규칙으로 표현
        - method: "POST"
          path: "/cloudcity.DoorManager/GetName"
        - method: "POST"
          path: "/cloudcity.DoorManager/GetLocation"
        - method: "POST"
          path: "/cloudcity.DoorManager/RequestMaintenance"
        # SetAccessCode, GetStatus → gRPC Status 7 PERMISSION_DENIED
```

## 15. allowlist 기본 의미론과 L7 deny

L7 규칙은 **allowlist** 방식이다:

| 설정 | 동작 |
|------|------|
| `rules: {}` (http 키 없음) | L7 proxy 우회 없음. L4 판단만 |
| `rules: { http: [] }` | 빈 리스트 → **모든 HTTP 허용** (L7 가시성 목적) |
| `rules: { http: [{}] }` | 빈 규칙 하나 = 와일드카드 → **모든 HTTP 허용** |
| `rules: { http: [{method: "GET", path: "/public$"}] }` | GET /public만 허용, 나머지 403 |

공식 문서 원문: *"A layer 7 request is permitted if at least one of the rules matches. If no rules are specified, then all traffic is permitted."*

**거부 응답은 조용한 drop이 아니다**:
- HTTP → `403 Forbidden`
- gRPC → `StatusCode.PERMISSION_DENIED (7)` — 클라이언트가 타임아웃이 아닌 명시적 거부를 받음

```text
# gRPC 클라이언트 쪽 에러
grpc._channel._InactiveRpcError:
  status = StatusCode.PERMISSION_DENIED
  details = "Access denied"
  grpc_status = 7
```

**⚠️ L4/L7 동일 포트 중복 규칙 함정**: 같은 포트에 L4-only 규칙과 L7 규칙이 공존하면, L4-only 규칙이 그 포트를 전체 허용해 L7 제약이 무효화된다. 하나의 `toPorts`로 합쳐서 관리해야 한다.

## 16. TLS Visibility — terminatingTLS / originatingTLS

Envoy는 **평문**을 파싱해야 한다. 외부로 나가는 HTTPS는 기본적으로 내용을 볼 수 없다. `terminatingTLS` + `originatingTLS`로 Envoy를 중간에 배치해 TLS를 종료·재개시하면 L7 파싱이 가능해진다.

```text
Pod A  ──TLS──▶  Envoy  ──TLS──▶  httpbin.org
       (CA cert)        (real cert)

1. terminatingTLS: Envoy가 Pod A의 TLS를 종료
   (클라이언트 Pod는 내부 CA 인증서를 신뢰해야 함)
2. 평문 HTTP 파싱 + L7 policy 적용
3. originatingTLS: Envoy가 실제 목적지로 새 TLS 연결 시작
```

```yaml
egress:
- toFQDNs:
  - matchName: "httpbin.org"
  toPorts:
  - ports:
    - port: "443"
      protocol: TCP
    terminatingTLS:           # Pod → Envoy TLS 종료
      secret:
        namespace: kube-system
        name: httpbin-tls-data
    originatingTLS:           # Envoy → httpbin.org 재연결
      secret:
        namespace: kube-system
        name: tls-orig-data
    rules:
      http:
      - {}                    # 모든 HTTP 허용 (가시성 목적)
- toPorts:                    # toFQDNs 필수 선행 조건
  - ports:
    - port: "53"
      protocol: ANY
    rules:
      dns:
        - matchPattern: "*"
```

**버전별 TLS 시크릿 관리**:

| 버전 | 방식 | 특징 |
|------|------|------|
| ~1.16 | NPDS (inline base64) | 동일 시크릿이 규칙 수만큼 복사 (메모리 낭비) |
| 1.17+ | SDS (Secret Discovery Service, **기본값**) | Envoy가 참조로 secret 접근, 중복 제거 |

## 17. Hubble에서 HTTP L7 흐름 확인

L7 가시성은 L7 `CiliumNetworkPolicy`가 존재해야 활성화된다. `[{}]` 패턴으로 정책 없이 가시성만 얻을 수 있다.

```text
# hubble observe -f -t l7 -o compact 출력 예시
default/testapp:33044 -> default/echo:8080
    http-request FORWARDED (HTTP/1.1 GET http://web/)

default/testapp:33044 <- default/echo:8080
    http-response FORWARDED (HTTP/1.1 200 4ms (GET http://web/))

# 거부된 요청
default/client:41233 -> default/api:8080
    http-request DROPPED (HTTP/1.1 POST http://api/admin)
    verdict: DROPPED, code: 403
```

---

# Part V. Node-local Envoy

## 18. Envoy란 — xDS로 동적 설정되는 L4/L7 프록시

Envoy는 Lyft가 만든 고성능 L4/L7 프록시(현재 CNCF 졸업 프로젝트, C++). Istio·Cilium·Gateway 구현체가 공유하는 데이터 플레인이다.

요청이 Envoy를 지나는 경로(설정 모델):

```text
Listener (수신 포트 — L7 규칙 있는 트래픽이 도착)
  └─ Filter Chain (TLS·HTTP Connection Manager 등)
       └─ Route (host/path 매칭 → 어느 Cluster로)
            └─ Cluster (논리적 upstream = 목적지 서비스 그룹)
                 └─ Endpoint (실제 백엔드 Pod IP:port)
```

xDS 프로토콜로 제어 플레인이 Envoy에 설정을 내려준다: **LDS** (Listener) / **RDS** (Route) / **CDS** (Cluster) / **EDS** (Endpoint) / **SDS** (Secret·인증서).

> **Cilium 사용자는 Envoy 설정을 직접 쓰지 않는다.** `CiliumNetworkPolicy`의 L7 규칙을 `cilium-agent`가 xDS로 자동 변환해 UNIX domain socket을 통해 Envoy에 push한다.

## 19. 핵심 차이 — Pod당이 아니라 노드당 1개

```text
[Istio Sidecar] → Pod마다 Envoy 1개 주입 → Pod 20개면 Envoy 20개
[Cilium]        → 노드당 Envoy 1개 공유  → Pod 20개여도 Envoy 1개
```

| 모델 | Envoy 위치 | 인스턴스 수 | L7 없는 Pod |
|------|-----------|------------|-------------|
| Istio Sidecar | Pod마다 1개 | Pod 수만큼 | 그래도 Envoy 경유 |
| **Cilium** | **노드당 1개** (DaemonSet) | 노드 수만큼 | **eBPF fast path, Envoy 미경유** |
| Istio Ambient Waypoint | 네임스페이스/서비스 단위 | 워크로드 그룹 수 | L4 ztunnel만 경유 |

노드 1개에 Pod 20개, 모두 L7 policy 적용 시:
- Istio Sidecar: Envoy 20개 (각 ~50-100MB RAM) → **최대 ~2 GB**
- Cilium: Envoy **1개** → **약 20배 메모리 절감**

게다가 **L7 규칙이 없는 Pod의 트래픽은 Envoy를 전혀 거치지 않는다** — eBPF fast path만 사용한다.

## 20. embedded → standalone cilium-envoy DaemonSet

**Embedded Envoy (~v1.15, 구버전)**:

```text
cilium-agent Pod
├── cilium-agent (Go 바이너리)
└── envoy (서브프로세스)    ← 같은 Pod 라이프사이클 공유
```

문제: `cilium-agent` 업그레이드 → Envoy도 재시작 → **진행 중인 모든 L7 연결 끊김** (GitHub Issue #13194). 운영 로그 섞임, 리소스 분리 불가.

**독립형 cilium-envoy DaemonSet (v1.14+ opt-in, v1.16+ 기본값)**:

```text
노드
├── cilium-agent Pod (DaemonSet)     ← agent 라이프사이클
│   └── cilium-agent (Go)
└── cilium-envoy Pod (DaemonSet)     ← Envoy 라이프사이클 (독립!)
    └── envoy
```

Cilium v1.16.0 릴리즈 노트: *"L7 Envoy Proxy as dedicated DaemonSet: With a dedicated DaemonSet, Envoy and Cilium can have a separate life-cycle from each other. Now on by default for new installs."*

분리 이점:

| 이점 | 설명 |
|------|------|
| L7 연결 유지 | `cilium-agent` 재시작·업그레이드 시 Envoy 계속 실행 → L7 연결 끊기지 않음 |
| 독립적 Envoy 업그레이드 | Envoy 패치 버전 업그레이드 시 agent 영향 없음 |
| 리소스 격리 | Envoy/agent 각각 CPU·메모리 limit 독립 설정 |
| 보안 격리 | 별도 Pod, 최소 권한 원칙 적용 가능 |
| 운영 편의 | 로그 분리, Envoy 전용 헬스 프로브 |

**통신**: 두 모드 모두 `cilium-agent` ↔ Envoy 간 통신은 **UNIX domain socket** (네트워크 오버헤드 없음).

Helm 설정: `--set envoy.enabled=true` (v1.14+); v1.16+ 신규 설치 기본값.

> **알려진 제한**: standalone DaemonSet 사용 시, L7-HTTP policy + ToFQDN 조합에서 `cilium-agent` 재시작 후 Envoy가 IPCache BPF 맵 변경을 즉시 반영하지 못해 일시적 차단 가능 (Issue #32651).

## 21. eBPF → Envoy 리다이렉트 메커니즘

```text
클라이언트 Pod
     │ 1. 패킷 송출
     ▼
[TC eBPF hook] ← veth 호스트 측 tc ingress에 부착
     │
     │ 2. Endpoint Policy Map 조회:
     │    "이 flow에 L7 규칙 있나?"
     │
     ├── L7 규칙 없음 → eBPF fast path 유지 (Envoy 미경유)
     │
     └── L7 규칙 있음 → skb->mark |= MARK_MAGIC_TO_PROXY (0x200)
                          ctx_redirect_to_proxy()
                               │
                     ┌─────────▼───────────────────────────┐
                     │  TPROXY (iptables mangle table)      │
                     │  또는 --enable-bpf-tproxy            │
                     │  (bpf_sk_assign, 커널 5.7+)          │
                     │  원본 dst IP:port 소켓에 보존         │
                     └─────────┬───────────────────────────┘
                               │
                     ┌─────────▼───────────────────────────┐
                     │  cilium-envoy (노드 로컬)            │
                     │                                      │
                     │  BPF Metadata Listener Filter:       │
                     │  eBPF map에서 source Pod의           │
                     │  Security Identity 읽어 전달         │
                     │                                      │
                     │  TCP reassembly 완료된               │
                     │  byte stream으로 HTTP/2 파싱         │
                     │  method/path/header 정책 평가        │
                     │                                      │
                     ├── ALLOW → 원래 목적지로 upstream     │
                     └── DENY  → 403 / PERMISSION_DENIED   │
                               │
                     서버 Pod (dstIP:dstPort)
```

핵심 디테일:
- **`MARK_MAGIC_TO_PROXY = 0x200`** — TC BPF(`bpf_lxc.c`의 `handle_ipv4_from_lxc`)가 L7 규칙 있는 패킷에 찍는 매직 마크
- **TPROXY**: 원본 목적지 IP:port를 소켓에 보존하면서 다른 로컬 소켓(Envoy 리스너)으로 전달. Envoy가 `SO_ORIGINAL_DST`로 실제 목적지를 조회 가능
- **BPF Metadata Listener Filter**: Cilium이 Envoy Listener에 자동 주입. source Pod의 Cilium Security Identity를 eBPF map에서 읽어 Envoy에 전달 → identity 기반 정책 평가 가능
- **Proxy Port**: `cilium-agent`가 각 Listener에 동적으로 임의 포트를 할당 (사용자는 신경 쓸 필요 없음)

> **L7 규칙이 없는 트래픽은 Envoy를 전혀 거치지 않는다.** 클러스터에 `cilium-envoy`가 실행 중이어도, 해당 flow에 L7 규칙이 없으면 100% eBPF 커널 경로로 처리된다.

## 22. CiliumNetworkPolicy → xDS 자동 변환 + CiliumEnvoyConfig CRD

**자동 경로**: `CiliumNetworkPolicy`에 `rules: http:` 규칙을 작성하면, `cilium-agent`가 Envoy xDS Listener/Route 설정으로 자동 변환해 UNIX socket으로 Envoy에 push한다.

**고급 경로**: `CiliumEnvoyConfig (CEC)` / `CiliumClusterwideEnvoyConfig (CCEC)` CRD로 Envoy xDS 리소스를 직접 정의:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: my-envoy-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-listener
    # ... Listener 설정 (레이트 리미팅, 서킷 브레이커 등)
  - "@type": type.googleapis.com/envoy.config.route.v3.RouteConfiguration
    name: my-route
    # ... 라우팅 규칙
  - "@type": type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: my-cluster
    # ... upstream 클러스터
```

Kubernetes Ingress와 Gateway API(`HTTPRoute`, `TLSRoute`)도 내부적으로 이 노드 로컬 Envoy 위에 구현된다 — 7주차 주제.

---

# Part VI. eBPF vs Envoy 역할 구분

## 23. 왜 eBPF만으로 HTTP를 처리할 수 없는가

### 근본 문제: per-packet 실행 모델

eBPF 프로그램은 **패킷 하나가 도착할 때마다 독립적으로 호출**된다 (tc hook, XDP hook). 호출 간에 스택 상태는 공유되지 않는다. HTTP 요청은 TCP 스트림 위에서 동작하므로 여러 세그먼트에 걸쳐 전송된다:

```text
TCP 세그먼트 1: "GET /api/v1/us"
TCP 세그먼트 2: "ers HTTP/1.1\r\nHost: ex"
TCP 세그먼트 3: "ample.com\r\n\r\n"

→ eBPF는 세그먼트 1만 보고 판단해야 하는데 요청이 아직 완결되지 않음.
  스트림을 재조합하려면 BPF Map에 연결 단위 상태를 유지해야 한다 —
  이는 극도로 복잡한 상태 기계를 요구한다.
```

### eBPF Verifier 제약

| 제약 | 값 | HTTP 파싱에 미치는 영향 |
|------|-----|------|
| 최대 명령어 수 | 1,000,000 (Linux 5.2+) | 복잡한 파서 작성 사실상 불가 |
| 스택 크기 | **512 bytes** | HTTP/2 디코더 상태 유지 불가 |
| 루프 | bounded loop만 허용 (Linux 5.3+) | 종료를 증명 못 하면 verifier 거부 |
| 함수 복잡도 | 경로당 4,096 유닛 | 중첩 파싱 로직 거부됨 |

루프 하나에 body 20 instructions, 최대 100회 반복이면 verifier가 수천 가지 경우의 수를 검사해 복잡도 한도에 도달한다. 가변 길이 HTTP 헤더를 다루는 파서는 verifier를 통과시키기 매우 어렵다.

### HTTP/2와 HPACK의 구조적 불가능성

HTTP/2(gRPC의 전송 레이어)는 **HPACK** 헤더 압축을 사용한다:

```text
HTTP/2 연결 시작
│
├─ 첫 번째 요청: HEADERS 프레임
│   Content-Type: application/grpc  → 동적 테이블 인덱스 31로 기록
│   Authorization: Bearer <token>   → 동적 테이블 인덱스 32로 기록
│
└─ 이후 요청: HEADERS 프레임
    :idx 31  (= "Content-Type: application/grpc")  ← 한 바이트로 전달
    :idx 32  (= "Authorization: Bearer <token>")   ← 한 바이트로 전달
```

HPACK 동적 테이블은 **연결 전체 수명 동안** 업데이트되며, 이전 모든 헤더 교환 이력이 있어야 현재 패킷을 디코딩할 수 있다. per-packet eBPF 프로그램은 이 연결 단위 상태를 유지할 수 없다.

또한 HTTP/2는 **스트림 멀티플렉싱** — 하나의 TCP 연결 위에 여러 스트림이 동시에 인터리빙된다. 어떤 HEADERS 프레임이 어느 스트림에 속하는지 추적하려면 연결 단위 상태 기계가 필요하다.

### Envoy가 가능한 이유: Userspace Full TCP Socket

```text
Envoy 내부 (userspace)
├── accept() → 클라이언트 연결 수락
├── read()   → 커널 TCP 스택이 이미 재조합한 byte stream 읽기
│              (패킷 순서 보장·재전송은 커널이 처리)
├── HTTP/2 디코더 (메모리 제한 없음, 상태 완전 유지)
│   ├── HPACK 동적 테이블 (connection lifetime 관리)
│   ├── 스트림 ID 추적
│   └── 프레임 재조합
└── 정책 평가 → upstream 연결
```

커널 TCP 스택이 패킷 재조합·순서 보장·재전송을 모두 처리해 주므로, Envoy는 **이미 재조합된 byte stream**을 받는다. 512 bytes 스택 제한도, verifier 복잡도 한계도, per-packet 제약도 없다. userspace 컨텍스트 스위치가 발생하지만, L7 규칙이 없는 트래픽은 이 경로를 전혀 거치지 않으므로 영향은 L7 policy를 명시적으로 쓴 경우에만 한정된다.

### DNS는 왜 eBPF + Go 프록시로 충분한가

DNS는 단순한 **요청-응답** 프로토콜이다: 고정 포트 53, 짧은 payload, 단일 메시지로 완결. TCP 스트림 재조합 부담이 없고 HTTP/2 HPACK 같은 연결 수명 상태가 없다. `cilium-agent` 안의 Go DNS proxy면 충분하며 Envoy를 전혀 쓸 필요가 없다.

## 24. 역할 분담 전체 표

```text
┌────────────────────────────┬────────────────────────────┬──────────────────┐
│ 기능                        │ 처리 주체                  │ 위치             │
├────────────────────────────┼────────────────────────────┼──────────────────┤
│ L3/L4 포워딩·정책           │ eBPF (tc/XDP)              │ 커널             │
│ Service LB (kube-proxy 대체)│ eBPF (socket LB)           │ 커널             │
│ NAT / masquerade           │ eBPF (ct map, nat map)     │ 커널             │
│ 노드간 암호화 (WireGuard)   │ eBPF                       │ 커널             │
│ L3/L4 관측 (Hubble flow)   │ eBPF                       │ 커널             │
├────────────────────────────┼────────────────────────────┼──────────────────┤
│ HTTP method/path/header    │ Envoy (cilium-envoy DS)    │ userspace / 노드당│
│ HTTP/2·gRPC L7 정책        │ Envoy                      │ userspace / 노드당│
│ HTTP L7 관측 (access log)  │ Envoy                      │ userspace / 노드당│
│ Ingress L7 라우팅          │ Envoy (CiliumEnvoyConfig)  │ userspace / 노드당│
│ Gateway API                │ Envoy (CiliumEnvoyConfig)  │ userspace / 노드당│
│ TLS 종료 / 재개시           │ Envoy                      │ userspace / 노드당│
├────────────────────────────┼────────────────────────────┼──────────────────┤
│ DNS proxy · FQDN 정책      │ cilium-agent 내장 Go       │ userspace / 노드당│
│ Kafka proxy (deprecated)   │ cilium-agent 내장 Go       │ userspace / 노드당│
└────────────────────────────┴────────────────────────────┴──────────────────┘
```

**중요**: DNS와 Kafka는 Envoy를 사용하지 않는다. `cilium-agent` 내 Go로 작성된 자체 프록시로 처리된다. Kafka L7 정책은 deprecated된 레거시 기능으로, 신규 구성에서는 사용하지 않을 것을 권장한다.

## 25. "Envoy는 언제 필요한가" — 실제 트래픽 분류

```text
클러스터 트래픽 유형별 처리 경로

① Pod → Pod (L3/L4만)         → eBPF fast path         (Envoy 미경유)
② Pod → Service (L4 LB)        → eBPF socket LB         (Envoy 미경유)
③ FQDN egress 정책              → DNS proxy (agent Go)   (Envoy 미경유)
④ HTTP/gRPC method·path 정책   → TPROXY → Envoy         (Envoy 경유)
⑤ Ingress / Gateway API        → TPROXY → Envoy         (Envoy 경유)

①②③이 클러스터 대부분의 트래픽 — 명시적 L7 규칙 없이 동작.
Envoy가 관여하는 것은 ④⑤ — 사용자가 L7을 명시적으로 선택한 경우에만.
```

**Envoy가 필요한 조건** (어느 하나라도 해당하면):
1. `CiliumNetworkPolicy`에 `toPorts.rules.http` 또는 gRPC 규칙이 있는 트래픽
2. Kubernetes Ingress (cilium Ingress controller)
3. Gateway API (`HTTPRoute` 등)
4. L7 Protocol Visibility 어노테이션 설정 트래픽 (관측 전용)

사이드카 모델처럼 "모든 트래픽 × 프록시" 곱셈 비용이 없다. 노드당 Envoy 1개가 선택적으로만 개입한다.

---

# Part VII. 정리

## 26. 4개 핵심 질문에 답한다

| 질문 | 답 |
|------|-----|
| **DNS 기반 정책은 어떻게 가능한가?** | `cilium-agent` 내장 **Go DNS proxy**가 DNS 질의를 TPROXY로 인터셉트해 이름→IP를 학습. `toFQDNs`(Part B)가 그 IP에 L3 연결을 허용. **반드시 Part A (`rules:dns`)와 함께 2단 구성**해야 동작. |
| **HTTP 정책은 어떻게 동작하는가?** | `toPorts.rules.http`(method/path/header 매칭) → TC eBPF가 `MARK_MAGIC_TO_PROXY` 마킹 → TPROXY로 **노드 로컬 Envoy**로 우회 → Envoy가 HTTP 파싱·정책 평가. 위반은 **HTTP 403** / gRPC는 **PERMISSION_DENIED**, 조용한 drop이 아님. |
| **eBPF만으로 L7이 가능한가?** | **아니오.** per-packet 실행 모델로 TCP 재조합 불가, 512B 스택, bounded-loop verifier, HTTP/2 HPACK·스트림 멀티플렉싱 처리 불가. eBPF는 리다이렉트 판단까지, 파싱은 Envoy(userspace). DNS는 단순해 agent Go proxy로 예외 처리. |
| **Envoy는 언제 필요한가?** | HTTP/gRPC L7 규칙·Ingress·Gateway API일 때만. **노드당 1개** (Pod당 1개 아님). L7 규칙 없는 트래픽은 **eBPF fast path**로만 흐르고 Envoy를 아예 거치지 않는다. |

> **결론 한 줄: 커널에서 될 건 eBPF로, 프로토콜 파싱이 꼭 필요할 때만 프록시로. L7 중에서도 DNS는 agent 내장 Go, HTTP/gRPC는 노드당 Envoy — 이 역할 분리가 Cilium 데이터 플레인의 핵심이다.**

**6주차 예고 — Hubble**: 오늘 생성된 `dns-request`·`dns-response`·`http-request`·`http-response` L7 이벤트를 흐름 단위로 관측한다. "왜 막혔나 / 어느 계층에서 끊겼나"를 Hubble CLI와 UI로 직접 확인할 수 있다.

---

## 참고 자료

**Cilium 공식 문서 (docs.cilium.io)**
- [DNS-Based Policies (stable)](https://docs.cilium.io/en/stable/security/dns/)
- [Layer 7 Policies (stable)](https://docs.cilium.io/en/stable/security/policy/layer7/)
- [Envoy Proxy — stable](https://docs.cilium.io/en/stable/security/network/proxy/envoy/)
- [Envoy Proxy — latest](https://docs.cilium.io/en/latest/security/network/proxy/envoy/)
- [TLS Visibility (stable)](https://docs.cilium.io/en/stable/security/tls-visibility/)
- [L7-Aware Traffic Management (stable)](https://docs.cilium.io/en/stable/network/servicemesh/l7-traffic-management/)
- [eBPF Introduction (stable)](https://docs.cilium.io/en/stable/network/ebpf/intro/)
- [Standalone DNS Proxy — alpha (stable)](https://docs.cilium.io/en/stable/security/standalone-dns-proxy/)
- [System Requirements (stable)](https://docs.cilium.io/en/stable/operations/system_requirements/)
- [L7 Protocol Visibility (stable)](https://docs.cilium.io/en/stable/observability/visibility/)

**Cilium GitHub 소스 및 예제 (github.com/cilium/cilium)**
- [pkg/fqdn/dnsproxy/proxy.go](https://github.com/cilium/cilium/blob/main/pkg/fqdn/dnsproxy/proxy.go) — `DNSProxy` struct 정의, Go 싱글톤 증거
- [pkg/fqdn/doc.go](https://github.com/cilium/cilium/blob/main/pkg/fqdn/doc.go) — fqdn 패키지 전체 아키텍처, caching/GC 메커니즘
- [Documentation/security/dns.rst](https://github.com/cilium/cilium/blob/main/Documentation/security/dns.rst) — DNS policy 공식 튜토리얼
- [Documentation/security/policy/layer7.rst](https://github.com/cilium/cilium/blob/main/Documentation/security/policy/layer7.rst) — HTTP/DNS L7 정책 상세
- [Documentation/security/grpc.rst](https://github.com/cilium/cilium/blob/main/Documentation/security/grpc.rst) — gRPC 정책 튜토리얼
- [Documentation/security/policy/intro.rst](https://github.com/cilium/cilium/blob/main/Documentation/security/policy/intro.rst) — enableDefaultDeny, DNS visibility 예시
- [Documentation/observability/visibility.rst](https://github.com/cilium/cilium/blob/main/Documentation/observability/visibility.rst) — L7 Protocol Visibility
- [examples/kubernetes-dns/dns-matchname.yaml](https://github.com/cilium/cilium/blob/main/examples/kubernetes-dns/dns-matchname.yaml)
- [examples/kubernetes-dns/dns-pattern.yaml](https://github.com/cilium/cilium/blob/main/examples/kubernetes-dns/dns-pattern.yaml)
- [examples/policies/l7/dns/dns.yaml](https://github.com/cilium/cilium/blob/main/examples/policies/l7/dns/dns.yaml)
- [examples/policies/l7/dns/dns-visibility.yaml](https://github.com/cilium/cilium/blob/main/examples/policies/l7/dns/dns-visibility.yaml)
- [examples/policies/l7/http/simple/l7.yaml](https://github.com/cilium/cilium/blob/main/examples/policies/l7/http/simple/l7.yaml)
- [examples/policies/l7/http/http.yaml](https://github.com/cilium/cilium/blob/main/examples/policies/l7/http/http.yaml)
- [examples/kubernetes-grpc/cc-door-ingress-security.yaml](https://github.com/cilium/cilium/blob/main/examples/kubernetes-grpc/cc-door-ingress-security.yaml)
- [examples/kubernetes-tls-inspection/l7-visibility-tls.yaml](https://github.com/cilium/cilium/blob/main/examples/kubernetes-tls-inspection/l7-visibility-tls.yaml)
- [Cilium v1.16.0 Release Notes](https://github.com/cilium/cilium/releases/tag/v1.16.0) — standalone Envoy DaemonSet 기본값 변경
- [GitHub Issue #13194](https://github.com/cilium/cilium/issues/13194) — embedded Envoy lifecycle 문제
- [GitHub Issue #32651](https://github.com/cilium/cilium/issues/32651) — standalone DS + ToFQDN 조합 이슈

**Cilium 블로그 및 커뮤니티**
- [Application-Aware Security Policies with Cilium Layer 7 Network Policies — cilium.io (2025)](https://cilium.io/blog/2025/05/20/cilium-l7-policies/)
- [Cilium 1.14 Feature: Envoy as a Daemonset — Isovalent](https://isovalent.com/videos/cilium-1-14-feature-envoy-as-a-daemonset/)
- [FQDN and DNS Proxy — DeepWiki (cilium/cilium)](https://deepwiki.com/cilium/cilium/9.2-fqdn-and-dns-proxy)
- [Episode 43 — Cilium FQDN Policy Deepdive — HackMD](https://hackmd.io/@Echo-Live/B1UOe_yr5)

**배경 기술 자료**
- [Observing HTTP/2 Traffic is Hard, but eBPF Can Help — Pixie Labs](https://blog.px.dev/ebpf-http2-tracing/) — HPACK과 eBPF 한계
- [We Put an L7 Firewall in the Kernel — yeet.cx](https://yeet.cx/blog/l7-firewall-in-the-kernel) — eBPF verifier와 L7 파싱 한계
- [Inside the eBPF Verifier — howtech.substack.com](https://howtech.substack.com/p/inside-the-ebpf-verifier-ensuring) — 1M inst, 512B stack 제약 상세
- [Cilium Proxy Injection — oneuptime.com](https://oneuptime.com/blog/post/2026-03-13-cilium-proxy-injection/view) — 노드당 vs Pod당 비교 (20x 절감)
- [Exploring Cilium Service Mesh — Sigrid Jin, Medium (2025)](https://sigridjin.medium.com/exploring-cilium-service-mesh-from-ebpf-powered-networking-to-advanced-l7-traffic-management-51e2619662aa)
