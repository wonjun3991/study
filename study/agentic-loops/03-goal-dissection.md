# 03 — `/goal` 해부 (Codex + Claude Code)

> **3줄 요약**:
> 1. 사용자가 `/goal "검증 가능한 종료 상태"`로 조건을 걸면, **작업 모델(Sonnet/Opus 등)**이 한 차례 일을 하고 결과를 대화 기록(transcript)에 남긴다 — 1, 2장처럼 LLM 본인이 "끝났다"고 선언하지 않는다.
> 2. 차례가 끝날 때마다 **별도의 작은 평가자 모델(Haiku 등)**이 조건과 대화 기록을 받아 `yes/no + 이유`를 판정한다. `no`면 그 이유가 다음 차례 가이드로 함께 주입돼 작업 모델이 부족한 부분을 채우러 들어간다.
> 3. 평가자가 `yes`라고 판정할 때까지 (또는 사용자가 일시정지/제거하거나 예산 한도에 닿을 때까지) 반복한다 — 즉 **종료 판정이 작업한 LLM이 아니라 다른 LLM에게 옮겨갔다**. 이게 Ralph 계열의 "스스로 평가자(self-assessor) 문제"에 대한 산업의 답.
>
> ---
>
> **목적**: Ralph 패턴이 안고 있던 "스스로 평가자(self-assessor) 문제"(LLM이 자기 일을 자기가 평가)를 산업이 어떻게 외부 평가자(evaluator)로 풀어냈는지, Codex `/goal`(2026-05-09)과 Claude Code `/goal`(v2.1.139+)의 프롬프트와 메커니즘을 원본 텍스트(raw text)로 직접 해부한다.
>
> **수집일**: 2026-05-18
> **출처**:
> - [Codex Cookbook — Using Goals in Codex (2026-05-09)](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)
> - [Codex Use case — Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals)
> - [Claude Code — `/goal` docs](https://code.claude.com/docs/en/goal)
> - [Claude Code — Hooks reference](https://docs.anthropic.com/en/docs/claude-code/hooks)
>
> **읽는 순서**: §0 (왜 이게 만들어졌나) → §1 (Codex `/goal`) → §2 (Claude `/goal`) → §3 (둘의 프롬프트 디자인 비교) → §4 (종료 훅(Stop hook)의 프롬프트 기반 메커니즘) → §5 (Ralph와의 연결: 무엇을 고쳤나) → §6 (남은 문제)

---

## 0. 왜 `/goal`이 만들어졌나 — 한 줄

**Ralph 패턴이 LLM 본인에게 "끝났냐"를 물어본 결과, LLM이 거짓말을 하거나(조기 종료) 멈출 줄 모름(무한 루프)** → 산업이 해결책으로 **작업 모델 ≠ 평가 모델** 분리에 도달. 그 구체적 구현이 OpenAI와 Anthropic이 거의 동시에 출시한 `/goal`.

핵심 문구 두 개:

> **OpenAI**: *"Completion must be evidence-based. A Goal should not be marked complete because the model believes it is probably done."*
>
> 한국어 풀이: **완료는 증거 기반이어야 한다. 모델이 "아마 끝났을 것"이라 믿는다고 Goal을 완료로 표시해선 안 된다.**
> — [Codex Cookbook, 2026-05-09](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)

> **Anthropic**: *"`/goal` adds a separate evaluator that checks your condition after every turn, so completion is decided by a fresh model rather than the one doing the work."*
>
> 한국어 풀이: **`/goal`은 매 차례 끝마다 조건을 확인하는 별도 평가자를 추가한다. 그래서 완료 여부는 작업 중인 모델이 아니라 새 모델이 결정한다.**
> — [Claude Code `/goal` docs](https://code.claude.com/docs/en/goal)

두 회사가 **별도 모델이 증거 기반(evidence-based)으로 yes/no 판정**이라는 동일 결론에 동시 도달. 이게 README §8-1의 "스스로 평가자(self-assessor) 문제"의 직접적 해결.

---

## 1. Codex `/goal` — 해부

### 1-A. 명령 표면 (CLI 슬래시 명령)

```
/goal Reduce p95 latency below 120 ms without regressing correctness tests
/goal              # 현재 goal 조회
/goal pause        # 일시 정지
/goal resume       # 재개
/goal clear        # 제거
```

활성화: `/experimental` 메뉴에서 켜거나 `config.toml`에:
```toml
[features]
goals = true
```

> **읽어낸 의도**: 실험적(experimental) 플래그 뒤에 숨김. 아직 안정화 전. 즉 **2026-05 시점에는 이 메커니즘이 정답인지 OpenAI도 확신하지 못함**. 데이터 모으는 단계.

### 1-B. ⭐ Goal 프롬프트 작성 패턴 — 6가지 슬롯

Cookbook 본문에서 직접 인용:

> *"The strongest Goals usually define six things:*
> - *Outcome: what should be true when the work is done.*
> - *Verification surface: the test, benchmark, report, artifact, command output, or source material that proves it.*
> - *Constraints: what must not regress while Codex works.*
> - *Boundaries: which files, tools, data, repositories, or resources Codex may use.*
> - *Iteration policy: how Codex should decide what to try next after each attempt.*
> - *Blocked stop condition: when Codex should stop and report that no defensible path remains under the current limits."*

→ 한국어 풀이: **가장 강력한 Goal은 보통 6가지를 정의한다.**
- **결과(Outcome)**: 작업이 끝났을 때 무엇이 참이어야 하는가.
- **검증 표면(Verification surface)**: 그것을 증명하는 테스트, 벤치마크, 보고서, 산출물, 명령 출력, 또는 원본 자료.
- **제약(Constraints)**: Codex가 작업하는 동안 망가지면 안 되는 것.
- **경계(Boundaries)**: Codex가 사용해도 되는 파일, 도구, 데이터, 저장소, 자원.
- **반복 정책(Iteration policy)**: 매번 시도 후 다음에 무엇을 시도할지 Codex가 결정하는 방법.
- **막힘 종료 조건(Blocked stop condition)**: 현재 한도 안에서 합리적 경로가 남지 않았을 때 Codex가 멈추고 보고해야 할 시점.

그리고 **표준 템플릿 형식**:

```
/goal <desired end state>
verified by <specific evidence>
while preserving <constraints>.
Use <allowed inputs, tools, or boundaries>.
Between iterations, <how Codex should choose the next best action>.
If blocked or no valid paths remain, <what Codex should report and what would unlock progress>.
```

→ 한국어 풀이:

```
/goal <원하는 종료 상태>
<구체적 증거>로 검증되고
<제약>을 보존하면서.
<허용된 입력, 도구, 또는 경계>를 사용하라.
반복 사이에는 <Codex가 다음 최선 행동을 고르는 방법>.
막히거나 유효 경로가 없으면 <Codex가 보고할 내용과 진척을 풀 방법>.
```

#### 1-B-1. 줄 단위 해부

| 슬롯 | 무엇을 채우나 | 왜 |
|---|---|---|
| `<원하는 종료 상태>` | 수치/사실 기반 종료 상태 (예: "p95 < 120ms") | "잘 됐다" 같은 주관 표현 금지. 평가자가 판정해야 하므로 |
| `<증거>로 검증` | 어떤 명령/파일/벤치마크로 증명할지 | **이게 증거 기반(evidence-based)의 메커니즘**. 모델이 "내 생각엔 빠른듯"이 아니라 "벤치마크 수치"를 보게 강제 |
| `<제약>을 보존하면서` | 망가뜨리면 안 되는 것 (테스트, API 호환) | LLM이 종료 조건만 만족시키려 다른 걸 깨는 것 방지 |
| `<경계>를 사용` | 어떤 파일/도구만 사용 가능 | 무한 탐색 방지. 사람이 범위(scope)를 잠그는 손잡이 |
| `반복 사이 <반복 정책>` | 한 시도가 안 통하면 다음을 어떻게 고를지 | **메타-학습 지침**. "벤치마크 결과 적기, 다음 가설 적기" 같은 연구 노트 행동 강제 |
| `막히면 <막힘 종료 조건>` | "막히면 어떻게 보고할지" | **이게 `/goal`의 가장 큰 진화**. 종료 = 성공만이 아님. "뭐가 막혔는지 정확히 보고"도 종료의 한 형태 |

> ⭐ **핵심 발견**: `/goal`은 단순히 "끝까지 가라"가 아니라 **"끝까지 가되, 막히면 막혔다고 정확히 말해라"**까지 프롬프트에 박음. Ralph 원본의 "fix_plan.md가 빌 때까지 무한 시도"와 결정적으로 다름.

#### 1-B-2. 약한 vs 강한 goal — Cookbook의 직접 비교

```
weak:    /goal Improve performance
strong:  /goal Reduce p95 latency below 120 ms on the checkout benchmark
         while keeping the correctness test suite green
```

→ 한국어 풀이:
- 약한 예: `/goal 성능 개선`
- 강한 예: `/goal 정합성 테스트 스위트가 통과(green)인 상태를 유지하면서 결제(checkout) 벤치마크에서 p95 응답시간을 120ms 이하로 줄여라`

```
weak:    /goal Write docs for this feature
strong:  /goal Produce a docs page for Goals that explains the lifecycle, command
         surface, and two examples. Verify that the page builds locally and that
         all referenced commands match the current CLI behavior.
```

→ 한국어 풀이:
- 약한 예: `/goal 이 기능에 대한 문서 작성`
- 강한 예: `/goal Goals의 생명주기, 명령 표면, 그리고 예제 두 개를 설명하는 문서 페이지를 만들어라. 페이지가 로컬에서 빌드되는지, 그리고 참조된 모든 명령이 현재 CLI 동작과 일치하는지 검증해라.`

> **읽어낸 패턴**: **약한 goal은 동사**(Improve, Write), **강한 goal은 종료 상태**(< 120ms, builds locally). 프롬프트를 동사가 아니라 "참(true)이어야 할 명제"로 바꾸는 게 핵심.

#### 1-B-3. ⭐ 가장 강한 예시 — 정량(quant) 논문 재현

Cookbook이 직접 든 가장 정교한 예:

```
/goal Produce the strongest evidence-backed reproduction of Buehler et al.,
"Deep Hedging," using the available paper materials and local resources.
Attempt every headline result, verify the outputs, and end with a report
that separates reproduced mechanics, approximate trained results,
blocked exact replay, and remaining uncertainty.
```

→ 한국어 풀이:

> **`/goal` 사용 가능한 논문 자료와 로컬 자원을 활용해 Buehler 외(外) "Deep Hedging" 논문의 가장 강력한 증거 기반 재현(reproduction)을 산출해라. 모든 대표 결과(headline result)를 시도하고, 출력을 검증하고, 다음 4가지를 분리한 보고서로 끝내라: (a) 재현된 메커니즘, (b) 근사 훈련 결과, (c) 차단된 정확 재생(blocked exact replay), (d) 남은 불확실성.**

뜯어보면:

| 부분 | 슬롯 매핑 |
|---|---|
| `Produce the strongest evidence-backed reproduction of...` | 결과 (강도까지 명시 — "최강의 증거 기반 재현") |
| `using the available paper materials and local resources` | 경계 |
| `Attempt every headline result` | 반복 정책 |
| `verify the outputs` | 검증 표면 |
| `end with a report that separates...` | **산출물 + 완료 정의** |
| `reproduced mechanics, approximate trained results, blocked exact replay, and remaining uncertainty` | **4단계 종료 분류**: 정확 재현 / 근사 / 차단 / 불확실 |

> **흥미점**: "완료 = 단일 yes/no" 아닌 **다층 분류**. 정확 재현이 안 되면 "차단(blocked)"이라고 정확히 말하라는 명령. 이건 진짜 연구자가 논문 reproduction 할 때 쓰는 공개(disclosure) 표준에 가까움. **"진실한 실패(truthful failure)"가 성공의 한 형태**.

### 1-C. 종료 상태 — 4가지

Cookbook + use-case 페이지에서:

| 상태 | 의미 |
|---|---|
| `achieved` (달성됨) | 평가자가 조건 충족 확인 |
| `paused` (일시 정지) | 사용자가 일시 정지 |
| `cleared` (제거됨) | 사용자가 `/goal clear` |
| `budget-limited` (예산 한도 도달) | 비용 한도 도달 (★ **완료 아님**) |

> ⭐ **핵심**: `budget-limited`가 별도 상태. 즉 "돈/시간 떨어져서 멈췄다"가 "완료"로 표시되지 않음. 사람이 결과 볼 때 "이건 진짜 끝난 게 아니다"가 한눈에 구분됨.
>
> Ralph 원본은 `max_iterations` 도달 시 그냥 종료. 완료/미완료 구분 없음. **이걸 `/goal`이 명시화**.

### 1-D. 아키텍처 노트 — Cookbook의 직접 인용

> *"Goals are implemented as persisted thread state, not as global memory and not as project-level instructions. That design choice is important: the objective belongs to the thread where the relevant context lives."*
>
> 한국어 풀이: **Goal은 영속 스레드 상태(persisted thread state)로 구현되며, 전역 메모리도 아니고 프로젝트 수준 지시문도 아니다. 이 설계 선택이 중요하다 — 목표는 관련 컨텍스트가 살아 있는 스레드에 속한다.**

→ **Goal은 스레드 단위(thread-scoped)**. 다른 스레드 / 프로젝트로 새지 않음.

> *"Continuation is event-driven rather than a simple loop. Codex checks for continuation only at safe boundaries: after a turn has finished, when no other work is pending, when no user input is queued, and when the thread is idle."*
>
> 한국어 풀이: **계속 실행은 단순 루프가 아니라 이벤트 기반(event-driven)이다. Codex는 안전 경계에서만 계속 실행 여부를 확인한다: 차례가 끝난 뒤, 다른 작업이 대기 중이지 않을 때, 사용자 입력이 큐에 없을 때, 그리고 스레드가 유휴(idle) 상태일 때.**

→ **이벤트 기반(event-driven)**. while 루프 아님. Ralph 원본의 bash `while true`와 정반대 모델.

> *"If a continuation turn makes no tool call, the next automatic continuation is suppressed so Codex does not spin."*
>
> 한국어 풀이: **계속 실행 차례가 도구 호출을 한 번도 안 하면, 다음 자동 계속 실행은 억제된다 — Codex가 헛바퀴 돌지 않도록.**

→ ⭐ **무한 루프 방어 메커니즘**: 도구 호출 0개 차례가 발생하면 자동 계속 실행을 즉시 중단. "헛바퀴 돌기(puttering)" 버그(README §5-B 참조) 직접 대응.

> *"The model can start a Goal and can mark an existing Goal complete only when the evidence supports completion. Pausing, resuming, clearing, and budget-limited transitions remain controlled by the user or the system."*
>
> 한국어 풀이: **모델은 Goal을 시작할 수 있고, 기존 Goal을 완료로 표시할 수 있다 — 단, 증거가 완료를 뒷받침할 때만. 일시 정지, 재개, 제거, 예산 한도 전이는 사용자 또는 시스템이 통제한다.**

→ **권한 분리**: 모델은 시작/완료 마크 가능, 일시정지/취소는 사용자만. **모델이 자기 권한으로 빠져나가지 못함**. Ralph 원본의 "거짓말 약속(promise)" 문제를 구조적으로 차단.

---

## 2. Claude Code `/goal` — 해부

### 2-A. 명령 표면

```
/goal all tests in test/auth pass and the lint step is clean
/goal              # 현재 상태 조회
/goal clear        # 제거 (별칭: stop, off, reset, none, cancel)
```

요구 버전: Claude Code v2.1.139+

### 2-B. ⭐ Codex와 다른 결정적 한 줄

Claude Code 도큐먼트에서 직접 인용:

> *"`/goal` is a wrapper around a session-scoped prompt-based Stop hook. Each time Claude finishes a turn, the condition and the conversation so far are sent to your configured small fast model, which defaults to Haiku. The model returns a yes-or-no decision and a short reason."*
>
> 한국어 풀이: **`/goal`은 세션 단위(session-scoped)의 프롬프트 기반(prompt-based) 종료 훅(Stop hook)을 감싸는 래퍼(wrapper)다. Claude가 차례를 끝낼 때마다, 조건과 그때까지의 대화가 설정된 소형 고속 모델(기본은 Haiku)로 전송된다. 모델은 yes/no 결정과 짧은 이유를 반환한다.**

분해:

| 부분 | 의미 |
|---|---|
| `세션 단위 프롬프트 기반 종료 훅의 래퍼` | **`/goal`은 새로운 메커니즘이 아니라 기존 종료 훅 위의 문법 설탕(syntax sugar)** |
| `조건과 그때까지의 대화 전송` | 평가자는 **대화 전체 + 조건** 둘 다 받음 |
| `설정된 소형 고속 모델, 기본 Haiku` | 비용 효율: Sonnet/Opus가 작업, Haiku가 평가 |
| `yes/no 결정과 짧은 이유` | 단순 boolean이 아니라 **이유 같이** |

> **읽어낸 의도**: Anthropic은 별도 메커니즘을 추가하지 않고, **이미 있던 종료 훅 시스템에 프롬프트 기반 변형을 얹어** `/goal`을 구현. 즉 §4에서 볼 프롬프트 기반 훅(prompt-based hooks)이 진짜 엔진이고 `/goal`은 그 UI 단축.

### 2-C. ⭐ 평가자 프롬프트 — 핵심 동작

> *"A 'no' tells Claude to keep working and includes the reason as guidance for the next turn. A 'yes' clears the goal and records an achieved entry in the transcript."*
>
> 한국어 풀이: **'no'는 Claude에게 계속 작업하라고 알리며, 이유를 다음 차례의 가이드로 포함시킨다. 'yes'는 goal을 제거하고 대화 기록(transcript)에 달성(achieved) 기록을 남긴다.**

매 차례 끝나면:
1. Haiku가 `(조건, 전체 대화)` 받음
2. yes/no + 이유 반환
3. **no면 다음 차례에 이유를 가이드로 주입**, **yes면 goal 제거 + 대화 기록 등재**

#### 2-C-1. "다음 차례 가이드 주입" — 자세히

```
condition: "all tests in test/auth pass and the lint step is clean"
last turn output: "Fixed the import bug. Tests still failing on auth_test.ts:42"
evaluator: "no — 1 test still failing"
→ 다음 차례 입력: 같은 condition + system msg "Continue: 1 test still failing"
```

이게 **Anthropic ralph-loop 플러그인의 프롬프트 재주입**(`02-ralph-plugin-dissection.md` §3-I)과 닮음. 차이:
- ralph-loop: **같은 프롬프트** 무조건 재주입
- `/goal`: **평가자의 이유**도 같이 주입 → 다음 차례가 어디 막혔는지 알고 시작

> ⭐ **이게 진화의 핵심**: Ralph는 동일 프롬프트만 반복(컨텍스트 추가 없음), `/goal`은 동일 프롬프트 + 외부 평가자의 진단을 함께 주입. **메타-학습이 모델 외부에서 일어남**.

### 2-D. 평가자의 한계 — 직접 명시됨

> *"The evaluator runs on whichever provider your session is configured for. It does not call tools, so it can only judge what Claude has already surfaced in the conversation."*
>
> 한국어 풀이: **평가자는 세션이 설정된 어떤 제공자(provider) 위에서든 동작한다. 도구를 호출하지 않으므로, Claude가 이미 대화에 드러낸 것만 판정할 수 있다.**

→ **평가자는 도구를 못 씀**. 직접 파일 못 읽고, 명령 못 실행. **대화에 이미 표면화된 것만** 봄.

이게 조건(condition) 작성에 결정적 영향:

> *"Write the condition as something Claude's own output can demonstrate. 'All tests in test/auth pass' works because Claude runs the tests and the result lands in the transcript for the evaluator to read."*
>
> 한국어 풀이: **조건은 Claude의 출력으로 입증할 수 있는 것으로 써라. "test/auth의 모든 테스트가 통과한다"는 작동한다 — Claude가 테스트를 실행하고 결과가 대화 기록에 떨어져서 평가자가 읽을 수 있기 때문이다.**

→ **사용자는 조건을 "대화 기록에서 검증 가능한 것"으로 써야 함**. "코드 품질이 좋다" 같은 추상적 조건은 작동 안 함. "`npm test` exits 0"처럼 대화 기록에 출력될 사실이어야.

> **연결**: Codex `/goal`도 같은 원칙(증거 기반) 강조하지만 표현이 다름. Codex는 "검증 표면(verification surface)", Claude는 "대화에 표면화 가능한 것". 같은 제약을 다른 각도에서.

### 2-E. 조건 길이 제한 — 4000자

> *"The condition can be up to 4,000 characters."*
>
> 한국어 풀이: **조건은 최대 4000자까지 가능하다.**

→ goal 프롬프트 자체에 상당한 명세(specification) 가능. Codex의 "6 슬롯 템플릿"을 그대로 4000자 안에 박을 수 있음.

### 2-F. 차례/시간 제한 — 조건 자체에 박음

> *"To bound how long a goal runs, include a turn or time clause in the condition, such as 'or stop after 20 turns'."*
>
> 한국어 풀이: **goal이 얼마나 오래 돌지 한정하려면 조건 안에 차례나 시간 절을 포함해라. 예: "또는 20차례 후 멈춰라".**

→ Claude `/goal`은 별도 `--max-iterations` 같은 옵션이 없음. **제한도 조건의 일부**로 작성. 즉 평가자가 "20차례 지났네 → yes (멈춤)"이라고 판정.

> **흥미점**: Codex는 별도 `budget-limited` 상태가 있고, Claude는 조건 안에 "or stop after X turns"를 박는다. **API 디자인 철학 차이** — Codex는 시스템 수준, Claude는 프롬프트 수준.

### 2-G. 비교 표 — Claude 도큐먼트가 직접 정리

| Approach | Next turn starts when | Stops when |
|---|---|---|
| `/goal` | The previous turn finishes | A model confirms the condition is met |
| `/loop` | A time interval elapses | You stop it, or Claude decides the work is done |
| Stop hook | The previous turn finishes | Your own script or prompt decides |

→ 한국어 풀이:

| 접근 방식 | 다음 차례 시작 시점 | 멈추는 시점 |
|---|---|---|
| `/goal` | 이전 차례가 끝나면 | 모델이 조건 충족을 확인 |
| `/loop` | 시간 간격이 경과하면 | 사용자가 멈추거나 Claude가 작업 끝났다고 판단 |
| 종료 훅(Stop hook) | 이전 차례가 끝나면 | 사용자 자신의 스크립트나 프롬프트가 결정 |

3가지 다 "세션 유지". 차이는:
- `/goal`: **별도 모델이 조건 평가** (외부 평가자)
- `/loop`: **시간 기반 재기동** (Claude 본인 판단으로 멈춤)
- 종료 훅: **사용자 정의 평가** (스크립트나 프롬프트)

→ `/goal`은 사실 종료 훅의 프롬프트 변형 + 표준 평가자 + UX 래퍼.

---

## 3. Codex vs Claude `/goal` — 프롬프트 디자인 비교

### 3-A. 공통

1. **증거 기반(evidence-based)**: 둘 다 "모델이 그렇게 믿어서"가 아니라 "대화 기록/코드/테스트/벤치마크"가 증거.
2. **외부 평가자**: 둘 다 작업 모델과 평가 모델 분리. Codex는 안 밝히지만 Cookbook 톤상 소형 모델 추정. Claude는 명시적 Haiku.
3. **`condition` 자체가 프롬프트**: 사용자가 조건 잘 쓰는 게 핵심. 도구가 아니라 프롬프팅 패턴이 제품.
4. **수동 제어 가능**: 일시정지/재개/제거 모두 사용자만 권한.

### 3-B. 다른 점

| 차원 | Codex `/goal` | Claude `/goal` |
|---|---|---|
| Goal 작성 가이드 | **6슬롯 명시 템플릿**(결과, 검증, 제약, 경계, 반복 정책, 막힘 종료) | "측정 가능한 종료 상태 + 검증 방법 + 제약" 3원칙 |
| 조건 길이 | 명시 안 됨 (실질 무제한) | **최대 4000자** |
| 종료 분류 | `achieved`/`paused`/`cleared`/`budget-limited` (4상태) | `achieved`/수동 제거 (이진) |
| 예산 한도 | 시스템 수준 (`budget-limited` 상태 별도) | **조건 안에** "or stop after 20 turns" |
| 평가자 모델 | "소형 모델" (구체 모델 미공개) | **Haiku 명시** (사용자가 변경 가능) |
| 평가자의 도구 사용 | 명시 안 됨 (Cookbook 어조상 대화만) | **명시적으로 "도구 안 씀"** |
| 상태 저장 | 스레드 단위 영속 | 세션 단위 (재개 시 차례 횟수/타이머 초기화) |
| 무한 루프 방어 | "도구 호출 0개 차례 → 다음 계속 실행 자동 억제" | 매 차례 평가자가 명시적 yes/no |
| 사전 검사(pre-flight) | 도구 안 씀 | 신뢰(trust) 다이얼로그 필수 + `disableAllHooks` 차단 |

### 3-C. ⭐ 한 줄 요약

> Codex `/goal`은 **프롬프트 작성 가이드라인이 풍부함** (6슬롯 템플릿, 약함-vs-강함 예시). Claude `/goal`은 **평가자 메커니즘이 명확히 노출됨** (Haiku, 대화 기록 기반, 프롬프트 기반 종료 훅 위 래퍼).
>
> 같은 문제(스스로 평가자 문제)에 두 회사가 다른 각도로 접근. **Codex = 사용자 프롬프팅 능력에 더 의존**, **Claude = 시스템 메커니즘이 더 표준화**.

---

## 4. 종료 훅(Stop hook)의 프롬프트 기반 변형 — `/goal`의 진짜 엔진

Claude Code 도큐먼트가 명시: "/goal is a wrapper around a session-scoped prompt-based Stop hook".

그렇다면 프롬프트 기반 종료 훅(prompt-based Stop hook)이 뭔지 원본 명세를 확인해야 함.

### 4-A. 훅 종류 5가지

[Hooks reference](https://docs.anthropic.com/en/docs/claude-code/hooks)에서:

> *"There are five types:*
> - *Command hooks (type: 'command'): run a shell command.*
> - *HTTP hooks (type: 'http'): send the event's JSON input as an HTTP POST request to a URL.*
> - *MCP tool hooks (type: 'mcp_tool'): call a tool on an already-connected MCP server.*
> - *Prompt hooks (type: 'prompt'): send a prompt to a Claude model for single-turn evaluation. The model returns a yes/no decision as JSON.*
> - *Agent hooks (type: 'agent'): spawn a subagent that can use tools like Read, Grep, and Glob to verify conditions before returning a decision."*

→ 한국어 풀이: **다섯 종류가 있다.**
- **명령 훅(command)**: 셸 명령을 실행한다.
- **HTTP 훅(http)**: 이벤트의 JSON 입력을 HTTP POST 요청으로 URL에 보낸다.
- **MCP 도구 훅(mcp_tool)**: 이미 연결된 MCP 서버의 도구를 호출한다.
- **프롬프트 훅(prompt)**: 단일 차례 평가를 위해 Claude 모델에게 프롬프트를 보낸다. 모델은 yes/no 결정을 JSON으로 반환한다.
- **에이전트 훅(agent)**: Read, Grep, Glob 같은 도구를 쓸 수 있는 서브에이전트를 띄워 결정을 반환하기 전 조건을 검증한다.

→ Anthropic 공식 ralph-loop 플러그인은 **`type: command`** (`02-ralph-plugin-dissection.md`). `/goal`은 **`type: prompt`**. 즉 같은 훅 시스템 위에 다른 type을 골라 다른 평가 메커니즘을 만든 것.

### 4-B. ⭐ 에이전트 훅 — `/goal`보다 한 단계 더

> *"Agent hooks (type: 'agent'): spawn a subagent that can use tools like Read, Grep, and Glob to verify conditions before returning a decision. Agent hooks are experimental and may change."*
>
> 한국어 풀이: **에이전트 훅: Read, Grep, Glob 같은 도구를 쓸 수 있는 서브에이전트를 띄워 결정을 반환하기 전에 조건을 검증한다. 에이전트 훅은 실험적이며 변경될 수 있다.**

프롬프트 훅이 **대화만** 본다는 한계(§2-D)를 극복하려는 다음 단계가 이미 존재. **에이전트 훅은 도구를 쓸 수 있어 직접 파일 읽고 grep해서 검증 가능**.

> **추정**: `/goal`의 다음 진화는 에이전트 훅 기반일 것. 평가자가 "테스트 진짜 통과했는지 직접 실행해서 확인" 가능. 단 비용 ↑ + 안정성 검증 필요해서 실험적 단계.

### 4-C. 공통 필드 — `if` 필터

```
"if": "Bash(git push *)"    # Bash 하위 명령 매치 시만 훅 실행
"if": "Edit(*.ts)"          # TypeScript 파일 편집 시만
```

→ `/goal`이 매 차례마다 무차별 평가하는 게 아니라, 훅 시스템 수준에서 세분화된(fine-grained) 제어 가능. 큰 그림에서 보면 **Anthropic은 종료 훅을 "에이전트 루프의 통제 평면(control plane)"으로 일반화** 중.

### 4-D. `if` 필드의 보안적 의미

```
"allowed-tools": ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup-ralph-loop.sh:*)"]
```

(02-ralph-plugin-dissection.md §4-A에서 본 패턴 재출현)

→ 훅이 호출할 수 있는 도구를 **명령 단위로 화이트리스트(허용 목록)**. 임의 bash 실행 금지. 이게 ralph-loop 플러그인이 안전한 이유. `/goal`도 같은 메커니즘 위에서 동작.

---

## 5. Ralph와의 연결 — 무엇을 고쳤나

### 5-A. Ralph 원본의 3가지 결함

1. **종료 판정 부재**: 사람 Ctrl+C 의존. 자동화 곤란.
2. **스스로 평가자(self-assessor)**: LLM이 자기가 끝났다고 선언 (#6159, #52362 같은 버그 발생).
3. **증거 흐릿**: 종료 = "fix_plan.md 할 일 비움" — 그게 진짜 끝났다는 보장 없음.

### 5-B. `/goal`이 각각에 어떻게 답하나

| Ralph 결함 | `/goal`의 처방 |
|---|---|
| ① 종료 판정 부재 | **외부 평가자가 매 차례 평가** → 자동 종료 가능 |
| ② 스스로 평가자 | **작업 ≠ 평가 모델 분리** (Haiku 또는 소형 모델) |
| ③ 증거 흐릿 | **조건에 검증 표면(verification surface) 명시** 강제 (테스트 결과, 벤치마크 수치) |

### 5-C. 그러나 — `/goal`도 ralph의 정신 일부를 잃음

| Ralph 원본의 강점 | `/goal`이 보존? |
|---|---|
| 매 반복마다 새 컨텍스트(fresh context per iteration) | ❌ 단일 스레드/세션 |
| 외부 파일이 진실의 단일 원천(source of truth) | ❌ 스레드 상태 안에 거의 다 들어감 |
| Git이 외부 백업 | ❌ 세션 단위 |
| LLM에게 종료 권한 zero | ✅ Codex만 부분 보존 (모델이 완료 마크 가능, 단 증거 검증 후) |

→ **`/goal`은 ralph의 스스로 평가자 문제를 푼 대신, 새 컨텍스트와 파일시스템-진실은 포기**. 이는 README §8-1과 §8-2의 두 인사이트를 정확히 매핑.

> **개인적 추론**: 사용자가 진짜로 새 컨텍스트까지 원하면 → ghuntley 원본 bash + `/goal` condition을 PROMPT.md에 박는 식으로 **합성** 가능. ralph의 외피(bash 루프) + `/goal`의 종료 판정(평가자). 산업이 곧 그 합성을 표준화할 것으로 추정.

---

## 6. 남은 문제 — `/goal`도 못 푸는 것

### 6-A. 평가자의 환각

평가자가 대화를 본 뒤 yes/no를 반환할 때, 평가자도 LLM이라 똑같이 환각 가능. "테스트 통과 안 했는데 통과했다고 판정"하면 `/goal` 종료. 이건 **단일 평가자 아키텍처(single-evaluator architecture)의 근본 한계**.

oh-my-claudecode의 ralph(README §3-C)는 **계층화된 리뷰어(tiered Reviewer)**(STANDARD/THOROUGH)로 이걸 부분 완화 — 큰 변경에는 더 강한 모델로 평가. `/goal`은 단일 소형 모델이라 그 구분이 없음.

> **개인적 의문**: 다음 진화는 평가자도 계층(tier)이 있는 구조? `/goal`이 성숙해지면 조건 복잡도에 따라 Haiku → Sonnet → Opus 단계적 평가가 보일 수도.

### 6-B. 조건 작성 비용

`/goal`의 6슬롯 템플릿을 제대로 채운 조건은 거의 미니 PRD(제품 요구 명세서). 사용자가 그걸 매번 쓰는 비용이 만만찮음. Cookbook도 *"Codex can help write the Goal itself"* — 한국어 풀이: **Codex가 Goal 자체 작성을 도와줄 수 있다** — 라고 인정. Codex에게 조건 초안을 부탁한 다음 사용자가 다듬는 패턴.

→ **프롬프트를 만드는 프롬프트의 메타 루프**가 발생. ralph가 단순했던 이유는 PROMPT.md 한 번만 쓰면 끝이었음. `/goal`은 매 작업마다 조건을 새로 써야 함.

### 6-C. 평가자의 프롬프트 조작 가능성

작업 모델이 대화 기록에 평가자를 속이는 텍스트를 일부러 남길 수 있음 (예: "All tests pass!" / "모든 테스트 통과!" 라고 거짓 출력). 평가자가 대화 기록만 보니 속을 수 있음.

> Anthropic 도큐먼트가 *"It does not call tools, so it can only judge what Claude has already surfaced in the conversation"* — 한국어 풀이: **도구를 호출하지 않으므로, Claude가 이미 대화에 드러낸 것만 판정할 수 있다** — 라고 명시한 것이 사실 이 한계의 자기 인정.

→ 에이전트 훅(§4-B)으로 도구 사용 가능 평가자를 만들면 부분 해결. 그래서 실험적 단계에 있음.

### 6-D. 비용 추적의 비대칭

Codex는 `budget-limited` 상태로 명시적 표시, Claude는 `maxBudgetUsd` 등 외부 한도. 둘 다 **goal 자체가 비용을 자가 추적해서 멈추진 않음**. 사람이 시스템 수준에서 한도를 박아야 함.

→ **goal은 "끝까지 가라"는 명령이지 "예산 안에서 가라"는 명령이 아님**. 이게 사용자가 자주 빠지는 함정.

---

## 7. README와의 연결

기존 [`README.md`](./README.md)에서 `/goal`을 다룬 §4 (Codex), §5-C (Claude)는 본 노트의 원본 인용을 통해 다음과 같이 보강 가능:

| README 섹션             | 본 노트의 추가                                                               |
| --------------------- | ---------------------------------------------------------------------- |
| §4-B (Codex `/goal`)  | **6슬롯 템플릿** 자세히 (§1-B) — 사용자가 직접 goal 쓸 때 참고                           |
| §4-B 종료 4상태           | `budget-limited`가 ★ 완료 아님임을 부각 (§1-C)                                  |
| §5-C (Claude `/goal`) | "세션 단위 프롬프트 기반 종료 훅의 래퍼"의 의미 (§2-B) — `/goal`은 새 메커니즘 아니라 기존 훅 위 문법 설탕 |
| §5-D (종료 훅 JSON)      | 5가지 훅 종류 중 prompt/agent의 자리매김 (§4-A, §4-B)                             |
| §6 비교표 "판정 신호" 행      | Codex/Claude `/goal` 모두 평가자의 이유도 다음 차례에 주입됨 명시 (§2-C-1)                |
| §8-1 스스로 평가자          | 본 노트 §0 + §5-A,B 가 그 문제의 정확한 해법 매핑                                     |

---

## 8. 다음 단계 — 손볼 것

### 8-A. 이 시리즈에서

이 노트(03번)로 사용자가 원래 요청한 "Ralph 원본 + Claude ralph 플러그인 + goal" 3대 원본 해부 시리즈는 **완성**.

남은 작업:
1. 기존 [`README.md`](./README.md)에 상호 참조(cross-reference) 섹션 추가 (이 3개 노트로 가는 링크)
2. README §3-B의 저장소 경로 정정 (02번 노트 §0 참고)

### 8-B. 더 깊게 갈 후보

README §10에 적힌 6가지 심화 후보 중, 본 노트가 부분 다룬 것:
- ✅ "스스로 평가자(self-assessor) 문제" 실제 사례 → 본 §0, §5, §6에서 다룸
- ⚠️ "Codex/Claude `/goal` 동시 등장의 산업적 의미" → 본 §0이 시발점만 제공. 더 깊게 가려면 OpenAI/Anthropic의 정책 문서, 시기적 배경, GPT-5.2-Codex 출시 시점과의 인과 추적 필요.
- ❌ "oh-my-claudecode 계층화된 리뷰어 전략" → 별도 노트(`04-oh-my-claudecode-reviewer.md`)에서 다룰 후보.
- ❌ "Claude Code Tasks (2026-01-23)" → 별도 노트(`05-claude-code-tasks.md`)에서 다룰 후보.
- ❌ "새 컨텍스트 vs 영속 컨텍스트(fresh vs persistent context) 트레이드오프" → 본 시리즈 3개 노트의 §6 통합 비교가 사실 그 시작. 더 분석적인 노트 필요.

---

## 부록: 1차 출처 원본 URL

### Codex `/goal`
| 자원 | URL |
|---|---|
| Cookbook (2026-05-09 발행) | <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex> |
| Cookbook ipynb (raw) | <https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/codex/using_goals_in_codex.ipynb> |
| Use case — Follow a goal | <https://developers.openai.com/codex/use-cases/follow-goals> |
| Codex CLI 슬래시 명령 | <https://developers.openai.com/codex/cli/slash-commands#set-an-experimental-goal-with-goal> |

### Claude Code `/goal`
| 자원 | URL |
|---|---|
| `/goal` 도큐먼트 | <https://code.claude.com/docs/en/goal> |
| Hooks reference | <https://docs.anthropic.com/en/docs/claude-code/hooks> |
| Hooks 빠른 시작 | <https://docs.anthropic.com/en/docs/claude-code/hooks-guide> |
| 자동 모드(Auto mode) | <https://code.claude.com/docs/en/auto-mode-config> |

### 관련
| 자원                                    | URL                                                      |
| ------------------------------------- | -------------------------------------------------------- |
| Codex `task_complete` 정지(hang) 버그     | <https://github.com/openai/codex/issues/13475>           |
| Claude Code "헛바퀴(Puttering)" 무한 루프 버그 | <https://github.com/anthropics/claude-code/issues/52362> |
| HumanLayer "Brief History of Ralph"   | <https://www.humanlayer.dev/blog/brief-history-of-ralph> |
