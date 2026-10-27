# mTLS · TLS · Envoy TLS 종료 — 심층 노트

## 핵심 메시지

> **L7 가시성과 종단간 암호화는 동시에 성립하지 않는다.**
>
> L7 판단(`method`, `path`, header)은 평문 없이는 정의 자체가 불가능하다. 따라서 L7 정책을 켜는 것은 곧 경로 어딘가에 **의도적으로 중간자를 세우는 것**이다. 설계 선택지는 딜레마를 없애는 것이 아니라 세 축을 최소화하는 것뿐이다 — *평문을 **누가** 쥐는가 · **얼마나 오래** 쥐는가 · **얼마나 멀리** 옮기는가.*

이 노트는 `slides.md` / `slides.pdf` / `slides.pptx` 발표의 보충 자료다. 슬라이드가 "순서"를 그렸다면, 이 문서는 각 단계에서 정확히 무엇이 노출되고 무엇을 지불하는지를 파고든다. 5주차 `week5-dns-fqdn-l7-envoy/`의 "eBPF는 L3/L4, L7은 프록시" 경계선이 **왜 거기에 그어졌는지**에 대한 답이기도 하다.

## 산출물 지도

| 파일 | 용도 | 대응 |
|---|---|---|
| `slides.md` | Marp 소스 (단일 진실의 원천). 25장, 슬라이드별 `<!-- -->` 발표자 노트 포함 | — |
| `slides.html` | 브라우저용 인터랙티브 덱 (← → 이동) | Part I~VI 전체 |
| `slides.pdf` | PDF, 발표자 노트를 annotation으로 포함(`--pdf-notes`) | 〃 |
| `slides.pptx` | PowerPoint, speaker notes 25개 자동 주입 | 〃 |
| `script.md` | 슬라이드별 구어체 대본 (30분 / 25장, 시간 배분·강조 포인트) | 슬라이드 1~25 |
| `README.md` | 이 문서 — 슬라이드가 생략한 근거·수치·한계 | Part I~VI |

슬라이드 ↔ 노트 대응: 슬라이드 4→§1, 7→§3, 8→§4, 9→§5, 10→§6, 12→§7, 13→§8, 14→§9, 16→§10, 17~20→§11~14, 22→§15, 23→§16, 24→§17, 25→§18.

빌드: `marp slides.md --html --allow-local-files -o slides.html` (PDF는 `--pdf --pdf-notes`, PPTX는 `--pptx`).

- **Part I** — 평문 HTTP: 기준점
- **Part II** — TLS: 순서 변화와, 암호화 뒤에도 남는 것
- **Part III** — mTLS: 무엇이 추가되고 무엇을 얻는가
- **Part IV** — Envoy TLS 종료: 네 가지 문제
- **Part V** — Cilium: 딜레마를 어떻게 좁히는가
- **Part VI** — 요약과 판단 기준

---

# Part I. 평문 HTTP — 기준점

## 1. 통신 순서

```text
Client                                    Server:80
  │──── ① SYN ─────────────────────────────▶│
  │◀─── ② SYN + ACK ────────────────────────│   1 RTT
  │──── ③ ACK ─────────────────────────────▶│
  │──── ④ GET /api/orders HTTP/1.1 ────────▶│   평문
  │      Host: api                           │
  │      Authorization: Bearer eyJhbGci…     │
  │◀─── ⑤ HTTP/1.1 200 OK ──────────────────│   평문
  │      {"orderId":1024,"card":"4111-…"}    │
```

- **첫 요청 바이트까지 1 RTT**, 응답까지 2 RTT.
- ③의 ACK에 요청을 실어 보낼 수 있으므로 실무적으로는 "TCP 1 왕복 뒤 요청"으로 기억하면 된다.

## 2. 평문의 양면성

같은 성질이 위험이자 기능의 전제다. 이 대칭이 이 문서 전체의 축이다.

| | 평문이라서 |
|---|---|
| **위험** | 토큰·쿠키·PII 노출 / 경로상 변조 가능(무결성 없음) / 상대 진위 확인 불가 |
| **전제** | Envoy가 `method`·`path`·header 파싱 가능 / L7 RBAC · 경로 라우팅 · 재시도 / 요청 단위 메트릭·트레이싱 |

보안이 요구하는 것과 관측·정책이 요구하는 것이 정확히 반대다. TLS는 위쪽을 해결하면서 아래쪽을 파괴한다.

---

# Part II. TLS — 순서와 잔여 정보

