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
    font-size: 1.32em;
    margin-bottom: 16px;
  }
  h2 { color: #00d4ff; font-size: 1.1em; }
  h3 { color: #7fdbff; font-size: 0.92em; margin-bottom: 6px; }
  strong { color: #ffd700; }
  em { color: #ff9e64; font-style: normal; }
  code {
    background-color: #16213e;
    color: #00ff88;
    font-size: 0.86em;
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
    font-size: 0.58em;
    line-height: 1.5;
  }
  table { font-size: 0.62em; margin: 10px auto; border-collapse: separate; border-spacing: 0; border-radius: 6px; overflow: hidden; }
  th { background-color: #16213e; color: #00d4ff; padding: 8px 13px; }
  td { background-color: #0f3460; padding: 8px 13px; }
  blockquote {
    border-left: 4px solid #ffd700;
    background-color: #2a1f3d;
    padding: 10px 18px;
    margin: 14px 0;
    font-style: normal;
    font-size: 0.82em;
    border-radius: 4px;
  }
  section.lead h1 { text-align: center; font-size: 1.95em; border: none; }
  section.lead p { text-align: center; font-size: 1.05em; }
  ul, ol { padding-left: 22px; }
  li { margin: 5px 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .small { font-size: 0.76em; color: #9aa0b0; }
  .src { font-size: 0.58em; color: #9aa0b0; margin-top: 8px; }

  /* ── 다이어그램 킷 ───────────────────────────── */
  .seq { display: flex; align-items: stretch; justify-content: center; margin: 24px 0 10px 0; }
  .seq-node {
    flex: 1 1 0; border: 2px solid #00d4ff; border-radius: 10px;
    background: #16213e; padding: 14px 8px; text-align: center;
    font-size: 0.56em; line-height: 1.35; color: #e0e0e0;
    display: flex; align-items: center; justify-content: center;
  }
  .seq-arrow { flex: 0 0 42px; align-self: center; position: relative; height: 3px; background: #ffd700; }
  .seq-arrow::after {
    content: ''; position: absolute; right: -1px; top: -7px;
    border-left: 13px solid #ffd700;
    border-top: 8px solid transparent; border-bottom: 8px solid transparent;
  }

  .stack { display: flex; flex-direction: column; align-items: center; margin: 22px 0 10px 0; }
  .stack-layer {
    border: 2px solid #00d4ff; border-radius: 8px; background: #16213e;
    padding: 11px 16px; margin: 5px 0; text-align: center;
    font-size: 0.56em; line-height: 1.35; box-sizing: border-box;
  }

  .steps { position: relative; margin: 20px 0 8px 0; }
  .steps::before { content: ''; position: absolute; left: 20px; top: 26px; bottom: 26px; width: 2px; background: #30363d; }
  .step { position: relative; padding: 9px 0 9px 60px; min-height: 42px; display: flex; align-items: center; }
  .step-num {
    position: absolute; left: 0; top: 50%; transform: translateY(-50%);
    width: 42px; height: 42px; border-radius: 50%;
    background: #0f3460; border: 2px solid #00d4ff; color: #00d4ff;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.6em; font-weight: 700;
  }
  .step-txt { font-size: 0.62em; line-height: 1.42; }

  .cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin: 20px 0 8px 0; }
  .cmp-col { border: 2px solid #5a6070; border-radius: 10px; padding: 14px 18px; background: #16213e88; }
  .cmp-col.left { border-color: #ff6b6b; }
  .cmp-col.right { border-color: #00ff88; }
  .cmp-title { font-size: 0.66em; font-weight: 700; text-align: center; margin-bottom: 10px; }
  .cmp-col.left .cmp-title { color: #ff6b6b; }
  .cmp-col.right .cmp-title { color: #00ff88; }
  .cmp-item { font-size: 0.58em; line-height: 1.45; margin: 7px 0; padding-left: 15px; position: relative; }
  .cmp-item::before { content: '·'; position: absolute; left: 3px; color: #9aa0b0; }

  .badge {
    display: inline-block; background: #0f3460; border: 1px solid #00d4ff;
    color: #00d4ff; border-radius: 999px; padding: 0 11px; margin: 0 3px;
    font-size: 0.76em; line-height: 1.6;
  }
  .badge.gold { border-color: #ffd700; color: #ffd700; }
  .badge.red { border-color: #ff6b6b; color: #ff6b6b; }
  .badge.green { border-color: #00ff88; color: #00ff88; }
---
<!-- _class: lead -->

# TLS · Istio Ambient · Cilium

<!--
바로 첫 챕터, TLS부터 갑니다.
-->

---

<!-- _class: lead -->

# 01 TLS에 대해서


<!--
여섯 장입니다. 이름 풀이부터 시작해서, 보장하는 게 뭔지, 그리고 버전이 왜 세 개인지까지 봅니다.
-->

---

# TLS = Transport Layer Security

**Transport** — 일반적으로 **TCP 연결 위에서 동작**한다. TCP가 만들어 놓은 신뢰성 있는 바이트 스트림을 이용한다.

**Layer** — 애플리케이션과 TCP 사이에서 **암호화·인증·무결성 보호를 제공하는 논리적인 계층**이라는 의미다. OSI 모델의 특정 계층을 뜻하는 것은 아니다. HTTP뿐 아니라 SMTP, IMAP 등 TCP 기반 프로토콜에서도 사용할 수 있다.

**Security** — 통신 상대 인증, 데이터 암호화, 데이터 무결성을 제공한다.

<div class="src">이전 이름은 SSL(Secure Sockets Layer)이었다. 이후 표준화 과정에서 TLS(Transport Layer Security)로 이어졌으며, 지금도 관행적으로 TLS 인증서를 "SSL 인증서"라고 부르는 경우가 많다.</div>

<!--
이름부터 풀고 갑니다. 세 단어에 이 프로토콜의 성격이 다 들어 있어요.

Transport. 일반적으로 TCP 연결 위에서 동작합니다. TCP가 이미 신뢰성 있는 바이트 스트림을 만들어 놨으니 TLS는 그걸 그대로 가져다 씁니다. 순서 보장이나 재전송을 TLS가 다시 할 필요가 없어요.

Layer. 애플리케이션과 TCP 사이에 끼어서 암호화와 인증과 무결성 보호를 해주는 논리적인 계층이라는 뜻입니다. 여기서 하나 짚고 갈 게, OSI 모델의 몇 계층이라고 딱 잘라 말하는 건 아닙니다. 4계층이다 5계층이다 논쟁이 있는데 그 논쟁은 실무에 도움이 안 됩니다. 애플리케이션과 TCP 사이라고만 기억하시면 됩니다.

그리고 HTTP 전용이 아닙니다. SMTP나 IMAP처럼 TCP를 쓰는 프로토콜이면 다 붙일 수 있어요. 메일 서버에 TLS 붙이는 것도 같은 원리입니다.

Security. 세 가지를 제공합니다. 통신 상대가 누구인지 확인하는 인증, 내용을 감추는 암호화, 중간에 바뀌지 않았는지 확인하는 무결성. 다음 장에서 하나씩 봅니다.

아래 회색 글씨. 예전 이름이 SSL이었습니다. 표준화되면서 TLS로 이어졌는데, 지금도 "SSL 인증서 갱신해야 한다"고 말하잖아요. 사실 TLS 인증서인데 이름만 관행으로 남은 겁니다.
-->

---

# TLS가 보장하는 세 가지

| 무엇 | 어떤 원리로 |
|---|---|
| **기밀성** | 데이터를 열쇠로 암호화해서 보낸다 |
| **무결성** | 보낼 때 검사값을 같이 붙이고, 받는 쪽이 다시 계산해 맞춰본다 |
| **인증** | 상대가 낸 인증서와, 그 인증서의 개인키로 만든 서명을 검증한다 |

<!--
용어 세 개를 확실히 하고 갑니다. 뒤에서 계속 나오는데 여기서 헷갈리면 mTLS 설명이 안 들어옵니다.

기밀성. 카페 와이파이에서 로그인하면 같은 와이파이에 붙은 사람이 그 비밀번호를 그대로 볼 수 있어요. 그걸 열쇠로 암호화해서 보내는 겁니다.

무결성은 좀 다릅니다. 내용을 못 읽게 하는 게 아니라 바뀌었는지를 알아내는 거예요. 송금 요청에서 계좌번호만 슬쩍 바꿔치기해도 받는 쪽이 알아채야 하잖아요. 원리는 단순합니다. 보낼 때 내용으로 검사값을 계산해서 같이 붙이고, 받는 쪽이 다시 계산해서 맞춰봅니다. 안 맞으면 중간에 손을 댄 거죠.

인증은 상대가 누구냐입니다. 인증서를 받고, 그 인증서에 대응하는 개인키로 만든 서명을 검증합니다. 개인키를 가진 쪽만 만들 수 있는 서명이라서 신원 확인이 됩니다.

다음 장에서 이 원리들에 어떤 종류의 열쇠가 쓰이는지 봅니다.
-->

---

# 공개키와 대칭키 — 어디에 쓰나

| 구간 | 무엇을 쓰나 | 왜 |
|---|---|---|
| 핸드셰이크 — 키 합의 | **공개키(비대칭)** | 미리 정한 비밀 없이도 처음 만난 상대와 공유 비밀을 만들 수 있다 |
| 핸드셰이크 — 상대 확인 | **공개키(서명·인증서)** | 개인키를 가진 쪽만 서명을 만들 수 있다 |
| 실제 데이터 전송 | **대칭키** | 비대칭은 훨씬 느리다. 양이 많은 본 통신에는 못 쓴다 |

TLS는 둘 중 하나를 고르는 게 아니라 **역할을 나눠 둘 다 쓴다**.

<!--
암호화 방식이 두 종류인데 TLS는 둘 다 씁니다. 이걸 구분해 두면 다음 장부터 나오는 왕복 얘기가 훨씬 쉬워져요.

공개키 방식은 열쇠가 두 개입니다. 하나는 공개하고 하나는 나만 갖습니다. 특이한 성질이 있어요. 서로 공개값만 교환해도 양쪽이 같은 비밀값을 계산해낼 수 있습니다. 미리 약속한 비밀이 하나도 없는, 처음 만난 상대와도요. 이게 첫 줄 키 합의에 쓰입니다.

둘째 줄 상대 확인도 공개키입니다. 서버가 자기 개인키로 서명하면 클라이언트가 인증서에 든 공개키로 그 서명을 검증해요. 개인키를 가진 쪽만 만들 수 있는 서명이니까 신원 확인이 됩니다.

셋째 줄이 왜 두 가지를 다 쓰는지에 대한 답입니다. 비대칭 연산은 훨씬 느려요. 파일 하나 내려받을 때마다 그 연산을 다 하면 못 씁니다. 그래서 핸드셰이크에서 공유 비밀을 만들고, 거기서 대칭키를 뽑아 본 통신은 대칭키로 합니다. 대칭키는 양쪽이 같은 열쇠를 쓰는 방식이고 훨씬 빠릅니다.

정리하면 앞부분은 공개키로 열쇠를 맞추고 뒷부분은 그 열쇠로 빠르게 나릅니다. 다음 장들의 왕복 얘기는 전부 앞부분, 열쇠 맞추는 구간 얘기입니다.
-->

---

# 버전은 세 개 — 1.1 · 1.2 · 1.3

| 버전 | 한 줄 |
|---|---|
| **1.1** (2006) | 지원하는 암호화 수준이 낮다 → **쓰지 말 것** |
| **1.2** (2008) | 암호화 수준 문제는 해결. 다만 **통신 횟수가 많다** |
| **1.3** (2018) | 통신 횟수를 줄였다. **지금 기준** |

지금 쓰이는 건 **1.2와 1.3** 두 개다. 1.2는 오래된 상대와 붙어야 할 때 남아 있다.

<!--
버전은 세 개만 보면 됩니다. 1.0도 있었는데 1.1과 같이 금지됐으니 묶어서 생각하시면 돼요.

표를 세로로 읽어주세요. 문제가 두 단계로 해결됩니다.

1.1은 암호화 수준 자체가 낮습니다. 그래서 지금은 쓰지 말라고 못 박혔어요.

1.2가 그 문제를 해결했습니다. 그런데 다른 문제가 남았어요. 통신을 너무 많이 주고받습니다.

1.3이 그 통신 횟수를 줄였습니다. 그래서 지금 새로 만들면 1.3입니다.

아래 문장이 현실입니다. 1.2가 없어진 게 아니에요. 오래된 장비나 오래된 라이브러리랑 붙어야 할 때가 있어서 아직 대량으로 쓰입니다. 다음 세 장에서 하나씩 봅니다.
-->

---

# 1.1 — 암호화 수준이 낮아서 금지

쓸 수 있는 해시가 **MD5와 SHA-1**뿐이었다. 둘 다 지금 기준으로는 약하다.

암호화와 위조검사를 **따로 처리**했고, 둘을 붙이는 순서에서 공격이 계속 나왔다.

더 센 알고리즘으로 바꾸자고 **협상할 필드가 프로토콜에 없었다.** 그래서 프로토콜을 갈아치우는 수밖에 없었다.

<span class="badge red">1.0도 함께 금지</span>

<!--
1.1이 왜 금지됐냐. 지원하는 암호화 수준이 낮습니다.

구체적으로 쓸 수 있는 해시가 MD5랑 SHA-1뿐이었어요. 둘 다 지금 기준으로는 약합니다. 그리고 암호화하고 위조 검사하는 걸 따로 처리하는데, 이걸 어떤 순서로 붙이느냐에서 공격이 계속 나왔습니다.

세 번째 줄이 진짜 원인입니다. 약한 알고리즘 자체는 고칠 수 있어요. 더 센 걸 쓰자고 서로 합의하면 되죠. 그런데 그 합의를 할 필드가 프로토콜 안에 없습니다. 말할 자리가 없어요. 그래서 프로토콜을 갈아치우는 수밖에 없었습니다. 1.2는 그 자리를 만들어놨기 때문에 지금까지 살아 있고요.

금지된 건 1.1만이 아니라 1.0과 1.1 둘 다입니다.
-->

---

# 1.2 — 문제는 고쳤지만 통신이 많다

<div class="steps" data-steps="클라이언트: 인사 + 내가 쓸 수 있는 방식 목록|서버: 이 방식으로 하자 + 내 인증서|클라이언트: 그 방식에 맞춰 키 정보 전송|서버: 확인 완료 — 이제야 데이터" data-start="1"></div>

열쇠를 맞추는 데만 **왕복이 두 번** 필요하다. 방식을 정한 *다음에* 키 정보를 보내는 순서였기 때문이다.

<!--
1.2는 암호화 수준 문제를 해결했습니다. 해시도 고를 수 있고, 암호화와 위조 검사를 한 번에 하는 방식도 들어왔어요.

그런데 순서를 보세요. 네 단계입니다.

클라이언트가 인사하면서 "저는 이런 방식들을 쓸 수 있어요" 목록을 보냅니다. 서버가 그중 하나 골라서 "이걸로 하자, 그리고 내 인증서 여기 있다" 답합니다. 그제서야 클라이언트가 그 방식에 맞는 키 정보를 만들어 보내요. 서버가 확인하면 끝입니다.

문제가 보이시죠. 오고 가는 게 두 번입니다. 방식을 먼저 정하고 그 다음에 키 정보를 보내는 순서라서 그래요. 순서상 어쩔 수 없었습니다.

연결 하나 만들 때마다 이게 반복됩니다. 요즘처럼 마이크로서비스가 서로 수백 개 연결을 여는 환경에서는 이 왕복이 그대로 지연으로 쌓입니다.
-->

---

# 1.3 — 통신을 어떻게 줄였나

<div class="cmp"
     data-left-title="1.2 — 왕복 두 번"
     data-left="방식을 정한 다음에 키 정보를 보낸다|서버 확인까지 끝나야 데이터가 나간다"
     data-right-title="1.3 — 왕복 한 번"
     data-right="첫 인사에 키 교환 그룹과 공개값을 미리 넣는다|서버가 그 그룹을 받아들이면 그 자리에서 키 완성|서버가 다른 그룹을 원하면 되물어본다 → 왕복 두 번"></div>

클라이언트가 **어느 그룹으로 키를 만들지 미리 찍어서** 공개값까지 같이 보낸다. 맞으면 한 번, 틀리면 서버가 되물어서 두 번이다.

<div class="src"><b>별개 변화</b> — 1.3은 암호 조합 이름에서 키 교환과 인증을 떼어내 따로 협상하게 바꿨다. 그래서 등록된 조합이 300개 이상에서 5개로 줄었다. 이건 <em>이름과 협상의 단순화</em>이고, 위의 왕복 감소와는 다른 이야기다.</div>

<!--
1.3이 순서를 뒤집었습니다. 클라이언트가 첫 인사에 "저는 이 그룹으로 키를 만들 생각이고 여기 제 공개값입니다" 하고 미리 보냅니다. 앞에서 본 그 공개키 방식이에요. 서버가 그 그룹을 받아들이면 그 자리에서 양쪽이 같은 키를 갖게 됩니다. 왕복 한 번에 끝나요.

여기서 질문이 나옵니다. 서버가 다른 그룹을 쓰고 싶으면 어떻게 되냐. 그때는 서버가 "그 그룹 말고 이걸로 다시 보내라"고 되물어봅니다. 클라이언트가 다시 보내면 왕복 두 번이 되죠. 그래서 1.3이 항상 한 번인 건 아닙니다. 대개 맞는 이유는 실제로 널리 쓰이는 그룹이 몇 개로 좁혀져 있어서입니다.

아래 회색 글씨는 따로 읽어주세요. 헷갈리기 쉬운데 왕복 감소와 다른 이야기입니다.

1.3은 암호 조합 이름에서 키 교환 방식과 인증 방식을 떼어내 각각 따로 협상하게 바꿨습니다. 그 결과 조합 이름의 종류가 300개 이상에서 5개로 줄었어요. 이름과 협상이 단순해진 겁니다. 왕복이 줄어든 이유가 조합이 5개라서가 아니에요. 두 개를 인과로 묶으면 틀립니다.
-->

---

<!-- _class: lead -->

# 02 TLS 통신 방법

ClientHello · ServerHello · 그리고 mTLS

<!--
두 번째 챕터, 다섯 장입니다. TLS가 실제로 뭘 주고받는지 열어보고 mTLS까지 갑니다.
핸드셰이크 메시지를 필드 수준까지 한 번 열어봅니다. 여기서 본 필드 이름이 3장 이후에 계속 나옵니다.
-->

---

# ClientHello — 실제로 나가는 내용

```text
ClientHello                                  # 전체가 평문
  supported_versions  TLS 1.3, TLS 1.2       # 쓸 수 있는 버전
  cipher_suites       TLS_AES_128_GCM_SHA256 # 암호 방식 후보
  key_share           x25519 + 공개값 32B    # 키 만들 그룹 + 내 공개값
  server_name         api.example.com        # 접속할 도메인
  alpn                h2, http/1.1           # 그 위에서 쓸 프로토콜
```

`server_name`과 `alpn`이 **평문으로 그대로 보인다**는 걸 여기서 확인할 수 있다.

<!--
실제로 와이어에 나가는 걸 줄여 적었습니다.

key_share에 x25519라는 그룹 이름과 32바이트 공개값이 들어가 있어요. 앞 장에서 본 그 공개값입니다.

server_name을 보세요. api.example.com이 그냥 보이죠. 서버가 인증서를 고르려면 어느 도메인인지 먼저 알아야 하니 어쩔 수 없습니다.

alpn에 h2가 있는데, 뒤에서 ztunnel이 이걸 h2로 고정한다는 얘기가 나올 때 이 줄입니다.

맨 윗줄 주석이 중요합니다. 전부 평문이에요. 열쇠를 맞추려고 보내는 첫 메시지니까 아직 감쌀 열쇠가 없습니다.
-->

---

# ServerHello — 서버가 고른 결과

```text
ServerHello
  supported_versions  TLS 1.3                 # 고른 버전
  cipher_suite        TLS_AES_128_GCM_SHA256  # 후보 중 하나만
  key_share           x25519 + 공개값 32B     # 서버 쪽 공개값
──────────────── 여기까지 평문 ────────────────
  {EncryptedExtensions} {Certificate} {Finished}
```

서버 공개값이 오면 양쪽 열쇠가 완성된다. 그래서 **그 다음 줄부터 암호화된다.**

<!--
ServerHello는 목록이 아니라 하나씩만 옵니다. 후보를 여러 개 받았으면 그중 하나만 골라 답해요.

key_share에 서버 쪽 공개값이 들어옵니다. 양쪽 공개값이 다 있으면 같은 열쇠를 계산할 수 있어요.

가운데 구분선을 봐주세요. ServerHello까지는 평문이고 그 다음부터 암호화됩니다. ServerHello 자체는 아직 평문이에요. 그림 그릴 때 자물쇠 안에 넣으면 틀립니다.

아래 중괄호로 묶인 게 암호화된 메시지입니다. 서버 인증서가 여기 들어갑니다. 그래서 지나가며 보는 사람은 어느 서비스 인증서인지 알 수 없습니다.
-->

---

# TLS → mTLS: 무엇이 추가되나

<div class="cmp"
     data-left-title="TLS — 서버만 인증"
     data-left="서버만 Certificate 제시|클라이언트는 검증만 한다|서버는 상대가 누구인지 모른다|앱 레벨 토큰·API 키로 따로 보완"
     data-right-title="mTLS — 상호 인증"
     data-right="서버가 CertificateRequest 를 추가|클라이언트도 Certificate + CertificateVerify|양쪽이 서로를 암호학적으로 확인|대신 인증서 배포·갱신 부담이 생긴다"></div>

<!--
웹 브라우징에서 쓰는 TLS는 한쪽만 인증합니다. 서버가 신분증을 보이고 브라우저가 확인합니다. 서버는 접속한 사람이 누군지 모릅니다. 그래서 로그인을 따로 합니다.
mTLS는 양쪽입니다. 서버가 CertificateRequest를 보내서 "너도 신분증 내라"고 요구하고, 클라이언트가 Certificate와 CertificateVerify를 보냅니다.
CertificateVerify가 핵심입니다. 인증서만 보내면 복사해서 쓸 수 있으니, 개인키로 지금까지의 핸드셰이크에 서명해서 "그 인증서의 개인키를 실제로 갖고 있다"를 증명합니다.
오른쪽 마지막 줄이 대가입니다. 클라이언트도 인증서를 가져야 하니, 그 인증서를 누가 만들어 어떻게 나눠주고 언제 갱신하느냐가 새 숙제로 생깁니다.
-->

---

# 순서로 보면 두 줄이 늘어난다

<div class="cmp"
     data-left-title="TLS"
     data-left="→ ClientHello + 내 공개값|← ServerHello + 서버 공개값|← {서버 인증서 + 서명 + Finished}|→ {Finished} — 데이터 시작"
     data-right-title="mTLS"
     data-right="→ ClientHello + 내 공개값|← ServerHello + 서버 공개값|← {서버 인증서 + 서명 + 인증서 요청 + Finished}|→ {클라이언트 인증서 + 서명 + Finished}"></div>

늘어난 것은 **서버의 인증서 요청**과 **클라이언트의 인증서·서명** 둘뿐이다. 왕복 수는 그대로다.

<!--
나란히 놓으면 뭐가 늘었는지 바로 보입니다. 위 두 줄은 완전히 같아요.

세 번째 줄에서 갈립니다. mTLS면 서버가 자기 인증서를 보낼 때 "너도 인증서 내라"는 요청을 같이 붙입니다.

네 번째 줄이 클라이언트 차례입니다. TLS는 Finished만 보내고 끝나는데, mTLS는 자기 인증서와 서명을 같이 보냅니다. 서명이 있어야 그 인증서의 개인키를 실제로 갖고 있다는 게 증명되니까요.

아래 문장이 핵심입니다. 늘어난 건 두 개뿐이고 왕복 수는 그대로예요. mTLS가 느려진다는 얘기는 왕복이 늘어서가 아니라 인증서 검증 연산과 배포·갱신 운영 때문입니다.
-->

---

<!-- _class: lead -->

# 03 Istio

Service Mesh 구현체 · k8s Add-On · istiod

<!--
세 번째 챕터, 여섯 장입니다.
Ambient로 바로 가지 않고 Istio 자체를 먼저 봅니다. istiod가 무엇을 하는 물건인지 모르면 4장에서 "istiod가 ztunnel에 뭘 준다"는 얘기가 안 잡힙니다.
-->

---

# Service Mesh — 앱에서 무엇을 빼내나

<div class="cmp"
     data-left-title="앱이 직접 하던 것"
     data-left="mTLS 라이브러리를 코드에 링크|리트라이 · 타임아웃 · 서킷브레이커 구현|언어마다 다시 구현 (Java, Go, Python…)|정책 하나 바꾸려면 재빌드 · 재배포"
     data-right-title="메시가 대신 하는 것"
     data-right="프록시가 mTLS를 종단|트래픽 정책을 선언으로 기술|언어 무관 — 프록시는 바깥에 있다|정책 변경 = CRD 수정"></div>

Istio는 이 아이디어의 **구현체 중 하나**다. Linkerd · Consul · Cilium Service Mesh도 있다.

<!--
서비스 메시를 한 문장으로 하면 "앱에서 네트워크 걱정을 빼내 인프라로 옮기는 것"입니다.
왼쪽이 메시 없을 때입니다. mTLS를 하려면 각 언어 라이브러리를 코드에 링크하고, 인증서 갱신을 앱이 처리하고, 리트라이도 직접 구현합니다. 문제는 마이크로서비스가 여러 언어로 쓰였을 때입니다. 같은 일을 언어마다 다시 만들고, 정책 하나 바꾸려면 전부 재배포해야 합니다.
오른쪽이 메시입니다. 프록시가 밖에서 대신 합니다. 앱은 평문으로 통신하고 자기가 메시 안에 있다는 걸 모릅니다. 정책은 CRD로 선언합니다.
마지막 줄은 균형을 위해 넣었습니다. Istio가 유일한 구현체는 아닙니다. 다만 오늘 다루는 Ambient 모드는 Istio가 처음 만든 방식입니다.
-->

---

# Istio는 k8s Add-On이다

<div class="stack" data-stack="CRD — networking · security · telemetry · extensions.istio.io 4개 API 그룹|Webhook — Mutating(사이드카 주입) · Validating(설정 검증)|istio-system 네임스페이스 — istiod Deployment|전제 조건 — 이미 동작하는 CNI" data-accent="cyan|green|gold|red"></div>

<!--
"애드온"이라는 말이 추상적이라 실제로 무엇이 설치되는지로 풀었습니다.
맨 위, CRD입니다. API 그룹이 네 개입니다. networking에 VirtualService와 DestinationRule, security에 AuthorizationPolicy와 PeerAuthentication이 들어갑니다. 쿠버네티스 API를 확장하는 방식입니다.
그 다음 웹훅이 두 종류. Mutating이 사이드카를 파드 스펙에 끼워넣고, Validating이 잘못된 설정을 거부합니다.
그리고 istio-system에 istiod 파드 하나.
맨 아래 빨간 층이 오늘 강조하고 싶은 부분입니다. Istio는 파드에 IP를 주지 않습니다. Calico나 Cilium이 이미 그 일을 해놓은 상태를 가정합니다.
이게 5장에서 Cilium과 비교할 첫 번째 항목입니다.
-->

---

# istiod — 넷이 하나로

<div class="seq" data-seq="Pilot · Galley · Citadel · injector\n각각 별도 배포 · 버전 · RBAC|istiod\n단일 바이너리 (Istio 1.5, 2020-03)" data-accent="dim|green"></div>

| 컴포넌트 | 하던 일 |
|---|---|
| **Pilot** | 서비스 목록을 모아 **프록시 설정으로 바꿔 배포**. 지금 istiod의 본체 |
| **Galley** | 설정 **검증** + MCP로 배포. **검증만 살아남았다** (MCP는 1.5에서 기본 off → 소멸) |
| **Citadel** | **CA** — 워크로드 인증서 발급·갱신. 지금은 **끌 수도 있다**(외부 CA·SPIRE) |
| **injector** | 파드 생성을 가로채 **사이드카 컨테이너를 끼워 넣음** |

<div class="src"><b>이 네 이름은 모두 역사 용어다.</b> 현행 istio.io 아키텍처 문서에는 등장하지 않고 <b>Envoy · Istiod</b> 두 상자로만 설명한다(코드에 이미지명 <code>pilot</code>, <code>CA_PROVIDER=Citadel</code> 같은 잔재만 남음).<br><b>용어</b> — "컨트롤플레인"은 <b>역할</b>이고, 쿠버네티스 오브젝트로는 <code>istio-system</code>의 <b>평범한 Deployment</b>다(차트 기본값에 <code>nodeSelector</code>·<code>tolerations</code>·<code>affinity</code>가 전부 비어 있다). <b>쿠버네티스 컨트롤플레인</b>(kube-apiserver 등)과는 층이 다르다.</div>

<!--
지금은 istiod 하나지만 원래는 컨트롤 플레인이 마이크로서비스 여러 개였습니다. 표를 보시면 넷이 뭘 했는지 나옵니다.

Pilot이 제일 큽니다. 쿠버네티스에서 서비스와 엔드포인트 목록을 읽어다가 프록시가 알아들을 설정으로 바꿔서 뿌립니다. 지금 istiod가 하는 일의 대부분이 이겁니다.

Galley는 두 가지를 했습니다. 설정을 검증하고, MCP라는 프로토콜로 다른 컴포넌트에 배포했어요. 이 중 검증만 살아남았습니다. MCP 배포 경로는 1.5에서 기본 비활성이 되고 그 뒤 사라졌습니다.

Citadel이 CA입니다. 앞에서 mTLS 얘기할 때 인증서를 누가 발급하냐고 했는데 이 자리예요. 한 가지 덧붙이면, 지금은 이게 고정이 아닙니다. istiod의 CA 서버를 끄고 외부 CA나 SPIRE에 맡길 수 있습니다. 기본값이 istiod라는 뜻이지 유일한 경로는 아니에요.

injector는 어드미션 웹훅입니다. 파드가 생기는 걸 가로채서 사이드카 컨테이너를 스펙에 끼워 넣습니다. 사이드카가 자동으로 붙는 게 이것 때문이에요.

문제는 운영이었습니다. 넷을 따로 배포하고 버전 맞추고 RBAC 설정하고 서로 통신까지 시켜야 했습니다. Istio 설치가 어렵다는 평판이 여기서 나왔습니다.

용어를 하나 정리하고 갑니다. istiod를 컨트롤플레인이라고 부르는데 그건 역할을 말하는 겁니다. 데이터플레인인 프록시들에게 설정을 내려주는 쪽이라는 뜻이죠.

쿠버네티스 오브젝트로 보면 그냥 Deployment입니다. istio-system 네임스페이스에 파드로 떠요. 마스터 노드의 kube-apiserver 같은 쿠버네티스 컨트롤플레인과는 층이 다릅니다. istiod는 그 쿠버네티스 위에 얹혀서 일반 워크로드로 스케줄되는 하나의 앱이에요. 보통 워커 노드에 뜨지만 노드 셀렉터나 톨러레이션을 주면 어디든 갈 수 있습니다. 스케줄러가 정하는 거지 정해진 자리가 있는 게 아닙니다. kubectl get deploy 해보면 그냥 보입니다.

그러니 두 표현이 충돌하는 게 아닙니다. 역할은 컨트롤플레인, 오브젝트 종류는 Deployment입니다.

2020년 3월 1.5에서 하나의 바이너리로 합쳤습니다. 그게 istiod입니다. Mixer라는 텔레메트리 컴포넌트도 있었는데 이건 합쳐진 게 아니라 같은 시점에 폐기됐고 1.8에서 제거됐습니다. 텔레메트리는 프록시가 직접 내보내는 방식으로 바뀌었습니다.

중요한 전제를 하나 말씀드리면, 이 네 이름은 전부 역사 용어입니다. 지금 istio.io 아키텍처 문서를 열면 Pilot이나 Citadel이라는 단어가 아예 안 나옵니다. Envoy와 Istiod 두 상자로만 설명해요. 코드에는 이미지 이름이 pilot이라거나 CA_PROVIDER 기본값이 Citadel이라는 잔재가 남아 있어서 검색하면 나오는데, 그것 때문에 헷갈리실 수 있습니다.

그리고 istiod는 1.5 당시에 없던 일도 지금 합니다. Gateway 리소스를 보고 waypoint Deployment를 만들어 주는 컨트롤러가 istiod 안에 있어요. 뒤에서 waypoint 얘기할 때 그 주체가 이겁니다.

어쨌든 지금은 파드 하나만 뜨면 컨트롤 플레인이 다 올라옵니다. 대신 그 파드가 하는 일이 많아졌고, 죽으면 여러 개가 동시에 멈춥니다. 두 장 뒤에 다룹니다.
-->

---

# istiod의 포트 네 개

| 포트 | 이름 | 용도 |
|---|---|---|
| 15010 | `grpc-xds` | XDS + CA — **평문**. 안전한 망에서만 |
| 15012 | `tls-xds` | XDS + CA — TLS/mTLS. **프로덕션 권장** |
| 15014 | `http-monitoring` | Prometheus 메트릭 |
| 15017 | `https-webhooks` | 주입 · 검증 webhook (Service 443 → 15017) |

<!--
포트를 외울 필요는 없지만 두 개는 알아두면 좋습니다.
15010과 15012가 같은 일을 합니다. 설정 배포와 인증서 발급입니다. 차이는 15010이 평문이라는 것입니다. 문서도 안전한 망에서만 쓰라고 적어뒀습니다. 프로덕션은 15012입니다. 4장에서 ztunnel이 붙는 포트가 이 15012입니다.
15014는 모니터링입니다.
15017이 웹훅입니다. 헷갈리기 쉬운 게, API 서버는 Service의 443으로 붙고 그게 컨테이너의 15017로 넘어갑니다. 방화벽 열 때 주의하세요.
-->

---

# istiod가 죽으면

| 대상 | 결과 |
|---|---|
| **신규 파드** | 주입 webhook이 `failurePolicy: Fail` → 주입 대상 파드 생성이 **거부** |
| 기존 트래픽 | 프록시가 마지막 설정으로 계속 동작 *(구조상 도출 — 1차 문구 미확인)* |
| 실질 데드라인 | 인증서 갱신 중단. ztunnel 기본 TTL **24시간** |
| 완화 | `autoscaleMin: 2` + podAntiAffinity (노드 필수 · 존 선호) |

<!--
장애 모드입니다. 오해가 많은 부분이라 한 장 잡았습니다.
"istiod가 죽으면 메시 트래픽이 끊긴다"고 생각하기 쉬운데 아닙니다. 먼저 아픈 건 새 파드입니다. 주입 웹훅의 failurePolicy가 Fail이라, istiod가 응답을 못 하면 주입 대상 파드의 생성 요청이 거부됩니다. 배포가 막힙니다.
두 번째 줄에 괄호를 달아둔 이유가 있습니다. "기존 프록시가 마지막 설정으로 계속 동작한다"는 건 xDS 스트림이 끊겼을 때의 일반적인 동작에서 도출한 것이고, istio.io의 명시적 문구를 찾지는 못했습니다. 그래서 단정하지 않습니다.
진짜 시한은 세 번째 줄입니다. 인증서 갱신이 멈춥니다. ztunnel 기본 TTL이 24시간이니 그게 실질 데드라인입니다.
완화책은 문서가 권하는 대로 replica 2개 이상에 anti-affinity입니다.
-->

---

<!-- _class: lead -->

# 04 Istio Ambient mode

ztunnel · waypoint

<!--
네 번째 챕터, 아홉 장입니다. 오늘의 중심입니다.
사이드카를 파드 밖으로 빼면 무엇이 좋아지고 무엇이 그대로인지, 이걸 정확히 따져봅니다.
-->

---

# 사이드카에서 Ambient로 — 무엇이 바뀌나

<div class="cmp"
     data-left-title="사이드카"
     data-left="파드마다 Envoy 하나|유저스페이스 프록시 통과 양쪽 2회|풀 L7 처리|프록시를 바꾸려면 앱 파드 재시작"
     data-right-title="Ambient"
     data-right="노드마다 ztunnel 하나|유저스페이스 프록시 통과 양쪽 2회 — 동일|L4만 처리|앱과 따로 교체"></div>

줄어든 것은 **프록시 개수**(파드당 → 노드당)와 **하는 일**(풀 L7 → L4)이다. 같은 노드 파드끼리도 로컬 ztunnel을 지난다.

<div class="src"><b>홉(hop)</b> = 패킷이 중간 지점을 한 번 지나가는 것. 여기서는 <em>유저스페이스 프록시를 한 번 통과</em>하는 걸 센다. 통과할 때마다 커널에서 프로세스로 올라갔다 다시 내려오므로 그만큼 지연이 붙는다.</div>

<!--
가로로 비교해 주세요. 두 번째 줄이 같습니다. 프록시를 지나는 횟수가 양쪽 다 두 번이에요.

달라진 건 첫 줄과 셋째 줄입니다. 프록시 개수가 파드 수에서 노드 수로 줄고, 하는 일이 풀 L7에서 L4로 줄어듭니다. 넷째 줄도 실무에서 큽니다. 프록시 버전을 올릴 때 앱을 재시작하지 않아도 됩니다.

같은 노드에 있는 파드끼리도 로컬 ztunnel을 지납니다. 정책과 텔레메트리를 일관되게 적용하려면 우회할 수 없어서요.

맨 아래 회색 글씨는 홉이라는 말의 정의입니다. 프록시를 한 번 통과하는 걸 한 홉으로 셉니다. 통과할 때마다 커널에서 유저 프로세스로 올라갔다 내려오니 그만큼 지연이 붙습니다.
-->

---

# 구성요소는 세 개

<div class="seq" data-seq="istio-cni-node\nDaemonSet\n파드를 메시에 등록|ztunnel\nDaemonSet\nL4 mTLS 전담|waypoint\nDeployment\nL7 — 선택" data-accent="gold|green|dim"></div>

**`istio-cni-node`는 이름과 달리 파드에 IP를 주지 않는다.** 하는 일이 두 개다.

① 기존 CNI 체인 **끝에 자기 바이너리를 얹는다** — 파드가 생길 때 호출되도록

② 상주 에이전트로 남아 파드 netns에 **리디렉션 규칙**을 넣고, ztunnel에 등록을 알린다

<!--
istio-cni-node는 이름 때문에 오해를 많이 삽니다. CNI가 들어가 있으니 Calico나 Cilium을 대체하는 것처럼 들리는데 아닙니다. 파드에 IP를 주지 않아요.

첫 번째 일. 노드에 뜨면 기존 CNI 설정 파일을 열어서 플러그인 목록 맨 끝에 자기 바이너리를 추가합니다. 그러면 앞으로 파드가 생길 때마다 자기가 호출됩니다. 왜 맨 끝이냐면, 주 CNI가 파드 IP를 먼저 만들어야 그 IP를 대상으로 규칙을 넣을 수 있으니까요.

두 번째 일. 프로세스가 죽지 않고 노드에 계속 남습니다. 파드가 생기면 그 파드의 네트워크 네임스페이스에 들어가 트래픽을 ztunnel로 돌리는 규칙을 넣고, ztunnel에게 이 파드가 등록됐다고 알립니다. 이 두 번째 역할이 본체입니다.

ztunnel은 Rust로 쓰인 L4 전용 프록시고 Envoy가 아닙니다. waypoint만 Envoy인데 안 붙여도 메시가 돌아갑니다. istio-cni-node는 사이드카 모드에서는 선택이지만 ambient에서는 없으면 아예 동작하지 않습니다.
-->

---

# ztunnel — Rust로 쓴 L4 전용 프록시

| 항목 | 내용 |
|---|---|
| 구현 | **Rust**. Envoy가 아니다 |
| 하는 일 | **L4까지** — mTLS 종단, 신원 기반 허용·차단 |
| 안 하는 일 | HTTP 라우팅 · 리트라이 · 타임아웃 → **waypoint 몫** |
| 터널 | **HBONE**, 포트 15008 |
| TLS | **1.3 고정** — 사이퍼는 `AES_128_GCM_SHA256` · `AES_256_GCM_SHA384` 둘뿐 |

**HTTP를 파싱할 일이 없다.** 그래서 ztunnel은 **노드 공유로 설계할 수 있었다.** 그 대가는 다음 장 — 키와 격리 경계가 노드 단위가 된다.

<div class="src"><b>HBONE</b> = 앱 트래픽을 HTTP/2 의 <code>CONNECT</code> 로 감싸 mTLS 터널 안에 넣는 방식. 겉에서 보면 15008 포트로 가는 TLS 스트림 하나로만 보인다.<br><b>사이퍼수트</b> = <em>데이터를 무슨 알고리즘으로 암호화할지</em>의 조합. TLS 1.3에서는 <b>AEAD + 해시</b> 둘만 남았고(키 교환·서명은 따로 협상해서 표준 조합이 5개로 줄었다), ztunnel은 그중 둘만 켠다 — <b>ChaCha20은 없다.</b></div>

<!--
ztunnel이 뭔지 한 장으로 정리하겠습니다.

첫째, Rust로 쓰였고 Envoy가 아닙니다. 사이드카는 Envoy였는데 이건 새로 만든 별개 프로그램이에요.

둘째, L4까지만 합니다. mTLS를 종단하고, 상대가 누구인지 보고 통과시킬지 막을지 정합니다. 딱 거기까지예요.

셋째, 그래서 안 하는 게 명확합니다. HTTP 경로를 보고 라우팅한다든가, 실패하면 재시도한다든가, 타임아웃을 건다든가 하는 건 못 합니다. 그게 필요하면 waypoint를 붙여야 해요.

가운데 굵은 문장이 핵심입니다. HTTP를 파싱할 일이 없습니다. 그래서 노드 하나에 프록시 하나만 두는 설계가 가능해졌습니다.

오해하실까 해서 덧붙이면, 사이드카가 파드마다 있어야 했던 이유가 L7 하나만은 아닙니다. mTLS만 하는 사이드카도 파드별 트래픽 캡처와 파드별 신원, 파드 단위 격리 때문에 파드마다 필요했습니다.

ztunnel은 그중 격리를 포기하는 쪽을 택한 겁니다. L7을 안 하니 노드로 모을 수 있었고, 그 대가로 키와 격리 경계가 노드 단위가 됩니다. 다음 장이 바로 그 얘기입니다.

표에서 질문 나오기 쉬운 게 사이퍼 두 개입니다. 사이퍼수트는 데이터를 무슨 알고리즘으로 암호화할지 정하는 조합이에요. TLS 1.2까지는 키 교환 방식, 서명 방식, 암호화 방식, 해시가 다 한 덩어리로 묶여서 조합이 수백 개였습니다. 앞에서 1.3이 고를 것을 없앴다고 했는데 여기가 그 부분이에요. 1.3은 암호화 알고리즘과 해시 둘만 남기고 나머지는 따로 협상합니다. 그래서 표준 조합이 다섯 개로 줄었습니다.

ztunnel은 그중 두 개만 켭니다. AES 128과 AES 256이고 둘 다 GCM 모드예요. ChaCha20은 목록에 아예 없습니다. 양쪽이 다 자기 코드라 여러 개를 열어둘 이유가 없는 거죠.

아래 회색 글씨는 HBONE 풀이입니다. 앱 트래픽을 HTTP/2의 CONNECT로 감싸서 mTLS 터널에 넣습니다. 밖에서 보면 15008 포트로 가는 TLS 스트림 하나로만 보여요. 이 성질이 뒤에서 Cilium 정책이 의미를 잃는 이유가 됩니다.
-->

---

# 인증서는 누가 갖고 있나

**그렇다 — 프록시가 앱 대신 갖는다.** 사이드카 Envoy가 하던 그 일을 ztunnel이 한다. 달라진 건 **보관 위치**다.

<div class="cmp"
     data-left-title="사이드카 Envoy"
     data-left="파드마다 프록시 하나|그 파드 신원의 인증서 하나|키는 프록시 프로세스 메모리|털리면 그 파드 하나"
     data-right-title="ztunnel"
     data-right="노드마다 프록시 하나|그 노드 모든 신원의 인증서|키는 프록시 프로세스 메모리 - 동일|털리면 그 노드 전부"></div>

**앱 컨테이너가 아무것도 갖지 않는 건 양쪽 다 같다.** 앱은 평문을 내보내고 자기 트래픽이 암호화되는 줄도 모른다.

<!--
앞 장에서 프록시가 mTLS를 종단한다고 했는데, 그럼 인증서를 프록시가 들고 있는 거냐는 질문이 나옵니다. 그렇습니다.

기존 사이드카 Envoy가 하던 일과 같습니다. 앱은 평문으로 통신하고 옆의 프록시가 앱을 대신해 인증서를 들고 mTLS를 합니다. ztunnel도 똑같이 합니다.

달라진 건 보관 위치예요. 표를 가로로 봐 주세요.

첫 줄. 사이드카는 파드마다 하나였고 ztunnel은 노드마다 하나입니다.

둘째 줄이 핵심입니다. 사이드카는 그 파드 신원의 인증서 하나만 들고 있으면 됐어요. ztunnel은 그 노드에 떠 있는 모든 파드의 신원을 다 들고 있어야 합니다. 노드에 열 개 서비스가 있으면 열 개 신원의 키를 한 프로세스가 갖는 겁니다.

셋째 줄은 같습니다. 둘 다 디스크에 안 쓰고 프로세스 메모리에만 둡니다.

넷째 줄이 그 대가입니다. 사이드카가 털리면 그 파드 하나를 사칭당하는 거고, ztunnel이 털리면 그 노드에 있는 모든 서비스를 사칭당합니다. 격리 경계가 파드에서 노드로 넓어졌어요.

맨 아래 문장. 앱 컨테이너는 양쪽 다 아무것도 안 갖습니다. 이건 그대로입니다.
-->

---

# 그 인증서를 언제 받나 — 파드가 뜰 때

<div class="steps" data-steps="주 CNI 가 veth 와 파드 IP 를 만든다|istio-cni 가 파드 안에 리디렉션 규칙을 넣는다|ztunnel 에 이 파드를 등록한다|앱 컨테이너가 시작된다" data-start="1"></div>

**네 단계가 다 끝나야 앱이 시작된다.** 그래서 앱의 **첫 패킷부터** 규칙이 걸려 있다. 인증서는 등록 시점에 ztunnel이 istiod에서 받아 둔다.

<div class="src">뒤집으면 - <code>istio-cni-node</code> 가 죽으면 <b>새 파드가 못 뜬다</b>(<code>ContainerCreating</code> 정지). 이미 떠 있는 파드는 영향 없다.</div>

<!--
그럼 그 인증서를 언제 받느냐. 파드가 뜨는 순서를 보면 나옵니다. 네 단계입니다.

1번. 주 CNI가 먼저 일합니다. Cilium이든 Calico든 veth를 만들고 파드 IP를 붙여요. istio-cni는 체인 끝에 있으니 이게 끝난 뒤에 호출됩니다.

2번. istio-cni가 파드 네트워크 네임스페이스 안에 리디렉션 규칙을 넣습니다. 나가는 건 15001, 들어오는 평문은 15006, 암호화된 HBONE은 15008로 보내는 규칙이에요.

3번. ztunnel에게 이 파드를 등록합니다. 이 시점에 ztunnel이 그 파드 신원의 인증서를 istiod에서 받아 둡니다. 앞 장에서 말한 그 인증서요.

4번. 그다음에야 앱 컨테이너가 시작됩니다.

가운데 굵은 문장이 중요합니다. 네 단계가 다 끝나야 앱이 시작돼요. 그래서 앱이 보내는 첫 패킷부터 이미 규칙이 걸려 있습니다. 나중에 붙이는 게 아니에요.

아래 회색 글씨가 그 대가입니다. istio-cni-node가 죽으면 2번 3번을 할 사람이 없으니 새 파드가 아예 못 뜹니다. ContainerCreating에서 멈춰요. 대신 이미 떠 있던 파드는 영향받지 않습니다.
-->

---

# istiod → ztunnel: 전송은 xDS, 타입은 전용

<div class="seq" data-seq="istiod|:15012\nxDS over gRPC|istio.workload.Address\nistio.security.Authorization" data-accent="cyan|gold|green"></div>

공식 표현은 *"a simplified set of resources are used in the **xDS APIs**"* — xDS를 안 쓰는 것이 아니라 **Envoy 타입 대신 Istio 전용 타입 2개**를 쓴다. 인증서도 같은 연결로 받는다.

<!--
여기도 정확하게 말해야 하는 지점입니다.
"ztunnel은 표준 xDS를 안 쓴다"고 말하면 공식 문서와 충돌합니다. 문서는 "xDS API에서 단순화된 리소스 집합을 쓴다"고 씁니다. 전송 프로토콜은 xDS 그대로입니다. 다른 건 실려오는 리소스 타입입니다.
사이드카 Envoy는 LDS, CDS, RDS, EDS를 받습니다. ztunnel은 두 타입만 받습니다. istio.workload.Address가 파드와 서비스 목록입니다. IP, SPIFFE 신원, 어느 노드에 있는지, waypoint가 붙어 있는지가 들어갑니다. istio.security.Authorization이 L4 인가 정책입니다.
재밌는 게 PeerAuthentication은 그대로 안 옵니다. istiod가 네임스페이스와 워크로드 정책을 합쳐 유효 정책을 계산한 다음 Authorization으로 변환해 보냅니다. 판단은 컨트롤 플레인에서 끝납니다.
그리고 인증서도 같은 연결로 받습니다. 별도 채널이 아닙니다.
받지 않는 것도 알아두세요. VirtualService, DestinationRule, L7 정책은 안 옵니다. waypoint 몫입니다.
-->

---

# waypoint — L7이 필요할 때만

<div class="seq" data-seq="출발지\nztunnel|waypoint\n(Envoy)|목적지\nztunnel|Pod B" data-accent="green|gold|green|cyan"></div>

**누가 waypoint로 보내나** — 파드 안 방화벽 규칙이 아니라 **출발지 ztunnel**이 정한다. 목적지에 waypoint가 붙어 있다는 걸 알고 그쪽으로 먼저 보낸다. 그래서 waypoint를 붙이거나 떼도 파드 안 설정은 건드리지 않는다.

**비용 두 가지** — 프록시를 지나는 횟수가 2회에서 **3회**로 늘고, waypoint는 별도 Deployment라 **다른 노드에 떠 있을 수 있어** 그 노드까지 다녀오는 왕복이 추가된다.

<!--
waypoint는 Envoy입니다. HTTP 라우팅, 리트라이, 타임아웃, L7 인가를 여기서 합니다.

첫 문단이 헷갈리기 쉬운 부분이라 풀어서 적었습니다. waypoint로 꺾는 주체가 누구냐는 얘기예요. 파드 안에 넣어둔 방화벽 규칙이 목적지를 바꾸는 게 아닙니다. 출발지 ztunnel이 "이 목적지에는 waypoint가 붙어 있네" 하고 알고 있어서, 목적지 파드로 바로 가지 않고 waypoint로 먼저 보냅니다.

이게 왜 좋냐면, waypoint를 새로 붙이거나 떼어낼 때 파드 안 설정을 다시 안 건드려도 됩니다. 판단이 ztunnel 쪽에 있으니까요.

두 번째 문단이 비용입니다. 하나, 앞에서 프록시를 두 번 지난다고 했는데 waypoint가 끼면 세 번이 됩니다. 둘, waypoint는 DaemonSet이 아니라 별도 Deployment입니다. 출발지나 목적지와 다른 노드에 떠 있을 수 있어요. 그러면 그 노드까지 갔다 오는 네트워크 왕복이 하나 더 붙습니다.

그래서 필요한 서비스에만 붙이라고 안내합니다. 전 네임스페이스에 다 붙이면 사이드카보다 무거워질 수 있습니다.
-->

---

<!-- _class: lead -->

# 05 Istio Ambient mode vs Cilium

**① 실제로 뜨는 리소스 · ② L4·L7 · ③ L3**

<!--
마지막 챕터입니다.

"둘 중 뭐가 나아요"에 한 문장으로 답할 수 없어서 세 가지로 쪼갰습니다.

첫째는 클러스터에 실제로 무엇이 몇 개나 뜨는지. 둘째는 같은 L4·L7이라는 말이 서로 다른 뜻이라는 얘기. 셋째가 제 결론인 L3입니다.

바로 첫째부터 보겠습니다.
-->

---

# ① 실제로 뜨는 리소스 - Istio Ambient

| 오브젝트 | 종류 | 개수 |
|---|---|---|
| `istiod` | **Deployment** | 1 (HPA 1~5) |
| `istio-cni-node` | **DaemonSet** | 노드 수 |
| `ztunnel` | **DaemonSet** | 노드 수 |
| `waypoint` | **Deployment** | **`Gateway` 리소스마다 1** (아래 참조) |

**waypoint는 DaemonSet이 아니다.** `Gateway` 하나당 Deployment 하나 + Service·HPA·PDB. istiod가 `Gateway`를 보고 자동으로 만든다.

붙이는 **단위는 선택**이다 — 네임스페이스에 공용 하나로 둘 수도, 서비스·서비스어카운트마다 따로 둘 수도 있다.

<div class="src">여기서 <b>Gateway</b>는 <b>쿠버네티스 Gateway API</b>의 표준 리소스(<code>gateway.networking.k8s.io/v1</code>)다. <code>gatewayClassName: istio-waypoint</code>로 하나 만들면 istiod가 그것을 보고 Deployment를 찍어낸다(<code>istioctl waypoint apply</code>가 대신 만들어 준다).<br><b>이름이 겹친다</b> — Istio 고유 API인 <code>networking.istio.io/v1 Gateway</code>(ingress·egress 게이트웨이 설정, <b>지금도 지원되는 안정 API</b>)와는 <b>별개 리소스</b>다. 그쪽은 메시 경계에 놓이고 waypoint는 <b>메시 안쪽</b>에 놓인다.</div>

<!--
실제로 클러스터에 뭐가 뜨는지 봅니다. 종류 칸을 봐 주세요. DaemonSet이냐 Deployment냐가 개수와 직결됩니다.

istiod는 Deployment 하나입니다. 오토스케일이 기본으로 켜져 있어서 부하에 따라 다섯 개까지 늘어납니다.

istio-cni-node와 ztunnel은 DaemonSet입니다. 노드마다 하나씩이니까 노드가 백 대면 각각 백 개예요.

마지막 줄이 오해가 많은 부분이라 굵게 적었습니다. waypoint는 DaemonSet이 아닙니다. Deployment입니다. Gateway 리소스를 하나 만들면 istiod가 그걸 보고 Deployment를 하나 만들어 줍니다. Service랑 오토스케일러랑 PDB까지 세트로 딸려 옵니다.

그러니까 개수가 노드 수에 비례하지 않습니다. Gateway 리소스를 몇 개 만드느냐에 달렸어요.

여기서 Gateway가 뭔지 짚고 가겠습니다. 회색 글씨 보시면 됩니다. 쿠버네티스 Gateway API의 표준 리소스입니다. Ingress를 대체하려고 나온 그거예요. gatewayClassName을 istio-waypoint로 줘서 하나 만들면 istiod가 그걸 보고 Deployment를 찍어냅니다. 보통은 손으로 안 쓰고 istioctl waypoint apply 명령이 대신 만들어 줍니다.

주의하실 게 이름이 겹칩니다. Istio에는 자체 Gateway API가 따로 있어요. networking.istio.io 쪽이고 ingress와 egress 게이트웨이를 설정합니다. 이건 폐기된 게 아니라 지금도 지원되는 안정 API예요. 쿠버네티스 Gateway API와 별개로 존재하는 겁니다.

둘은 이름만 같고 다른 리소스입니다. Istio 쪽 Gateway는 메시 경계에 놓이고, waypoint는 메시 안쪽에 놓여서 서비스 사이 트래픽을 처리합니다.

그리고 붙이는 단위를 고를 수 있습니다. 네임스페이스에 공용으로 하나만 둘 수도 있고 서비스마다 따로 둘 수도 있어요. 격리를 원하면 잘게, 파드 수를 아끼려면 굵게 갑니다. 다음 장 숫자는 서비스마다 따로 둔 경우를 가정한 겁니다.
-->

---

# ① 실제로 뜨는 리소스 - Cilium

**기본 설치** - 이 셋이 전부다

| 오브젝트 | 종류 | 개수 |
|---|---|---|
| `cilium` (agent) | **DaemonSet** | 노드 수 |
| `cilium-operator` | **Deployment** | 2 |
| `cilium-envoy` | **DaemonSet** | 노드 수 - **1.16부터 신규 설치 기본값** |

**선택 (opt-in)** - 켜야 뜬다

| 오브젝트 | 종류 | 조건 |
|---|---|---|
| `ztunnel-cilium` | DaemonSet | `encryption.type: ztunnel` - **1.19 Beta** |

`cilium-envoy`는 예전엔 에이전트 파드 안의 프로세스였다. 지금은 별도 DaemonSet이 기본이고 **L7을 쓰든 안 쓰든 노드마다 하나 뜬다.**

<!--
Cilium 쪽입니다. 기본과 선택을 나눠서 적었습니다.

위 표가 기본 설치입니다. 셋뿐이에요. 에이전트가 DaemonSet, 오퍼레이터가 Deployment 두 개, 그리고 envoy가 DaemonSet입니다.

세 번째 줄을 강조하고 싶습니다. cilium-envoy는 1.16부터 신규 설치의 기본값입니다. 옵션이 아니라 기본이에요. 예전에는 에이전트 파드 안에서 프로세스로 돌았는데, 수명주기를 따로 관리하려고 별도 DaemonSet으로 분리했습니다. 그래서 L7 정책을 하나도 안 써도 노드마다 하나씩 떠 있습니다.

아래 표가 선택입니다. ztunnel은 켜야 뜹니다. encryption.type을 ztunnel로 줘야 하고, 1.19에서 들어온 Beta예요. 기본 설치에는 없습니다.

이 구분이 다음 장 숫자에서 중요해집니다. 기본만 세는 것과 ztunnel을 켠 걸 세는 게 다르니까요.
-->

---

# ① 규모를 넣어 보면 - 노드 50

| | Istio Ambient | Cilium |
|---|---|---|
| 노드 단위 | cni 50 + ztunnel 50 = **100** | agent 50 + envoy 50 = **100** |
| 그 외 | istiod 1~5 | operator 2 |
| **기본 합계** | **약 101~105** | **약 102** |
| 선택 추가 | waypoint - `Gateway`마다 1 | ztunnel-cilium 50 (**Beta**) |

**기본은 거의 같다.** 갈리는 건 아래 줄이다 - Ambient는 **L7을 켤 때** `Gateway` 수만큼, Cilium은 **워크로드 mTLS를 켤 때** 노드 수만큼 늘어난다.

<div class="src">Ambient 쪽 숫자에는 <b>주 CNI가 빠져 있다</b> - Cilium이든 Calico든 무언가는 깔아야 하고 그것도 DaemonSet이다. 지연·처리량은 여기서 말하지 않는다: 공개된 head-to-head 수치가 없고, Istio 2025 벤치마크의 Cilium은 <code>v1.16.6</code>으로 ztunnel 도입(1.19) 이전이다.</div>

<!--
숫자를 넣어 보겠습니다. 노드 50대 클러스터입니다.

첫 줄, 노드 단위. 양쪽 다 백 개입니다. Ambient는 cni와 ztunnel, Cilium은 에이전트와 envoy예요. 우연히 같습니다.

둘째 줄도 비슷합니다. istiod 몇 개 대 오퍼레이터 둘.

그래서 세 번째 줄, 기본 합계가 거의 같습니다. 백 개 남짓씩이에요. 여기까지는 차이가 없습니다.

갈리는 건 네 번째 줄입니다. 그런데 방향이 다릅니다.

Ambient는 L7을 켤 때 늘어납니다. Gateway를 몇 개 만드느냐에 달렸어요. 서비스마다 따로 두면 서비스 수만큼, 네임스페이스 공용으로 묶으면 네임스페이스 수만큼입니다.

Cilium은 워크로드 단위 mTLS를 켤 때 늘어납니다. 이건 DaemonSet이라 노드 수만큼, 즉 오십 개가 붙습니다. 그리고 Beta예요.

정리하면 Ambient는 L7 기능에 비용을 내고 Cilium은 워크로드 신원에 비용을 냅니다. 둘 다 켜면 둘 다 냅니다.

회색 글씨 두 가지. 하나, Ambient 쪽 숫자에는 주 CNI가 아직 안 들어 있습니다. 그걸 넣으면 Ambient가 더 많아집니다. 둘, 성능 수치는 말하지 않겠습니다. 공개된 맞대결 자료가 없고, 이스티오 벤치마크가 쓴 Cilium은 ztunnel 들어오기 전 버전입니다.
-->

---

# ② 같은 L4·L7, 다른 뜻

<div class="cmp"
     data-left-title="Cilium (ztunnel 없이)"
     data-left="정책 판정 = 숫자 CiliumIdentity (라벨에서 파생)|커널 eBPF 에서 판정|cilium-envoy 도 숫자 ID 로 매칭|인증서는 k8s Secret 에서 SDS 로"
     data-right-title="Istio Ambient"
     data-right="정책 판정 = SPIFFE 신원 (ns/sa)|유저스페이스 ztunnel 에서 판정|IP 기반 (ipBlocks) 도 쓸 수 있다|L7 은 waypoint - 붙인 범위만큼"></div>

**L7** - 차이는 성능이 아니라 **격리 범위**다. 노드 Envoy는 그 노드의 L7이 한곳에 모이고, waypoint는 붙인 범위만큼 나뉜다.

<div class="src">예외 하나 - <b>mutual authentication</b>은 SPIRE 기반이다. 다만 <b>1.19부터 기본 꺼짐 · 1.20 deprecated</b>(1.21 제거 예정)이고, 핸드셰이크는 Envoy가 아니라 <b>cilium-agent</b>가 노드 간 4250으로 한다. 신원도 <code>spiffe://.../identity/&lt;숫자&gt;</code> - 숫자 identity를 URI로 감싼 것이지 <code>ns/sa</code> 워크로드 신원이 아니다.</div>

<!--
둘째입니다. 양쪽 다 L4 정책, L7 정책이라는 말을 쓰는데 뜻이 다릅니다.

왼쪽은 ztunnel을 켜지 않은 기본 Cilium입니다. 정책 판정 근거가 숫자 identity예요. 파드 라벨을 모아서 숫자 하나를 부여하고, 정책은 그 숫자로 매칭합니다.

여기서 질문이 나올 수 있습니다. L7은 Envoy가 하는데 Envoy는 SPIFFE 쓰지 않느냐. 안 씁니다. cilium-envoy가 받는 정책 규칙을 열어 보면 필드 이름부터 remote_policies이고 타입이 숫자 배열이에요. 상대가 누구인지는 소스 IP로 숫자 identity를 역조회해서 정합니다. 인증서를 검증하는 게 아닙니다.

인증서를 아예 안 쓰는 건 아니에요. TLS Visibility나 Ingress에서 씁니다. 그런데 그 인증서는 쿠버네티스 Secret에 넣어둔 걸 가져다 쓰는 거지 SPIFFE가 아닙니다. 표 왼쪽 마지막 두 줄이 그 얘기입니다.

오른쪽 Ambient는 상대 인증서의 SPIFFE 신원이 그대로 정책 판정 근거가 됩니다. 물론 IP 조건도 쓸 수 있어요. AuthorizationPolicy는 ipBlocks도 지원하니까 신원만 쓴다는 뜻은 아닙니다.

L7 얘기는 격리 범위입니다. Cilium은 노드마다 Envoy 하나라 그 노드 L7이 한곳에 모입니다. 한 서비스에 몰리면 같은 노드의 다른 서비스가 영향을 받아요. Ambient의 waypoint는 붙인 범위만큼 나뉩니다.

맨 아래 회색 글씨가 예외입니다. Cilium에도 SPIFFE를 쓰는 기능이 하나 있어요. mutual authentication입니다. 그런데 세 가지 단서가 붙습니다.

하나, 1.19부터 기본으로 꺼져 있고 1.20에서 deprecated 됐습니다. 1.21에서 제거될 예정이에요. 공식 안내가 대신 ztunnel을 쓰라고 합니다.

둘, 핸드셰이크를 하는 게 Envoy가 아닙니다. cilium-agent가 상대 노드의 4250 포트로 붙어서 대역 외로 mTLS를 맺습니다. 트래픽 경로 밖에서 하는 거예요.

셋, 신원 형식이 다릅니다. spiffe 슬래시 identity 슬래시 숫자입니다. Cilium 숫자 identity를 URI로 감싼 것뿐이에요. Istio식으로 네임스페이스와 서비스어카운트가 들어가는 워크로드 신원이 아닙니다.
-->

---

# ③ Cilium에만 있는 것 - 주소와 경로

Ambient는 **주 CNI 뒤에 붙는 플러그인**이라 아래 셋은 **책임 범위 밖**이다.

**IPAM** - 파드에 IP를 나눠주는 규칙. AWS ENI 모드면 파드가 **VPC IP를 직접** 받는다.
<span class="tag">VPC 내부 목적지로 갈 때 오버레이 캡슐화도 노드 SNAT도 없다 (인터넷은 NAT GW를 거친다)</span>

**BGP** - 파드 대역과 Service IP를 **외부 라우터에 광고**한다. 사내 장비가 그 경로를 배우면 클러스터 밖에서 파드 IP로 바로 붙는다.
<span class="tag">클러스터 <b>안</b> 도달성을 만드는 게 아니라 <b>이미 있는 경로를 알리는</b> 기능이다</span>

**LB IPAM** - 클라우드 LB가 없는 환경에서 `LoadBalancer` Service에 IP를 준다. 그 IP를 **알리는 건 BGP·L2 몫**이다.

<!--
셋째, L3입니다. 여섯 가지를 두 장에 나눠 보겠습니다.

맨 위 문장부터. Ambient는 주 CNI 뒤에 붙는 플러그인이에요. 파드에 IP를 주는 일 자체를 안 하니까 아래 기능들이 있을 수가 없습니다. 못 하는 게 아니라 책임 범위가 아닙니다.

IPAM. 파드에 IP를 어떤 규칙으로 나눠줄지입니다. 제일 크게 갈리는 게 AWS ENI 모드예요. 파드가 클러스터 내부 IP가 아니라 VPC IP를 직접 받습니다.

옆 작은 글씨에 범위를 적어 뒀습니다. VPC 안에 있는 목적지로 갈 때 얘기입니다. 그 경우엔 오버레이로 감싸지도 않고 노드 IP로 바꾸지도 않아요. 보안그룹도 파드에 직접 걸립니다. 인터넷으로 나갈 때는 여전히 NAT 게이트웨이를 거칩니다.

BGP. 파드 대역과 서비스 IP를 외부 라우터에 광고합니다. 사내 라우터가 그 경로를 배우면 클러스터 밖 서버에서 파드 IP로 바로 접속할 수 있어요.

옆 글씨가 오해하기 쉬운 지점입니다. BGP는 클러스터 안쪽 도달성을 만드는 기능이 아닙니다. 이미 있는 경로를 밖에 알리는 것뿐이에요.

LB IPAM. 온프렘에는 클라우드 로드밸런서가 없어서 LoadBalancer 타입 서비스가 계속 pending에 머뭅니다. Cilium이 정해둔 풀에서 IP를 꺼내 줍니다. 단, IP를 줬다고 트래픽이 찾아오지는 않아요. 그 IP를 알리는 건 BGP나 L2 광고가 합니다.
-->

---

# ③ Cilium에만 있는 것 - 출발지·노드·클러스터

**Egress Gateway** - 밖으로 나가는 파드 트래픽을 **지정한 노드**로 보내 **고정 IP로 SNAT**한다.
<span class="tag">외부에서 방화벽에 출발지 IP 등록을 요구할 때 - 없으면 노드 IP를 전부 등록해야 한다</span>
<span class="tag">Istio의 동명 기능과 다르다 - 그쪽은 나가는 트래픽을 <b>모아서 정책·관측</b>을 걸 뿐 출발지 IP를 고정하지 않는다</span>

**Host Firewall** - 정책 대상이 파드가 아니라 **노드 자신**이다. SSH·kubelet처럼 노드가 직접 여는 포트를 같은 문법으로 통제한다.

**ClusterMesh** - 클러스터 여러 개의 **파드망을 연결**한다. 같은 이름의 Service를 경계 너머로 묶는다.
<span class="tag">ztunnel 암호화와 <b>동시 사용 불가</b> - 켜면 validation error</span>

<!--
나머지 셋입니다.

이그레스 게이트웨이가 실무에서 제일 자주 필요합니다. 상황을 그려 볼게요. 외부 결제사가 접속할 IP를 알려주면 방화벽에 등록해 주겠다고 합니다. 그런데 파드 IP는 재시작마다 바뀌고, 노드 IP로 나간다 해도 노드가 오십 대면 오십 개를 다 등록해야 해요. 노드를 늘리면 또 등록해야 하고요.

이 기능은 그 대역으로 나가는 트래픽만 지정한 노드로 먼저 보냅니다. 거기서 정해둔 IP로 바꿔 내보내요. 등록할 IP가 하나로 고정됩니다.

두 번째 작은 글씨가 중요합니다. Istio에도 egress gateway가 있습니다. 이름은 같은데 하는 일이 달라요. Istio 쪽은 나가는 트래픽을 한 게이트웨이로 모아서 정책을 걸고 로그를 남기는 겁니다. 출발지 IP를 고정해 주지는 않습니다.

호스트 방화벽. 지금까지 정책은 다 파드 얘기였는데 이건 노드 자신입니다. SSH나 kubelet처럼 노드가 직접 여는 포트를 파드 정책과 같은 문법으로 막습니다. 노드 오십 대에 iptables를 따로 관리하지 않아도 돼요.

클러스터메시. 클러스터 여러 개의 파드망을 연결합니다. 파드가 다른 클러스터 파드에 IP로 바로 붙어요. 같은 이름의 서비스를 두 클러스터에 두면 하나처럼 묶입니다.

아래 글씨가 제약입니다. ztunnel 암호화와 같이 못 씁니다. 켜려고 하면 검증 단계에서 에러가 나요. 둘 다 필요하면 지금은 답이 없습니다.
-->

<script>
(function () {
  var C = { cyan: '#00d4ff', green: '#00ff88', gold: '#ffd700', red: '#ff6b6b', orange: '#ff9e64', dim: '#5a6070' };
  var CYCLE = ['cyan', 'green', 'gold', 'orange'];

  function parts(el, name) {
    var v = el.getAttribute(name);
    return v ? v.split('|') : [];
  }
  function txt(s) {
    return s.split('\\n').join('<br>');
  }
  function done(el) {
    if (el.getAttribute('data-rendered') === '1') return true;
    el.setAttribute('data-rendered', '1');
    return false;
  }

  Array.prototype.forEach.call(document.querySelectorAll('.seq'), function (el) {
    if (done(el)) return;
    var nodes = parts(el, 'data-seq');
    var acc = parts(el, 'data-accent');
    var html = '';
    for (var i = 0; i < nodes.length; i++) {
      var key = acc[i] && C[acc[i]] ? acc[i] : 'cyan';
      if (i > 0) html += '<div class="seq-arrow"></div>';
      html += '<div class="seq-node" style="border-color:' + C[key] + '">' + txt(nodes[i]) + '</div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.stack'), function (el) {
    if (done(el)) return;
    var layers = parts(el, 'data-stack');
    var acc = parts(el, 'data-accent');
    var html = '';
    for (var i = 0; i < layers.length; i++) {
      var w = 100 - i * 8;
      var key = acc[i] && C[acc[i]] ? acc[i] : CYCLE[i % CYCLE.length];
      html += '<div class="stack-layer" style="width:' + w + '%;border-color:' + C[key] + '">' + txt(layers[i]) + '</div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.steps'), function (el) {
    if (done(el)) return;
    var items = parts(el, 'data-steps');
    var start = parseInt(el.getAttribute('data-start') || '1', 10);
    var html = '';
    for (var i = 0; i < items.length; i++) {
      html += '<div class="step"><div class="step-num">' + (start + i) + '</div>'
        + '<div class="step-txt">' + txt(items[i]) + '</div></div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.cmp'), function (el) {
    if (done(el)) return;
    var html = '';
    ['left', 'right'].forEach(function (side) {
      var title = el.getAttribute('data-' + side + '-title') || '';
      var items = parts(el, 'data-' + side);
      var body = '';
      for (var i = 0; i < items.length; i++) body += '<div class="cmp-item">' + txt(items[i]) + '</div>';
      html += '<div class="cmp-col ' + side + '"><div class="cmp-title">' + title + '</div>' + body + '</div>';
    });
    el.innerHTML = html;
  });
})();
</script>
