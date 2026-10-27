# Cilium 5주차 — DNS · FQDN · L7 Policy 와 Envoy 대본

총 발표 시간: ~27분 / 슬라이드 35장

---

## 슬라이드 1: Cilium 5주차 — DNS · FQDN · L7 Policy 와 Envoy

**예상 시간**: 25초

5주차입니다. 지난 4주 동안 우리는 Pod가 어떻게 IP를 얻는지, eBPF가 kube-proxy를 어떻게 대체하는지, 그리고 L3/L4 NetworkPolicy가 커널에서 어떻게 강제되는지까지 살펴봤습니다. 오늘은 그 "위층"을 다룹니다. 도메인 이름 기반 정책, HTTP와 gRPC를 구별하는 L7 정책, 그리고 이를 실제로 처리하는 Envoy가 오늘의 주인공입니다. 오늘 발표 전체를 한 줄로 요약하면 "eBPF는 L3/L4까지, L7은 프록시로 넘긴다 — 왜 그렇게 나눴는가"를 이해하는 것이 목표입니다.

**강조**: eBPF는 L3/L4까지, L7은 프록시(Envoy·DNS proxy)로 — 왜 나눴는가를 이해하는 것이 목표
**다음 슬라이드 연결**: "먼저 오늘 다룰 네 가지 핵심 질문부터 보겠습니다."

---

## 슬라이드 2: 오늘의 목표와 4개의 질문

**예상 시간**: 45초

오늘 슬라이드 전체는 화면에 보이는 네 가지 질문에 답하는 구조로 짜여 있습니다. 첫째, DNS 기반 Policy는 어떻게 가능한가. 둘째, HTTP Policy는 어떻게 동작하는가. 셋째, eBPF만으로 L7이 가능한가. 넷째, Envoy는 언제 필요한가. 발표가 끝나면 이 슬라이드로 다시 돌아와서 하나씩 답을 확인할 것입니다. 오른쪽 "다룰 것" 목록의 첫 항목인 L1~L7 페이로드가 변하는 방식을 나머지 전부의 기반으로서 먼저 짚고 가겠습니다.

**강조**: 4개 질문이 오늘의 뼈대 — 발표 끝에 이 슬라이드로 돌아와 하나씩 답을 확인한다
**다음 슬라이드 연결**: "그러기 위해 먼저 4주차까지 우리가 알고 있는 것을 한 번 짚고 넘어가겠습니다."

---

## 슬라이드 3: 4주차까지의 복습 — 우리가 아는 것

**예상 시간**: 40초

잠깐 복습입니다. 4주차까지 우리가 다룬 CiliumNetworkPolicy의 정보 단위를 정확히 짚어보면 — label에서 파생된 security identity, 목적지 IP나 CIDR, 그리고 L4 포트와 프로토콜, 딱 여기까지입니다. 오른쪽에 보이는 YAML은 "payment 앱으로 8080 TCP를 허용한다"는 정책인데, HTTP 경로나 도메인 이름 같은 개념은 전혀 없습니다. 이 한계가 오늘의 출발점입니다.

**강조**: 4주차 정책이 보는 것은 누가(identity) · 어디로(IP) · 어느 포트(L4)까지 — 그 이상은 없다
**다음 슬라이드 연결**: "그렇다면 이 L3/L4 정책으로는 해결이 안 되는 두 가지 문제가 있습니다."

---

## 슬라이드 4: 그런데 이걸로 안 되는 두 가지

**예상 시간**: 50초

두 가지 문제가 있습니다. 첫 번째는 외부 도메인 통제입니다. `api.github.com`만 허용하고 싶은데, CIDR로 쓰려면 IP를 하드코딩해야 합니다. 그런데 CDN이나 anycast, 로드밸런서 교체로 그 IP가 수시로 바뀌니 관리가 불가능합니다. 두 번째는 같은 포트에 다른 요청입니다. `GET /public`은 허용하고 `POST /admin`은 거부하고 싶은데, 둘 다 목적지가 80번 TCP라 L3/L4 수준에서는 구별이 안 됩니다. 이 두 문제의 공통점은 "L4 헤더만 봐서는 답이 안 나온다"는 것입니다. 패킷의 더 안쪽을 열어봐야 합니다. 첫 번째는 DNS/FQDN Policy로, 두 번째는 HTTP L7 Policy로 풉니다.

**강조**: L4 헤더만으로는 도메인도 HTTP 메서드도 구별 불가 — 패킷의 더 안쪽(payload)을 봐야 한다
**다음 슬라이드 연결**: "그 '더 안쪽'이 무슨 의미인지, OSI 계층 구조부터 짚겠습니다."

---

## 슬라이드 5: 기초 다지기 — 패킷은 L1~L7에서 어떻게 변하는가

**예상 시간**: 50초

이 슬라이드가 오늘의 기초입니다. 캡슐화 개념을 확실히 짚고 가겠습니다. 앱이 만든 HTTP 요청은 아래 계층으로 내려가면서 TCP 헤더, IP 헤더, Ethernet 헤더가 순서대로 앞에 붙고, 마지막에는 전선 위의 비트 신호가 됩니다. 받는 쪽은 정확히 역순으로 껍질을 벗깁니다. L2를 벗기고, L3를 벗기고, L4에서 재조합하고, L7에서 앱이 최종 HTTP 요청을 봅니다. 다음 슬라이드에서 핵심 포인트가 나옵니다. 정책 지점이 어느 계층에 있느냐가 볼 수 있는 정보를 결정한다는 것입니다.