## 3. TLS 1.3 통신 순서

```text
  TCP 3-way handshake                                       1 RTT
  │──── ④ ClientHello ──────────────────────────────────────▶│
  │        versions · cipher_suites · key_share              │
  │        SNI=api.example.com · ALPN=h2                     │  ← 키가 없다 → 전부 평문
  │◀─── ⑤ ServerHello (key_share) ───────────────────────────│  ← 여기까지 평문
  │        [ EncryptedExtensions · Certificate               │     여기부터 암호화
  │          CertificateVerify · Finished ]                  │
  │──── ⑥ [ Finished ] + [ GET /api/orders ] ───────────────▶│  1 RTT
  │◀─── ⑦ [ HTTP/1.1 200 OK ] ───────────────────────────────│
```

**왜 ClientHello가 평문일 수밖에 없는가** — 이 시점에는 공유 세션 키가 존재하지 않는다. 키 협상 자체를 담은 메시지이므로 암호화할 수단이 없다. 이것이 SNI 노출의 구조적 원인이며, ECH(Encrypted Client Hello)가 해결하려는 문제다.

**TLS 1.3의 개선** — 서버가 ⑤에서 `key_share`를 보내는 즉시 세션 키가 유도되므로, 같은 비행의 인증서까지 암호화된다. TLS 1.2에서는 서버 인증서가 평문으로 노출됐다.

**⑥의 순서 주의** — 클라이언트는 ⑤의 인증서 체인을 신뢰 CA로 검증하고 호스트명을 확인한 **뒤에야** ⑥을 보낸다. 검증 실패 시 여기서 연결이 끊긴다.

## 4. RTT 비교

| 구간 | 평문 HTTP | TLS 1.2 | TLS 1.3 | TLS 1.3 재개(0-RTT) |
|---|---|---|---|---|
| TCP 핸드셰이크 | 1 RTT | 1 RTT | 1 RTT | 1 RTT |
| TLS 핸드셰이크 | — | **2 RTT** | **1 RTT** | 0 RTT |
| **첫 요청 바이트까지** | **1 RTT** | **3 RTT** | **2 RTT** | **1 RTT** |
| 바이트당 대칭 암복호 | 없음 | 양단 각 1회 | 양단 각 1회 | 양단 각 1회 |
| 연결당 비대칭 연산 | 없음 | 서명 검증 1회 | 서명 검증 1회 | 생략 가능 |

TLS 1.2가 2-RTT인 이유: `ServerHelloDone` → `ClientKeyExchange`+`ChangeCipherSpec`+`Finished` → `ChangeCipherSpec`+`Finished` 왕복이 한 번 더 필요하다.

**오해 정정** — 핸드셰이크 RTT는 **연결당 1회**다. 커넥션 풀·keep-alive·HTTP/2 멀티플렉싱으로 상각된다. AES-NI가 있는 CPU에서 대칭 암복호도 병목이 아니다. **실제 비용의 대부분은 Part IV의 프록시 홉에서 발생한다.**

0-RTT 재개는 replay 공격에 노출되므로 멱등 요청(GET)에만 써야 한다.

## 5. 암호화해도 남는 것

```text
핸드셰이크 첫 패킷 (ClientHello)
┌──────┬────────────┬────────────────┬────────────┬──────────────────────────────┐
│ Eth  │ IP src/dst │ TCP sport/dport│ TLS record │ ClientHello: SNI·ALPN·cipher │
└──────┴────────────┴────────────────┴────────────┴──────────────────────────────┘
                                    전부 평문 (ECH 미사용 시)

이후 애플리케이션 데이터 패킷
┌──────┬────────────┬────────────────┬────────────┬──────────────────────────────┐
│ Eth  │ IP src/dst │ TCP 포트       │ type / len │ ▨▨▨ 암호문 ▨▨▨              │
└──────┴────────────┴────────────────┴────────────┴──────────────────────────────┘
                                    method·path·header·cookie·body 전부 여기 안
```

| 계층 | 암호화 후 | 정책 가능 여부 |
|---|---|---|
| L3 IP | 노출 | ✅ CIDR·identity 정책 |
| L4 포트 | 노출 | ✅ 포트 정책 |
| TLS SNI · ALPN | 노출 (첫 패킷) | ✅ FQDN·SNI 기반 정책 |
| 패킷 크기·타이밍 | 노출 | ⚠️ 사이드채널 (fingerprinting) |
| **L7 method·path·header·body** | **불가시** | ❌ **원천 불가** |

