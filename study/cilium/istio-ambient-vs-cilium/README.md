# TLS부터 Istio Ambient, 그리고 Cilium까지

신규 설계 기준은 TLS 1.3이다. RFC 8996(BCP 195)이 폐기한 것은 1.0과 1.1이고, RFC 9846(2026-07)은 TLS 1.2 명세인 RFC 5246을 obsolete했다. 다만 RFC 9846은 TLS 1.2 구현에 대한 새 요구사항도 규정하고 있으며, 1.2는 기존 배포와의 호환을 위해 현장에서 여전히 널리 지원되는 상태다. "이제 1.3만 쓴다"는 말은 틀렸다.

Istio는 CNI가 아니다. 동작하는 CNI를 전제하고 그 위에 CRD·webhook·프록시를 얹는 k8s 애드온이다. `istio-cni-node`는 CNI 플러그인 체인에 append되는 플러그인이며, 파드 IP를 만들지 않는다. Istio 설치 전제조건 1번이 *"correctly-configured primary interface CNI plugin"*이다.

Ambient는 프록시 홉을 줄이지 않았다. 공식 성능 문서는 L4 경로에서 유저스페이스 프록시를 "클라이언트 노드 ztunnel, 서버 노드 ztunnel"로 두 번 통과한다고 명시한다. 사이드카의 "클라이언트 사이드카, 서버 사이드카"와 구조가 같다. 줄어든 것은 프록시 인스턴스 수(파드당 → 노드당)와 처리 깊이(L7 → L4)다. 같은 노드의 파드끼리도 로컬 ztunnel을 경유한다.

Cilium과의 진짜 차이는 L3 축의 유무다. 성능 수치가 아니다. Cilium에는 IPAM 7종, BGP, LB-IPAM, Cluster Mesh, EgressGatewayPolicy, Host Firewall이 있다. Istio Ambient에는 대응하는 개념 자체가 없다. 두 제품을 head-to-head로 비교한 공개 처리량 수치도 현재 존재하지 않는다.

---

## 산출물

| 파일 | 설명 |
|---|---|
| `Chapter.md` | 구성 아웃라인 (사용자 제공 5챕터) |
| `pages/` | **페이지별 편집 소스 41개** + `_head.md`(front-matter·CSS) + `_tail.md`(렌더러 script) + `README.md`(색인). 내용 수정은 여기서 한다 |
| `build.sh` | `pages/` → `slides.md` 조립 + HTML/PPTX/PDF 빌드 + 산출물 수 검증 |
| `slides.md` | **산출물** — `pages/` 를 이어붙인 결과. 직접 고치지 말 것 |
| `slides.html` | HTML 빌드 |
| `slides.pdf` | PDF 빌드 (발표자 노트 포함) |
| `slides.pptx` | PowerPoint 빌드 |
| `script.md` | 슬라이드별 구어체 대본 (35섹션, 31분 40초). **RFC 번호를 쓰지 않는다** — 무엇이 달라졌는지로 서술 |
| `README.md` | 이 파일 |
| `explainer.html` | **처음 보는 사람용 학습 페이지.** 같은 5장 구성을 배경지식 없이 읽도록 풀어 쓴 단일 HTML. 애니메이션 포함(1.2/1.3/mTLS 핸드셰이크 왕복 비교, 홉 카운트 4종 토글, 키 보관 오해/사실 토글, 파드 부팅 4단계 스테퍼, 프로브 정상/고장 경로) + 확인 퀴즈 7문항. Marp 산출물이 아닌 손으로 쓴 파일이므로 `slides.md`를 고쳐도 자동 갱신되지 않는다 |

### 편집 워크플로우

내용은 `pages/` 의 페이지 파일에서 고친다. `slides.md` 는 조립 산출물이므로 직접 편집하면 다음 빌드에 덮어써진다.

```bash
vi pages/24-ztunnel-spec.md   # 1. 고칠 페이지만 편집
./build.sh                    # 2. 조립 + HTML/PPTX/PDF 재생성 + 검증
```

| 명령 | 동작 |
|---|---|
| `./build.sh` | 조립 → `slides.md` → 3종 빌드 → 페이지 수와 산출물 수 일치 검증 |
| `./build.sh --md` | 조립만 (`slides.md` 만 갱신, 빌드 생략) |
| `./build.sh --check` | 조립 결과가 현재 `slides.md` 와 같은지만 확인 (파일 변경 없음) |

페이지 목록과 각 페이지의 구성 요소는 [`pages/README.md`](pages/README.md) 참조.

### 빌드 명령 (수동으로 돌릴 때)

`--html` 플래그는 세 명령 모두에 필수다. 출력 포맷이 아니라 "raw HTML 허용" 스위치로, 없으면 CSS/JS 다이어그램 킷이 텍스트로 이스케이프된다.

```bash
marp slides.md --html --allow-local-files -o slides.html
marp slides.md --html --pptx --allow-local-files -o slides.pptx
marp slides.md --html --pdf --pdf-notes --allow-local-files -o slides.pdf
```

---

## 발표 개요

**35장 / 31분 40초**. 챕터가 끝날 때마다 질문을 받는 형식이다.