**강조**: 캡슐화 — 아래로 내려가며 헤더를 덧씌우고, 위로 올라오며 하나씩 벗긴다
**다음 슬라이드 연결**: "각 계층에서 정책이 실제로 무엇을 볼 수 있는지 표로 정리해 보겠습니다."

---

## 슬라이드 6: 계층별로 "무엇이 보이는가"

**예상 시간**: 50초

표에서 확인할 수 있듯이 L3는 IP만, L4는 포트까지, L7은 HTTP method와 path, header, host까지 볼 수 있습니다. 깊이 볼수록 더 세밀한 정책을 쓸 수 있지만 비용도 그만큼 커집니다. 결정적인 차이는 이겁니다. L3/L4는 패킷 하나의 고정 위치에 있는 헤더 몇 바이트만 읽으면 끝납니다. 그래서 커널에서 eBPF가 즉시 판단할 수 있습니다. 반면 L7은 요청 하나가 여러 TCP 세그먼트에 걸쳐 올 수 있어서 재조합이 필요합니다. 이 "재조합"이라는 단어가 나중에 'eBPF만으로 L7이 안 되는 이유'의 핵심이 됩니다. 그래서 Cilium은 L3/L4는 eBPF로, L7은 userspace 프록시로 나눕니다. 이것이 오늘 전체의 뼈대입니다.

**강조**: L3/L4는 헤더 몇 바이트 → eBPF 즉시 판단; L7은 재조합 필요 → userspace 프록시
**다음 슬라이드 연결**: "이 세 역할을 맡는 처리자가 오늘 발표에서 세 번 등장합니다. 미리 소개하겠습니다."

---

## 슬라이드 7: 큰 그림 — 오늘 등장하는 3명의 처리자

**예상 시간**: 50초

이 그림을 머릿속에 넣고 나머지를 들으면 길을 잃지 않습니다. 오늘 등장하는 처리자는 세 명입니다. 첫째 eBPF, 커널에서 L3/L4 전부를 처리합니다. 둘째 DNS Proxy, cilium-agent 안에 내장된 Go 구현체로 DNS 질의를 필터하고 이름에서 IP를 관찰합니다. 여기서 가장 흔한 오해를 먼저 깨겠습니다. "L7이면 다 Envoy"라는 생각 — 아닙니다. DNS는 Envoy가 아닙니다. 셋째 Envoy, 노드당 하나짜리 프록시로 HTTP와 gRPC를 파싱하고 정책을 집행합니다. 대부분의 트래픽은 eBPF fast path로만 흐르고 Envoy를 아예 안 거칩니다. 이것이 사이드카 모델과의 결정적 차이입니다.

**강조**: "L7이면 다 Envoy"는 오해 — DNS는 agent 내장 Go 프록시, HTTP/gRPC만 Envoy
**다음 슬라이드 연결**: "그럼 첫 번째 파트, DNS와 FQDN Policy부터 시작하겠습니다."

---

## 슬라이드 8: Part 1. DNS / FQDN Policy

**예상 시간**: 20초

Part 1입니다. 네 가지 질문 중 첫 번째, "DNS 기반 Policy는 어떻게 가능한가"에 답하는 구간입니다. 이름으로 외부 접근을 통제하는 방법입니다.

**강조**: 이름으로 외부 접근을 통제한다
**다음 슬라이드 연결**: "먼저 DNS 자체가 어떻게 동작하는지 기초부터 짚겠습니다."

---

## 슬라이드 9: DNS란 — 계층적 이름 해석 시스템

**예상 시간**: 55초

DNS 자체를 모르는 분은 없겠지만, FQDN 정책을 정확히 이해하려면 이름 해석이 어떻게 일어나는가를 짚어야 합니다. DNS는 이름과 IP를 매핑하는 전 세계 분산 데이터베이스로, 흔히 인터넷 전화번호부에 비유합니다. 핵심은 계층 구조입니다. 맨 끝 root(.)부터 com 같은 TLD, 그 아래 도메인을 실제로 책임지는 authoritative 서버로 권한이 위임됩니다. 우리가 쓰는 stub resolver는 recursive resolver에게 질의를 부탁하고, recursive resolver가 root → TLD → authoritative 순으로 순회해서 답을 가져옵니다. 레코드 타입 중 오늘 중요한 것은 A와 AAAA, 이름에서 IP로의 매핑입니다. 그리고 모든 응답에는 TTL이 붙어 캐시되는데, 이 TTL이 뒤에서 Cilium이 특정 IP를 얼마나 오래 허용할지와 직접 연결됩니다.

**강조**: DNS = 계층적 이름 해석; 응답의 TTL이 Cilium IP 허용 기간과 직결된다
**다음 슬라이드 연결**: "이 DNS에서 사용하는 이름의 완전한 형태, FQDN이 무엇인지 정의해 보겠습니다."

---

## 슬라이드 10: FQDN이란 — 이름의 완전한 주소

**예상 시간**: 55초

