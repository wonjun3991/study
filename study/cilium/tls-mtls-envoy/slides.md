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
    padding: 48px 60px;
  }
  h1 {
    color: #00d4ff;
    border-bottom: 2px solid #00d4ff;
    padding-bottom: 8px;
    font-size: 1.42em;
    margin-bottom: 14px;
  }
  h2 { color: #00d4ff; font-size: 1.18em; }
  h3 { color: #7fdbff; font-size: 1.0em; margin-bottom: 6px; }
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
    padding: 12px 14px;
  }
  pre code {
    background-color: transparent !important;
    color: #e6edf3;
    font-size: 0.62em;
    line-height: 1.4;
  }
  table { font-size: 0.68em; margin: 4px auto 8px auto; border-collapse: separate; border-spacing: 0; border-radius: 6px; overflow: hidden; }
  th { background-color: #16213e; color: #00d4ff; padding: 6px 12px; }
  td { background-color: #0f3460; padding: 6px 12px; }
  blockquote {
    border-left: 4px solid #ffd700;
    background-color: #2a1f3d;
    padding: 10px 18px;
    margin: 12px 0;
    font-style: normal;
    font-size: 0.86em;
    border-radius: 4px;
  }
  section.lead h1 { text-align: center; font-size: 2.1em; border: none; }
  section.lead p { text-align: center; font-size: 1.05em; }
  ul, ol { padding-left: 22px; }
  li { margin: 4px 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .columns3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  .small { font-size: 0.78em; color: #9aa0b0; }
  .tag { color: #00d4ff; font-size: 0.8em; letter-spacing: 0.04em; }
  .cap { font-size: 0.66em; color: #9aa0b0; text-align: center; margin-top: 2px; }
  .cap b { color: #ffd700; }
  svg { display: block; width: 100%; height: auto; margin: 0 auto; }
  .svgtext { font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; }
  .box { border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; background: #16213e55; }
  .box.red { border-color: #ff6b6b88; }
  .box.gold { border-color: #ffd70088; }
  .box.cyan { border-color: #00d4ff88; }
---
<!-- _class: lead -->

# mTLS · TLS · 그리고<br/>Envoy가 암호를 풀었다 다시 감을 때

<span class="tag">평문 HTTP → TLS → mTLS → 프록시 종료 — 순서와 그 대가</span>

Cilium 스터디 보충 자료

<!--
오늘은 Cilium 본편에서 잠깐 스쳐 지나간 주제를 제대로 파고든다.
"L7 정책을 걸려면 프록시가 평문을 봐야 한다"는 한 줄 문장 뒤에 숨은 비용이 뭔지.
순서는 평문 HTTP → TLS → mTLS → Envoy가 끼어들었을 때, 이렇게 네 단계로 간다.
마지막에 Cilium이 이 문제를 어떻게 비껴가는지로 마무리한다.
-->

---

# 오늘 답할 네 가지 질문

<div class="columns">
<div>

**통신 순서**
1. 평문 HTTP는 어떤 순서로 오가나?
2. TLS가 끼면 그 순서가 어떻게 바뀌나?
3. mTLS는 거기서 무엇이 더 붙나?

</div>
<div>

**그리고 대가**
4. Envoy가 TLS를 **복호화했다 재암호화**하면
   - 무엇이 평문으로 노출되고
   - 무엇이 느려지고
   - 무엇이 망가지나?

</div>
</div>

> 한 줄 요약: **L7 가시성과 종단간 암호화는 동시에 성립할 수 없다.** 선택지는 "누가, 얼마나 오래, 얼마나 멀리 평문을 들고 있는가"뿐이다.

<!--
질문을 먼저 못 박아두고 시작한다. 앞의 세 개는 사실 확인 문제고, 네 번째가 오늘의 본론이다.
아래 blockquote가 오늘 발표의 결론이다. 지금은 이해 안 돼도 되고, 마지막 슬라이드에서 다시 나온다.
"동시에 성립할 수 없다" — 이건 구현이 미숙해서가 아니라 원리적으로 그렇다는 뜻이다. 그 이유를 오늘 증명한다.
-->

---

<!-- _class: lead -->

# 01 — 평문 HTTP

<span class="tag">아무것도 감추지 않을 때의 순서</span>

<!--
기준점부터. 암호화가 하나도 없을 때 HTTP 한 번이 어떤 순서로 오가는지.
여기서 "몇 RTT 걸리나"와 "와이어에 뭐가 보이나" 두 숫자를 기억해두면
뒤에서 TLS·mTLS·Envoy가 붙을 때마다 얼마씩 늘어나는지 바로 비교된다.
-->

---

# 평문 HTTP — 통신 순서

<svg viewBox="0 0 1000 330" style="max-height:420px">
<defs>
<marker id="c1" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00d4ff"/></marker>
<marker id="n1" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00ff88"/></marker>
</defs>
<rect x="70" y="6" width="220" height="40" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="180" y="32" fill="#e6ecf5" font-size="16" text-anchor="middle" font-weight="700">Client Pod (curl)</text>
<rect x="710" y="6" width="220" height="40" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="820" y="32" fill="#e6ecf5" font-size="16" text-anchor="middle" font-weight="700">Server Pod :80</text>
<line x1="180" y1="48" x2="180" y2="318" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<line x1="820" y1="48" x2="820" y2="318" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<text class="svgtext" x="500" y="76" fill="#7fdbff" font-size="14" text-anchor="middle">① TCP SYN</text>
<line x1="180" y1="84" x2="812" y2="84" stroke="#00d4ff" stroke-width="2" marker-end="url(#c1)"/>
<text class="svgtext" x="500" y="106" fill="#7fdbff" font-size="14" text-anchor="middle">② SYN + ACK</text>
<line x1="820" y1="114" x2="188" y2="114" stroke="#00d4ff" stroke-width="2" marker-end="url(#c1)"/>
<text class="svgtext" x="500" y="136" fill="#7fdbff" font-size="14" text-anchor="middle">③ ACK</text>
<line x1="180" y1="144" x2="812" y2="144" stroke="#00d4ff" stroke-width="2" marker-end="url(#c1)"/>
<path d="M74 82 L58 82 L58 146 L74 146" fill="none" stroke="#9aa0b0" stroke-width="1.4"/>
<text class="svgtext" x="52" y="118" fill="#9aa0b0" font-size="13" text-anchor="end">1 RTT</text>
<text class="svgtext" x="500" y="182" fill="#00ff88" font-size="14" text-anchor="middle">④ GET /api/orders HTTP/1.1 · Host: api · Authorization: Bearer eyJhbGci…</text>
<line x1="180" y1="192" x2="812" y2="192" stroke="#00ff88" stroke-width="3" marker-end="url(#n1)"/>
<text class="svgtext" x="500" y="222" fill="#00ff88" font-size="14" text-anchor="middle">⑤ HTTP/1.1 200 OK · {"orderId":1024,"card":"4111-…"}</text>
<line x1="820" y1="232" x2="188" y2="232" stroke="#00ff88" stroke-width="3" marker-end="url(#n1)"/>
<path d="M74 190 L58 190 L58 234 L74 234" fill="none" stroke="#9aa0b0" stroke-width="1.4"/>
<text class="svgtext" x="52" y="216" fill="#9aa0b0" font-size="13" text-anchor="end">1 RTT</text>
<rect x="150" y="252" width="700" height="66" rx="10" fill="#ff6b6b1a" stroke="#ff6b6b" stroke-width="1.4"/>
<text class="svgtext" x="500" y="277" fill="#ff9b9b" font-size="15" text-anchor="middle">④⑤의 모든 바이트가 평문 — 경로상 스위치·라우터·tcpdump·CNI가 그대로 읽는다</text>
<text class="svgtext" x="500" y="302" fill="#9aa0b0" font-size="14" text-anchor="middle">동시에, 그래서 프록시·eBPF가 method / path / header 를 보고 L7 정책을 걸 수 있다</text>
</svg>

<div class="cap">첫 요청 바이트를 보내기까지 <b>1 RTT</b> · 응답까지 <b>2 RTT</b></div>

<!--
순서 자체는 단순하다. TCP 3-way handshake 한 왕복, 그다음 요청·응답 한 왕복.
③번 ACK에 요청을 실어보낼 수도 있으니 실무적으로는 "1 RTT 뒤에 요청이 나간다"고 기억하면 된다.
중요한 건 아래 빨간 박스다. 두 문장이 정확히 같은 사실의 앞뒷면이다.
평문이라 위험하다 = 평문이라 정책을 걸 수 있다. 오늘 발표 내내 이 동전의 양면이 계속 나온다.
-->

---

# 평문의 양면성 — 위험이자 전제

<div class="columns">
<div class="box red">

### ❌ 위험

- Authorization 토큰·쿠키·PII가 그대로
- 경로상 어느 홉에서든 **수정** 가능 (무결성 없음)
- 상대가 진짜 그 서버인지 **확인 불가**

</div>
<div class="box cyan">

### ✅ 전제

- Envoy가 `method` / `path` / `header` 파싱 가능
- L7 AuthorizationPolicy, 경로 라우팅, 재시도
- 요청 단위 메트릭 · 분산 트레이싱

</div>
</div>

> 보안이 요구하는 것과 관측·정책이 요구하는 것이 **정확히 반대**다. TLS는 위쪽을 해결하면서 아래쪽을 파괴한다.

<!--
왼쪽은 우리가 TLS를 쓰는 이유고, 오른쪽은 서비스 메시가 존재하는 이유다.
그런데 둘이 같은 자원, 즉 "평문을 볼 수 있느냐"를 놓고 다툰다.
이 충돌이 뒤에서 Envoy 사이드카 구조를 낳는 원인이다. 지금은 충돌이 있다는 것만 잡고 넘어가자.
-->

---

<!-- _class: lead -->

# 02 — TLS

<span class="tag">순서가 어떻게 바뀌고, 무엇이 남는가</span>

<!--
이제 TLS를 씌운다. 두 가지를 볼 건데,
하나는 핸드셰이크 때문에 순서와 RTT가 어떻게 바뀌는지,
다른 하나는 암호화 뒤에도 여전히 와이어에 남아 있는 정보가 뭔지.
두 번째가 Cilium 같은 L3/L4 데이터플레인한테 훨씬 중요한 얘기다.
-->

---

# TLS 1.3 — 통신 순서

<svg viewBox="0 0 1000 400" style="max-height:430px">
<defs>
<marker id="c2" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00d4ff"/></marker>
<marker id="n2" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00ff88"/></marker>
<marker id="r2" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ff6b6b"/></marker>
</defs>
<rect x="70" y="4" width="220" height="38" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="180" y="29" fill="#e6ecf5" font-size="16" text-anchor="middle" font-weight="700">Client</text>
<rect x="710" y="4" width="220" height="38" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="820" y="29" fill="#e6ecf5" font-size="16" text-anchor="middle" font-weight="700">Server :443</text>
<line x1="180" y1="44" x2="180" y2="330" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<line x1="820" y1="44" x2="820" y2="330" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<text class="svgtext" x="500" y="66" fill="#7fdbff" font-size="13" text-anchor="middle">①②③ TCP 3-way handshake</text>
<line x1="180" y1="76" x2="812" y2="76" stroke="#00d4ff" stroke-width="2" marker-end="url(#c2)"/>
<line x1="820" y1="92" x2="188" y2="92" stroke="#00d4ff" stroke-width="2" marker-end="url(#c2)"/>
<line x1="180" y1="108" x2="812" y2="108" stroke="#00d4ff" stroke-width="2" marker-end="url(#c2)"/>
<text class="svgtext" x="500" y="142" fill="#ff9b9b" font-size="14" text-anchor="middle">④ ClientHello — versions · cipher_suites · key_share · SNI=api.example.com · ALPN=h2</text>
<text class="svgtext" x="500" y="160" fill="#9aa0b0" font-size="12" text-anchor="middle">아직 키가 없다 → 이 메시지는 전부 평문</text>
<line x1="180" y1="170" x2="812" y2="170" stroke="#ff6b6b" stroke-width="2.6" marker-end="url(#r2)"/>
<text class="svgtext" x="500" y="200" fill="#7fdbff" font-size="14" text-anchor="middle">⑤ ServerHello (key_share) — 여기까지 평문</text>
<text class="svgtext" x="500" y="220" fill="#00ff88" font-size="14" text-anchor="middle">[ EncryptedExtensions · Certificate · CertificateVerify · Finished ]</text>
<line x1="820" y1="230" x2="188" y2="230" stroke="#00ff88" stroke-width="2.6" marker-end="url(#n2)"/>
<path d="M74 168 L58 168 L58 232 L74 232" fill="none" stroke="#ffd700" stroke-width="1.6"/>
<text class="svgtext" x="52" y="196" fill="#ffd700" font-size="13" text-anchor="end">1 RTT</text>
<text class="svgtext" x="500" y="262" fill="#00ff88" font-size="14" text-anchor="middle">⑥ [ Finished ] + [ GET /api/orders ] — 앱 데이터를 같은 비행에 동봉 가능</text>
<line x1="180" y1="272" x2="812" y2="272" stroke="#00ff88" stroke-width="3" marker-end="url(#n2)"/>
<text class="svgtext" x="500" y="302" fill="#00ff88" font-size="14" text-anchor="middle">⑦ [ HTTP/1.1 200 OK ]</text>
<line x1="820" y1="312" x2="188" y2="312" stroke="#00ff88" stroke-width="3" marker-end="url(#n2)"/>
<rect x="130" y="342" width="740" height="52" rx="10" fill="#ffd7001a" stroke="#ffd700" stroke-width="1.3"/>
<text class="svgtext" x="500" y="363" fill="#ffd700" font-size="14" text-anchor="middle">[ ] = 암호화 구간 · 클라이언트는 ⑤에서 인증서 체인과 호스트명을 검증한 뒤에야 ⑥을 보낸다</text>
<text class="svgtext" x="500" y="384" fill="#9aa0b0" font-size="13" text-anchor="middle">TLS 1.2 는 ServerHelloDone · ClientKeyExchange · ChangeCipherSpec 왕복이 한 번 더 필요하다</text>
</svg>

<!--
TCP 3WHS는 그대로고, 그 위에 TLS 핸드셰이크가 얹힌다.
④ ClientHello가 결정적이다. 아직 공유 키가 없으니 통째로 평문이고, 여기 SNI와 ALPN이 들어간다. 이 사실은 다음다음 슬라이드에서 크게 쓰인다.
⑤에서 서버가 key_share를 주는 순간부터 암호화가 시작된다. 그래서 TLS 1.3은 인증서조차 암호화돼서 간다. 1.2는 인증서가 평문이었다.
⑥에서 클라이언트가 Finished와 함께 애플리케이션 데이터를 바로 실어보낼 수 있다. 이게 1.3이 1-RTT인 이유.
-->

---

# RTT 비교 — 무엇이 얼마나 늘어나나

| 구간 | 평문 HTTP | HTTPS (TLS 1.2) | HTTPS (TLS 1.3) | TLS 1.3 재개(0-RTT) |
|---|---|---|---|---|
| TCP 핸드셰이크 | 1 RTT | 1 RTT | 1 RTT | 1 RTT |
| TLS 핸드셰이크 | — | **2 RTT** | **1 RTT** | 0 RTT |
| **첫 요청 바이트까지** | **1 RTT** | **3 RTT** | **2 RTT** | **1 RTT** |
| 바이트당 대칭 암복호 | 없음 | 양단 각 1회 | 양단 각 1회 | 양단 각 1회 |
| 연결당 비대칭 연산 | 없음 | 서명 검증 1회 | 서명 검증 1회 | 생략 가능 |

- **0-RTT 재개**는 replay 공격에 취약하므로 멱등 요청(GET)에만 써야 한다.
- RTT 비용은 **연결당 1회**다. keep-alive / HTTP2 멀티플렉싱으로 상각된다.
- 진짜 지속 비용은 RTT가 아니라 **바이트당 대칭 암복호**와, 잠시 뒤 볼 **프록시 홉**이다.

<!--
숫자로 정리하고 넘어간다. 흔히 "TLS 느리다"고 하는데, 핸드셰이크 RTT는 연결당 한 번이라 커넥션 풀 쓰면 거의 사라진다.
남는 건 바이트당 AES 연산인데 요즘 CPU는 AES-NI가 있어서 이것도 생각보다 싸다.
정말 비싼 건 마지막 줄, 프록시 홉이다. 이게 오늘 본론이고 4번 섹션에서 다룬다.
0-RTT는 편의를 위해 replay 위험을 사는 거라 실무에서 조심해야 한다는 것만 짚고 넘어가자.
-->

---

# 암호화해도 남는 것 vs 사라지는 것

<svg viewBox="0 0 1000 210" style="max-height:280px">
<text class="svgtext" x="10" y="26" fill="#7fdbff" font-size="15" font-weight="700">핸드셰이크 첫 패킷 (ClientHello)</text>
<rect x="20" y="36" width="90" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="65" y="64" fill="#9aa0b0" font-size="13" text-anchor="middle">Eth</text>
<rect x="112" y="36" width="148" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="186" y="59" fill="#e6ecf5" font-size="13" text-anchor="middle">IP</text>
<text class="svgtext" x="186" y="75" fill="#9aa0b0" font-size="11" text-anchor="middle">src / dst</text>
<rect x="262" y="36" width="148" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="336" y="59" fill="#e6ecf5" font-size="13" text-anchor="middle">TCP</text>
<text class="svgtext" x="336" y="75" fill="#9aa0b0" font-size="11" text-anchor="middle">sport / dport</text>
<rect x="412" y="36" width="118" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="471" y="64" fill="#9aa0b0" font-size="12" text-anchor="middle">TLS record</text>
<rect x="532" y="36" width="448" height="46" rx="6" fill="#ffd7001f" stroke="#ffd700" stroke-width="1.6"/>
<text class="svgtext" x="756" y="59" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">ClientHello — SNI · ALPN · cipher list</text>
<text class="svgtext" x="756" y="75" fill="#9aa0b0" font-size="11" text-anchor="middle">전부 평문 (ECH 미사용 시)</text>
<text class="svgtext" x="10" y="122" fill="#7fdbff" font-size="15" font-weight="700">이후 애플리케이션 데이터 패킷</text>
<rect x="20" y="132" width="90" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="65" y="160" fill="#9aa0b0" font-size="13" text-anchor="middle">Eth</text>
<rect x="112" y="132" width="148" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="186" y="160" fill="#e6ecf5" font-size="13" text-anchor="middle">IP src / dst</text>
<rect x="262" y="132" width="148" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="336" y="160" fill="#e6ecf5" font-size="13" text-anchor="middle">TCP 포트</text>
<rect x="412" y="132" width="118" height="46" rx="6" fill="#16213e" stroke="#3a4570"/>
<text class="svgtext" x="471" y="160" fill="#9aa0b0" font-size="12" text-anchor="middle">type / len</text>
<rect x="532" y="132" width="448" height="46" rx="6" fill="#ff6b6b1f" stroke="#ff6b6b" stroke-width="1.6"/>
<text class="svgtext" x="756" y="155" fill="#ff9b9b" font-size="14" text-anchor="middle" font-weight="700">▨ 암호문 ▨</text>
<text class="svgtext" x="756" y="171" fill="#9aa0b0" font-size="11" text-anchor="middle">method · path · header · cookie · body 전부 여기 안</text>
<text class="svgtext" x="10" y="202" fill="#9aa0b0" font-size="13">남는 것: IP · 포트 · SNI · ALPN · 패킷 크기 / 타이밍  ⟶  L3/L4 정책은 여전히 가능, L7 정책은 불가능</text>
</svg>

<!--
이 슬라이드가 오늘 가장 실용적인 그림이다.
위 줄: 핸드셰이크 첫 패킷은 키 협상 전이라 SNI가 평문으로 노출된다. 그래서 "어느 도메인에 붙었는지"는 감출 수 없다. ECH가 이걸 고치려는 표준인데 아직 보편화 전이다.
아래 줄: 그 이후 모든 패킷에서 HTTP는 통째로 암호문 안에 들어간다.
결론은 맨 아래 줄. IP·포트·SNI는 남으니 eBPF의 L3/L4 정책과 FQDN 정책은 그대로 작동한다. 하지만 method나 path 기반 정책은 원리적으로 불가능해진다.
-->

---

# 그래서 L7 정책은 원천적으로 불가능하다

```text
CiliumNetworkPolicy — L4까지
  toPorts: [{ port: "443", protocol: TCP }]        ✅ 커널 eBPF에서 판단 가능

CiliumNetworkPolicy — L7
  rules:
    http:
      - method: "GET"
        path: "/api/orders"                        ❌ 암호문 안이라 볼 수 없음
```

- eBPF는 패킷 하나를 훅에서 즉시 판단한다. **복호화 키도, 스트림 재조합 상태도 없다.**
- 정책이 `path`를 보려면 **누군가 반드시 복호화해야 한다.** 예외 없다.
- 그 "누군가"가 프록시 — Istio에선 사이드카 Envoy, Cilium에선 노드당 `cilium-envoy`.

> L7 정책을 켜는 순간 당신은 **의도적으로 중간자(MITM)를 세우는 것**이다. 문제는 그 대가가 뭐냐다.

<!--
5주차에서 "eBPF는 L3/L4, L7은 프록시"라고 배웠는데, 그 경계선의 진짜 이유가 성능이 아니라 이거다.
암호화된 트래픽에서 path를 보려면 키가 있어야 하고, 키가 있으려면 TLS 세션의 한쪽 끝이 되어야 한다. 즉 프록시가 되어야 한다.
"의도적으로 MITM을 세운다"는 표현이 과격해 보이지만 기술적으로 정확한 서술이다. 여기서부터 4번 섹션의 비용 이야기가 시작된다.
-->

---

<!-- _class: lead -->

# 03 — mTLS

<span class="tag">한쪽이 아니라 양쪽을 증명한다</span>

<!--
그 프록시가 도대체 왜 필요했는지를 이해하려면 mTLS를 먼저 알아야 한다.
서비스 메시가 Envoy를 넣은 첫 번째 이유가 mTLS니까.
일반 TLS와 뭐가 다른지, 순서상 뭐가 추가되는지 보자.
-->

---

# TLS vs mTLS — 누가 누구를 증명하나

<svg viewBox="0 0 1000 250" style="max-height:330px">
<defs>
<marker id="g3" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ffd700"/></marker>
<marker id="c3" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00d4ff"/></marker>
</defs>
<rect x="10" y="4" width="470" height="242" rx="12" fill="#16213e55" stroke="#3a4570"/>
<text class="svgtext" x="245" y="32" fill="#7fdbff" font-size="17" text-anchor="middle" font-weight="700">TLS — 단방향 인증</text>
<rect x="50" y="58" width="130" height="54" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="115" y="91" fill="#e6ecf5" font-size="15" text-anchor="middle">Client</text>
<rect x="310" y="58" width="130" height="54" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="375" y="91" fill="#e6ecf5" font-size="15" text-anchor="middle">Server</text>
<line x1="308" y1="85" x2="188" y2="85" stroke="#ffd700" stroke-width="2.4" marker-end="url(#g3)"/>
<text class="svgtext" x="245" y="134" fill="#ffd700" font-size="13" text-anchor="middle">서버 인증서 제출</text>
<text class="svgtext" x="245" y="152" fill="#9aa0b0" font-size="12" text-anchor="middle">클라이언트가 신뢰 CA로 검증</text>
<rect x="40" y="168" width="400" height="62" rx="8" fill="#ff6b6b14" stroke="#ff6b6b88"/>
<text class="svgtext" x="240" y="191" fill="#ff9b9b" font-size="13" text-anchor="middle">클라이언트 신원은? → 네트워크 계층엔 없음</text>
<text class="svgtext" x="240" y="212" fill="#9aa0b0" font-size="12" text-anchor="middle">앱 계층 JWT · 비밀번호 · API key 에 위임</text>
<rect x="520" y="4" width="470" height="242" rx="12" fill="#ffd70012" stroke="#ffd70066"/>
<text class="svgtext" x="755" y="32" fill="#ffd700" font-size="17" text-anchor="middle" font-weight="700">mTLS — 양방향 인증</text>
<rect x="560" y="58" width="130" height="54" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="625" y="91" fill="#e6ecf5" font-size="15" text-anchor="middle">Client</text>
<rect x="820" y="58" width="130" height="54" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="885" y="91" fill="#e6ecf5" font-size="15" text-anchor="middle">Server</text>
<line x1="818" y1="76" x2="698" y2="76" stroke="#ffd700" stroke-width="2.4" marker-end="url(#g3)"/>
<line x1="692" y1="99" x2="812" y2="99" stroke="#ffd700" stroke-width="2.4" marker-end="url(#g3)"/>
<text class="svgtext" x="755" y="134" fill="#ffd700" font-size="13" text-anchor="middle">서버 인증서 ⇄ 클라이언트 인증서</text>
<text class="svgtext" x="755" y="152" fill="#9aa0b0" font-size="12" text-anchor="middle">양쪽 모두 개인키 소유를 서명으로 증명</text>
<rect x="550" y="168" width="400" height="62" rx="8" fill="#00ff8814" stroke="#00ff8877"/>
<text class="svgtext" x="750" y="191" fill="#00ff88" font-size="13" text-anchor="middle">네트워크 계층에서 양쪽 신원이 확정된다</text>
<text class="svgtext" x="750" y="212" fill="#9aa0b0" font-size="12" text-anchor="middle">인가 기준 = 위조 가능한 IP → 암호학적 워크로드 신원</text>
</svg>

<!--
왼쪽이 우리가 브라우저에서 매일 쓰는 TLS다. 클라이언트는 서버를 검증하지만 서버는 클라이언트가 누군지 네트워크 수준에선 모른다.
오른쪽 mTLS는 서버도 클라이언트 인증서를 요구한다. 그래서 "이 연결의 상대는 frontend 서비스 계정이다"가 암호학적으로 확정된다.
왜 이게 쿠버네티스에서 중요하냐면, Pod IP는 재사용되고 위조 가능하고 몇 분 만에 바뀐다. IP를 신원으로 쓰는 건 원래 무리였다.
-->

---

# mTLS 핸드셰이크 — 무엇이 더 붙나

<svg viewBox="0 0 1000 400" style="max-height:430px">
<defs>
<marker id="c4" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00d4ff"/></marker>
<marker id="g4" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ffd700"/></marker>
<marker id="n4" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00ff88"/></marker>
</defs>
<rect x="70" y="4" width="220" height="36" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="180" y="28" fill="#e6ecf5" font-size="15" text-anchor="middle" font-weight="700">Client (Envoy A)</text>
<rect x="710" y="4" width="220" height="36" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="820" y="28" fill="#e6ecf5" font-size="15" text-anchor="middle" font-weight="700">Server (Envoy B)</text>
<line x1="180" y1="42" x2="180" y2="392" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<line x1="820" y1="42" x2="820" y2="392" stroke="#3a4570" stroke-width="2" stroke-dasharray="5 5"/>
<text class="svgtext" x="500" y="62" fill="#7fdbff" font-size="13" text-anchor="middle">ClientHello (TCP 3WHS 이후)</text>
<line x1="180" y1="72" x2="812" y2="72" stroke="#00d4ff" stroke-width="2" marker-end="url(#c4)"/>
<text class="svgtext" x="500" y="94" fill="#7fdbff" font-size="13" text-anchor="middle">ServerHello · [ EncryptedExtensions ]</text>
<line x1="820" y1="104" x2="188" y2="104" stroke="#00d4ff" stroke-width="2" marker-end="url(#c4)"/>
<text class="svgtext" x="500" y="128" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">+ [ CertificateRequest ] — 서버가 클라 인증서를 요구</text>
<line x1="820" y1="138" x2="188" y2="138" stroke="#ffd700" stroke-width="2.8" marker-end="url(#g4)"/>
<text class="svgtext" x="500" y="160" fill="#7fdbff" font-size="13" text-anchor="middle">[ Certificate(server) · CertificateVerify · Finished ]</text>
<line x1="820" y1="170" x2="188" y2="170" stroke="#00d4ff" stroke-width="2" marker-end="url(#c4)"/>
<text class="svgtext" x="500" y="200" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">+ [ Certificate ] — SAN: URI spiffe://cluster.local/ns/shop/sa/frontend</text>
<line x1="180" y1="210" x2="812" y2="210" stroke="#ffd700" stroke-width="2.8" marker-end="url(#g4)"/>
<text class="svgtext" x="500" y="234" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">+ [ CertificateVerify ] — 개인키로 transcript 서명 = 키 소유 증명</text>
<line x1="180" y1="244" x2="812" y2="244" stroke="#ffd700" stroke-width="2.8" marker-end="url(#g4)"/>
<text class="svgtext" x="500" y="266" fill="#7fdbff" font-size="13" text-anchor="middle">[ Finished ]</text>
<line x1="180" y1="276" x2="812" y2="276" stroke="#00d4ff" stroke-width="2" marker-end="url(#c4)"/>
<rect x="600" y="292" width="380" height="56" rx="8" fill="#ffd7001a" stroke="#ffd700" stroke-width="1.4"/>
<text class="svgtext" x="790" y="313" fill="#ffd700" font-size="13" text-anchor="middle">체인 검증 → SPIFFE ID 추출</text>
<text class="svgtext" x="790" y="333" fill="#9aa0b0" font-size="12" text-anchor="middle">→ AuthorizationPolicy / CNP 평가 → allow · deny</text>
<text class="svgtext" x="380" y="370" fill="#00ff88" font-size="13" text-anchor="middle">[ 200 OK ] 또는 RBAC deny</text>
<line x1="820" y1="380" x2="188" y2="380" stroke="#00ff88" stroke-width="2.6" marker-end="url(#n4)"/>
</svg>

<div class="cap">노란 줄 세 개가 mTLS의 전부 — <b>RTT는 늘지 않는다.</b> 늘어나는 건 비대칭 연산 2회와 flight 크기.</div>

<!--
노란색 세 줄만 보면 된다. CertificateRequest, 클라이언트 Certificate, 클라이언트 CertificateVerify.
자주 오해하는 게 "mTLS는 왕복이 더 필요하다"인데 아니다. 기존 flight 안에 메시지가 추가될 뿐이라 RTT 수는 같다.
대신 서명 생성 1회, 검증 1회가 양쪽에 추가된다. 연결이 짧고 많으면 이게 CPU로 체감된다. 그래서 커넥션 재사용이 중요하다.
마지막 노란 박스가 핵심 가치다. 여기서 나온 SPIFFE ID가 곧 AuthorizationPolicy의 주체가 된다.
-->

---

# 메시가 mTLS를 원하는 진짜 이유

<div class="columns">
<div>

### 신원 = 인증서, IP 아님

```text
SAN: URI, spiffe://cluster.local
        /ns/shop/sa/frontend
```

- Pod IP는 **재사용·위조·수시 변경**
- SPIFFE ID는 ServiceAccount에 고정

</div>
<div>

### 운영 특성

- **단명 인증서** (24h 내외) + 자동 rotation
- **SDS**로 UDS를 통해 메모리 전달 — 디스크에 키를 쓰지 않음
- 앱 코드 **무수정**

</div>
</div>

> 얻는 것: L3/L4 정책이 "어느 IP에서 왔나"가 아니라 **"어느 워크로드가 왔나"**로 바뀐다. 그런데 이걸 얻으려고 세운 Envoy가, 바로 다음 섹션의 모든 문제의 원인이 된다.

<!--
SPIFFE ID는 URI 형태의 SAN으로 인증서에 박힌다. istiod나 SPIRE가 발급하고 하루도 안 되는 수명으로 계속 갱신한다.
SDS는 이 인증서를 유닉스 도메인 소켓으로 Envoy 메모리에 직접 꽂아주는 프로토콜이다. 디스크에 개인키 파일이 안 남는 게 포인트.
그리고 마지막 문장. 지금까지는 mTLS의 장점만 봤는데, 이걸 구현하려고 Pod마다 Envoy를 넣은 그 결정이 다음 섹션의 문제 목록 전부를 만든다.
-->

---

<!-- _class: lead -->

# 04 — Envoy가 풀었다 다시 감을 때

<span class="tag">TLS termination & re-origination 의 청구서</span>

<!--
드디어 본론이다. 질문했던 그 부분.
Envoy가 TLS를 복호화하고 재암호화하면 정확히 무슨 일이 벌어지는지, 경로를 한 장에 그려놓고 문제를 네 개로 나눠서 본다.
-->

---

# 사이드카 전체 경로 — 평문 구간이 어디인가

<svg viewBox="0 0 1000 415" style="max-height:445px">
<defs>
<marker id="r5" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ff6b6b"/></marker>
<marker id="g5" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ffd700"/></marker>
<marker id="n5" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00ff88"/></marker>
</defs>
<rect x="20" y="2" width="450" height="24" rx="6" fill="#00d4ff14" stroke="#00d4ff66"/>
<text class="svgtext" x="245" y="19" fill="#7fdbff" font-size="13" text-anchor="middle" font-weight="700">Pod A — frontend</text>
<rect x="530" y="2" width="450" height="24" rx="6" fill="#00d4ff14" stroke="#00d4ff66"/>
<text class="svgtext" x="755" y="19" fill="#7fdbff" font-size="13" text-anchor="middle" font-weight="700">Pod B — orders</text>
<rect x="30" y="32" width="150" height="36" rx="8" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="105" y="55" fill="#e6ecf5" font-size="14" text-anchor="middle" font-weight="700">App A</text>
<rect x="300" y="32" width="150" height="36" rx="8" fill="#16213e" stroke="#ffd700" stroke-width="2"/>
<text class="svgtext" x="375" y="55" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">Envoy A</text>
<rect x="560" y="32" width="150" height="36" rx="8" fill="#16213e" stroke="#ffd700" stroke-width="2"/>
<text class="svgtext" x="635" y="55" fill="#ffd700" font-size="14" text-anchor="middle" font-weight="700">Envoy B</text>
<rect x="820" y="32" width="150" height="36" rx="8" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="895" y="55" fill="#e6ecf5" font-size="14" text-anchor="middle" font-weight="700">App B</text>
<line x1="105" y1="70" x2="105" y2="360" stroke="#3a4570" stroke-width="1.6" stroke-dasharray="5 5"/>
<line x1="375" y1="70" x2="375" y2="360" stroke="#3a4570" stroke-width="1.6" stroke-dasharray="5 5"/>
<line x1="635" y1="70" x2="635" y2="360" stroke="#3a4570" stroke-width="1.6" stroke-dasharray="5 5"/>
<line x1="895" y1="70" x2="895" y2="360" stroke="#3a4570" stroke-width="1.6" stroke-dasharray="5 5"/>
<rect x="105" y="86" width="270" height="24" rx="5" fill="#ff6b6b1a"/>
<text class="svgtext" x="240" y="103" fill="#ff9b9b" font-size="12" text-anchor="middle" font-weight="700">① GET /orders — 평문, loopback</text>
<line x1="105" y1="120" x2="368" y2="120" stroke="#ff6b6b" stroke-width="2.6" marker-end="url(#r5)"/>
<text class="svgtext" x="240" y="140" fill="#9aa0b0" font-size="11" text-anchor="middle">iptables REDIRECT :15001 (또는 eBPF sockmap)</text>
<text class="svgtext" x="505" y="170" fill="#ffd700" font-size="12" text-anchor="middle" font-weight="700">② TCP 3WHS + mTLS 핸드셰이크 (+1 RTT)</text>
<line x1="375" y1="180" x2="628" y2="180" stroke="#ffd700" stroke-width="2.6" marker-end="url(#g5)"/>
<text class="svgtext" x="505" y="204" fill="#00ff88" font-size="12" text-anchor="middle" font-weight="700">③ [ GET /orders ] 암호화 전송 + XFCC 헤더 주입</text>
<line x1="375" y1="214" x2="628" y2="214" stroke="#00ff88" stroke-width="2.8" marker-end="url(#n5)"/>
<rect x="540" y="234" width="190" height="72" rx="8" fill="#ff6b6b1f" stroke="#ff6b6b" stroke-width="1.6"/>
<text class="svgtext" x="635" y="255" fill="#ff9b9b" font-size="12" text-anchor="middle" font-weight="700">④ 복호화 → 평문</text>
<text class="svgtext" x="635" y="274" fill="#9aa0b0" font-size="11" text-anchor="middle">RBAC (peer SPIFFE ID)</text>
<text class="svgtext" x="635" y="292" fill="#9aa0b0" font-size="11" text-anchor="middle">L7 정책 · 경로 라우팅</text>
<rect x="635" y="318" width="260" height="24" rx="5" fill="#ff6b6b1a"/>
<text class="svgtext" x="765" y="335" fill="#ff9b9b" font-size="12" text-anchor="middle" font-weight="700">⑤ GET /orders — 평문, loopback</text>
<line x1="635" y1="352" x2="888" y2="352" stroke="#ff6b6b" stroke-width="2.6" marker-end="url(#r5)"/>
<rect x="40" y="368" width="920" height="42" rx="8" fill="#ffd70014" stroke="#ffd70066"/>
<text class="svgtext" x="500" y="385" fill="#ffd700" font-size="13" text-anchor="middle" font-weight="700">요청 1건 = TCP 연결 3개 · TLS 암복호 2회 · HTTP 파싱/재직렬화 4회 · 프로세스 경계 4회 통과</text>
<text class="svgtext" x="500" y="403" fill="#9aa0b0" font-size="12" text-anchor="middle">응답은 ⑤→④→③→① 역순으로 같은 비용을 한 번 더 지불한다</text>
</svg>

<!--
이 그림을 천천히 보자. 빨간색이 평문 구간, 초록이 암호화 구간, 노랑이 핸드셰이크다.
①에서 앱은 그냥 http로 호출한다. 앱은 mTLS가 있는지도 모른다. 이게 사이드카의 장점이자 문제의 시작이다.
iptables가 이 소켓을 15001로 돌린다. 여기까지 전부 평문이고 Pod 네트워크 네임스페이스 안이다.
②③에서만 암호화된다. 진짜 암호화되는 구간은 Envoy와 Envoy 사이, 딱 이 구간뿐이다.
④에서 Envoy B가 복호화한다. 이 순간 Envoy B의 메모리에 요청 전문이 평문으로 존재한다. 여기서 RBAC과 L7 정책을 건다.
⑤에서 다시 평문으로 앱에 넘긴다.
맨 아래 노란 띠가 청구서다. 요청 하나에 TCP 연결 3개, 암복호 2회, HTTP 파싱 4회.
-->

---

# 문제 ① — E2E가 아니라 hop-by-hop이다

<div class="columns">
<div class="box red">

### 평문이 존재하는 곳

- Pod A의 loopback (App A ↔ Envoy A)
- **Envoy A 프로세스 메모리**
- **Envoy B 프로세스 메모리**
- Pod B의 loopback (Envoy B ↔ App B)

</div>
<div class="box">

### 공격 표면

- Pod 내 `CAP_NET_RAW` → `tcpdump -i lo`
- `kubectl debug` 임시 컨테이너, ephemeral sidecar
- Envoy 침해 시 **평문 + 신원 위조** 동시 획득
- 코어 덤프 · 메모리 스크래핑

</div>
</div>

> "서비스 메시를 켰으니 종단간 암호화된다"는 **틀린 문장**이다. 정확히는 *Envoy-to-Envoy 구간만* 암호화된다. 신뢰 경계가 앱이 아니라 **Pod 샌드박스**로 이동했을 뿐이다.

<!--
가장 자주 오해하는 부분이다. mTLS를 켰다고 종단간 암호화가 된 게 아니다.
실제로 애플리케이션 컨테이너 안에서 tcpdump를 뜨면 다른 서비스로 나가는 요청이 그대로 평문으로 잡힌다. 실습으로 보여주면 사람들이 놀란다.
그럼 무의미하냐? 아니다. 네트워크 도청과 노드 간 스니핑은 확실히 막는다. 다만 "Pod 안은 신뢰한다"는 가정을 새로 깔고 있다는 걸 인지해야 한다.
보안 심사에서 "E2E 암호화 되어 있습니다"라고 답하면 안 되고 "Pod 경계까지 신뢰, 노드 간은 mTLS"라고 정확히 말해야 한다.
-->

---

# 문제 ② — 비용

| 항목 | 프록시 없음 | 사이드카 mTLS |
|---|---|---|
| 요청 경로의 TCP 연결 수 | 1 | **3** |
| 바이트당 암복호 | 0 | **2회** (A 암호화, B 복호화) |
| HTTP 파싱 / 재직렬화 | 0 | **4회** |
| 첫 요청까지 RTT | 1 | **3** (TCP + mTLS 1.3) |
| Pod당 상주 메모리 | 0 | Envoy 1개 분량 추가 |
| 컨트롤플레인 설정 전파 | 없음 | Pod 수에 비례해 xDS 증가 |

- 지연은 대개 **밀리초 단위**로 잡히지만, 문제가 되는 건 평균이 아니라 **p99 꼬리**다.
- 사이드카가 **Pod 수만큼** 존재한다 → 노드당 수용 Pod 감소, 기동 지연, 롤링 업데이트 폭증.

> 실측 수치는 워크로드·CPU·커넥션 재사용률에 따라 크게 달라진다. **구조적으로 늘어나는 항목**을 기억하는 게 숫자를 외우는 것보다 유용하다.

<!--
표의 왼쪽/오른쪽 대비만 봐도 충분하다. 특히 위 세 줄.
연결 3개, 암복호 2회, 파싱 4회. 이건 환경과 무관하게 구조적으로 발생한다.
지연 수치를 굳이 외우지 말라고 한 이유는, 벤치마크마다 편차가 너무 크고 커넥션 재사용률에 지배되기 때문이다.
대신 마지막 불릿이 실무에서 진짜 아픈 부분이다. Pod 1000개면 Envoy 1000개. 메모리도 메모리지만 xDS 설정 전파량이 제곱으로 늘어난다.
Istio Ambient가 ztunnel을 DaemonSet으로 뺀 이유가 정확히 이거다.
-->

---

# 문제 ③ — 의미 손실과 운영 함정

<div class="columns">
<div>

**연결 의미가 바뀐다**
- 앱이 보는 src IP = `127.0.0.1`
- 원 신원은 `X-Forwarded-Client-Cert` 헤더로 재주입 → **헤더를 신뢰해야 함**
- 앱이 XFCC를 직접 받지 않도록 막아야 스푸핑 방지

</div>
<div>

**프로토콜 충실도**
- h2 → h1.1 다운그레이드 변환, 헤더 케이스 정규화
- trailer · WebSocket · 양방향 gRPC 스트리밍 엣지케이스
- 파싱 못 하는 프로토콜은 raw TCP 패스스루로 강등 → **L7 기능 상실**

</div>
</div>

**수명주기 경합** — Envoy보다 앱이 먼저 뜨면 `connection refused`, 앱보다 Envoy가 먼저 죽으면 트래픽 블랙홀. (k8s 1.29 native sidecar로 완화)

**인증서 배관** — SDS, cert rotation, CA rotation, 시계 오차 → 핸드셰이크 실패. 디버깅이 앱 로그가 아니라 프록시 로그로 이동한다.

<!--
①②가 보안과 성능이었다면 ③은 "운영하다 보면 만나는 것들"이다.
src IP가 127.0.0.1이 되는 건 로깅·레이트리밋·IP 화이트리스트를 쓰는 레거시 앱을 통째로 깨뜨린다.
XFCC 헤더는 특히 조심해야 한다. 외부에서 들어온 요청이 이 헤더를 달고 오면 신원을 위조할 수 있으니 엣지에서 반드시 제거해야 한다.
프로토콜 충실도 문제는 gRPC 스트리밍이나 WebSocket 쓰는 팀이 반드시 한 번은 밟는다.
그리고 마지막. 장애가 났을 때 봐야 할 로그가 앱 로그에서 Envoy 로그로 옮겨간다. 팀 전체의 디버깅 습관을 바꿔야 한다.
-->

---

# 문제 ④ — 근본 딜레마

<div class="columns">
<div class="box cyan">

### 앱이 진짜 E2E TLS를 하면

- 평문은 App A · App B 안에만 존재 ✅
- Envoy는 **TCP 바이트 스트림**만 봄
- 경로 라우팅 · L7 RBAC · HTTP 메트릭 **전부 불가**
- 얻는 건 L4 통계와 연결 수뿐

</div>
<div class="box gold">

### 메시가 TLS를 종료하면

- L7 기능 **전부 가능** ✅
- 대신 평문이 **프록시 메모리**에 존재
- 신뢰 경계가 앱 → Pod 샌드박스로 확대
- 프록시가 곧 최우선 공격 표적

</div>
</div>

> **둘 다는 원리적으로 불가능하다.** L7 판단은 평문 없이는 정의되지 않기 때문이다.
> 실제 설계 선택지는 딱 세 가지: *평문을 누가 쥐는가 · 얼마나 오래 쥐는가 · 얼마나 멀리 옮기는가.*

<!--
이게 오늘의 결론 슬라이드다. 2번 슬라이드에서 예고했던 그 문장.
왼쪽을 고르면 보안은 최고인데 서비스 메시를 쓸 이유가 거의 없어진다. L4 통계만 얻자고 사이드카를 넣진 않으니까.
오른쪽이 현실적인 선택인데, 그 대가가 앞의 ①②③이었다.
그래서 좋은 설계란 이 딜레마를 없애는 게 아니라, 세 가지 축 — 누가, 얼마나 오래, 얼마나 멀리 — 을 최소화하는 거다.
Istio Ambient가 L7 Waypoint를 옵션으로 뺀 것도, Cilium이 L7 정책이 있는 흐름만 Envoy로 우회시키는 것도 전부 이 최소화 전략이다.
-->

---

<!-- _class: lead -->

# 05 — Cilium은 어떻게 비껴가나

<span class="tag">복호화하지 않고도 되는 부분은 복호화하지 않는다</span>

<!--
마지막 섹션. 그럼 Cilium은 이 딜레마를 어떻게 다루느냐.
스포일러: 딜레마를 깨지는 못한다. 대신 "복호화가 필요 없는 일"을 최대한 늘려서 프록시를 타는 트래픽 자체를 줄인다.
-->

---

# Cilium 경로 — 프록시 홉이 없다

<svg viewBox="0 0 1000 265" style="max-height:340px">
<defs>
<marker id="c6" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#00d4ff"/></marker>
<marker id="g6" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto"><path d="M0,0 L8,3.2 L0,6.4 Z" fill="#ffd700"/></marker>
</defs>
<rect x="60" y="4" width="230" height="34" rx="8" fill="#16213e" stroke="#ffd70088" stroke-width="1.6"/>
<text class="svgtext" x="175" y="26" fill="#ffd700" font-size="13" text-anchor="middle">cilium-agent A + SPIRE SVID</text>
<rect x="710" y="4" width="230" height="34" rx="8" fill="#16213e" stroke="#ffd70088" stroke-width="1.6"/>
<text class="svgtext" x="825" y="26" fill="#ffd700" font-size="13" text-anchor="middle">cilium-agent B + SPIRE SVID</text>
<line x1="292" y1="21" x2="702" y2="21" stroke="#ffd700" stroke-width="2" stroke-dasharray="7 4" marker-end="url(#g6)"/>
<text class="svgtext" x="500" y="15" fill="#ffd700" font-size="12" text-anchor="middle" font-weight="700">out-of-band mTLS 핸드셰이크</text>
<text class="svgtext" x="500" y="52" fill="#9aa0b0" font-size="12" text-anchor="middle">identity 쌍마다 1회 → 결과를 eBPF auth cache 에 기록 (연결마다 하지 않는다)</text>
<rect x="20" y="86" width="120" height="76" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="80" y="130" fill="#e6ecf5" font-size="14" text-anchor="middle" font-weight="700">App A</text>
<rect x="172" y="86" width="196" height="76" rx="9" fill="#16213e" stroke="#00ff88" stroke-width="2"/>
<text class="svgtext" x="270" y="115" fill="#00ff88" font-size="13" text-anchor="middle" font-weight="700">eBPF TC hook</text>
<text class="svgtext" x="270" y="134" fill="#9aa0b0" font-size="11" text-anchor="middle">security identity 정책</text>
<text class="svgtext" x="270" y="151" fill="#9aa0b0" font-size="11" text-anchor="middle">+ auth cache 확인</text>
<rect x="400" y="86" width="130" height="76" rx="9" fill="#16213e" stroke="#00ff88" stroke-width="2"/>
<text class="svgtext" x="465" y="118" fill="#00ff88" font-size="13" text-anchor="middle" font-weight="700">WireGuard</text>
<text class="svgtext" x="465" y="137" fill="#9aa0b0" font-size="11" text-anchor="middle">커널 암호화</text>
<text class="svgtext" x="465" y="153" fill="#9aa0b0" font-size="11" text-anchor="middle">(또는 IPsec)</text>
<ellipse cx="608" cy="124" rx="58" ry="38" fill="#1a1a2e" stroke="#3a4570" stroke-width="1.6"/>
<text class="svgtext" x="608" y="129" fill="#9aa0b0" font-size="12" text-anchor="middle">네트워크</text>
<rect x="686" y="86" width="150" height="76" rx="9" fill="#16213e" stroke="#00ff88" stroke-width="2"/>
<text class="svgtext" x="761" y="118" fill="#00ff88" font-size="13" text-anchor="middle" font-weight="700">복호화 + eBPF</text>
<text class="svgtext" x="761" y="139" fill="#9aa0b0" font-size="11" text-anchor="middle">ingress 정책</text>
<rect x="868" y="86" width="112" height="76" rx="9" fill="#0f3460" stroke="#00d4ff" stroke-width="2"/>
<text class="svgtext" x="924" y="130" fill="#e6ecf5" font-size="14" text-anchor="middle" font-weight="700">App B</text>
<line x1="140" y1="124" x2="166" y2="124" stroke="#00d4ff" stroke-width="2.4" marker-end="url(#c6)"/>
<line x1="368" y1="124" x2="394" y2="124" stroke="#00d4ff" stroke-width="2.4" marker-end="url(#c6)"/>
<line x1="530" y1="124" x2="548" y2="124" stroke="#00d4ff" stroke-width="2.4" marker-end="url(#c6)"/>
<line x1="666" y1="124" x2="680" y2="124" stroke="#00d4ff" stroke-width="2.4" marker-end="url(#c6)"/>
<line x1="836" y1="124" x2="862" y2="124" stroke="#00d4ff" stroke-width="2.4" marker-end="url(#c6)"/>
<text class="svgtext" x="153" y="180" fill="#ff9b9b" font-size="11" text-anchor="middle">평문(소켓)</text>
<text class="svgtext" x="381" y="180" fill="#9aa0b0" font-size="11" text-anchor="middle">커널 내부</text>
<text class="svgtext" x="608" y="180" fill="#00ff88" font-size="11" text-anchor="middle">암호문</text>
<text class="svgtext" x="849" y="180" fill="#ff9b9b" font-size="11" text-anchor="middle">평문(소켓)</text>
<rect x="60" y="200" width="880" height="56" rx="9" fill="#00ff8814" stroke="#00ff8877"/>
<text class="svgtext" x="500" y="222" fill="#00ff88" font-size="14" text-anchor="middle" font-weight="700">userspace 프록시 0개 · 추가 TCP 연결 0개 · 복호화된 평문이 userspace 에 존재하지 않는다</text>
<text class="svgtext" x="500" y="243" fill="#9aa0b0" font-size="12" text-anchor="middle">단, 이 경로로는 L3/L4 정책만 가능하다 — HTTP method / path 는 여전히 볼 수 없다</text>
</svg>

<!--
위쪽 점선이 핵심 아이디어다. mTLS 핸드셰이크를 데이터 경로에서 빼서 agent끼리 미리 해둔다.
identity 쌍 단위로 한 번만 하고 결과를 eBPF 맵에 캐싱하니까, 연결마다 TLS 종료를 할 필요가 없다.
그리고 실제 데이터 암호화는 WireGuard가 커널에서 한다. 패킷이 userspace로 올라오지 않는다.
아래 초록 띠가 사이드카 모델과의 대비다. 프록시 0개, 추가 연결 0개, userspace에 평문 없음.
다만 마지막 줄. 공짜는 아니다. 이 경로로는 L3/L4까지만 된다. 그리고 이 mutual authentication 기능은 아직 beta다.
-->

---

# 그래도 L7 + HTTPS는 결국 명시적 MITM

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
spec:
  egress:
  - toPorts:
    - ports: [{ port: "443", protocol: TCP }]
      terminatingTLS:                 # Pod → Envoy 구간 TLS 종료 (Pod가 내부 CA를 신뢰해야 함)
        secret: { namespace: default, name: tls-orig }
      originatingTLS:                 # Envoy → 목적지 구간 TLS 재개시
        secret: { namespace: default, name: tls-dest }
      rules:
        http:
        - method: "GET"
          path: "/v1/orders"          # 이 판단은 평문에서만 가능
```

- Cilium도 예외가 아니다. `terminatingTLS` + `originatingTLS` = **문서화된 TLS interception**.
- 차이는 **범위**: Pod마다가 아니라 **노드당 `cilium-envoy` 1개**, 그리고 **L7 룰이 걸린 흐름만** 우회.
- 나머지 트래픽은 eBPF fast path로 프록시를 아예 타지 않는다.

<!--
정직하게 말하자면 Cilium도 딜레마를 깨지 못한다. HTTPS 안의 path를 보려면 똑같이 중간에서 풀어야 한다.
차이는 두 가지다. 첫째, 프록시가 Pod당이 아니라 노드당 하나다. 둘째, L7 룰이 명시된 흐름만 프록시로 우회하고 나머지는 커널에서 끝난다.
terminatingTLS를 쓰려면 Pod가 클러스터 내부 CA를 신뢰하도록 인증서를 넣어줘야 한다. 이게 운영상 꽤 번거로워서 실무에서 널리 쓰이진 않는다.
결국 "L7 정책이 정말 필요한 흐름이 몇 개인가"를 먼저 세어보는 게 설계의 출발점이다.
-->

---

# 세 모델 비교

| | Istio 사이드카 | Istio Ambient | Cilium |
|---|---|---|---|
| L4 암호화 주체 | Pod마다 Envoy | 노드당 ztunnel (Rust) | 커널 WireGuard / IPsec |
| 데이터 경로 프록시 홉 | **2** | 2 (L4) / 4 (Waypoint) | **0** (L3/L4) |
| 신원 | SPIFFE 인증서 | SPIFFE 인증서 | security identity + SPIFFE(auth, **beta**) |
| mTLS 핸드셰이크 시점 | 연결마다 | 연결마다 | identity 쌍당 1회, out-of-band |
| userspace 평문 | 항상 | L4는 없음 | L7 룰 있을 때만 |
| L7 정책 | 항상 가능 | Waypoint 배치 시 | 노드당 Envoy로 우회 시 |
| 성숙도 | 안정 | 안정 | L3/L4 안정, mutual auth **beta** |

> 축은 하나다: **평문을 만드는 지점을 몇 개 두고, 얼마나 좁게 유지하는가.**

<!--
세로로 읽지 말고 가로로 읽자. 각 행이 "평문 노출 지점을 줄이려는 서로 다른 시도"다.
사이드카는 Pod마다 두 개의 평문 지점을 만든다. Ambient는 L4만 필요하면 ztunnel이 평문을 안 만든다. Cilium은 L3/L4 전체를 커널로 내려서 평문 지점 자체를 없앤다.
공정하게 짚을 것: Cilium의 mutual authentication은 beta이고 WireGuard 통합 같은 항목이 아직 로드맵에 남아 있다. 프로덕션 mTLS 성숙도는 Istio가 앞선다.
선택 기준은 "우리 트래픽 중 진짜 L7 정책이 필요한 비율이 얼마인가"다.
-->

---

<!-- _class: lead -->

# 한 장 요약

**평문 HTTP** = 1 RTT · 전부 노출 · 그래서 L7 정책 가능
**TLS 1.3** = +1 RTT · IP·포트·SNI만 남고 L7은 사라짐
**mTLS** = RTT 그대로 · 서명 2회 추가 · 신원이 IP → 인증서
**Envoy 종료** = 연결 3개 · 암복호 2회 · 파싱 4회 · **평문 지점 2곳**

> L7 가시성과 종단간 암호화는 **동시에 성립하지 않는다.**
> 좋은 설계 = 평문을 **누가 · 얼마나 오래 · 얼마나 멀리** 들고 있는지를 최소화하는 것.

<!--
마지막. 네 줄만 기억하면 된다.
그리고 blockquote. 이건 Istio든 Cilium이든 Linkerd든 무엇을 쓰든 변하지 않는 제약이다.
다음에 누가 "우리는 서비스 메시로 종단간 암호화를 합니다"라고 하면, 평문 지점이 어디 몇 개인지 물어보면 된다.
질문 받겠습니다.
-->
