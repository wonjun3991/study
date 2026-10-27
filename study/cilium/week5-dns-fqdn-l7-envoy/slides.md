---
marp: true
theme: default
paginate: true
backgroundColor: "#1a1a2e"
color: "#e0e0e0"
style: |
  section {
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    background-color: #1a1a2e;
    font-size: 30px;
    line-height: 1.5;
    padding: 56px 64px;
  }
  h1 {
    color: #00d4ff;
    border-bottom: 2px solid #00d4ff;
    padding-bottom: 10px;
    font-size: 1.5em;
  }
  h2 { color: #00d4ff; font-size: 1.22em; }
  h3 { color: #7fdbff; font-size: 1.02em; margin-bottom: 6px; }
  strong { color: #ffd700; }
  em { color: #ff9e64; font-style: normal; }
  code {
    background-color: #16213e;
    color: #00ff88;
    font-size: 0.9em;
    padding: 1px 6px;
    border-radius: 4px;
  }
  pre {
    background-color: #0d1117 !important;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 16px;
  }
  pre code {
    background-color: transparent !important;
    color: #e6edf3;
    font-size: 0.7em;
    line-height: 1.4;
  }
  table { font-size: 0.72em; margin: 4px auto 10px auto; border-collapse: separate; border-spacing: 0; border-radius: 6px; overflow: hidden; }
  th { background-color: #16213e; color: #00d4ff; padding: 6px 12px; }
  td { background-color: #0f3460; padding: 6px 12px; }
  blockquote {
    border-left: 4px solid #ffd700;
    background-color: #2a1f3d;
    padding: 12px 20px;
    margin: 16px 0;
    font-style: normal;
    font-size: 0.9em;
    border-radius: 4px;
  }
  section.lead h1 { text-align: center; font-size: 2.2em; border: none; }
  section.lead p { text-align: center; font-size: 1.1em; }
  ul, ol { padding-left: 22px; }
  li { margin: 5px 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
  .small { font-size: 0.8em; color: #9aa0b0; }
  .tag { color: #00d4ff; font-size: 0.8em; letter-spacing: 0.04em; }
---
<!-- _class: lead -->

# Cilium 5주차<br/>DNS · FQDN · L7 Policy 와 Envoy

<span class="tag">L3/L4를 넘어서 — 언제, 왜 Envoy가 개입하는가</span>

발표자 — 최원준

<!--
5주차 시작. 지난 4주간 우리는 Pod가 IP를 얻고(CNI), eBPF가 kube-proxy를 대체하고, L3/L4 NetworkPolicy가 커널에서 강제되는 것까지 봤다.
오늘은 그 "위층" — 도메인 이름 기반 정책, HTTP/gRPC 정책, 그리고 이걸 처리하는 Envoy를 다룬다.
핵심 한 줄: "eBPF는 L3/L4까지, L7은 프록시(Envoy·DNS proxy)로 넘긴다 — 왜 그렇게 나눴는가"를 이해하는 게 목표.
-->

---

# 오늘의 목표와 4개의 질문

L3/L4를 넘어 **L7 Policy가 필요한 이유**와 **Envoy가 언제 개입하는지** 이해한다.

<div class="columns">
<div>

**핵심 질문**
1. DNS 기반 Policy는 어떻게 가능한가?
2. HTTP Policy는 어떻게 동작하는가?
3. eBPF만으로 L7이 가능한가?
4. Envoy는 언제 필요한가?

</div>
<div>

**다룰 것**
- L1~L7 페이로드가 변하는 방식
- DNS Proxy · FQDN · `toFQDNs`
- HTTP / gRPC L7 Policy
- Node-local Envoy
- eBPF와 Envoy의 역할 구분

</div>
</div>

<!--
오늘 슬라이드는 이 4개 질문에 답하는 구조다. 발표 끝에 이 슬라이드로 다시 돌아와 하나씩 답을 확인할 것.
"다룰 것" 왼쪽 첫 항목 — L1~L7 페이로드 변화 — 은 나머지 전부의 기반이니 먼저 깔고 간다.
-->

---

# 4주차까지의 복습 — 우리가 아는 것

<div class="columns">
<div>

- **CNI**: Pod에 IP·veth 부여
- **eBPF datapath**: tc/XDP 훅에서 패킷 처리
- **kube-proxy 대체**: socket LB + Service map (O(1))
- **CiliumNetworkPolicy (L3/L4)**: **identity(label)** + **port** 기반, 커널에서 allow/drop

</div>
<div>

```yaml
# 4주차: L3/L4 정책
egress:
- toEndpoints:
  - matchLabels:
      app: payment
  toPorts:
  - ports:
    - port: "8080"
      protocol: TCP
```

</div>
</div>

> 여기까지 정책이 보는 것은 **누가(identity) · 어디로(IP) · 어느 포트(L4)** 까지다.

<!--
복습. 4주차 정책의 정보 단위를 명확히 하자: label에서 파생된 security identity, 목적지 IP/CIDR, 그리고 L4 포트/프로토콜. 딱 여기까지다.
오른쪽 YAML은 "payment 앱으로 8080 TCP 허용" — HTTP 경로나 도메인 이름 같은 개념은 전혀 없다. 이 한계가 오늘의 출발점.
-->

---

# 그런데 이걸로 안 되는 두 가지

<div class="columns">
<div>

### ① 외부 도메인 통제
`api.github.com`만 허용하고 싶다.
그런데 CIDR로 쓰려면?
```yaml
- ipBlock:
    cidr: 140.82.121.3/32  # 내일 바뀜
```
CDN·anycast·LB 교체로 **IP가 수시로 변함** → 관리 불가

</div>
<div>

### ② 같은 포트, 다른 요청
`GET /public` 은 허용,
`POST /admin` 은 거부하고 싶다.
```text
둘 다 목적지 :80/TCP
→ L3/L4로는 구별 불가
```
포트만 봐서는 **HTTP 메서드·경로**를 알 수 없다

</div>
</div>

> ①은 **DNS/FQDN Policy**, ②는 **HTTP L7 Policy** 로 푼다. 둘 다 패킷의 **더 안쪽(payload)** 을 봐야 한다.

<!--
동기 슬라이드. 두 문제 모두 "L4 헤더만 봐서는 답이 안 나온다"는 공통점이 있다.
①은 목적지 IP가 불안정 → 이름이라는 안정적 식별자가 필요. ②는 목적지가 같아 payload를 열어봐야 함.
"더 안쪽을 봐야 한다"가 다음 파트(L1~L7)로의 다리. 여기서 자연스럽게 OSI 캡슐화 이야기로 넘어간다.
-->

---

# 기초 다지기 — 패킷은 L1~L7에서 어떻게 변하는가

정책이 "어디까지 볼 수 있나"는 곧 **패킷의 어느 껍질까지 열어보느냐**의 문제다.

```text
   보내는 쪽 (캡슐화 = 껍질을 덧씌움)         받는 쪽 (역캡슐화)
 L7 App    │ HTTP: GET /pay  {JSON body}    │  ▲  애플리케이션이 최종 소비
 L5/6 TLS  │ [TLS 암호화] 세션·암호화        │  │  복호화·세션 종료
 L4 TCP    │ [TCP hdr | payload]  포트·SEQ   │  │  재조합(reassembly)·순서보장
 L3 IP     │ [IP hdr | ...]       출발/목적 IP│  │  라우팅
 L2 Eth    │ [MAC hdr | ... | FCS] 프레임    │  │  스위칭
 L1 Wire   │ 0101010101...  전기/광 신호      │  │  비트 수신
```

각 계층은 아래로 내려갈수록 **자기 헤더를 앞에 덧붙인다(encapsulation)**. 위로 올라오며 하나씩 벗긴다.

<!--
이 슬라이드가 오늘의 기초. 캡슐화 개념을 확실히. 앱이 만든 데이터(HTTP 요청)는 아래 계층으로 내려가며 TCP 헤더, IP 헤더, Ethernet 헤더가 순서대로 앞에 붙는다. 마지막엔 전선 위 비트.
받는 쪽은 정확히 역순으로 껍질을 벗긴다. L2 벗기고 L3 벗기고 L4에서 재조합하고... L7에서 앱이 최종 HTTP 요청을 본다.
핵심 포인트를 다음 슬라이드에서: "정책 지점이 어느 계층에 있느냐가 볼 수 있는 정보를 결정한다."
-->

---

# 계층별로 "무엇이 보이는가"

| 계층 | 헤더/단위 | 그 계층에서 볼 수 있는 것 | 정책으로 쓰면 |
|---|---|---|---|
| **L3** IP | IP packet | 출발/목적지 **IP** | CIDR 허용/차단 |
| **L4** TCP/UDP | segment | **포트**, TCP flags | 포트 기반 정책 |
| **L7** HTTP | 재조합된 스트림 | **method·path·header·host** | 경로/메서드 정책 |

- L3/L4는 **헤더의 앞부분 몇 바이트**만 보면 된다 → 커널(eBPF)이 패킷 단위로 즉시 판단 가능.
- L7은 **payload 안쪽 + 여러 패킷에 걸친 스트림**을 재조합·파싱해야 한다 → 훨씬 무겁다.

> 그래서 Cilium은 **L3/L4는 eBPF(커널)**, **L7은 프록시(userspace)** 로 나눈다. 오늘의 전체 뼈대.

<!--
이 표가 "왜 계층을 나누는가"의 핵심. L3=IP만, L4=포트까지, L7=HTTP 세부까지. 깊이 볼수록 더 많은 걸 결정할 수 있지만 비용도 커진다.
결정적 차이: L3/L4는 패킷 하나의 고정 위치 헤더만 읽으면 끝. L7은 요청 하나가 여러 TCP 세그먼트에 걸칠 수 있어서 재조합이 필요하다.
이 "재조합" 한 단어가 나중에 'eBPF만으로 L7 안 되는 이유'의 핵심이 된다. 미리 씨를 뿌려둔다.
-->

---

# 큰 그림 — 오늘 등장하는 3명의 처리자

```text
        Pod가 보내는 트래픽
              │
   ┌──────────┼───────────────────────────────┐
   ▼          ▼                                ▼
 L3/L4      DNS 질의(:53)                 HTTP/gRPC (L7 규칙)
   │          │                                │
[eBPF]   [DNS Proxy]                        [Envoy]
 커널     cilium-agent 내 Go               노드당 1개 프록시
 즉시판단  이름→IP 관찰·필터                HTTP 파싱·정책
```

<div class="columns">
<div>

- **eBPF** — 커널, L3/L4 전부
- **DNS Proxy** — agent 내장 Go, *Envoy 아님*

</div>
<div>

- **Envoy** — 노드 로컬, HTTP/gRPC L7
- 대부분 트래픽은 **eBPF만** 거친다

</div>
</div>

<!--
오늘 나올 3명의 처리자를 미리 소개. 이 그림을 머릿속에 넣고 나머지를 들으면 길을 잃지 않는다.
가장 흔한 오해를 먼저 깬다: "L7이면 다 Envoy" — 아니다. DNS는 cilium-agent 안의 Go 프록시가 처리한다. Envoy를 안 쓴다. 이건 뒤에서 코드로 확인.
그리고 오른쪽 아래 — 대부분의 트래픽은 eBPF fast path로만 흐르고 Envoy를 아예 안 거친다. 이게 사이드카 모델과의 결정적 차이.
-->

---

<!-- _class: lead -->
# Part 1. DNS / FQDN Policy

이름으로 외부 접근을 통제한다

<!--
첫 번째 파트. 4개 질문 중 "DNS 기반 Policy는 어떻게 가능한가"에 답하는 구간.
-->

---

# DNS란 — 계층적 이름 해석 시스템

**이름(`api.github.com`) → IP(`140.82.121.3`)** 를 매핑하는 전 세계 분산 데이터베이스. "인터넷의 전화번호부."

<div class="columns">
<div>

### 계층 구조 (root부터 위임)
```text
. (root)
└─ com.            ← TLD
   └─ github.com.  ← authoritative
      └─ api       ← host
```
질의는 **root → TLD → authoritative** 순으로 위임되고, recursive resolver가 대신 순회한다.

</div>
<div>

### 주요 레코드 타입
| 타입 | 의미 |
|---|---|
| `A`/`AAAA` | 이름 → IPv4 / IPv6 |
| `CNAME` | 이름 → 다른 이름(별칭) |
| `NS` | 도메인 담당 네임서버 |
| `TXT` | 임의 텍스트(SPF 등) |

응답에는 **TTL**이 붙어 resolver가 그만큼 **캐시**한다.

</div>
</div>

<!--
DNS 자체를 모르는 사람은 없지만, FQDN 정책을 이해하려면 "이름 해석이 어떻게 일어나는가"를 정확히 짚어야 한다. DNS는 이름과 IP를 매핑하는 전 세계 분산 DB, 흔히 인터넷 전화번호부에 비유한다.
핵심은 계층 구조다: 맨 끝 root(.)부터 com 같은 TLD, 그 아래 도메인을 실제로 책임지는 authoritative 서버로 권한이 위임된다. 우리가 쓰는 stub resolver는 recursive resolver에게 부탁하고, recursive resolver가 root→TLD→authoritative를 순회해 답을 가져온다.
레코드 타입 중 오늘 중요한 건 A/AAAA(이름→IP). CNAME은 별칭이라 FQDN 정책에서 체인 처리가 필요하다는 점만 기억. 그리고 모든 응답에는 TTL이 붙어 캐시되는데, 이 TTL이 뒤에서 Cilium이 IP를 얼마나 오래 허용할지와 직접 연결된다.
-->

---

# FQDN이란 — 이름의 완전한 주소

**FQDN** = 루트부터 호스트까지 전부 명시한 **절대 이름**. 끝의 `.`이 root(보통 생략).

```text
api.github.com.
│   │      │  └ root ('.' 생략)
│   │      └──── TLD  (com)
│   └─────────── SLD  (github)
└─────────────── host (api)
```

<div class="columns">
<div>

### FQDN vs 상대 이름
- `api.github.com.` → **FQDN** (절대)
- `web`, `web.default` → **상대** 이름
- 상대 이름 + **search** 도메인 → FQDN

</div>
<div>

### K8s 확장 (resolv.conf)
```text
search default.svc.cluster.local …
options ndots:5
web → web.default.svc.cluster.local.
```
`ndots:5`: 점 < 5개면 search 먼저

</div>
</div>

<!--
FQDN은 "완전히 자격을 갖춘 도메인 이름", 즉 root부터 호스트까지 전부 명시된 절대 주소다. 진짜 FQDN은 끝에 root를 뜻하는 점(.)이 붙는데 일상에서는 생략한다.
구조를 왼쪽부터 보면 host(api), SLD(github), TLD(com), root(.) 순. 이렇게 완전하면 어디서 조회해도 같은 결과가 나온다.
반대로 web, web.default 같은 상대 이름은 그 자체로는 모호해서, resolv.conf의 search 도메인을 붙여 FQDN으로 확장해야 한다. K8s에서 web을 조회하면 ndots:5 규칙 때문에 search 도메인부터 붙여 web.default.svc.cluster.local.을 먼저 시도한다.
왜 이게 중요한가? Cilium FQDN 정책은 이 "이름"을 매칭 단위로 쓴다. 즉 정책의 matchName/matchPattern이 바로 이 FQDN 문자열과 비교된다. 그래서 다음 슬라이드부터는 이 이름이 실제로 IP로 바뀌는 순간을 어떻게 가로채는지 본다.
-->

---

# DNS 복습 — 이름이 IP가 되는 과정

<div class="columns">
<div>

Pod의 `/etc/resolv.conf`:
```text
nameserver 10.96.0.10   # kube-dns ClusterIP
search default.svc.cluster.local ...
options ndots:5
```
`curl api.github.com` 이면:
1. `getaddrinfo()` → DNS 질의(:53)
2. kube-dns가 IP 응답
3. 그 IP로 TCP 연결

</div>
<div>

**관찰**: 앱은 항상 **이름 → IP 변환을 먼저** 한다.

그렇다면 이 **DNS 질의를 가로채서**
- 어떤 이름을 허용할지 필터하고
- 응답으로 온 **IP를 기록**해두면?

→ 그 IP만 나중에 허용하면
**도메인 단위 통제**가 된다.

</div>
</div>

> Cilium FQDN Policy의 핵심 아이디어: *DNS 응답을 엿봐서 "허용된 이름의 IP"를 실시간으로 알아낸다.*

<!--
3주차/4주차에서 본 resolv.conf·kube-dns 경로를 짧게 복습. 핵심은 "앱이 IP로 연결하기 전에 반드시 이름을 IP로 바꾸는 DNS 단계를 거친다"는 것.
바로 이 지점이 통제 포인트다. DNS 질의를 프록시가 가로채면 (1) 허용 이름 필터링 (2) 응답 IP 수집을 동시에 할 수 있다.
아이디어 자체는 단순하다. "이름을 정책에 못 쓰니, 이름이 IP로 바뀌는 순간을 엿보자." 다음 슬라이드에서 그 프록시의 정체.
-->

---

# Cilium DNS Proxy — 정체는 Envoy가 아니다

```go
// pkg/fqdn/dnsproxy/proxy.go
// DNSProxy is a L7 proxy for DNS traffic. ... A singleton is
// always running inside cilium-agent.
type DNSProxy struct { ... }
```

- **cilium-agent 프로세스 안의 Go 구현체** (miekg/dns 계열 라이브러리). *Envoy와 무관.*
- Pod의 DNS 질의(UDP/TCP 53)를 **eBPF가 TPROXY/`sk_assign`으로 프록시에 투명 리다이렉트**.
- 프록시는 질의를 **정책으로 필터** → 허용되면 kube-dns로 forward → **응답을 관찰**.

> **흔한 오해 정정**: "L7이니까 Envoy" ❌ — HTTP/gRPC만 Envoy. **DNS·Kafka는 agent 내장 Go 프록시**가 처리한다.

<!--
이 슬라이드가 이번 파트의 가장 중요한 사실. 소스 주석을 직접 인용했다 — DNS proxy는 cilium-agent 안에서 도는 Go 싱글톤이다. Envoy가 아니다.
왜 강조하나? "Cilium L7 = Envoy"라는 일반화가 워낙 퍼져 있어서. 실제로는 DNS는 agent 내장, HTTP/gRPC만 Envoy. 이 구분이 오늘 4번 질문(Envoy 언제 필요한가)의 답과 직결된다.
리다이렉트 메커니즘은 HTTP와 공유한다(TPROXY/sk_assign) — 인프라는 공유, 처리 주체는 다르다.
-->

---

# toFQDNs 정책은 항상 "2단 구성"

```yaml
egress:
# Part A — DNS 질의를 프록시로: "어떤 이름을 관찰/허용할지"
- toEndpoints:
  - matchLabels: {k8s:k8s-app: kube-dns, k8s:io.kubernetes.pod.namespace: kube-system}
  toPorts:
  - ports: [{port: "53", protocol: ANY}]
    rules:
      dns:
      - matchPattern: "*"
# Part B — 관찰로 알아낸 IP에 대한 L3 연결 허용
- toFQDNs:
  - matchName: "api.github.com"
  toPorts:
  - ports: [{port: "443", protocol: TCP}]
```

> **Part A 없이 Part B만 쓰면 동작하지 않는다.** 프록시가 이름→IP를 못 봤으니 허용할 IP를 모른다.

<!--
FQDN 정책을 처음 쓰는 사람이 가장 많이 틀리는 지점. 반드시 두 개의 egress 규칙이 짝을 이뤄야 한다.
Part A: kube-dns로 가는 53 트래픽을 허용하면서, rules.dns로 "프록시야, 이 이름들을 관찰해"라고 지시. matchPattern "*"는 모든 이름 관찰.
Part B: toFQDNs로 "관찰된 결과 중 api.github.com의 IP만 443 허용."
Part A를 빼먹으면? DNS 질의가 프록시로 안 가니 IP 수집이 안 되고, Part B가 허용할 대상이 비어 결국 연결 실패. 실무 디버깅 1순위.
-->

---

# 이름이 허용 IP가 되기까지 — 동적 갱신

```text
Pod ──DNS 질의──→ eBPF ──TPROXY──→ DNS Proxy(Go) ──→ kube-dns
                                       │  ① rules:dns 로 이름 필터
                                       │  ② 응답 파싱: name → IP 목록
                                       │  ③ NameManager → ipcache에
                                       │     그 IP를 /32 identity로 주입
                                       │  ④ endpoint policy map 갱신
                                       ▼
Pod ←── DNS 응답 (≤100ms 지연) ────────┘
그 후: Pod ──TCP SYN(그 IP)──→ eBPF 조회 → toFQDNs 매칭 → ALLOW
```

- 응답은 **datapath 갱신이 끝난 뒤** Pod에 전달(최대 `--tofqdns-proxy-response-max-delay`, 기본 100ms).
- 갱신 완료 전에 IP를 알고 그냥 연결하면(예: `curl --resolve`) **차단**된다.

<!--
메커니즘의 핵심 흐름. 프록시가 응답을 파싱해서 name→IP를 뽑고, NameManager가 그 IP를 ipcache에 /32 identity로 넣고, endpoint policy map을 갱신한다. 그래야 Part B의 toFQDNs가 그 IP를 "허용"으로 인식.
중요한 타이밍: 프록시는 datapath 갱신이 끝날 때까지(최대 100ms) 응답을 Pod에 살짝 늦게 준다. race condition 방지. 그래서 앱이 응답 받고 바로 연결하면 이미 허용돼 있다.
반대로 DNS를 우회해서 IP를 직접 박으면(curl --resolve) 프록시가 그 이름을 못 봤으니 차단. 이게 보안상 오히려 장점.
-->

---

# matchName vs matchPattern

<div class="columns">
<div>

**matchName** — 완전 일치
```yaml
toFQDNs:
- matchName: "api.github.com"
```
- `api.github.com` ✅
- `sub.api.github.com` ❌
- `github.com` ❌

</div>
<div>

**matchPattern** — 와일드카드
```yaml
toFQDNs:
- matchPattern: "*.github.com"
```
- `api.github.com` ✅
- `gist.github.com` ✅
- `github.com` ❌ (`*`는 `.` 못 넘음)

</div>
</div>

- `*` 는 **하나의 라벨**만 대체하고 `.` 을 넘지 않는다. `github.com` 자체도 허용하려면 `matchName` 추가.
- Part A(`rules: dns`)와 Part B(`toFQDNs`)는 **같은 문법**을 쓰되 역할이 다르다: A=관찰 대상, B=연결 허용 대상.

<!--
와일드카드 규칙에서 가장 헷갈리는 것: `*`는 dot을 넘지 않는다. `*.github.com`은 서브도메인만, 루트 도메인 github.com은 별도 matchName 필요.
그리고 A와 B에서 같은 matchName/matchPattern 문법을 쓰지만 의미가 다르다는 걸 재강조: A는 "프록시가 볼 이름", B는 "실제 연결 허용할 이름". A에서 허용됐지만 B에 없으면 DNS는 성공해도 TCP는 막힌다.
-->

---

# FQDN — 운영 시 주의사항

| 함정 | 증상 / 해결 |
|---|---|
| **Part A 누락** | toFQDNs가 조용히 안 됨 → DNS 규칙 먼저 확인 |
| **musl(alpine) 이미지** | REFUSED 받으면 search 순회 중단 → `--tofqdns-dns-reject-response-code=nameError`(NXDOMAIN) |
| **클러스터 내부 IP** | `toFQDNs`는 in-cluster IP 처리 불가 → `toEndpoints`/`toServices` 사용 |
| **TTL 너무 짧음** | CDN이 TTL 30s → 잦은 갱신 → `--tofqdns-min-ttl`(기본 3600s)로 하한 |
| **agent 재시작** | 캐시 미보유 이름 일시 차단 → Standalone DNS Proxy(alpha)로 완화 |

- 캐시는 **노드 로컬**: Node A의 학습 결과는 Node A agent에만. 확인: `cilium fqdn cache list`.

<!--
실무 함정 모음. 발표에서 시간 없으면 위 두 줄(Part A 누락, musl)만 강조하고 나머지는 "슬라이드 참고".
musl 함정은 특히 악명 높다: alpine 기반 이미지가 많은데, REFUSED를 받으면 검색 도메인 순회를 멈춰서 정상 이름도 실패한 것처럼 보인다. reject code를 nameError(NXDOMAIN)로 바꾸면 순회를 계속한다.
toFQDNs는 외부용이다. 클러스터 내부는 identity 기반 toEndpoints가 정석. min-ttl은 짧은 TTL로 인한 잦은 정책 갱신·순간 차단을 막는 안전장치.
-->

---

# Hubble로 DNS 흐름 보기

```text
default/app:36657 -> kube-system/coredns:53
    L3-L4 REDIRECTED (UDP)            ← eBPF가 프록시로 우회
    to-proxy FORWARDED (UDP)
    dns-request FORWARDED (DNS Query api.github.com. A)     ← L7 이벤트
default/app:36657 <- kube-system/coredns:53
    dns-response FORWARDED (DNS Answer "140.82.121.3"
        TTL: 30 (Proxy api.github.com. A))                  ← 응답+IP
default/app:44754 -> api.github.com:443
    L3-Only FORWARDED (TCP Flags: SYN)  ← 학습된 IP로 연결 허용
```

```bash
hubble observe --protocol dns -f        # DNS 질의/응답 실시간
kubectl exec ds/cilium -- cilium fqdn cache list   # 학습된 이름→IP
```

<!--
6주차(Hubble) 예고 겸, DNS 정책이 실제로 동작하는지 확인하는 법. Hubble에서 dns-request / dns-response가 L7 이벤트로 찍힌다. 응답 라인에 실제 IP와 TTL이 보인다.
그 다음 라인 — 학습된 IP로 가는 TCP SYN이 L3-Only FORWARDED로 허용됨. 정책이 잘 붙었다는 증거.
디버깅 팁: cilium fqdn cache list로 agent가 어떤 이름을 어떤 IP로 알고 있는지 직접 볼 수 있다.
-->

---

<!-- _class: lead -->
# Part 2. HTTP / gRPC L7 Policy

같은 포트, 다른 요청을 구별한다

<!--
두 번째 파트. "HTTP Policy는 어떻게 동작하는가"에 답한다. 여기서부터 Envoy가 본격 등장.
-->

---

# HTTP Policy — toPorts에 rules.http 추가

```yaml
ingress:
- fromEndpoints:
  - matchLabels: {app: frontend}
  toPorts:
  - ports: [{port: "80", protocol: TCP}]
    rules:
      http:
      - method: "GET"
        path: "/public$"      # 나머지는 전부 403
```

| 필드 | 의미 | 생략 시 |
|---|---|---|
| `method` | POSIX 정규식 (`GET`, `POST\|PUT`) | 모든 메서드 |
| `path` | POSIX 정규식, `/`로 시작 | 모든 경로 |
| `host` / `headers` | Host 헤더 / 필수 헤더 | 무관 |

> `path`는 **부분 매칭**이다. `/public`은 `/public-admin`도 매칭 → 앵커 `^...$` 필수.

<!--
HTTP 정책 문법. 4주차 toPorts에 rules.http 블록을 얹으면 그 포트가 L7-aware가 된다. method/path/host/headers로 매칭.
가장 자주 내는 실수: path 정규식은 부분 매칭이라 /public이 /public-admin도 통과시킨다. 반드시 /public$ 또는 ^/public$로 앵커. 보안 정책에서 이거 놓치면 우회 구멍이 생긴다.
포인트: L7 위반은 조용한 drop이 아니라 HTTP 403이다 — 다음 슬라이드에서 강조.
-->

---

# gRPC Policy = HTTP/2 위의 http 규칙

gRPC는 전송이 **HTTP/2**다. 각 RPC 호출은 이렇게 매핑된다:

```text
POST  /<package>.<Service>/<Method>     Content-Type: application/grpc
```

따라서 **별도 `grpc:` 필드 없이** `http:` 규칙으로 표현한다.

```yaml
toPorts:
- ports: [{port: "50051", protocol: TCP}]
  rules:
    http:                    # gRPC도 http 규칙
    - method: "POST"
      path: "/cloudcity.DoorManager/GetName"
    - method: "POST"
      path: "/cloudcity.DoorManager/RequestMaintenance"
    # SetAccessCode 호출 → gRPC status 7 PERMISSION_DENIED
```

<!--
gRPC를 위한 특별한 문법이 따로 없다는 게 포인트. gRPC = HTTP/2이고, 메서드 호출 하나가 POST /패키지.서비스/메서드로 매핑되니, 그냥 http 규칙의 method=POST + path로 특정 RPC를 허용/차단한다.
공식 예제 DoorManager: GetName·RequestMaintenance는 허용, SetAccessCode·GetStatus는 목록에 없으니 차단. 차단 시 gRPC 클라이언트는 status 7 PERMISSION_DENIED를 받는다.
이게 방화벽 드롭과 다른 점: 클라이언트가 "타임아웃"이 아니라 "명시적 권한 거부"를 받아 디버깅이 쉽다.
-->

---

# L7 규칙은 allowlist — 위반은 drop이 아니라 거부 응답

<div class="columns">
<div>

**allowlist 의미론**
| 설정 | 동작 |
|---|---|
| `rules: {}` | L7 우회 없음(L4만) |
| `http: [{}]` | 전부 허용 + **가시성** |
| `http: [{GET /a}]` | 그것만, 나머지 403 |

하나라도 규칙을 쓰면 **매칭 안 된 요청은 거부**.

</div>
<div>

**거부 = 프로토콜 응답**
- HTTP → `403 Forbidden`
- gRPC → `PERMISSION_DENIED(7)`

패킷 드롭(타임아웃)과 달리
**의도된 거부**임이 명확 → 디버깅 유리

</div>
</div>

> 함정: 같은 포트에 **L4-only 규칙**이 따로 있으면 그게 더 넓게 허용해 L7 규칙이 무력화될 수 있다 → 규칙을 합쳐라.

<!--
L7 규칙의 두 가지 의미론을 정확히. 빈 http:[{}]는 "전부 허용하되 Hubble에 L7 flow 노출" — 순수 가시성 목적. 구체 규칙을 하나라도 넣으면 그 순간 allowlist가 되어 나머지는 403.
거부 방식이 프로토콜 응답이라는 게 Cilium L7의 장점. 드롭은 클라이언트 입장에서 네트워크 장애와 구별이 안 되지만, 403/PERMISSION_DENIED는 "정책이 막았다"가 분명.
함정: 같은 포트에 L4만 있는 규칙과 L7 규칙이 공존하면, L4 규칙이 그 포트를 통째로 허용해 L7 제약이 사실상 무효가 된다. 하나의 toPorts로 합쳐 관리.
-->

---

# HTTPS(암호화)는? — TLS Visibility

Envoy는 **평문**을 파싱해야 한다. 외부로 나가는 HTTPS는 기본적으로 내용을 못 본다.

```yaml
egress:
- toFQDNs: [{matchName: "httpbin.org"}]
  toPorts:
  - ports: [{port: "443", protocol: TCP}]
    terminatingTLS:   # Pod <-> Envoy 구간 TLS 종료 (Pod는 내부 CA 신뢰 필요)
      secret: {namespace: kube-system, name: httpbin-tls-data}
    originatingTLS:   # Envoy <-> httpbin.org 구간 TLS 재개시
      secret: {namespace: kube-system, name: tls-orig-data}
    rules:
      http: [{}]      # 이제 평문으로 HTTP 규칙 적용 가능
```

- Cilium 1.17+ : 인증서는 **SDS**로 참조 전달(중복 제거). 이전엔 inline(NPDS).

<!--
현실적 질문: "요즘 다 HTTPS인데 L7 정책이 의미 있나?" 기본적으로 암호화 트래픽은 Envoy가 내용을 못 본다.
해결책은 TLS interception. Envoy가 중간에서 Pod쪽 TLS를 종료(terminatingTLS)하고, 목적지로 새 TLS를 개시(originatingTLS). 그 사이에서 평문 HTTP를 보고 정책 적용.
대가: 클라이언트 Pod가 Cilium이 제시하는 내부 CA 인증서를 신뢰하도록 구성해야 한다(안 그러면 handshake 실패). MITM을 합법적으로 하는 것이라 신중히.
1.17+는 SDS로 인증서를 참조 전달해 메모리 낭비를 줄였다는 정도만 기억.
-->

---

<!-- _class: lead -->
# Part 3. Node-local Envoy

L7을 실제로 처리하는 프록시

<!--
세 번째 파트. Envoy가 뭔지, Cilium에서 어떻게 배치되고, eBPF가 어떻게 넘겨주는지. "Envoy는 언제 필요한가"의 본론.
-->

---

# Envoy란 — 프로그래밍 가능한 L4/L7 프록시

- Lyft가 만든 고성능 프록시(현재 CNCF 졸업, C++). Istio·Cilium·Gateway 구현체가 공유하는 **데이터 플레인**.
- **동적 설정(xDS)**: 재시작 없이 리스너·라우트·클러스터를 API로 주입 → 제어 플레인이 실시간 조종.
- 요청이 지나는 경로:

```text
Listener(수신 포트) → Filter Chain(TLS·HTTP 파서)
   → Route(host/path 매칭) → Cluster(목적지 그룹) → Endpoint(실제 Pod IP)
```

> Cilium은 사용자가 Envoy 설정을 직접 안 쓴다. **CiliumNetworkPolicy의 L7 규칙을 agent가 xDS로 번역**해 Envoy에 주입한다.

<!--
Envoy를 처음 듣는 사람도 있을 테니 짧게. 핵심은 두 가지: (1) HTTP/2·gRPC·TLS까지 이해하는 L7 프록시, (2) xDS로 동적 설정되어 제어 플레인이 실시간 조종 가능.
Istio도 이 Envoy를 쓴다. 차이는 "누가, 어디에, 몇 개" 배치하느냐 — 다음 슬라이드.
Cilium 사용자 입장에서 중요한 건: Envoy config를 손으로 안 쓴다. CiliumNetworkPolicy에 http 규칙만 쓰면 agent가 알아서 xDS로 번역해 넣어준다.
-->

---

# 핵심 차이 — Pod당이 아니라 노드당 1개

```text
[Istio Sidecar]  Pod마다 Envoy      → Pod 20개면 Envoy 20개
[Cilium]         노드당 Envoy 1개    → Pod 20개여도 Envoy 1개
```

<div class="columns">
<div>

| 모델 | Envoy 위치 | 개수 |
|---|---|---|
| Istio Sidecar | Pod마다 | Pod 수 |
| **Cilium** | **노드당** | 노드 수 |
| Istio Ambient | ns/서비스 | 워크로드군 |

</div>
<div>

- 노드 1개 Envoy 20개 → **1개**
- L7 규칙 **없는** Pod는 Envoy를 **아예 안 거침** (eBPF fast path)
- 8주차 Ambient ztunnel/waypoint와 대조

</div>
</div>

<!--
Cilium과 Istio 사이드카의 가장 큰 아키텍처 차이. 사이드카는 Pod마다 Envoy를 하나씩 주입 — Pod 20개면 Envoy 20개. Cilium은 노드당 1개 공유.
게다가 L7 정책이 없는 Pod의 트래픽은 Envoy를 아예 안 거치고 eBPF로만 흐른다. 사이드카는 정책이 없어도 무조건 통과.
이게 리소스·지연 절감의 핵심. 8주차에 Istio Ambient(ztunnel=노드당 L4, waypoint=워크로드군 L7)와 자세히 비교할 텐데, Cilium은 이 노드-공유 모델을 CNI에 통합했다는 게 차이.
-->

---

# 배포 형태 — embedded → 독립 DaemonSet

<div class="columns">
<div>

**예전 (~1.15): embedded**
```text
cilium-agent Pod
├── cilium-agent (Go)
└── envoy (서브프로세스)
```
agent 재시작 → Envoy도 재시작 → **L7 연결 끊김**

</div>
<div>

**지금 (1.16+ 기본): 독립 DS**
```text
노드
├── cilium-agent Pod
└── cilium-envoy Pod
```
agent 재시작해도 **Envoy 생존** → L7 연결 유지

</div>
</div>

- 통신은 두 모드 모두 **UNIX 도메인 소켓** (네트워크 오버헤드 없음).
- 분리 이점: 독립 lifecycle·리소스 격리·보안 격리. `--set envoy.enabled=true` (1.14+ opt-in, 1.16+ 기본).

<!--
Envoy 배포 형태의 진화. 예전엔 cilium-agent 안의 서브프로세스라, agent를 업그레이드/재시작하면 Envoy도 죽어 진행 중 L7 연결이 끊겼다(GitHub #13194).
1.14에서 독립 cilium-envoy DaemonSet 옵션이 생겼고, 1.16(2024.7)부터 신규 설치 기본값. 이제 agent를 재시작해도 Envoy는 살아있어 L7 연결이 유지된다.
두 모드 다 agent<->Envoy는 UNIX 소켓 통신이라 네트워크 비용 없음. 분리의 실익은 lifecycle·리소스·보안 격리.
-->

---

# eBPF는 어떻게 Envoy로 넘기는가

```text
Pod A ─→ tc eBPF hook (veth)
          │  이 flow에 L7 규칙 있나? (policy map 조회)
          ├─ 없음 → eBPF fast path로 직행 (Envoy 안 거침)
          └─ 있음 → skb mark = MARK_MAGIC_TO_PROXY, redirect
                     │
                     ▼  TPROXY (원래 목적지 보존) / sk_assign
              cilium-envoy (노드 로컬 리스너 :proxyPort)
                     │  BPF Metadata filter로 source Identity 전달
                     │  HTTP 파싱 → method/path/header 정책 평가
                     ├─ allow → 원래 목적지 Pod로 upstream
                     └─ deny  → 403 / PERMISSION_DENIED
                     ▼
                  Pod B
```

<!--
가장 기술적인 슬라이드. 천천히. tc eBPF 훅이 flow를 보고 policy map에서 "L7 규칙 있나?"를 조회. 없으면 그대로 fast path — Envoy 근처도 안 감.
있으면 skb에 매직 마크(MARK_MAGIC_TO_PROXY)를 찍고, TPROXY로 노드 로컬 Envoy 리스너로 투명 리다이렉트. TPROXY라서 원래 목적지 IP:port가 소켓에 보존됨.
결정적 디테일: BPF Metadata filter가 eBPF map에서 source Pod의 Cilium security identity를 읽어 Envoy에 넘긴다. 그래서 Envoy도 identity 기반으로 정책을 평가할 수 있다. 평가 후 원래 목적지로 upstream, 거부면 403.
proxyPort는 Cilium이 자동 할당 — 사용자는 신경 안 씀.
-->

---

# Envoy를 직접 태우는 길 — CiliumEnvoyConfig

- **자동 경로**: `CiliumNetworkPolicy`의 L7 규칙 → agent가 xDS로 번역 (사용자는 Envoy 몰라도 됨).
- **고급 경로**: `CiliumEnvoyConfig` / `CiliumClusterwideEnvoyConfig` CRD로 **Envoy 리소스를 직접** 정의.

```yaml
kind: CiliumEnvoyConfig
spec:
  services: [{name: my-svc, namespace: default}]
  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    # ... 라우팅·레이트리밋·서킷브레이커 등
```

> **Ingress·Gateway API도 이 노드 Envoy 위에 구현된다** (7주차 예고). L7 라우팅·TLS 종료가 전부 같은 Envoy.

<!--
Envoy를 쓰는 두 가지 층위. 대부분은 자동 경로 — 정책에 http 규칙만 쓰면 끝. 하지만 레이트 리미팅, 서킷 브레이커, 커스텀 라우팅 같은 고급 기능은 CiliumEnvoyConfig CRD로 Envoy xDS 리소스를 직접 정의할 수 있다.
그리고 중요한 연결고리: 7주차에 다룰 Cilium Ingress와 Gateway API도 내부적으로 바로 이 노드 로컬 Envoy 위에 구현된다. L7 HTTP 라우팅·TLS 종료가 전부 동일한 Envoy 인스턴스. 즉 오늘 배운 Envoy가 7주차의 토대.
-->

---

<!-- _class: lead -->
# Part 4. eBPF vs Envoy

왜 이렇게 역할을 나눴는가

<!--
마지막 파트. "eBPF만으로 가능한가", "eBPF와 Envoy의 역할 구분" — 4개 질문 중 남은 둘을 정면으로.
-->

---

# eBPF만으로 HTTP를 못 하는 이유

<div class="columns">
<div>

**eBPF의 실행 모델**
- 패킷 **1개마다** 독립 호출 (per-packet)
- 호출 간 상태 공유 없음
- verifier 제약: **bounded loop**만, **스택 512B**, 명령어 상한

</div>
<div>

**HTTP/2·gRPC의 현실**
- 요청이 **여러 TCP 세그먼트**에 걸침 → **재조합** 필요
- HTTP/2 **HPACK**: 연결 수명 내내 유지되는 동적 테이블 필요
- 스트림 **멀티플렉싱**

</div>
</div>

```text
세그먼트1: "GET /api/v1/us"   세그먼트2: "ers HTTP/1.1\r\nHost: ex"   세그먼트3: "ample..."
   → eBPF는 세그먼트1만 보고 판단해야 하는데, 요청이 아직 안 끝남
```

> 커널에서 TCP 스트림 재조합 + HTTP/2 상태기계를 구현하는 것은 verifier 제약상 비현실적.

<!--
3번 질문의 핵심. eBPF는 패킷 하나가 올 때마다 독립적으로 호출되고, 호출 사이에 상태를 안 들고 있다. 그런데 HTTP 요청은 여러 TCP 세그먼트에 쪼개져 오니 재조합이 필요하고, 그건 연결 단위 상태를 요구한다.
게다가 verifier가 무한 루프를 금지하고(종료 증명 못 하면 거부) 스택을 512바이트로 제한한다. 가변 길이 HTTP 헤더 파서를 이 제약 안에서 쓰기가 지극히 어렵다.
HTTP/2는 더하다: HPACK 헤더 압축이 연결 전체에 걸친 동적 테이블을 요구하고, 스트림이 멀티플렉싱된다. per-packet eBPF로는 이 연결 상태를 유지할 수 없다.
아래 예시 — GET /api/v1/us... 가 세 조각으로 오면 eBPF는 첫 조각만 보고 결정해야 하는데 요청이 완결되지 않았다. 이게 그림 한 장 요약.
-->

---

# Envoy는 왜 가능한가 — 그리고 DNS는 왜 예외인가

<div class="columns">
<div>

**Envoy (userspace)**
- 표준 TCP **소켓** 사용
- 커널이 **재조합한 바이트 스트림**을 `read()`
- 메모리·스택 제약 없음 → HTTP/2·HPACK 상태기계 완비

</div>
<div>

**DNS는 왜 eBPF+Go로 OK?**
- 단순 **요청-응답**, 고정 포트, 짧은 payload
- 스트림 재조합 부담 없음
- agent 내 **Go 프록시**면 충분 (Envoy 불필요)

</div>
</div>

> 결론(질문 3): **eBPF만으로는 HTTP/gRPC L7 불가.** eBPF는 *리다이렉트 판단*까지, 파싱은 userspace(Envoy). DNS는 단순해서 agent 내장 Go 프록시로 해결.

<!--
대비. Envoy는 userspace에서 평범한 TCP 소켓을 쓴다. 커널 TCP 스택이 이미 재조합·순서보장을 다 해준 바이트 스트림을 read()로 받는다. 512바이트 제약도, verifier도 없다. 그래서 완전한 HTTP/2 디코더와 HPACK 테이블을 유지할 수 있다.
그럼 DNS는 왜 Envoy 없이 되나? DNS는 프로토콜이 단순하다 — 한 번 질의, 한 번 응답, 고정 포트 53, 짧은 메시지. 스트림 재조합 부담이 없어 agent 안의 Go 프록시로 충분하다.
그래서 3번 질문 답: eBPF만으로 HTTP L7은 안 된다. eBPF는 "이 flow를 프록시로 보낼지" 판단까지만 하고, 실제 파싱은 userspace가 한다. DNS만 예외적으로 agent 내장 Go로 처리.
-->

---

# 역할 구분표 — 누가 무엇을 처리하나

| 기능 | 처리자 | 위치 |
|---|---|---|
| L3/L4 포워딩·정책, Service LB, NAT, 암호화 | **eBPF** | 커널 |
| 대부분의 관측(flow, Hubble L3/L4) | **eBPF** | 커널 |
| HTTP/gRPC method·path·header 정책 | **Envoy** | userspace / **노드당** |
| Ingress·Gateway API L7 라우팅, TLS 종료 | **Envoy** | userspace / 노드당 |
| **DNS** proxy · FQDN, Kafka(레거시) | **cilium-agent 내장 Go** | userspace / 노드당 |

> 한 문장: **커널에서 될 건 eBPF로, 프로토콜 파싱이 필요할 때만 프록시로.** L7 중에서도 DNS는 agent Go, HTTP/gRPC는 Envoy.

<!--
종합표. 4번 질문(역할 구분)의 완성. 세 명의 처리자를 다시 정리: eBPF(커널)가 L3/L4 전부 + LB + NAT + 암호화 + 대부분 관측. Envoy(노드당 userspace)가 HTTP/gRPC 정책 + Ingress/Gateway + TLS. cilium-agent 내장 Go가 DNS/Kafka.
Kafka도 DNS처럼 agent 내장 프록시지만 레거시(deprecated)라 새로 쓸 일은 없다 — 참고만.
철학 한 줄: 커널에서 처리 가능한 건 eBPF로 남기고, 프로토콜 파싱이 꼭 필요할 때만 userspace 프록시로 우회. 이 원칙이 오늘 전체를 관통한다.
-->

---

# "Envoy는 언제 필요한가" — 실제 빈도

```text
① Pod → Pod (L3/L4만)          → eBPF fast path        (Envoy X)
② Pod → Service (L4 LB)         → eBPF socket LB        (Envoy X)
③ FQDN egress 정책              → DNS proxy(agent Go)   (Envoy X)
④ HTTP/gRPC method·path 정책    → TPROXY → Envoy        (Envoy O)
⑤ Ingress / Gateway API        → TPROXY → Envoy        (Envoy O)
```

- ①②③이 클러스터 트래픽의 **대부분**. Envoy가 실제로 관여하는 건 ④⑤ — **명시적으로 L7을 쓸 때만**.
- 그래서 사이드카처럼 "모든 트래픽 × 프록시" 곱셈 비용이 없다.

> 답(질문 4): **HTTP/gRPC L7 규칙, 또는 Ingress/Gateway를 쓸 때만 Envoy가 개입한다.**

<!--
4번 질문의 실전 감각. 클러스터 트래픽을 5종으로 나누면, ①②③(순수 L3/L4, Service LB, FQDN egress)이 절대다수고 이들은 Envoy를 안 거친다. Envoy는 ④HTTP/gRPC 정책과 ⑤Ingress/Gateway에서만.
즉 실무에서 깊은 L7을 쓰는 비중은 생각보다 작고, 그럴 때만 노드 Envoy 하나를 공유해서 처리한다. "모든 Pod에 프록시" 곱셈이 없으니 비용이 선형(노드 수)이다.
이게 오늘의 실용적 결론이자, 8주차 Istio Ambient 비교의 밑밥.
-->

---

# 정리 — 4개의 질문에 답한다

| 질문 | 답 |
|---|---|
| DNS 기반 Policy는? | agent 내장 **DNS Proxy**(Go)가 질의를 엿봐 이름→IP를 학습, `toFQDNs`가 그 IP를 허용 (2단 정책) |
| HTTP Policy는? | `toPorts.rules.http`(method/path/header) → **Envoy**가 파싱·집행, 위반은 403 |
| eBPF만으로 L7? | **아니오.** per-packet·verifier·재조합 한계. eBPF는 리다이렉트까지, 파싱은 userspace |
| Envoy는 언제? | **HTTP/gRPC L7 규칙·Ingress/Gateway** 일 때만. 노드당 1개, 나머진 eBPF fast path |

> **커널에서 될 건 eBPF, 프로토콜 파싱이 필요할 때만 Envoy. DNS만 예외적으로 agent 내장 Go 프록시.**

<!--
오늘의 결론. 두 번째 슬라이드에서 던진 4개 질문에 한 줄씩 답하며 닫는다. 이 표 하나가 5주차 요약.
청중에게: 이 네 줄만 기억해도 5주차는 성공. 특히 "L7이라고 다 Envoy가 아니다 — DNS는 agent Go"와 "대부분 트래픽은 eBPF fast path"가 오늘의 두 반전.
-->

---

# 다음 주 & 우리 환경에 적용한다면

<div class="columns">
<div>

**6주차 예고 — Hubble**
- 오늘 본 dns-request / http-request L7 이벤트를 **흐름 단위로 관측**
- "왜 막혔나 / 어느 계층에서 끊겼나"

</div>
<div>

**생각해볼 것**
- 외부 API 연동에 `toFQDNs` 적용 지점?
- HTTP L7까지 갈 트래픽이 실제로 얼마나?
- HTTPS 비중 → TLS visibility 필요성?

</div>
</div>

<span class="small">참고: Cilium Docs — DNS-Based policies / Layer 7 / Envoy · cilium/cilium `pkg/fqdn` · v1.16 Release Notes</span>

<!--
마무리. 6주차 Hubble로 자연스럽게 연결 — 오늘 만든 L7 이벤트를 실제로 관측하는 주. 그리고 우리 서비스에 어떻게 적용할지 세 가지 질문을 던지며 토론 유도.
발표 끝. 질문 받기.
-->