FQDN은 Fully Qualified Domain Name, 즉 root부터 호스트까지 전부 명시된 절대 이름입니다. 진짜 FQDN은 끝에 root를 뜻하는 점(.)이 붙는데, 일상에서는 생략합니다. `api.github.com.`을 분해하면 가장 오른쪽 점이 root, 그 왼쪽이 TLD인 com, 그 왼쪽이 SLD인 github, 맨 왼쪽이 host인 api입니다. 이렇게 완전하면 어디서 조회해도 같은 결과가 나옵니다. 반대로 `web`이나 `web.default` 같은 상대 이름은 그 자체로 모호해서 resolv.conf의 search 도메인을 붙여 FQDN으로 확장해야 합니다. K8s에서 `web`을 조회하면 ndots:5 규칙 때문에 search 도메인을 먼저 붙여 `web.default.svc.cluster.local.`을 먼저 시도합니다. 왜 이것이 중요한가 — Cilium FQDN 정책의 `matchName`과 `matchPattern`이 바로 이 FQDN 문자열과 비교됩니다. 다음 슬라이드부터는 이 이름이 실제로 IP로 바뀌는 순간을 어떻게 가로채는지 봅니다.

**강조**: FQDN = root부터 전부 명시된 절대 이름 — matchName/matchPattern이 이 문자열과 비교
**다음 슬라이드 연결**: "그럼 Pod 안에서 이름이 IP로 바뀌는 과정을 따라가 보겠습니다."

---

## 슬라이드 11: DNS 복습 — 이름이 IP가 되는 과정

**예상 시간**: 50초

이전 주차에서 본 DNS 경로를 짧게 복습합니다. Pod의 `/etc/resolv.conf`를 보면 nameserver로 kube-dns ClusterIP가 잡혀 있습니다. 앱이 `curl api.github.com`을 실행하면 먼저 `getaddrinfo()`가 DNS 질의를 53번 포트로 보내고, kube-dns가 IP를 응답하고, 그제야 그 IP로 TCP 연결을 맺습니다. 핵심은 앱이 IP로 연결하기 전에 반드시 이름을 IP로 바꾸는 DNS 단계를 거친다는 것입니다. 바로 이 지점이 통제 포인트입니다. DNS 질의를 프록시가 가로채면 허용할 이름을 필터링하는 동시에 응답으로 온 IP를 수집할 수 있습니다. "이름을 정책에 못 쓰니, 이름이 IP로 바뀌는 순간을 엿보자." 그 프록시의 정체를 다음 슬라이드에서 확인합니다.

**강조**: 앱은 반드시 이름→IP 변환을 먼저 한다 — 그 DNS 단계가 Cilium의 통제 포인트
**다음 슬라이드 연결**: "그 DNS 질의를 가로채는 프록시의 정체, 바로 확인해 보겠습니다."

---

## 슬라이드 12: Cilium DNS Proxy — 정체는 Envoy가 아니다

**예상 시간**: 60초

이 슬라이드가 이번 파트에서 가장 중요한 사실입니다. 화면의 소스 주석을 직접 보면 `pkg/fqdn/dnsproxy/proxy.go`에 "DNSProxy is a L7 proxy for DNS traffic. A singleton is always running inside cilium-agent"라고 나와 있습니다. cilium-agent 프로세스 안에서 돌아가는 Go 싱글톤입니다. Envoy와 무관합니다. 왜 이것을 강조하냐면 "Cilium L7은 Envoy"라는 일반화가 워낙 퍼져 있기 때문입니다. 실제로는 DNS는 agent 내장 Go 프록시가 처리하고, HTTP와 gRPC만 Envoy가 처리합니다. Pod의 DNS 질의는 eBPF가 TPROXY 또는 `sk_assign`으로 이 프록시에 투명하게 리다이렉트합니다. 리다이렉트 인프라는 HTTP와 공유하지만, 처리 주체는 다릅니다.

**강조**: Cilium DNS Proxy = cilium-agent 내장 Go 싱글톤, Envoy 아님 — "L7이면 Envoy"는 오해
**다음 슬라이드 연결**: "그럼 이 DNS Proxy를 활용하는 toFQDNs 정책이 어떻게 구성되는지 보겠습니다."

---

## 슬라이드 13: toFQDNs 정책은 항상 "2단 구성"

**예상 시간**: 65초

toFQDNs 정책을 처음 쓰는 분들이 가장 많이 틀리는 지점입니다. 반드시 두 개의 egress 규칙이 짝을 이뤄야 합니다. YAML을 보면 Part A와 Part B가 있습니다. Part A는 kube-dns로 가는 53번 트래픽을 허용하면서 `rules.dns`로 "프록시야, 이 이름들을 관찰해"라고 지시하는 역할입니다. `matchPattern: "*"`는 모든 이름을 관찰하겠다는 뜻입니다. Part B는 `toFQDNs`로 "관찰된 결과 중 `api.github.com`의 IP만 443으로 허용"합니다. Part A를 빼먹으면 어떻게 될까요? DNS 질의가 프록시로 안 가서 IP 수집이 안 되고, Part B가 허용할 대상이 비어 결국 연결에 실패합니다. 실무 디버깅에서 1순위로 확인해야 하는 사항입니다.

**강조**: toFQDNs는 반드시 Part A(rules:dns) + Part B(toFQDNs) 2단 구성 — A 없이 B만 쓰면 동작 안 함
**다음 슬라이드 연결**: "이 두 규칙이 어떻게 협력해서 동적으로 IP를 허용하는지 흐름을 따라가 보겠습니다."

---

## 슬라이드 14: 이름이 허용 IP가 되기까지 — 동적 갱신

**예상 시간**: 55초

