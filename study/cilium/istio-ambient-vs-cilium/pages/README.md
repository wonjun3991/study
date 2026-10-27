# pages/ 색인

`slides.md` 는 이 파일들을 이어붙인 **산출물**이다. 내용은 여기서 고치고 `./build.sh` 를 돌린다.

| # | 파일 | 제목 | 종류 | 구성 요소 |
|---|---|---|---|---|
| 1 | `01-cover.md` | TLS · Istio Ambient · Cilium | 리드 | — |
| 2 | `02-ch1-lead.md` | 01 TLS에 대해서 | 리드 | — |
| 3 | `03-tls-what-is-it.md` | TLS = Transport Layer Security | 본문 | — |
| 4 | `04-tls-three-guarantees.md` | TLS가 보장하는 세 가지 | 본문 | 표 |
| 5 | `05-keys-asym-sym.md` | 공개키와 대칭키 — 어디에 쓰나 | 본문 | 표 |
| 6 | `06-tls-versions.md` | 버전은 세 개 — 1.1 · 1.2 · 1.3 | 본문 | 표 |
| 7 | `07-tls11-deprecated.md` | 1.1 — 암호화 수준이 낮아서 금지 | 본문 | — |
| 8 | `08-tls12-roundtrips.md` | 1.2 — 문제는 고쳤지만 통신이 많다 | 본문 | .steps |
| 9 | `09-tls13-handshake.md` | 1.3 — 통신을 어떻게 줄였나 | 본문 | .cmp |
| 10 | `10-ch2-lead.md` | 02 TLS 통신 방법 | 리드 | — |
| 11 | `11-clienthello.md` | ClientHello — 실제로 나가는 내용 | 본문 | 코드 |
| 12 | `12-serverhello.md` | ServerHello — 서버가 고른 결과 | 본문 | 코드 |
| 13 | `13-tls-to-mtls.md` | TLS → mTLS: 무엇이 추가되나 | 본문 | .cmp |
| 14 | `14-mtls-handshake.md` | 순서로 보면 두 줄이 늘어난다 | 본문 | .cmp |
| 15 | `15-ch3-lead.md` | 03 Istio | 리드 | — |
| 16 | `16-service-mesh.md` | Service Mesh — 앱에서 무엇을 빼내나 | 본문 | .cmp |
| 17 | `17-istio-is-addon.md` | Istio는 k8s Add-On이다 | 본문 | .stack |
| 18 | `18-istiod-unified.md` | istiod — 넷이 하나로 | 본문 | .seq 표 |
| 19 | `19-istiod-ports.md` | istiod의 포트 네 개 | 본문 | 표 |
| 20 | `20-istiod-down.md` | istiod가 죽으면 | 본문 | 표 |
| 21 | `21-ch4-lead.md` | 04 Istio Ambient mode | 리드 | — |
| 22 | `22-sidecar-to-ambient.md` | 사이드카에서 Ambient로 — 무엇이 바뀌나 | 본문 | .cmp |
| 23 | `23-three-components.md` | 구성요소는 세 개 | 본문 | .seq |
| 24 | `24-ztunnel-spec.md` | ztunnel — Rust로 쓴 L4 전용 프록시 | 본문 | 표 |
| 25 | `25-ztunnel-identity.md` | 인증서는 누가 갖고 있나 | 본문 | .cmp |
| 26 | `26-pod-startup.md` | 그 인증서를 언제 받나 — 파드가 뜰 때 | 본문 | .steps |
| 27 | `27-istiod-to-ztunnel-xds.md` | istiod → ztunnel: 전송은 xDS, 타입은 전용 | 본문 | .seq |
| 28 | `28-waypoint.md` | waypoint — L7이 필요할 때만 | 본문 | .seq |
| 29 | `29-ch5-lead.md` | 05 Istio Ambient mode vs Cilium | 리드 | — |
| 30 | `30-resources-istio.md` | ① 실제로 뜨는 리소스 - Istio Ambient | 본문 | 표 |
| 31 | `31-resources-cilium.md` | ① 실제로 뜨는 리소스 - Cilium | 본문 | 표 |
| 32 | `32-resources-scale.md` | ① 규모를 넣어 보면 - 노드 50 | 본문 | 표 |
| 33 | `33-axis2-l4-l7.md` | ② 같은 L4·L7, 다른 뜻 | 본문 | .cmp |
| 34 | `34-l3-detail-1.md` | ③ Cilium에만 있는 것 - 주소와 경로 | 본문 | — |
| 35 | `35-l3-detail-2.md` | ③ Cilium에만 있는 것 - 출발지·노드·클러스터 | 본문 | — |

## 특수 파일

| 파일 | 역할 |
|---|---|
| `_head.md` | front-matter — `marp: true`, 테마 색, 폰트, 표/코드 스타일, **다이어그램 킷 CSS**(`.seq` `.stack` `.steps` `.cmp` `.badge`) |
| `_tail.md` | 다이어그램 렌더러 `<script>`. `data-seq` 등 속성을 읽어 DOM 을 만든다. 마지막 슬라이드 끝에 붙는다 |

## 편집 규칙

- 페이지 파일 안에 **맨 앞 열 `---` 금지**. 슬라이드 구분자와 충돌한다(`build.sh` 가 검사해서 막는다).
- 발표자 노트는 각 페이지 끝의 `<!-- ... -->` 주석. PPTX 노트와 PDF annotation 으로 들어간다.
- 리드(챕터 표지) 페이지는 첫 줄이 `<!-- _class: lead -->`.
- 페이지를 추가·삭제하면 파일명 번호를 다시 매긴다. `build.sh` 는 파일명 정렬 순서대로 이어붙인다.
- 밀도 규칙: 본문 6행 이하 · 표 5행 이하(헤더 제외) · **다이어그램 1개/페이지** · 코드 블록은 덱 전체에서 4개 이하.
- `script.md` 의 섹션 번호는 페이지 번호와 1:1 이다. 페이지를 옮기면 대본도 같이 옮겨야 한다.

## 다이어그램 킷 사용법

```html
<div class="seq" data-seq="A|B|C" data-accent="dim|red|green"></div>
<div class="stack" data-stack="1층|2층|3층" data-accent="red|red|green"></div>
<div class="steps" data-steps="첫째|둘째|셋째" data-start="1"></div>
<div class="cmp" data-left-title="좌" data-left="a|b" data-right-title="우" data-right="c|d"></div>
```

- `|` 로 항목 구분, 노드 안에서 줄바꿈은 `\n`(백슬래시+n).
- `data-accent` 색: `cyan` `green` `gold` `red` `orange` `dim`. 생략하면 기본값.
- `.cmp` 는 좌측이 빨강(문제/오해), 우측이 초록(해법/사실)으로 고정이다.