슬라이드와 대본에는 **RFC 번호를 넣지 않았다.** 문서 번호를 말하면 청중이 따라오지 못하므로 "무엇이 달라졌나"로만 서술한다. 원문 출처는 이 문서 아래 [참고 자료](#참고-자료)에 남겨 둔다.

| Chapter.md 장 | 덱 구간 | 슬라이드 범위 | 슬라이드 수 |
|---|---|---|---|
| 도입 | 표지 (목차·결론 슬라이드 없음 — 바로 Ch1로 진입) | 1 | 1 |
| 1. TLS에 대해서 | 01 TLS에 대해서 | 2–9 | 8 |
| 2. TLS 통신 방법 | 02 TLS 통신 방법 | 10–16 | 7 |
| 3. Istio | 03 Istio | 17–22 | 6 |
| 4. Istio Ambient mode | 04 Istio Ambient mode | 23–31 | 9 |
| 5. Istio Ambient mode vs Cilium | 05 Ambient vs Cilium | 32–43 | 12 |
| 마무리 | 정리 | 44 | 1 |

---

## 슬라이드 ↔ 대본 매핑

| # | 제목 | 한 줄 요지 |
|---|---|---|
| 1 | TLS · Istio Ambient · Cilium | 제목만. 부제·출처줄 없음 |
| 2 | 01 TLS에 대해서 | 챕터 1 리드 — 이름 풀이 → 보장 셋 → 버전 셋 |
| 3 | TLS = Transport Layer Security | Transport / Layer / Security 세 단어 풀이 — 논리적 계층이지 OSI 특정 계층이 아니다 |
| 4 | TLS가 보장하는 세 가지 | 기밀성·무결성·인증을 용어 정의 + 없을 때 무슨 일이 생기는지 |
| 5 | 공개키와 대칭키 — 어디에 쓰나 | 키 합의·상대 확인은 공개키, 본 통신은 대칭키 — 역할 분담 |
| 6 | 버전은 세 개 — 1.1 · 1.2 · 1.3 | 1.1 암호화 수준 낮음 / 1.2 통신 많음 / 1.3 통신 줄임 — 현재는 1.2·1.3 병존 |
| 7 | 1.1 — 암호화 수준이 낮아서 금지 | MD5·SHA-1만 가능 + 암호화·검사 분리 + 협상 필드 부재 → 1.0과 함께 금지 |
| 8 | 1.2 — 문제는 고쳤지만 통신이 많다 | 방식을 정한 다음 키 재료를 보내는 순서라 왕복 두 번 |
| 9 | 1.3 — 통신을 어떻게 줄였나 | 키 교환 그룹을 미리 찍어 보냄 → 맞으면 1왕복, 틀리면 되물어 2왕복. 조합 축소는 별개 변화 |
| 10 | 02 TLS 통신 방법 | 챕터 2 리드: ClientHello · ServerHello · mTLS |
| 11 | ClientHello — 실제로 나가는 내용 | 실제 덤프 — 필드 값과 주석. server_name·alpn이 평문으로 보인다 |
| 12 | ServerHello — 서버가 고른 결과 | 실제 덤프 — 고른 값 하나씩, "여기까지 평문" 구분선 |
| 13 | TLS → mTLS: 무엇이 추가되나 | 서버만 인증 vs 양쪽 인증. 대가는 인증서 배포·갱신 |
| 14 | 순서로 보면 두 줄이 늘어난다 | TLS/mTLS 순서를 나란히 — 늘어난 두 줄, 왕복은 그대로 |
| 15 | 03 Istio | 4단계: ClientHello+key_share → 서버인증+CertReq → 클라이언트인증 → Finished |
| 16 | Service Mesh — 앱에서 무엇을 빼내나 | 개인키 보유 + CA 신뢰 증명; 누가 들고 있는지는 증명 안 함 |
| 17 | Istio는 k8s Add-On이다 | 챕터 3 리드: Service Mesh 구현체 · k8s Add-On · istiod |
| 18 | istiod — 넷이 하나로 | Pilot·Galley·Citadel·injector가 하던 일 — 넷 다 **역사 용어**. Galley는 검증만 남음 |
| 19 | istiod의 포트 네 개 | CRD 4그룹 + webhook + istio-system 파드; 전제조건은 동작하는 CNI |
| 20 | istiod가 죽으면 | Pilot·Galley·Citadel·injector → 단일 Deployment (Istio 1.5, 2020-03) |
| 21 | 04 Istio Ambient mode | 15010 xDS 평문 / 15012 xDS TLS / 15014 모니터링 / 15017 webhook |
| 22 | 사이드카에서 Ambient로 — 무엇이 바뀌나 | 프록시 개수와 하는 일이 줄었다(홉은 2회 동일) + 홉 용어 풀이 |
| 23 | 구성요소는 세 개 | istio-cni-node의 두 역할 — 체인에 얹기, 상주 에이전트 |
| 24 | ztunnel — Rust로 쓴 L4 전용 프록시 | Rust · L4 전용 — L7을 안 하니 노드 공유가 가능했다(대가는 노드 단위 격리) |
| 25 | 인증서는 누가 갖고 있나 | 사이드카와 같다 — 프록시가 앱 대신 인증서를 갖는다. 위치가 파드에서 노드로 |
| 26 | 그 인증서를 언제 받나 — 파드가 뜰 때 | 네 단계가 끝나야 앱이 시작된다. 등록 시점에 ztunnel이 인증서를 받아 둔다 |
| 27 | istiod → ztunnel: 전송은 xDS, 타입은 전용 | 개인키는 ztunnel 프로세스 HashMap, 앱은 평문만; 이득은 주장 해상도 |
| 28 | waypoint — L7이 필요할 때만 | 경로는 출발지 ztunnel이 정한다 · 통과 3회 · 노드 왕복 가능 |
| 29 | 05 Istio Ambient mode vs Cilium | 세 가지 — 리소스 · L4/L7 · L3 |
| 30 | ① 실제로 뜨는 리소스 - Istio Ambient | waypoint는 Deployment — `Gateway`는 쿠버네티스 Gateway API 리소스 |
| 31 | ① 실제로 뜨는 리소스 - Cilium | 노드 50 기준 기본 합계는 거의 같다. Ambient는 L7에, Cilium은 워크로드 신원에 비용 |
| 32 | ① 규모를 넣어 보면 - 노드 50 | L4는 판정 근거가 다르고, L7 차이는 성능이 아니라 격리다 |
| 33 | ② 같은 L4·L7, 다른 뜻 | ztunnel 없이는 Cilium 경로에 SPIFFE가 없다 — cilium-envoy도 숫자 identity로 매칭 |
| 34 | ③ Cilium에만 있는 것 - 주소와 경로 | Egress Gateway(Istio 동명 기능과 다름) · Host Firewall · ClusterMesh(ztunnel과 배타) |
| 35 | ③ Cilium에만 있는 것 - 출발지·노드·클러스터 | 정책이 꺼지는 게 아니라 매칭 대상을 잃는다 + 동거 체크리스트 |

---

## 이번 개정에서 바로잡은 것

| 항목 | 기존 설명 (오류) | 정정 | 근거 |
|---|---|---|---|
| ① TLS 폐기 범위 | "RFC 8996이 TLS 1.1을 폐기했다" / "이제 1.3만 남았다" | RFC 8996(BCP 195)이 폐기한 것은 **1.0과 1.1**. RFC 9846(2026-07)이 RFC 5246(TLS 1.2)을 obsolete했으나, RFC 9846은 TLS 1.2 구현에 대한 새 요구사항도 규정한다. 1.2는 기존 배포와의 호환을 위해 현장에서 널리 지원된다. "이제 1.3만 쓴다"는 틀림. | RFC 8996 §5; RFC 9846 abstract("also specifies new requirements for TLS 1.2 implementations") |
| ② 1.0/1.1 사망 원인 | "SHA-1 취약점 때문에 1.1이 폐기됐다" | 단일 취약점이 아니라 **설계 전반**: MD5/SHA-1 러닝 해시 의존, AEAD 부재(CBC MAC-then-encrypt만), `signature_algorithms` 확장 없어 해시 협상 수단 자체가 부재 → 업그레이드 경로가 프로토콜 교체뿐 | RFC 8996 §3; RFC 4346 §1.1 (5개 차이점만 열거) |
| ③ "300 → 5"의 의미 | "메시지 크기가 줄었다" / "패킷이 작아졌다" | 줄어든 것은 **사이퍼수트 등록 개수**: IANA 레지스트리 300개 이상 → RFC 8446 §B.4가 정의한 5개. 키 교환을 `supported_groups`·`key_share`로, 인증을 `signature_algorithms`로 분리해서 사이퍼수트가 단순해짐 | RFC 8446 §1.2 "cipher suite concept has been changed"; §B.4 |
| ⑤ Ambient 프록시 홉 | "Ambient는 프록시 홉을 줄여서 빠르다" | L4 경로 유저스페이스 통과는 **사이드카와 동일하게 2회**. 줄어든 것은 인스턴스 수(파드당→노드당)와 처리 깊이(L7→L4). 같은 노드 파드끼리도 로컬 ztunnel 경유 | istio.io *performance-and-scalability*: "pass through the client node ztunnel and then the server node ztunnel"; *ambient/architecture/data-plane* |
| ⑥ ztunnel 키 보관 위치 | "파드가 자기 인증서를 들고 mTLS를 한다" / "격리 경계가 파드 단위" | 개인키는 **ztunnel 프로세스 메모리의 `HashMap<Identity, …>`**에 보관. 앱 파드는 평문만 처리하며 TLS를 보지 못함. 침해 시 그 노드의 모든 SA 사칭 가능(WireGuard 노드 키와 동일 경계). 이득은 격리 경계가 아니라 와이어에 실리는 주장 해상도(`ns/…/sa/…`) | istio/ztunnel `src/identity/manager.rs` |
| ⑦ ztunnel xDS 사용 여부 | "ztunnel은 표준 xDS를 쓰지 않는다" | **전송 프로토콜은 xDS**(delta xDS over gRPC, istiod:15012). 다른 것은 리소스 타입: Envoy 타입(LDS/CDS/RDS/EDS) 대신 `istio.workload.Address`와 `istio.security.Authorization` 사용. 인증서도 같은 연결로 수신 | istio.io *ambient/architecture/control-plane*: "a simplified set of resources are used in the xDS APIs" |
| ⑧ ztunnel SO_REUSEPORT | "ztunnel 재시작은 SO_REUSEPORT로 무중단이다" | istio/ztunnel 소스에서 SO_REUSEPORT 사용 근거를 확인하지 못함. 공식 업그레이드 문서는 in-place 업그레이드가 *"may involve a short downtime"*을 명시하고 장수명 TCP는 cordon/drain 권장. 확인된 것은 DaemonSet 설정 `maxSurge:1/maxUnavailable:0`까지 | Istio *ambient/upgrade/helm* |
| ⑨ 성능 수치 | "Istio 2025 벤치마크에서 Cilium보다 빠르다/느리다가 증명됐다" | Istio ztunnel vs Cilium ztunnel **head-to-head 공개 수치 없음**. Istio 2025 벤치마크의 Cilium은 v1.16.6(ztunnel 도입 1.19 이전). Cilium CFP #38548은 "under certain conditions"만 언급하고 조건·메커니즘·측정치 모두 없음. 2024 벤치마크는 Cilium 커널 CPU가 계측에서 빠졌다고 스스로 밝힘 | Istio blog/2025/ambient-performance; cilium/cilium issue #38548 |
| ⑩ Cilium 정책 비활성 | "Ambient mTLS를 켜면 Cilium 정책이 전면 비활성화된다" | 정책은 여전히 평가되지만 **의미를 잃는다**. 파드를 떠나기 전 암호화돼 eBPF 훅에는 포트 15008의 암호화된 L4만 보임. 원래 8080을 막던 규칙이 매칭 대상을 잃고, 에러도 나지 않음. 켜기 전 기존 정책 전수 검토 필요 | Cilium docs: "L4 policies won't work except for directly targeting the ztunnel HBONE port (15008)" |

---

## 심화 노트

슬라이드가 밀도 규칙상 생략한 내용을 정리한다.

### (a) istiod 토폴로지와 통합 이력

Istio 1.5(2020-03) 이전에는 컨트롤 플레인이 여러 컴포넌트로 나뉘어 있었다: Pilot(xDS 설정 배포), Galley(설정 검증), Citadel(PKI/CA), 사이드카 인젝터, Mixer(텔레메트리). 컴포넌트마다 별도 배포·버전·RBAC가 필요했다. 공식 블로그는 istiod를 *"unifies functionality that Pilot, Galley, Citadel and the sidecar injector previously performed, into a single binary"*로 정의한다.

**포트 네 개의 용도**:
- `15010` (`grpc-xds`): XDS + CA, 평문. 신뢰할 수 있는 망에서만 사용.
- `15012` (`tls-xds`): XDS + CA, TLS/mTLS. 프로덕션 권장. ztunnel이 이 포트로 설정과 인증서를 받는다.
- `15014` (`http-monitoring`): Prometheus 메트릭.
- `15017` (`https-webhooks`): 주입·검증 webhook. k8s API 서버는 Service 443으로 붙고, 컨테이너는 15017로 받는다.

**주입 webhook의 `failurePolicy: Fail`**: istiod가 응답하지 못하면 주입 대상 파드 생성 요청이 거부된다. 기존 트래픽은 프록시가 마지막 설정으로 유지하지만 이 동작은 xDS 스트림 단절 시 일반 Envoy 동작에서 도출된 것으로 istio.io의 명시적 문구는 확인되지 않았다.

### (b) ztunnel 인증서 라이프사이클

- **키 생성**: 신원별로 ECDSA P-256 키쌍을 ztunnel 프로세스가 직접 생성. 개인키는 메모리의 `HashMap<Identity, CertificateChain>` 구조에 보관; 디스크에 쓰지 않는다.
- **갱신 시점**: 인증서 수명(기본 TTL 24시간)의 **50%** 지점에서 갱신을 시도한다. 즉 기본 설정에서는 약 12시간마다 갱신.
- **비활성화 항목**: SNI 전송 비활성 — 상대 인증서의 SAN만 보고 신원을 판단한다. 세션 재개(session resumption) 비활성. ALPN은 `h2`로 고정.
- **상태 상승**: ztunnel은 노드에 파드가 있는 모든 ServiceAccount의 인증서를 보유한다. istiod CA는 "자기 노드 파드 신원만" 요청할 수 있도록 강제한다.
- **실질 데드라인**: istiod 장애 시 갱신이 멈추면 기존 인증서 만료 시각이 실질 서비스 중단 시각이 된다.

### (c) istiod CA의 impersonation 3단 검사

ztunnel이 노드에 있는 타 ServiceAccount 인증서를 요청할 때 istiod CA(`node_auth.go`)는 세 단계를 확인한다:
1. 요청자가 인증된 k8s ServiceAccount JWT를 갖고 있는가.
2. 그 ServiceAccount가 해당 노드에 실제로 파드를 갖고 있는가 (K8s API 검증).
3. 요청한 신원이 같은 노드 범위인가.

`CA_TRUSTED_NODE_ACCOUNTS` 환경 변수로 특정 SA에만 교차 SA 인증서 발급을 허용할 수 있다. 이 검사가 ztunnel의 신원 주장이 임의 SA를 사칭하지 못하도록 막는 핵심 게이트다.

### (d) 데이터패스 요소 카운트

| 구성 | 유저스페이스 프록시 | TCP 커넥션 | 암호화 위치 | 신원 해상도 |
|---|---|---|---|---|
| 사이드카 양단 | 2 | 3 | Envoy (유저스페이스) | 워크로드(SPIFFE) |
| Ambient ztunnel only | **2 (동일)** | 3 | ztunnel (유저스페이스) | 워크로드(SPIFFE) |
| Ambient + waypoint | **3** | 4 | 2구간 | 워크로드(SPIFFE) |
| Cilium eBPF (암호화 없음) | **0** | 1 | — | — |
| Cilium WireGuard/IPsec | **0** | 1 | 커널 | 노드 |
| Cilium ztunnel (Beta) | **2** | 3 | ztunnel (유저스페이스) | 워크로드(SPIFFE) |

**주의**: 유저스페이스 프록시 횟수와 Ambient 구조는 공식 문서 근거다. TCP 커넥션 수는 프록시 토폴로지에서 도출한 값이며 문서가 명시적으로 카운트한 것은 아니다 `[INFERENCE]`. "Cilium ztunnel"은 Istio ztunnel의 fork이므로 데이터패스 구조가 동일하다.

### (e) 설치·업그레이드 운영 모델 차이

**Istio Ambient Helm 설치 순서 (역전 금지)**:
```bash
helm install istio-base  istio/base      -n istio-system --set profile=ambient
helm install istiod      istio/istiod    -n istio-system --set profile=ambient
helm install istio-cni   istio/cni       -n istio-system --set profile=ambient
helm install ztunnel     istio/ztunnel   -n istio-system
```
`profile=ambient`는 컴포넌트 자동 설치가 아닌 값(value) 묶음이다. `istioctl install --set profile=ambient`와 달리 Helm에서는 각 차트를 직접 설치해야 한다.

**업그레이드 모델 비교**:
- Istio: `revision` 태그로 새 컨트롤 플레인을 병행 가동. `istioctl tag set` + 네임스페이스 라벨 교체로 점진 이관. 문제 발생 시 롤백 가능 — 카나리 방식.
- Cilium: 전 컴포넌트 동일 버전 강제. 마이너 버전을 한 단계씩만 올리는 것이 검증된 경로. 카나리 불가.

**Cilium ztunnel 활성화 시 `cilium-ztunnel-secrets` 수작업 생성** (1.19 기준):
```bash
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 \
  -days 3650 -nodes -out ca.crt -keyout ca.key -subj "/CN=ztunnel-ca"
kubectl create secret generic cilium-ztunnel-secrets \
  --from-file=ca.crt=ca.crt --from-file=ca.key=ca.key -n kube-system
```
Istio는 istiod가 CA이므로 이 단계가 없다.

**진단 명령**:
```bash
# Istio Ambient
istioctl ztunnel-config workloads
istioctl ztunnel-config certificates

# Cilium
cilium-dbg status
hubble observe --namespace default
```
Cilium 자체 ztunnel을 사용하는 경우(시나리오 B) `istioctl`은 붙을 istiod가 없어 사용 불가.

### (f) Cilium L3 기능 전수와 Istio 대응물 부재

| 기능 | Cilium | Istio Ambient |
|---|---|---|
| IPAM 모드 | 7종 (cluster-pool, ENI, Azure, GKE, Alibabacloud, delegated-plugin, multi-pool) | 없음 — k8s 기본 IPAM 그대로 |
| 라우팅 | native, VXLAN, Geneve; 선택 가능 | 없음 |
| BGP | `CiliumBGPPeeringPolicy` / BGP Control Plane | 없음 |
| LB-IPAM | LoadBalancer IP를 내부적으로 할당 | 없음 |
| Cluster Mesh | 여러 클러스터의 서비스·정책 연합 | 없음 |
| L3 정책 selector | identity·CIDR·FQDN·entity·node·host | `AuthorizationPolicy.ipBlocks`만 (메시 등록 워크로드 한정) |
| 이그레스 소스 IP | `EgressGatewayPolicy`로 게이트웨이 노드에서 고정 SNAT | 없음 — 공식 문서가 *"cannot securely enforce that all egress traffic actually flows through the egress gateways"*라고 스스로 밝힘 |
| Host Firewall | 노드 자체 인터페이스 보호 | 없음 — "노드"라는 개념이 없음 |

### (g) 용어 — AEAD와 "대체(obsolete)"

발표 슬라이드 4에 회색 각주로 넣은 두 용어를 풀어 둔다. 청중 배경지식이 얕을 때 이 두 단어에서 막힌다.

**AEAD** (Authenticated Encryption with Associated Data) — 암호화와 위조 검사를 **한 번의 연산으로 함께** 처리하는 방식. TLS 1.1까지는 "암호화 따로, 무결성 검사(MAC) 따로"였고, 둘을 어떤 순서로 조합하느냐(MAC-then-encrypt vs encrypt-then-MAC)에서 BEAST·Lucky13 같은 취약점이 반복해서 나왔다. TLS 1.2가 AEAD를 선택지로 도입했고, TLS 1.3은 **AEAD만** 남겨서 이 조합 문제를 구조적으로 제거했다. 슬라이드에서 1.2의 정체를 "AEAD 도입"이라고 쓴 이유다.

**대체 (obsolete)** — 새 RFC가 옛 RFC를 **갈아치웠다**는 문서 관계이며, 해당 프로토콜을 당장 쓰지 말라는 **금지와는 다르다**. 이 구분이 슬라이드 4 표의 마지막 줄이다.

| 관계 | 대상 | 의미 |
|---|---|---|
| **금지** (deprecate, MUST NOT) | RFC 8996 → TLS 1.0 · 1.1 | 협상하지 말 것. 받으면 `protocol_version` alert |
| **대체** (obsolete) | RFC 9846 → RFC 5246 (TLS 1.2) | 명세 문서가 교체됨. 프로토콜은 호환용으로 계속 널리 지원되며, RFC 9846이 TLS 1.2 구현에 대한 새 요구사항을 규정 |

발표에서는 "1.1은 금지된 쪽, 1.2는 문서만 대체된 쪽"으로 한 문장에 대비시키면 전달이 빠르다.

---

## 자주 나오는 오해

| 오해 | 사실 |
|---|---|
| ① 이제 TLS는 1.3만 쓴다 | RFC 8996이 폐기한 것은 1.0과 1.1뿐이다. RFC 9846(2026-07)이 RFC 5246(TLS 1.2)을 obsolete했지만, 동시에 TLS 1.2 구현에 대한 새 요구사항도 규정한다. 1.2는 기존 배포와의 호환을 위해 현장에서 여전히 널리 지원된다. |
| ② ServerHello도 암호화된다 | RFC 9846 §1.3 (구 RFC 8446 §1.2)은 *"All handshake messages **after** the ServerHello are now encrypted."*라고 명시한다. ServerHello 자체는 평문이다. |
| ③ Ambient는 프록시 홉을 줄인다 | L4 경로에서 유저스페이스 프록시를 지나는 횟수는 사이드카와 동일하게 2회다. 줄어든 것은 프록시 인스턴스 수와 처리 깊이다. |
| ④ 파드가 자기 인증서를 들고 mTLS를 한다 | 개인키는 노드의 ztunnel 프로세스 메모리(`HashMap<Identity, …>`)에 있다. 앱 파드는 평문만 처리하며 TLS를 보지 못한다. |
| ⑤ ztunnel은 표준 xDS를 쓰지 않는다 | 전송 프로토콜은 xDS(delta xDS over gRPC)다. 다른 것은 리소스 타입: Envoy 타입 대신 `istio.workload.Address`와 `istio.security.Authorization`을 사용한다. |
| ⑥ Istio를 설치하면 파드 네트워킹이 된다 | Istio는 파드 IP를 만들지 않는다. 설치 전제조건 1번이 이미 동작하는 CNI다. `istio-cni`는 체인 플러그인으로 기존 CNI 설정 배열 끝에 append된다. |
| ⑦ Ambient가 Cilium보다 빠르다/느리다가 증명됐다 | Istio ztunnel과 Cilium ztunnel을 직접 비교한 공개 수치가 없다. Istio 2025 벤치마크의 Cilium은 ztunnel 도입(1.19) 이전 버전(v1.16.6)이다. |

---

## 검증 상태

### [VERIFIED] 출처 확인 완료

- RFC 8996 §5: TLS 1.0과 1.1 MUST NOT be used
- RFC 9846 §1.3 (구 RFC 8446 §1.2): "All handshake messages after the ServerHello are now encrypted"; 사이퍼수트 개념 변경. 동 RFC는 RFC 5246(TLS 1.2)도 obsolete하며 TLS 1.2 구현에 대한 새 요구사항을 규정함.
- RFC 8446 §B.4 (= RFC 9846 해당 섹션): TLS 1.3 사이퍼수트 5개 정의. 이 덱의 조항 번호 인용은 `RFC 8446 §X` 기준으로 유지(RFC 9846에서 섹션 번호 이동).
- RFC 8446 §2 Figure 1: "1-RTT" 용어를 RFC가 직접 사용
- RFC 9849 (2026-03): ECH Proposed Standard (draft 아님)
- istio.io *performance-and-scalability*: L4 경로 ztunnel 2회 통과 문구
- istio.io *ambient/architecture/data-plane*: 동일 노드도 ztunnel 경유 명시
- istio.io *ambient/architecture/control-plane*: "a simplified set of resources are used in the xDS APIs"
- istiod 통합: blog/2020/istiod
- istiod 포트: ops/deployment/application-requirements
- `failurePolicy: Fail`: Istio webhook 설정
- ztunnel TLS 설정: TLS 1.3 고정, SNI 비활성, ALPN h2 (istio/ztunnel 소스)
- 개인키 위치: `HashMap<Identity, …>`, istio/ztunnel `src/identity/manager.rs`
- 인증서 갱신 시점: 수명 50% 지점
- istiod CA node impersonation 검사: `security/pkg/server/ca/node_auth.go`
- Cilium issue #38548: "under certain conditions" — 조건·메커니즘·수치 없음
- Istio 2025 벤치마크: Cilium v1.16.6 사용 (ztunnel 1.19 이전)
- Cilium docs: "L4 policies won't work except for directly targeting the ztunnel HBONE port (15008)"

### [INFERENCE] / [미확인] 주의 필요

- **TLS 1.2 "왕복 두 번"**: RFC 5246은 "2-RTT"라는 표현을 쓰지 않는다. 메시지 묶음(flight) 구조에서 읽어낸 관찰값이다. RFC 8446만 "1-RTT"라는 용어를 직접 사용한다.
- **TCP 커넥션 수**: 표의 숫자(3·4·1)는 프록시 토폴로지에서 도출한 것이며, 문서가 명시적으로 카운트한 값이 아니다.
- **"istiod 부재 시 기존 프록시가 마지막 설정 유지"**: xDS 스트림 단절 시 Envoy의 일반 동작에서 도출. istio.io의 명시적 문구를 확인하지 못했다. 슬라이드 22에 괄호 주석으로 표기됨.
- **ztunnel SO_REUSEPORT 사용 여부**: istio/ztunnel 소스(2026-08 기준)에서 근거를 찾지 못했다. 업그레이드 문서는 "short downtime"을 명시하고 cordon/drain을 권장한다.
- **Cilium ztunnel 처리량 개선의 조건·메커니즘·수치**: Cilium CFP issue #38548에 "under certain conditions"만 있고, 조건이 무엇인지, 왜 그런지, 얼마나인지가 모두 없다. 설계 문서도 현재 없다.

---

## 참고 자료

링크는 2026-08-22 확인 완료.

### istio.io

- [Ops / Deployment](https://istio.io/latest/docs/ops/deployment/) — 설치 아키텍처 개요
- [istiod 블로그 (2020)](https://istio.io/latest/blog/2020/istiod/) — Pilot·Galley·Citadel·injector 통합 이력; istiod 탄생 배경
- [Application Requirements / Ports Used by Istio](https://istio.io/latest/docs/ops/deployment/application-requirements/#ports-used-by-istio) — 포트 15010/15012/15014/15017 용도 명시
- [Setup / CNI](https://istio.io/latest/docs/setup/additional-setup/cni/) — istio-cni 역할, 체이닝 방식, PSA 관계
- [Config Profiles](https://istio.io/latest/docs/setup/additional-setup/config-profiles/) — ambient 프로파일이 값 묶음임을 확인
- [Ambient / Control Plane Architecture](https://istio.io/latest/docs/ambient/architecture/control-plane/) — ztunnel xDS API, WDS 리소스 타입, 인증서 흐름
- [Ambient / Data Plane Architecture](https://istio.io/latest/docs/ambient/architecture/data-plane/) — 같은 노드 ztunnel 경유 명시; 홉 구조
- [Ambient / HBONE](https://istio.io/latest/docs/ambient/architecture/hbone/) — HTTP/2 CONNECT over mTLS, 포트 15008
- [Ambient / Helm Install](https://istio.io/latest/docs/ambient/install/helm/) — 차트 4개 순서 (base → istiod → cni → ztunnel)
- [Ambient / Helm Upgrade](https://istio.io/latest/docs/ambient/upgrade/helm/) — "short downtime" 명시; cordon/drain 권장
- [Ambient / Troubleshoot ztunnel](https://istio.io/latest/docs/ambient/usage/troubleshoot-ztunnel/) — 진단 명령 (`istioctl ztunnel-config`)
- [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/) — L4 경로 ztunnel 2회 통과 문구; Ambient 이득 정의
- [Blog 2024: Ambient vs Cilium](https://istio.io/latest/blog/2024/ambient-vs-cilium/) — 2024 벤치마크; 커널 CPU 계측 제외 자인
- [Blog 2025: Ambient Performance](https://istio.io/latest/blog/2025/ambient-performance/) — 2025 벤치마크; Cilium v1.16.6 사용
- [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/) — revision 기반 카나리 업그레이드 절차
- [Best Practices / Deployment](https://istio.io/latest/docs/ops/best-practices/deployment/) — HA 권장 (`autoscaleMin: 2` + podAntiAffinity)

### docs.cilium.io

- [Ztunnel Transparent Encryption (Beta)](https://docs.cilium.io/en/stable/security/network/encryption-ztunnel/) — Cilium ztunnel 활성화 절차; `cilium-ztunnel-secrets` 수작업 생성; iptables 필수; Beta 상태
- [WireGuard Encryption](https://docs.cilium.io/en/stable/security/network/encryption-wireguard/) — 노드 키 기반 암호화; 신원 한계
- [IPsec Encryption](https://docs.cilium.io/en/stable/security/network/encryption-ipsec/) — 클러스터 PSK 방식
- [IPAM](https://docs.cilium.io/en/stable/network/concepts/ipam/) — 7종 IPAM 모드 목록
- [Routing](https://docs.cilium.io/en/stable/network/concepts/routing/) — native/VXLAN/Geneve
- [Layer 3 Policy](https://docs.cilium.io/en/stable/security/policy/layer3/) — identity·CIDR·FQDN·entity·node selector
- [Egress Gateway](https://docs.cilium.io/en/stable/network/egress-gateway/egress-gateway/) — 고정 SNAT 메커니즘
- [BGP Control Plane](https://docs.cilium.io/en/stable/network/bgp-control-plane/bgp-control-plane/) — BGP 피어링 정책
- [Performance Benchmark](https://docs.cilium.io/en/stable/operations/performance/benchmark/) — Cilium 자체 벤치마크
- [Upgrade](https://docs.cilium.io/en/stable/operations/upgrade/) — 연속 마이너 1단계 정책
- [Troubleshooting](https://docs.cilium.io/en/stable/operations/troubleshooting/) — `cilium-dbg status` 진단
- [Terminology](https://docs.cilium.io/en/stable/gettingstarted/terminology/) — CiliumIdentity 등 용어 정의

### GitHub

- [istio/ztunnel `src/identity/manager.rs`](https://github.com/istio/ztunnel/blob/master/src/identity/manager.rs) — `HashMap<Identity, …>` 키 보관 구조
- [istio/ztunnel `src/identity/caclient.rs`](https://github.com/istio/ztunnel/blob/master/src/identity/caclient.rs) — CA 클라이언트 구현; 인증서 요청 로직
- [istio/ztunnel `src/tls/csr.rs`](https://github.com/istio/ztunnel/blob/master/src/tls/csr.rs) — ECDSA P-256 CSR 생성
- [istio/ztunnel `src/tls/certificate.rs`](https://github.com/istio/ztunnel/blob/master/src/tls/certificate.rs) — 인증서 갱신(50% 수명) 로직
- [istio/ztunnel `src/config.rs`](https://github.com/istio/ztunnel/blob/master/src/config.rs) — TLS 1.3 고정, SNI 비활성, ALPN h2 설정
- [istio/ztunnel `ARCHITECTURE.md`](https://github.com/istio/ztunnel/blob/master/ARCHITECTURE.md) — ztunnel 설계 문서
- [istio/istio `security/pkg/server/ca/node_auth.go`](https://github.com/istio/istio/blob/master/security/pkg/server/ca/node_auth.go) — CA의 impersonation 3단 검사; `CA_TRUSTED_NODE_ACCOUNTS`
- [istio/istio `security/pkg/server/ca/server.go`](https://github.com/istio/istio/blob/master/security/pkg/server/ca/server.go) — CA 서버 구현
- [istio/istio `manifests/charts/ztunnel/values.yaml`](https://github.com/istio/istio/blob/master/manifests/charts/ztunnel/values.yaml) — DaemonSet 기본값 (`maxSurge:1/maxUnavailable:0`, 리소스 요청)
- [cilium/cilium issue #38548](https://github.com/cilium/cilium/issues/38548) — Cilium ztunnel CFP; "under certain conditions" 전체 문맥
- [cilium/cilium `install/kubernetes/cilium/values.yaml`](https://github.com/cilium/cilium/blob/main/install/kubernetes/cilium/values.yaml) — encryption.type=ztunnel, 리소스 기본값 (cpu 200m / memory 512Mi)
- [cilium/ztunnel](https://github.com/cilium/ztunnel) — Istio ztunnel의 Cilium fork; SPIRE 통합을 위한 임시 fork (README: "temporary fork, 목표는 upstream 반영")
- [istio/tools `perf/benchmark`](https://github.com/istio/tools/tree/master/perf/benchmark) — 벤치마크 방법론

### RFC

- [RFC 4346](https://www.rfc-editor.org/rfc/rfc4346) — TLS 1.1; §1.1이 1.0 대비 5개 차이만 열거
- [RFC 5246](https://www.rfc-editor.org/rfc/rfc5246) — TLS 1.2 명세 (RFC 9846에 의해 obsolete됨); AEAD 도입, `signature_algorithms` 확장
- [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446) — TLS 1.3; §1.2 변경 목록, §B.4 사이퍼수트 5개, §2 Figure 1 (1-RTT). RFC 9846에 의해 obsolete됐으나 조항 인용 기준으로 유지.
- [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996) — BCP 195; TLS 1.0·1.1 MUST NOT; §3 폐기 근거 (MD5/SHA-1 의존, 업그레이드 경로 없음)
- [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846) — 2026-07-11, Proposed Standard. RFC 8446(TLS 1.3)과 RFC 5246(TLS 1.2)을 obsolete. 와이어 버전 0x0304 유지. §1.3에 "All handshake messages after the ServerHello are now encrypted" 확인. TLS 1.2 구현에 대한 새 요구사항 포함.
- [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849) — ECH (Encrypted Client Hello), 2026-03 Proposed Standard. Draft 아님.

---

## 관련 자료

- [`../tls-mtls-envoy/`](../tls-mtls-envoy/) — TLS 핸드셰이크·mTLS·Envoy 사이드카의 4개 평문 지점을 다루는 선행 덱. 이 덱의 Ch1·Ch2가 그 내용을 압축·재구성한 것이다. 사이드카 모드의 Envoy 토폴로지(3개 TCP 커넥션, XFCC 헤더, L7 가시성 vs E2E mTLS 딜레마)를 더 깊이 이해하려면 함께 보면 좋다.
- [`../week5-dns-fqdn-l7-envoy/`](../week5-dns-fqdn-l7-envoy/) — DNS·FQDN·Envoy L7 필터 체인을 다루는 덱. `FQDN`과 `entity` selector로 Cilium L3 정책을 쓸 때 DNS 해석 타이밍이 어떻게 영향을 주는지, Envoy가 HTTP 헤더를 어디서 보는지를 설명한다. 이 덱의 L4·L7 비교(슬라이드 39)의 배경 지식으로 연결된다.