흐름을 따라가 보겠습니다. Pod에서 DNS 질의가 나오면 eBPF가 TPROXY로 DNS Proxy에 리다이렉트합니다. 프록시는 `rules.dns` 필터로 이름을 확인하고, 허용된 이름이면 kube-dns로 포워드합니다. 응답이 오면 프록시가 응답을 파싱해서 이름에서 IP 목록을 뽑아냅니다. 그리고 NameManager를 통해 그 IP를 ipcache에 /32 identity로 주입하고, endpoint policy map을 갱신합니다. 그래야 Part B의 `toFQDNs` 규칙이 그 IP를 허용으로 인식할 수 있습니다. 중요한 타이밍 문제가 있습니다. 프록시는 datapath 갱신이 끝날 때까지 최대 100ms 동안 응답을 Pod에 늦게 전달합니다. race condition을 방지하기 위해서입니다. 반대로 DNS를 우회해서 IP를 직접 지정하면 프록시가 그 이름을 못 봤으니 차단됩니다. 이것이 보안상 오히려 장점입니다.

**강조**: DNS 응답 → NameManager → ipcache /32 identity 주입 → policy map 갱신 → 그제야 TCP 허용
**다음 슬라이드 연결**: "이름을 지정하는 방법에는 matchName과 matchPattern 두 가지가 있는데, 차이를 보겠습니다."

---

## 슬라이드 15: matchName vs matchPattern

**예상 시간**: 50초

와일드카드 규칙에서 가장 많이 헷갈리는 부분입니다. `matchName`은 완전 일치입니다. `api.github.com`을 적으면 그 이름만 매칭되고, `sub.api.github.com`이나 `github.com`은 매칭되지 않습니다. `matchPattern`은 와일드카드 매칭인데, 핵심은 별표(`*`)가 점(`.`)을 넘지 않는다는 것입니다. `*.github.com`은 `api.github.com`이나 `gist.github.com`은 허용하지만, `github.com` 자체는 허용하지 않습니다. 루트 도메인도 허용하려면 `matchName: "github.com"`을 별도로 추가해야 합니다. 그리고 Part A와 Part B에서 같은 문법을 쓰지만 역할이 다릅니다. A는 "프록시가 관찰할 이름"이고, B는 "실제 TCP 연결을 허용할 이름"입니다. A에서 허용됐지만 B에 없으면 DNS 질의는 성공해도 TCP 연결은 막힙니다.

**강조**: `*`는 점(.)을 넘지 않는다 — `*.github.com`은 루트 도메인 불포함, matchName 별도 필요
**다음 슬라이드 연결**: "실제 운영에서 조심해야 할 함정들을 정리해 보겠습니다."

---

## 슬라이드 16: FQDN — 운영 시 주의사항

**예상 시간**: 45초

실무에서 만나는 함정을 빠르게 정리합니다. 첫째, Part A 누락 — toFQDNs가 조용히 실패하면 Part A의 DNS 규칙부터 확인하세요. 둘째, musl alpine 이미지 — 프록시가 REFUSED를 반환하면 musl libc는 search 도메인 순회를 멈춰 정상 이름도 실패한 것처럼 보입니다. `--tofqdns-dns-reject-response-code=nameError`로 NXDOMAIN을 반환하면 순회가 계속됩니다. 셋째, `toFQDNs`는 클러스터 내부 IP에 쓸 수 없습니다. 내부 서비스에는 `toEndpoints`나 `toServices`를 쓰세요. 넷째, TTL이 짧으면 `--tofqdns-min-ttl`로 하한을 걸어 두면 됩니다. DNS 캐시는 노드 로컬이고 `cilium fqdn cache list`로 직접 확인할 수 있습니다.

**강조**: Part A 누락 · musl REFUSED가 운영 1·2순위 함정 — toFQDNs는 외부 서비스 전용
**다음 슬라이드 연결**: "이 모든 흐름을 Hubble로 어떻게 관측하는지 보겠습니다."

---

## 슬라이드 17: Hubble로 DNS 흐름 보기

**예상 시간**: 45초

이 슬라이드는 6주차 Hubble 발표 예고를 겸합니다. DNS 정책이 실제로 동작하는지 확인하는 방법입니다. 화면의 출력을 보면 먼저 eBPF가 DNS 패킷을 프록시로 리다이렉트한 것이 `L3-L4 REDIRECTED`로 찍힙니다. 그다음 `dns-request FORWARDED`와 `dns-response FORWARDED`가 L7 이벤트로 나타나는데, 응답 라인에 실제 IP와 TTL이 보입니다. 그 아래 줄에서 학습된 IP로 향하는 TCP SYN이 `L3-Only FORWARDED`로 허용됩니다. 정책이 잘 붙었다는 증거입니다. `cilium fqdn cache list`를 실행하면 agent가 어떤 이름을 어떤 IP로 학습했는지 직접 확인할 수 있습니다.

**강조**: Hubble에서 dns-request → dns-response → TCP SYN FORWARDED 세 줄로 FQDN 정책 동작 확인
**다음 슬라이드 연결**: "이제 두 번째 파트, 같은 포트를 쓰는 HTTP 요청을 어떻게 구별하는지 보겠습니다."

---

## 슬라이드 18: Part 2. HTTP / gRPC L7 Policy

**예상 시간**: 20초

Part 2입니다. "HTTP Policy는 어떻게 동작하는가"에 답하는 구간이고, 여기서부터 Envoy가 본격적으로 등장합니다.