## 6. 그래서 eBPF는 L7을 못 본다

```yaml
# L4까지 — 커널 eBPF에서 헤더만 읽으면 판단 가능
toPorts:
- ports: [{ port: "443", protocol: TCP }]        # ✅

# L7 — 암호문 안이라 볼 수 없음
  rules:
    http:
    - method: "GET"
      path: "/api/orders"                        # ❌
```

eBPF는 **패킷 하나를 훅에서 즉시 판단**하는 실행 모델이다. 복호화 키도 없고, 여러 패킷에 걸친 스트림을 재조합할 상태도 없다(verifier 제약과 per-packet 실행 모델 — 5주차 Part VI 참조).

정책이 `path`를 보려면 **누군가 반드시 복호화**해야 하고, 복호화하려면 **TLS 세션의 한쪽 끝**이 되어야 하며, 그것이 곧 **프록시**다. 예외는 없다.

---

# Part III. mTLS

## 7. TLS vs mTLS

| | TLS | mTLS |
|---|---|---|
| 서버 증명 | ✅ | ✅ |
| 클라이언트 증명 | ❌ (앱 계층 JWT·비밀번호·API key에 위임) | ✅ 인증서 + 서명 |
| 인가 주체 | IP 또는 앱 토큰 | **암호학적 워크로드 신원** |

쿠버네티스에서 이것이 중요한 이유: **Pod IP는 재사용되고, 위조 가능하고, 수시로 바뀐다.** IP를 신원으로 쓰는 것은 애초에 무리였다.

## 8. mTLS 핸드셰이크 — 추가되는 세 메시지

```text
  │──── ClientHello ────────────────────────────────────────▶│
  │◀─── ServerHello · [ EncryptedExtensions ] ───────────────│
  │◀─── [ CertificateRequest ] ──────────────────────────────│  ★ 추가
  │◀─── [ Certificate(server) · CertificateVerify · Finished ]│
  │──── [ Certificate ] ────────────────────────────────────▶│  ★ 추가
  │        SAN: URI spiffe://cluster.local/ns/shop/sa/frontend│
  │──── [ CertificateVerify ] ──────────────────────────────▶│  ★ 추가
  │        handshake transcript 를 개인키로 서명             │
  │──── [ Finished ] ───────────────────────────────────────▶│
  │                          서버: 체인 검증 → SPIFFE ID 추출 │
  │                              → AuthorizationPolicy / CNP  │
  │◀─── [ 200 OK ] 또는 RBAC deny ───────────────────────────│
```

- **RTT는 늘지 않는다.** 메시지가 기존 flight 안에 추가될 뿐이다. 흔한 오해다.
- 늘어나는 것: **비대칭 연산 2회**(서명 생성 1 + 검증 1)와 flight 크기. 짧고 많은 연결에서 CPU로 체감된다 → 커넥션 재사용이 중요.
- `CertificateVerify`가 있는 이유: 인증서만 제출하면 **남의 공개 인증서를 복사**해 쓸 수 있다. transcript 서명이 **개인키 소유**를 증명한다.

## 9. 메시가 mTLS를 원하는 이유

| 항목 | 내용 |
|---|---|
| 신원 표현 | `SAN: URI, spiffe://<trust-domain>/ns/<ns>/sa/<serviceaccount>` |
| 발급 | istiod 또는 SPIRE server + per-node agent |
| 수명 | 단명(하루 내외) + 자동 rotation |
| 전달 | **SDS**(Secret Discovery Service) over UDS → 프록시 메모리. **디스크에 개인키를 쓰지 않음** |
| 앱 영향 | 코드 무수정 |

여기까지가 명분이다. 그런데 **이것을 얻으려고 Pod마다 세운 Envoy가 Part IV 모든 문제의 원인이 된다.**

---

# Part IV. Envoy TLS 종료 — 네 가지 문제

## 10. 전체 경로

```text
┌──── Pod A (frontend) ────┐            ┌──── Pod B (orders) ────┐
│  App A  ──①──▶ Envoy A   │            │  Envoy B ──⑤──▶ App B  │
└──────────────────┬───────┘            └────┬───────────────────┘
                   │                         │
                   └──② TCP 3WHS + mTLS ─────┤   (+1 RTT)
                   └──③ [ GET /orders ] ─────▶   암호화 + XFCC 주입
                                             ④ 복호화 → 평문
                                                RBAC(peer SPIFFE ID)
                                                L7 정책 · 경로 라우팅

① 평문 (loopback)   ②③ 암호화   ④ 평문(Envoy B 메모리)   ⑤ 평문 (loopback)
```