**강조**: 같은 포트, 다른 요청을 구별한다 — Envoy 본격 등장
**다음 슬라이드 연결**: "HTTP 정책을 어떻게 작성하는지 YAML로 바로 보겠습니다."

---

## 슬라이드 19: HTTP Policy — toPorts에 rules.http 추가

**예상 시간**: 55초

4주차에서 배운 `toPorts`에 `rules.http` 블록을 얹으면 그 포트가 L7-aware가 됩니다. YAML을 보면 80번 TCP 포트에 `method: GET`, `path: /public$`를 지정해서 GET /public만 허용하고, 나머지는 모두 403을 반환하도록 합니다. 매칭 필드는 method, path, host, headers가 있고, 각각 생략하면 그 필드는 모든 값을 허용합니다. 여기서 가장 자주 내는 실수 하나 — path 정규식은 부분 매칭입니다. `/public`이라고 쓰면 `/public-admin`도 통과됩니다. 반드시 `^/public$` 또는 `/public$`처럼 앵커를 달아야 합니다. 보안 정책에서 이것을 놓치면 우회 구멍이 생깁니다. L7 위반은 조용한 패킷 드롭이 아니라 HTTP 403 응답이라는 점도 다음 슬라이드에서 강조하겠습니다.

**강조**: path 정규식은 부분 매칭 — `/public`이 `/public-admin`도 통과시킨다, 반드시 앵커 필요
**다음 슬라이드 연결**: "gRPC는 전송이 HTTP/2이기 때문에 별도 문법 없이 http 규칙으로 표현할 수 있습니다."

---

## 슬라이드 20: gRPC Policy = HTTP/2 위의 http 규칙

**예상 시간**: 55초

gRPC를 위한 별도의 `grpc:` 문법은 없습니다. gRPC의 전송이 HTTP/2이기 때문입니다. 각 RPC 호출은 `POST /<패키지>.<서비스>/<메서드>` 형태로 HTTP/2 요청에 매핑됩니다. 따라서 그냥 `http:` 규칙에 `method: POST`와 path로 특정 RPC를 허용하거나 차단하면 됩니다. 화면의 공식 예제에서 `DoorManager`의 `GetName`과 `RequestMaintenance`는 허용하고, `SetAccessCode`는 목록에 없으니 차단됩니다. 차단 시 gRPC 클라이언트는 status 7 `PERMISSION_DENIED`를 받습니다. 이것이 기존 방화벽 드롭과 다른 점입니다. 클라이언트가 타임아웃이 아니라 명시적 권한 거부를 받아 디버깅이 훨씬 쉽습니다.

**강조**: gRPC = HTTP/2, 별도 문법 없이 http 규칙으로 표현 — 차단 시 PERMISSION_DENIED(status 7) 반환
**다음 슬라이드 연결**: "L7 규칙의 allowlist 의미론과 거부 방식을 더 정확히 정리해 보겠습니다."

---

## 슬라이드 21: L7 규칙은 allowlist — 위반은 drop이 아니라 거부 응답

**예상 시간**: 55초

L7 규칙의 의미론을 정확하게 짚겠습니다. `rules: {}` 처럼 http 키가 없으면 L7 우회 자체가 없고 L4 판단만 합니다. `http: [{}]` 처럼 빈 객체 하나를 넣으면 모든 HTTP를 허용하되 Hubble에 L7 flow가 노출됩니다. 순수 가시성 목적의 패턴입니다. 구체적인 규칙을 하나라도 넣으면 그 순간 allowlist가 되어 매칭 안 된 요청은 전부 403입니다. 거부 방식이 프로토콜 응답이라는 것이 Cilium L7의 장점입니다. 패킷 드롭은 클라이언트 입장에서 네트워크 장애와 구별이 안 되지만, 403이나 PERMISSION_DENIED는 "정책이 막았다"가 분명합니다. 한 가지 함정이 있습니다. 같은 포트에 L4-only 규칙이 따로 있으면 그것이 더 넓게 허용해서 L7 규칙이 무력화될 수 있습니다. 하나의 `toPorts`로 합쳐서 관리하세요.

**강조**: L7 규칙은 allowlist — 규칙 하나라도 있으면 나머지는 403; 거부는 드롭 아닌 프로토콜 응답
**다음 슬라이드 연결**: "그런데 실제 서비스는 HTTPS를 쓰는데, 암호화된 트래픽에도 L7 정책을 적용할 수 있을까요?"

---

## 슬라이드 22: HTTPS(암호화)는? — TLS Visibility

**예상 시간**: 50초

현실적인 질문입니다. "요즘 다 HTTPS인데 L7 정책이 의미 있나?" 기본적으로 암호화된 트래픽은 Envoy가 내용을 볼 수 없습니다. 해결책은 TLS interception입니다. YAML에서 `terminatingTLS`와 `originatingTLS`를 함께 씁니다. Envoy가 Pod 쪽의 TLS를 종료하고, 목적지로 새 TLS 연결을 개시하여, 그 사이에서 평문 HTTP를 보고 정책을 적용합니다. 대가가 있습니다. 클라이언트 Pod가 Cilium이 제시하는 내부 CA 인증서를 신뢰하도록 구성해야 합니다. 그렇지 않으면 TLS handshake가 실패합니다. 사실상 합법적인 MITM이라 신중하게 사용해야 합니다. Cilium 1.17부터는 인증서를 SDS 방식으로 참조 전달해서 메모리 낭비를 줄였다는 점도 알아두세요.

**강조**: HTTPS는 기본 불가 — terminatingTLS + originatingTLS로 TLS interception, 단 클라이언트 CA 신뢰 필요
**다음 슬라이드 연결**: "이 HTTP와 gRPC 정책을 실제로 집행하는 Envoy를 이제 본격적으로 살펴보겠습니다."

---

## 슬라이드 23: Part 3. Node-local Envoy

**예상 시간**: 20초

Part 3입니다. Envoy가 무엇인지, Cilium에서 어떻게 배치되고 eBPF가 어떻게 트래픽을 넘겨주는지 살펴봅니다. "Envoy는 언제 필요한가"의 본론입니다.

**강조**: L7을 실제로 처리하는 프록시 — Envoy 본론
**다음 슬라이드 연결**: "먼저 Envoy 자체가 무엇인지 간단히 짚겠습니다."

---

## 슬라이드 24: Envoy란 — 프로그래밍 가능한 L4/L7 프록시

**예상 시간**: 50초

Envoy는 Lyft가 만들고 현재 CNCF 졸업 프로젝트로 C++로 작성된 고성능 L4/L7 프록시입니다. Istio와 Cilium이 공유하는 데이터 플레인이기도 합니다. 핵심은 두 가지입니다. 첫째, HTTP/2와 gRPC, TLS까지 이해하는 L7 프록시입니다. 둘째, xDS API로 동적 설정되어 제어 플레인이 재시작 없이 실시간으로 리스너, 라우트, 클러스터를 주입할 수 있습니다. Cilium 사용자 입장에서 중요한 것은 Envoy 설정을 직접 쓸 필요가 없다는 점입니다. CiliumNetworkPolicy에 http 규칙만 쓰면 agent가 알아서 xDS로 번역해서 Envoy에 넣어줍니다.

**강조**: Envoy = HTTP/2·gRPC·TLS 이해 + xDS 동적 설정 — CiliumNetworkPolicy가 자동 번역
**다음 슬라이드 연결**: "Cilium이 Envoy를 배치하는 방식이 Istio와 근본적으로 다릅니다."

---

## 슬라이드 25: 핵심 차이 — Pod당이 아니라 노드당 1개

**예상 시간**: 55초

Cilium과 Istio 사이드카의 가장 큰 아키텍처 차이입니다. Istio 사이드카 모델은 Pod마다 Envoy를 하나씩 주입합니다. Pod 20개면 Envoy 20개입니다. Cilium은 노드당 Envoy 하나를 공유합니다. Pod 20개여도 Envoy는 1개입니다. 게다가 Cilium에서는 L7 정책이 없는 Pod의 트래픽은 Envoy를 아예 안 거치고 eBPF fast path로만 흐릅니다. 사이드카는 정책이 없어도 무조건 Envoy를 통과합니다. 이것이 리소스와 지연 절감의 핵심입니다. 8주차에 Istio Ambient — ztunnel이 노드당 L4, waypoint가 워크로드군 L7 — 와 자세히 비교할 텐데, Cilium은 이 노드-공유 모델을 CNI 레이어에 통합했다는 점이 차이입니다.

**강조**: Cilium = 노드당 Envoy 1개 + L7 정책 없는 트래픽은 Envoy 우회 — 사이드카의 N배 곱셈 없음
**다음 슬라이드 연결**: "이 Envoy가 어떻게 배포되어 왔는지 배포 형태의 진화를 보겠습니다."

---

## 슬라이드 26: 배포 형태 — embedded → 독립 DaemonSet

**예상 시간**: 55초

Envoy 배포 형태의 진화입니다. 1.15 이전에는 Envoy가 cilium-agent Pod 안의 서브프로세스로 실행됐습니다. 이렇게 하면 agent를 업그레이드하거나 재시작할 때 Envoy도 함께 죽어서 진행 중인 모든 L7 연결이 끊기는 문제가 있었습니다. 1.14에서 독립적인 `cilium-envoy` DaemonSet 옵션이 생겼고, 1.16부터 신규 설치의 기본값이 되었습니다. 이제 agent를 재시작해도 Envoy는 살아있어 L7 연결이 유지됩니다. 두 모드 모두 agent와 Envoy 사이의 통신은 UNIX 도메인 소켓으로 이루어져 네트워크 오버헤드가 없습니다. 분리의 실익은 lifecycle 독립, 리소스 격리, 보안 격리입니다.

**강조**: 1.16+에서 cilium-envoy 독립 DaemonSet이 기본 — agent 재시작해도 L7 연결 유지
**다음 슬라이드 연결**: "그럼 eBPF가 실제로 어떻게 트래픽을 Envoy로 넘기는지 메커니즘을 보겠습니다."

---

## 슬라이드 27: eBPF는 어떻게 Envoy로 넘기는가

**예상 시간**: 65초