`①`에서 App A는 그냥 `http://orders/...`를 호출한다. 앱은 mTLS의 존재를 모른다. iptables `REDIRECT`(또는 eBPF sockmap)가 소켓을 `:15001`로 돌린다.

**요청 1건의 청구서: TCP 연결 3개 · TLS 암복호 2회 · HTTP 파싱/재직렬화 4회 · 프로세스 경계 4회 통과.** 응답은 이를 역순으로 한 번 더 지불한다.

## 11. 문제 ① — hop-by-hop이지 E2E가 아니다

**평문 존재 지점 4곳**: Pod A loopback / Envoy A 프로세스 메모리 / Envoy B 프로세스 메모리 / Pod B loopback.

**공격 표면**:
- Pod 내 `CAP_NET_RAW` → `tcpdump -i lo`로 나가는 요청이 그대로 잡힌다.
- `kubectl debug` 임시 컨테이너, 주입된 디버그 사이드카.
- Envoy 침해 시 **평문 획득 + 신원 위조**를 동시에 얻는다.
- 코어 덤프 · 메모리 스크래핑.

> "서비스 메시를 켰으니 종단간 암호화된다"는 **틀린 문장**이다. 정확히는 *Envoy-to-Envoy 구간만* 암호화된다.

무의미하다는 뜻이 아니다. 네트워크 도청과 노드 간 스니핑은 확실히 막는다. 다만 신뢰 경계가 **앱 → Pod 샌드박스**로 이동했을 뿐이며, 보안 심사에서는 "Pod 샌드박스 경계까지 신뢰, 노드 간 mTLS"라고 정확히 서술해야 한다.

## 12. 문제 ② — 비용

| 항목 | 프록시 없음 | 사이드카 mTLS |
|---|---|---|
| 요청 경로 TCP 연결 수 | 1 | **3** |
| 바이트당 암복호 | 0 | **2회** |
| HTTP 파싱 / 재직렬화 | 0 | **4회** |
| 첫 요청까지 RTT | 1 | **3** |
| Pod당 상주 메모리 | 0 | Envoy 1개 분량 |
| 컨트롤플레인 부하 | 없음 | Pod 수에 비례한 xDS 전파 |

- 위 세 줄은 **환경·벤치마크와 무관하게 구조적으로 발생**한다. 실측 지연은 커넥션 재사용률에 지배되므로 특정 수치를 외우는 것보다 이 구조를 아는 편이 유용하다.
- 문제가 되는 것은 평균이 아니라 **p99 꼬리**다. 프록시가 2개 끼면 GC·스케줄링 지연이 곱해진다.
- 사이드카는 **Pod 수만큼** 존재한다 → 노드당 수용 Pod 감소, 기동 지연, 롤링 업데이트 시 재시작 대상 2배. Istio Ambient가 ztunnel을 DaemonSet으로 뺀 직접적 동기다.

## 13. 문제 ③ — 의미 손실과 운영 함정

**연결 의미 변화**
- 앱이 보는 src IP = `127.0.0.1` → IP 화이트리스트·레이트리밋·접근 로그를 쓰는 앱이 깨진다.
- 원 신원은 `X-Forwarded-Client-Cert`(XFCC)로 재주입 → 앱이 **헤더를 신뢰**해야 한다.
- ⚠️ 외부 유입 요청이 XFCC를 직접 달고 오면 **신원 위조**가 된다. 엣지에서 반드시 제거해야 한다.

**프로토콜 충실도**
- h2 → h1.1 다운그레이드 변환, 헤더 케이스 정규화.
- trailer · WebSocket · 양방향 gRPC 스트리밍 엣지케이스.
- 파싱 불가 프로토콜은 raw TCP 패스스루로 강등 → **L7 기능 상실**(조용히 발생하므로 더 위험).

**수명주기 경합**
- Envoy보다 앱이 먼저 기동 → `connection refused`.
- 앱보다 Envoy가 먼저 종료 → egress 블랙홀.
- k8s 1.29 native sidecar(`initContainers` + `restartPolicy: Always`)로 상당 부분 완화.

**인증서 배관**
- SDS · cert rotation · CA rotation · 노드 간 시계 오차 → 핸드셰이크 실패.
- 장애 시 봐야 할 로그가 **앱 로그 → 프록시 로그**로 이동한다. 팀의 디버깅 습관 자체를 바꿔야 한다.