오늘 가장 기술적인 슬라이드입니다. 천천히 보겠습니다. Pod A에서 패킷이 나오면 veth의 tc eBPF 훅이 호출됩니다. 이 훅이 policy map을 조회해서 "이 flow에 L7 규칙이 있나?"를 확인합니다. L7 규칙이 없으면 그냥 eBPF fast path로 직행합니다. Envoy 근처도 안 갑니다. L7 규칙이 있으면 패킷의 skb에 `MARK_MAGIC_TO_PROXY` 매직 마크를 찍고, TPROXY로 노드 로컬 Envoy의 리스너 포트로 투명하게 리다이렉트합니다. TPROXY이기 때문에 원래 목적지 IP와 포트가 소켓에 보존됩니다. 결정적인 디테일이 있습니다. BPF Metadata filter가 eBPF map에서 source Pod의 Cilium security identity를 읽어 Envoy에 전달합니다. 그래서 Envoy도 identity 기반으로 정책을 평가할 수 있습니다. 평가 후 허용이면 원래 목적지로 upstream하고, 거부면 403을 반환합니다.

**강조**: tc eBPF → L7 규칙 있을 때만 TPROXY로 Envoy 리다이렉트 — BPF Metadata filter로 security identity 전달
**다음 슬라이드 연결**: "CiliumNetworkPolicy 외에 Envoy를 더 직접적으로 제어하는 방법도 있습니다."

---

## 슬라이드 28: Envoy를 직접 태우는 길 — CiliumEnvoyConfig

**예상 시간**: 45초

Envoy를 쓰는 경로가 두 가지 있습니다. 대부분의 경우는 자동 경로입니다. CiliumNetworkPolicy에 http 규칙만 쓰면 agent가 알아서 xDS로 번역해 Envoy에 주입합니다. 레이트 리미팅, 서킷 브레이커, 커스텀 라우팅 같은 고급 기능이 필요하다면 `CiliumEnvoyConfig` CRD로 Envoy xDS 리소스를 직접 정의할 수 있습니다. 그리고 중요한 연결고리가 있습니다. 7주차에 다룰 Cilium Ingress와 Gateway API도 내부적으로 바로 이 노드 로컬 Envoy 위에 구현됩니다. 오늘 배운 Envoy가 7주차의 토대가 됩니다.

**강조**: CiliumNetworkPolicy → agent xDS 자동 번역이 기본; 고급 기능은 CiliumEnvoyConfig CRD로 직접 정의
**다음 슬라이드 연결**: "마지막 파트에서 eBPF와 Envoy의 역할을 왜 이렇게 나눴는지 정면으로 다뤄보겠습니다."

---

## 슬라이드 29: Part 4. eBPF vs Envoy

**예상 시간**: 20초

Part 4, 마지막 파트입니다. "eBPF만으로 L7이 가능한가"와 "eBPF와 Envoy의 역할 구분"을 정면으로 다룹니다. 남은 두 질문의 답입니다.

**강조**: 왜 이렇게 역할을 나눴는가 — 마지막 두 질문의 답
**다음 슬라이드 연결**: "eBPF만으로 HTTP를 처리하지 못하는 이유를 근본부터 보겠습니다."

---

## 슬라이드 30: eBPF만으로 HTTP를 못 하는 이유

**예상 시간**: 60초

세 번째 질문의 핵심입니다. eBPF의 실행 모델부터 보면 — tc 훅이나 XDP 훅에 붙은 eBPF 프로그램은 패킷 하나가 올 때마다 독립적으로 호출됩니다. 호출과 호출 사이에 상태를 공유하지 않습니다. 그런데 HTTP 요청은 여러 TCP 세그먼트에 쪼개져서 옵니다. 화면의 예시처럼 첫 번째 조각만 보고 결정해야 하는데, 요청이 아직 완결되지 않았습니다. TCP 재조합은 연결 단위 상태를 요구합니다. 게다가 verifier 제약이 있습니다. bounded loop만 허용하고, 스택은 512바이트로 제한됩니다. HTTP/2는 더합니다. HPACK 헤더 압축이 연결 전체 수명에 걸친 동적 테이블을 요구하고 스트림이 멀티플렉싱됩니다. per-packet eBPF로는 이 연결 상태를 유지할 수 없습니다.

**강조**: eBPF는 per-packet 호출·상태 없음 → TCP 재조합 불가; verifier 512B 스택·bounded loop 제약
**다음 슬라이드 연결**: "그럼 Envoy는 왜 가능하고, DNS는 왜 예외가 될 수 있는지 비교해 보겠습니다."

---

## 슬라이드 31: Envoy는 왜 가능한가 — 그리고 DNS는 왜 예외인가

**예상 시간**: 60초

대비를 보겠습니다. Envoy는 userspace에서 표준 TCP 소켓 API를 사용합니다. 커널 TCP 스택이 이미 재조합과 순서 보장을 다 처리해준 byte stream을 `read()`로 받습니다. 512바이트 스택 제약도 없고 verifier도 없습니다. 그래서 완전한 HTTP/2 디코더와 HPACK 동적 테이블을 유지할 수 있습니다. 그럼 DNS는 왜 Envoy 없이 가능할까요? DNS 프로토콜이 단순하기 때문입니다. 한 번 질의하고 한 번 응답하며, 포트는 고정 53번이고 메시지가 짧습니다. 스트림 재조합 부담이 없어서 agent 안의 Go 프록시로 충분합니다. 따라서 세 번째 질문의 답은 이렇습니다. eBPF만으로 HTTP/gRPC L7은 안 됩니다. eBPF는 "이 flow를 프록시로 보낼지" 판단까지만 하고, 실제 파싱은 userspace가 합니다. DNS만 예외적으로 agent 내장 Go로 처리합니다.

**강조**: Envoy = 커널이 재조합한 byte stream을 read() — 제약 없음; DNS는 단순 req-res라 Go proxy로 충분
**다음 슬라이드 연결**: "세 처리자의 역할을 한 표에 종합해 보겠습니다."

---

## 슬라이드 32: 역할 구분표 — 누가 무엇을 처리하나

**예상 시간**: 55초

네 번째 질문의 완성입니다. 표에서 보면 L3/L4 포워딩과 정책, Service LB, NAT, 암호화, 대부분의 관측은 모두 eBPF, 즉 커널이 처리합니다. HTTP와 gRPC의 method·path·header 정책, Ingress와 Gateway API의 L7 라우팅, TLS 종료는 Envoy, userspace의 노드당 1개짜리 프록시가 처리합니다. DNS proxy와 FQDN 엔진, 그리고 Kafka는 cilium-agent 내장 Go가 처리합니다. Kafka는 DNS처럼 agent 내장 프록시지만 deprecated이라서 새로 쓸 일은 없습니다. 철학을 한 줄로 요약하면 "커널에서 될 건 eBPF로, 프로토콜 파싱이 필요할 때만 프록시로." 이 원칙이 오늘 전체를 관통합니다.

**강조**: 커널에서 될 건 eBPF, 프로토콜 파싱 필요할 때만 프록시 — L7 중에서도 DNS는 Go, HTTP/gRPC는 Envoy
**다음 슬라이드 연결**: "그럼 실제 클러스터에서 Envoy가 개입하는 빈도를 보겠습니다."

---

## 슬라이드 33: "Envoy는 언제 필요한가" — 실제 빈도

**예상 시간**: 50초

네 번째 질문의 실전 감각입니다. 클러스터 트래픽을 다섯 종류로 나눠보면 — 첫째 Pod-to-Pod L3/L4만, 둘째 Pod-to-Service L4 LB, 셋째 FQDN egress 정책. 이 세 가지는 Envoy를 안 거칩니다. 클러스터 트래픽의 절대다수입니다. 넷째 HTTP/gRPC method·path 정책이 있는 트래픽, 다섯째 Ingress와 Gateway API 트래픽만 TPROXY를 거쳐 Envoy로 갑니다. 실무에서 깊은 L7을 쓰는 비중은 생각보다 작고, 그럴 때만 노드의 Envoy 하나를 공유해서 처리합니다. "모든 Pod에 프록시"라는 곱셈이 없으니 비용이 노드 수에 선형적입니다. 이것이 오늘의 실용적 결론이자 8주차 Istio Ambient 비교의 밑밥입니다.

**강조**: Envoy 개입은 ④HTTP/gRPC L7 규칙 + ⑤Ingress/Gateway에서만 — 나머지는 eBPF fast path
**다음 슬라이드 연결**: "처음 던진 네 가지 질문으로 돌아가서 답을 확인해 보겠습니다."

---

## 슬라이드 34: 정리 — 4개의 질문에 답한다

**예상 시간**: 55초

두 번째 슬라이드에서 던진 네 가지 질문으로 돌아왔습니다. 하나씩 답하겠습니다. 첫째, DNS 기반 Policy는 어떻게 가능한가 — agent 내장 DNS Proxy인 Go 프록시가 DNS 질의를 엿봐서 이름과 IP의 매핑을 학습하고, `toFQDNs`가 그 IP를 허용합니다. 반드시 2단 정책이 필요합니다. 둘째, HTTP Policy는 어떻게 동작하는가 — `toPorts.rules.http`로 method와 path, header를 지정하면 Envoy가 파싱하고 집행하며, 위반은 403입니다. 셋째, eBPF만으로 L7이 가능한가 — 아닙니다. per-packet 실행과 verifier 제약, 재조합 불가라는 한계로 eBPF는 리다이렉트 판단까지만 하고 파싱은 userspace가 합니다. 넷째, Envoy는 언제 필요한가 — HTTP/gRPC L7 규칙과 Ingress, Gateway를 쓸 때만, 노드당 1개가 관여합니다. 특히 "L7이라고 다 Envoy가 아니다, DNS는 agent Go"와 "대부분 트래픽은 eBPF fast path"가 오늘의 두 가지 반전입니다.

**강조**: 5주차 핵심 — DNS는 agent Go, HTTP는 Envoy, eBPF는 리다이렉트까지, Envoy는 L7만 개입
**다음 슬라이드 연결**: "마지막으로 다음 주 예고와 우리 환경에 적용할 때 생각해볼 것들을 짚겠습니다."

---

## 슬라이드 35: 다음 주 & 우리 환경에 적용한다면

**예상 시간**: 35초

마무리입니다. 6주차는 Hubble입니다. 오늘 보았던 `dns-request`, `http-request` 같은 L7 이벤트를 흐름 단위로 실제로 관측합니다. "왜 막혔는가, 어느 계층에서 끊겼는가"를 직접 보는 주입니다. 우리 환경에 적용한다면 외부 API 연동에 `toFQDNs`를 어디에 적용할지, HTTP L7 규칙까지 갈 트래픽이 실제로 얼마나 되는지, 그리고 HTTPS 비중을 생각하면 TLS visibility가 필요한지를 생각해보세요. 이상으로 발표를 마칩니다. 질문 받겠습니다.

**강조**: 6주차 Hubble에서 L7 이벤트를 직접 관측 — 오늘 배운 DNS/HTTP 정책의 실제 흐름 확인
**다음 슬라이드 연결**: "이상으로 발표를 마칩니다. 질문 있으시면 받겠습니다."