## 14. 문제 ④ — 근본 딜레마

| 앱이 진짜 E2E TLS | 메시가 TLS 종료 |
|---|---|
| 평문은 App A·B 안에만 ✅ | L7 기능 전부 가능 ✅ |
| Envoy는 TCP 바이트만 봄 | 평문이 프록시 메모리에 존재 |
| 라우팅·L7 RBAC·HTTP 메트릭 **전부 불가** | 신뢰 경계가 Pod 샌드박스로 확대 |
| 얻는 것은 L4 통계뿐 | 프록시가 최우선 공격 표적 |

> **둘 다는 원리적으로 불가능하다.** L7 판단은 평문 없이는 정의되지 않기 때문이다.

실제 설계 선택지는 세 축뿐이다: *평문을 **누가** 쥐는가 · **얼마나 오래** 쥐는가 · **얼마나 멀리** 옮기는가.* Istio Ambient가 L7 Waypoint를 옵션으로 분리한 것도, Cilium이 L7 룰이 걸린 흐름만 Envoy로 우회시키는 것도 전부 이 세 축의 최소화 전략이다.

---

# Part V. Cilium은 어떻게 좁히는가

## 15. L3/L4 경로 — 프록시 홉 0

```text
  cilium-agent A ⟨SPIRE SVID⟩ ┈┈┈ out-of-band mTLS 핸드셰이크 ┈┈┈▶ cilium-agent B
        identity 쌍마다 1회 → 결과를 eBPF auth cache 에 기록 (연결마다 하지 않는다)

  App A ─평문(소켓)─▶ eBPF TC hook ─▶ WireGuard 커널 암호화 ─▶ (( 네트워크 ))
                     identity 정책          (또는 IPsec)              │
                     + auth cache 확인                                ▼
  App B ◀─평문(소켓)─ eBPF ingress 정책 ◀───── 커널 복호화 ◀──────────┘
```

- **userspace 프록시 0개 · 추가 TCP 연결 0개 · 복호화된 평문이 userspace에 존재하지 않는다.**
- 핵심 아이디어 두 가지:
  1. **인증을 데이터 경로에서 분리** — mTLS 핸드셰이크를 agent끼리 out-of-band로 수행하고 결과를 eBPF auth cache에 저장. 연결마다 TLS 종료를 하지 않는다.
  2. **암호화를 커널로** — WireGuard/IPsec이 커널에서 처리. 패킷이 userspace로 올라오지 않는다.
- 정책 활성화: `CiliumNetworkPolicy`의 `authentication: { mode: "required" }`.
- 설치: `--set authentication.mutual.spire.enabled=true --set authentication.mutual.spire.install.enabled=true`

**정직한 한계** (Cilium 공식 문서 *Mutual Authentication (Beta)* 로드맵 표 기준):
- 기능 전체가 **beta**. SPIFFE/SPIRE 통합, agent 간 mTLS 핸드셰이크, auth cache, CNP 지원까지 Beta.
- **TODO 상태**: WireGuard 통합, per-connection handshake, ipcache와 auth 데이터 동기화, 보안 모델 문서화, 침투 테스트.
- Cluster Mesh와 **호환되지 않는다**(단일 trust domain을 여러 클러스터에 걸칠 수 없음).
- 외부 mTLS 솔루션과 연동 불가.
- 이 경로로는 **L3/L4 정책만** 가능하다. HTTP `method`/`path`는 여전히 보이지 않는다.

## 16. L7 + HTTPS — Cilium도 결국 명시적 MITM

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-visibility-tls
spec:
  endpointSelector:
    matchLabels: { org: empire, class: mediabot }
  egress:
  - toPorts:
    - ports: [{ port: "443", protocol: TCP }]
      terminatingTLS:                 # Pod → Envoy 구간 TLS 종료
        secret: { namespace: default, name: tls-orig }
      originatingTLS:                 # Envoy → 목적지 구간 TLS 재개시
        secret: { namespace: default, name: tls-dest }
      rules:
        http:
        - method: "GET"
          path: "/v1/orders"          # 평문에서만 가능한 판단
```

Cilium 공식 문서의 기능명은 **TLS Visibility**다. 즉 **문서화된 TLS interception**이다.

- `terminatingTLS` — L7 프록시가 **종료**하는 쪽의 TLS 파라미터. egress 정책에서는 로컬 엔드포인트가 개시한 연결을 프록시가 받는 서버 측 파라미터, ingress 정책에서는 원격 소스가 개시한 연결을 프록시가 받는 서버 측 파라미터.
- `originatingTLS` — 프록시가 업스트림으로 **재개시**할 때의 클라이언트 측 파라미터. 클라이언트 인증서를 요구하는 서비스에 필요.
- 두 stanza 모두 인증서·키를 담은 **Kubernetes Secret**을 참조한다.

**사이드카와의 차이는 "범위"다**:
1. 프록시가 Pod당이 아니라 **노드당 `cilium-envoy` 1개**.
2. **L7 룰이 명시된 흐름만** 프록시로 우회, 나머지는 eBPF fast path에서 완결.

**운영 주의** — `terminatingTLS`를 쓰려면 Pod가 클러스터 내부 CA를 신뢰하도록 트러스트 스토어를 주입해야 한다. 번거로워서 실제 채택률이 높지 않다. 설계의 출발점은 **"우리 트래픽 중 진짜 L7 정책이 필요한 흐름이 몇 개인가"**를 세어보는 것이다.

## 17. 세 모델 비교

| | Istio 사이드카 | Istio Ambient | Cilium |
|---|---|---|---|
| L4 암호화 주체 | Pod마다 Envoy | 노드당 ztunnel (Rust) | 커널 WireGuard / IPsec |
| 데이터 경로 프록시 홉 | **2** | 2 (L4) / 4 (Waypoint) | **0** (L3/L4) |
| 신원 | SPIFFE 인증서 | SPIFFE 인증서 | security identity + SPIFFE(auth, **beta**) |
| mTLS 핸드셰이크 시점 | 연결마다 | 연결마다 | identity 쌍당 1회, out-of-band |
| userspace 평문 | 항상 | L4는 없음 | L7 룰 있을 때만 |
| L7 정책 | 항상 가능 | Waypoint 배치 시 | 노드당 Envoy로 우회 시 |
| 성숙도 | 안정 | 안정 | L3/L4 안정, mutual auth **beta** |

각 행을 가로로 읽으면 전부 **"평문 노출 지점을 줄이려는 서로 다른 시도"**다.

공정한 서술: 프로덕션 mTLS 성숙도는 **Istio가 앞선다.** Cilium의 강점은 L3/L4 데이터플레인 통합이며, mutual authentication은 아직 beta다.

---

# Part VI. 요약과 판단 기준

## 18. 한 장 요약

| 단계 | 순서 비용 | 노출 |
|---|---|---|
| 평문 HTTP | 1 RTT | 전부 — 그래서 L7 정책 가능 |
| TLS 1.3 | +1 RTT | IP·포트·SNI·ALPN만 남고 L7 소멸 |
| mTLS | RTT 동일, 서명 2회 | 동일 + 신원이 IP → 인증서 |
| Envoy 종료 | 연결 3개·암복호 2회·파싱 4회 | **평문 지점 2곳 추가** |

## 19. 실무 판단 체크리스트

1. **우리 트래픽 중 L7 정책이 실제로 필요한 흐름 비율은?** 대개 생각보다 훨씬 적다. 적다면 L4 암호화만으로 충분하고 프록시를 뺄 수 있다.
2. **규정상 워크로드 신원 기반 mTLS가 필수인가?** 필수라면 성숙도 기준으로 Istio가 안전한 선택.
3. **"E2E 암호화"라고 문서에 쓰고 있지 않은가?** hop-by-hop이 정확한 표현이다.
4. **XFCC 헤더를 엣지에서 제거하는가?** 안 하면 신원 위조 경로다.
5. **평문 지점이 어디에 몇 개 있는지 즉답할 수 있는가?** 이 질문 하나가 아키텍처 이해도를 판별한다.

## 20. 참고

- Cilium — [Inspecting TLS Encrypted Connections with Cilium (TLS Visibility)](https://docs.cilium.io/en/stable/security/tls-visibility/)
- Cilium — [Mutual Authentication (Beta)](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)
- Cilium — [CFP-22215: Mutual Auth for Service Mesh](https://github.com/cilium/design-cfps/blob/main/cilium/CFP-22215-mutual-auth-for-service-mesh.md)
- SPIFFE — https://spiffe.io/
- 관련 노트 — `../week5-dns-fqdn-l7-envoy/README.md` (§16 TLS Visibility), `../istio-ambient-cilium-study.md`
