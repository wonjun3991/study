# Agentic Loops — Ralph / Codex `/goal` / Claude `/goal`

> **학습 목표**: agentic coding 시스템에서 "언제 멈추는가"를 결정하는 메커니즘이
> 어떻게 진화해 왔는지, 세 대표 시스템(Ralph · OpenAI Codex · Anthropic Claude Code)이
> 종료 조건을 어떻게 잡는지 1차 출처를 근거로 정리한다.
>
> **조사 기준일**: 2026-05-16 (메타 비교) / 2026-05-18 (raw 해부 노트)
> **레포 SHA**: `openai/codex@de9c5c0`, `anthropics/claude-plugins-official@b5a156b`
>
> **시리즈 구성**:
> 본 README는 메커니즘 비교(메타). 1차 자료의 프롬프트와 스크립트를 줄 단위로 직접 해부한 노트가 별도 3개 있다.
>
> | 노트 | 다루는 자료 | 형식 |
> |---|---|---|
> | [`01-ralph-original-dissection.md`](./01-ralph-original-dissection.md) | ghuntley `how-to-ralph-wiggum` 5개 파일 (`loop.sh`, `PROMPT_build.md`, `PROMPT_plan.md`, `AGENTS.md`, `IMPLEMENTATION_PLAN.md`) | 원본 텍스트(raw text) + 줄 단위 주석 |
> | [`02-ralph-plugin-dissection.md`](./02-ralph-plugin-dissection.md) | Anthropic 공식 ralph-loop 플러그인 6개 파일 (`commands/*.md`, `hooks/stop-hook.sh`, `scripts/setup-ralph-loop.sh`) | 원본 텍스트 + 줄 단위 주석 |
> | [`03-goal-dissection.md`](./03-goal-dissection.md) | Codex `/goal` Cookbook + Claude `/goal` 도큐먼트 + 종료 훅(Stop hook) 프롬프트 기반 명세 | 원본 인용 + 프롬프트 디자인 비교 |
>
> 본 README의 §3,4,5와 해부 노트는 짝을 이룸. 깊게 알고 싶으면 본문에서 해부 노트로 점프.

---

## 0. TL;DR

세 시스템의 종료 판정은 **3단계 진화**를 거쳤다.

```
[1] 외부 bash 루프 + 파일시스템 상태  ─ Ralph 원본 (2025-07)
        ↓ "LLM은 self-assessor가 약하다"는 문제 발견
[2] 내장 Stop hook + 동일 LLM 자체 판단 ─ Anthropic 공식 ralph-wiggum (2025-12)
        ↓ "같은 모델이 자기 일을 평가하면 신뢰성 ↓"
[3] 작업 LLM ≠ 평가 LLM 분리 (외부 evaluator) ─ Codex /goal · Claude /goal (2026-05)
```

핵심 한 줄:

- **Ralph 원본**: 종료 조건이 **없다**. 사람이 Ctrl+C 누르거나 `fix_plan.md`가 빌 때까지.
- **Codex `/goal`**: *"A Turn yielding no output terminates the Task"* — tool call 없는 최종 응답 = 종료. `/goal` 모드에서는 별도 소형 모델이 evidence 기반 평가.
- **Claude `/goal`**: *"completion is decided by a fresh model rather than the one doing the work"* — 작업 모델과 평가 모델 분리.

---

## 1. 발전 타임라인

| 시기 | 사건 |
|------|------|
| **2025-02** | Geoffrey Huntley(ghuntley)가 SaaS 클로닝 실험 중 Ralph 개념 내부 발견 |
| **2025-06** | SFO Twitter 밋업에서 ~15명에게 첫 시연, "Ralph Wiggum" 명명 |
| **2025-07-14** | [`ghuntley.com/ralph/`](https://ghuntley.com/ralph/) 공개 발행 — 원본 블로그 |
| **2025-08-20** | Claude Code [issue #6159](https://github.com/anthropics/claude-code/issues/6159) — TodoWrite 조기 종료 버그 보고 |
| **2025-09** | OpenAI **GPT-5-Codex** 출시 (agentic coding 최적화) |
| **2025-12** | Ralph 바이럴 확산; Boris Cherny(Anthropic Head of Claude Code)가 공식 `ralph-wiggum` 플러그인으로 형식화 |
| **2025-12** | OpenAI **GPT-5.2-Codex** 출시 ("신뢰 가능한 long-horizon" 시점) |
| **2026-01-06** | HumanLayer ["A Brief History of Ralph"](https://www.humanlayer.dev/blog/brief-history-of-ralph) — 공식 플러그인이 fresh-context 원칙을 놓쳤다고 비판 |
| **2026-01-10** | [`github.com/ghuntley/how-to-ralph-wiggum`](https://github.com/ghuntley/how-to-ralph-wiggum) 생성 |
| **2026-01-17** | [`ghuntley.com/loop/`](https://ghuntley.com/loop) — "everything is a ralph loop" 철학 확장 |
| **2026-01-23** | Anthropic **Claude Code Tasks** 출시 (DAG 의존성, 파일시스템 영속, 멀티세션) |
| **2026-01-26** | [VentureBeat](https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across) — "Tasks = Ralph workaround의 native 대체재" |
| **2026-05-09** | OpenAI [Codex `/goal` Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) 공식 발행 |
| **2026-05 부근** | Claude Code `/goal` 명령 정식 문서화 (v2.1.139+) |

> **관전 포인트**: 2026-05에 **OpenAI와 Anthropic이 거의 동시에** "외부 evaluator 분리" 패턴(`/goal`)을 도입했다.
> 산업 전체가 같은 결론(LLM의 self-assessment 한계)에 도달한 시점.

---

## 2. 시스템별 정체성 한 줄 요약

| 시스템 | 본질 | 종료 결정 주체 |
|---|---|---|
| **Ralph (Huntley 원본)** | bash `while :;` 무한 루프 + 매 iteration **fresh context** + 파일시스템 상태(`fix_plan.md`) | 사람(Ctrl+C) 또는 에이전트가 fix_plan.md 비었음을 보고 자연 exit |
| **Ralph (Anthropic 공식 플러그인)** | 단일 세션 + Stop hook | LLM이 `<promise>EXACT_TEXT</promise>` 출력 OR `max_iterations` 도달 |
| **Ralph (oh-my-claudecode)** | 단일 세션 + `prd.json` + tiered Reviewer | **외부 Reviewer LLM**(architect/critic/codex)이 acceptance criteria 검증 후 APPROVED |
| **Codex `/goal`** | 단일 스레드(compaction) + completion contract | **별도 소형 모델**(Haiku 계열)이 매 턴 후 evidence 기반 평가 |
| **Claude `/goal`** | 세션 스코프 prompt-based Stop hook 래퍼 | **별도 소형 모델**(Haiku)이 매 턴 후 yes/no 판정 |
| **Claude Code 기본 루프** | 단일 세션 | LLM 자체가 `stop_reason: "end_turn"` 반환 (tool call 없는 최종 텍스트) |

---

## 3. Ralph — 종료 판정 변천사

### 3-A. Huntley 원본 (2025-07): "stop condition 없음"

```bash
while :; do cat PROMPT.md | claude ; done
```

> *"Ralph is a Bash loop."*
> *"That's the beauty of Ralph — the technique is deterministically bad in an undeterministic world."*
> *"Ralph is monolithic. Ralph works autonomously in a single repository as a single process that performs one task per loop."*
> — [ghuntley.com/ralph/](https://ghuntley.com/ralph/)

> *"In practice this means doing the loop manually via prompting or via automation with a pause that involves having to press CTRL+C to progress onto the next task."*
> — [ghuntley.com/loop/](https://ghuntley.com/loop)

**핵심 메커니즘**:

1. **단일 루프, 단일 태스크**: 매 루프마다 `PROMPT.md`를 LLM에 주입. 루프당 딱 하나의 작업.
2. **외부 파일이 공유 상태**: `fix_plan.md` / `IMPLEMENTATION_PLAN.md` 가 루프 간 유일한 영속 상태.
3. **Fresh context per iteration** (이게 핵심 원칙): 컨텍스트 윈도우는 매 루프마다 초기화.
4. **백프레셔(backpressure)**: 빌드/테스트를 단일 서브에이전트로 실행 → 실패 시 `fix_plan.md`에 기록 → 다음 루프에서 재시도.
5. **종료 판정**: 명시적 stop condition 없음. `fix_plan.md`의 TODO가 소진되면 자연 종료. 인간이 루프를 감시하다 `Ctrl+C`.

> **인사이트**: 종료를 LLM이 선언하지 않는다. **파일시스템 상태**(fix_plan.md, 테스트 통과)가 완료를 증명한다.

### 3-B. Anthropic 공식 `ralph-loop` 플러그인 (2025-12)

> ⚠️ **경로 정정**: 이 정리의 초기 버전은 `anthropics/claude-code/plugins/ralph-wiggum/` 으로 적었으나,
> 2026-05 시점 실제 위치는 별도 저장소 [`anthropics/claude-plugins-official/plugins/ralph-loop/`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop) 임. 디렉토리 이름도 `ralph-wiggum` → `ralph-loop`로 변경(rename)됨.
> 자세한 원본 해부는 [`02-ralph-plugin-dissection.md`](./02-ralph-plugin-dissection.md) 참조.

[`plugins/ralph-loop/hooks/stop-hook.sh`](https://github.com/anthropics/claude-plugins-official/blob/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/hooks/stop-hook.sh) 실제 코드:

```bash
# 종료 조건 1: 최대 iteration 도달
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  echo "🛑 Ralph loop: Max iterations ($MAX_ITERATIONS) reached."
  rm "$RALPH_STATE_FILE"
  exit 0
fi

# 종료 조건 2: <promise> 태그 일치
if [[ -n "$PROMISE_TEXT" ]] && [[ "$PROMISE_TEXT" = "$COMPLETION_PROMISE" ]]; then
  echo "✅ Ralph loop: Detected <promise>$COMPLETION_PROMISE</promise>"
  rm "$RALPH_STATE_FILE"
  exit 0
fi

# 그 외: 같은 프롬프트로 계속
jq -n '{"decision": "block", "reason": $prompt, "systemMessage": $msg}'
```

**종료 조건 4종**:

1. `<promise>EXACT_TEXT</promise>` 태그가 LLM 출력에 등장 → 즉시 종료
2. `max_iterations` 도달 → 강제 종료
3. 상태 파일 손상/없음 → 안전 종료
4. `/cancel-ralph` 명령 → 수동 종료

**HumanLayer 비판** ([brief-history-of-ralph](https://www.humanlayer.dev/blog/brief-history-of-ralph)):
> 공식 플러그인은 단일 세션 내 Stop hook으로 구현되어 **원본의 핵심인 "fresh context per iteration"을 놓쳤다.**

### 3-C. oh-my-claudecode `ralph` (가장 정교)

[`skills/ralph/SKILL.md`](https://github.com/yeachan-heo/oh-my-claudecode/blob/main/skills/ralph/SKILL.md):

> *"Check PRD completion: Read prd.json -- are ALL stories marked passes: true? ... Reviewer verification (tiered, against acceptance criteria) ... The selected reviewer verifies against the SPECIFIC acceptance criteria from prd.json, not vague 'is it done?'"*

**종료 조건 5종**:

1. `prd.json`의 모든 stories `passes: true`
2. **외부 Reviewer LLM** (architect/critic/codex, 변경 규모에 따라 STANDARD/THOROUGH tier 선택)이 acceptance criteria 대비 APPROVED
3. `max_iterations` 기본 100, 도달 시 +10 자동 연장 (하드 리밋 없음)
4. `isStaleState` 2시간 초과 → 자동 종료
5. 사용자가 "stop", "cancel", "abort" 발화 → 수동 종료

**Reviewer 선택 로직** (변경 규모 기반):

| 변경 규모 | Reviewer Tier | 모델 |
|---|---|---|
| <5 files, <100 lines, full tests | STANDARD | Sonnet 계열 |
| >20 files OR security/architectural | THOROUGH | Opus |

> **시점적 의미**: oh-my-claudecode는 Codex/Claude `/goal`(2026-05)보다 먼저 외부 evaluator 패턴을 구현했다. 사실상 같은 철학에 산업이 한참 뒤에 도달한 셈.

---

## 4. OpenAI Codex — 종료 판정 (자세히)

Codex의 종료는 **두 층**으로 구성된다.

### 4-A. 층 1 — 프로토콜 수준 (`/goal` 없이도 항상 적용)

[`codex-rs/docs/protocol_v1.md`](https://github.com/openai/codex/blob/de9c5c0/codex-rs/docs/protocol_v1.md):

> *"3. Task — The Task executes until:*
> - *The Model completes the task and there is no output to feed into an additional Turn*
> - *Additional user-turn input aborts the current task and starts a new one*
> - *UI interrupts with `Op::Interrupt`*
> - *Fatal errors are encountered, eg. Model connection exceeding retry limits*
> - *Blocked by user approval (executing a command or patch)"*
>
> *"4. Turn — A Turn yielding no output terminates the Task."*

핵심 원칙: **LLM이 더 이상 tool call을 발행하지 않고 최종 텍스트만 반환할 때** `TurnComplete` 이벤트 자동 발행 → Task 종료.
별도의 `<task_complete/>` XML 태그나 `final_message` 필드는 **없다**. 종료는 "더 이상 실행할 tool call이 없음"이라는 **상태**로 판정된다.

**상태 머신** ([`codex-rs/core/src/agent/status.rs`](https://github.com/openai/codex/blob/de9c5c0/codex-rs/core/src/agent/status.rs)):

```rust
pub(crate) fn agent_status_from_event(msg: &EventMsg) -> Option<AgentStatus> {
    match msg {
        EventMsg::TurnStarted(_) => Some(AgentStatus::Running),
        EventMsg::TurnComplete(ev) => Some(AgentStatus::Completed(ev.last_agent_message.clone())),
        EventMsg::TurnAborted(ev) => match ev.reason {
            TurnAbortReason::Interrupted
            | TurnAbortReason::BudgetLimited => Some(AgentStatus::Interrupted),
            _ => Some(AgentStatus::Errored(format!("{:?}", ev.reason))),
        },
        EventMsg::Error(ev) => Some(AgentStatus::Errored(ev.message.clone())),
        EventMsg::ShutdownComplete => Some(AgentStatus::Shutdown),
        _ => None,
    }
}
```

### 4-B. 층 2 — `/goal` 명령 (선택적, 외부 evaluator)

[Codex Cookbook (2026-05-09)](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex):

> *"A Goal gives Codex a completion condition: what should be true, how success should be checked, and what constraints must stay intact."*
>
> *"Completion must be evidence-based. A Goal should not be marked complete because the model believes it is probably done. It should be complete only after the objective is checked against the relevant files, tests, logs, benchmark output, generated artifacts, or other concrete evidence."*

[Codex use-cases / Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals):

> *"It will stop running when it is fairly confident it has reached the stopping condition."*

**종료 상태 4종**:

| 상태 | 의미 |
|---|---|
| `achieved` | evaluator가 condition 충족 확인 |
| `budget-limited` | 예산 소진 (완료 아님, 명시적으로 구분) |
| `unmet` | 미달성 |
| `paused` | 일시 정지 |

**핵심 분리**: 작업 모델(GPT-5-Codex)과 평가 모델(소형, Haiku 계열)을 분리해 "자기 자신이 완료 선언"의 신뢰성 문제를 회피.
평가는 **대화 내 실제 증거**(테스트 결과, 빌드 로그, 벤치마크 수치)를 보고 판단.

### 4-C. cancel vs terminate

[`codex-cli/src/utils/agent/agent-loop.ts`](https://github.com/openai/codex/blob/de9c5c0/codex-cli/src/utils/agent/agent-loop.ts):

```typescript
public cancel(): void {
  // Soft: 스트림 abort, 인스턴스 재사용 가능
  this.currentStream?.controller?.abort?.();
  this.canceled = true;
  this.execAbortController?.abort();
  this.generation += 1;
}

public terminate(): void {
  // Hard: 인스턴스 폐기
  this.terminated = true;
  this.hardAbort.abort();
  this.cancel();
}
```

사용자 Esc 키 → `cancel()`, 세션 종료 → `terminate()`.

---

## 5. Claude Code — 종료 판정 (자세히)

Claude Code의 종료는 **세 층**으로 구성된다.

### 5-A. 층 1 — 기본 Agent Loop

[`code.claude.com/docs/en/agent-sdk/agent-loop`](https://code.claude.com/docs/en/agent-sdk/agent-loop):

> *"The loop runs until Claude finishes on its own, which is fine for well-scoped tasks but can run long on open-ended prompts."*
>
> *"`ResultMessage`: marks the end of the agent loop. Contains the final text result, token usage, cost, and session ID. Check the `subtype` field to determine whether the task succeeded or hit a limit."*

| `subtype` | 의미 |
|---|---|
| `success` | 정상 완료 (Claude가 `stop_reason: "end_turn"` 반환) |
| `error_max_turns` | `maxTurns` 한도 초과 |
| `error_max_budget_usd` | 비용 한도 초과 |
| `error_during_execution` | API 오류 |

기본 루프에서 종료 결정자는 **Claude 자기 자신**. Anthropic Messages API의 `stop_reason: "end_turn"` 이 신호.

> *"The result also includes a `stop_reason` field indicating why the model stopped generating on its final turn. Common values are `end_turn` (model finished normally), `max_tokens` (hit the output token limit), and `refusal`."*

### 5-B. 층 2 — TodoWrite (세션 내 체크리스트)

- 상태 전이: `pending → in_progress → completed`
- 모든 항목 `completed` 시 리스트 자동 클리어
- **알려진 버그**: TODO 미완료 상태에서 조기 종료하거나, 반대로 멈추지 않는 사례
  - [#6159](https://github.com/anthropics/claude-code/issues/6159) (2025-08-20)
  - [#599](https://github.com/anthropics/claude-code-action/issues/599)
  - [#52362](https://github.com/anthropics/claude-code/issues/52362) (2026-04-23) — "Puttering" 무한 루프

이 버그들이 `/goal` 도입의 동기가 됐다고 추정.

### 5-C. 층 3 — `/goal` 명령 (외부 evaluator)

[`code.claude.com/docs/en/goal`](https://code.claude.com/docs/en/goal):

> *"`/goal` is a wrapper around a session-scoped prompt-based Stop hook. Each time Claude finishes a turn, the condition and the conversation so far are sent to your configured small fast model, which defaults to **Haiku**. The model returns a yes-or-no decision and a short reason. A 'no' tells Claude to keep working and includes the reason as guidance for the next turn. A 'yes' clears the goal and records an achieved entry in the transcript."*
>
> *"Auto mode on its own approves tool calls within a single turn but doesn't start a new one. Claude stops when it judges the work done. /goal adds a separate evaluator that checks your condition after every turn, so completion is decided by a fresh model rather than the one doing the work."*

| 방식 | 다음 턴 시작 조건 | 종료 조건 |
|---|---|---|
| `/goal` | 이전 턴 완료 | **별도 모델(Haiku)이 조건 충족 확인** |
| `/loop` | 시간 간격 경과 | 사용자 중단 또는 Claude 자체 판단 |
| Stop hook | 이전 턴 완료 | 사용자 스크립트/프롬프트 결정 |

### 5-D. Stop Hook의 JSON 응답

[`docs.anthropic.com/en/docs/claude-code/hooks`](https://docs.anthropic.com/en/docs/claude-code/hooks):

```json
// 종료 차단
{ "decision": "block", "reason": "Work is not done. Continue working." }

// 즉시 종료 강제
{ "continue": false, "stopReason": "Task complete" }
```

oh-my-claudecode의 ralph 구현이 이 메커니즘을 활용한다.

---

## 6. 종료 판정 통합 비교표

| 항목 | Ralph 원본 | Ralph (Anthropic 공식) | Ralph (oh-my-claudecode) | Codex `/goal` | Claude `/goal` |
|---|---|---|---|---|---|
| **판정 주체** | 사람 + 파일 상태 | LLM 자체 (promise 토큰) | 외부 Reviewer LLM | 외부 evaluator (Haiku) | 외부 evaluator (Haiku) |
| **판정 신호** | `fix_plan.md` 비었음 | `<promise>` 일치 | `passes:true` + Reviewer APPROVED | evidence 기반 yes/no | yes/no + reason |
| **컨텍스트** | **Fresh per iteration** ✅ | 단일 세션 ❌ | 단일 세션 ❌ | 단일 스레드 + compaction | 단일 세션 + compaction |
| **작업/평가 모델 분리** | N/A (사람이 평가) | ❌ 같은 모델 | ✅ 분리 (tiered) | ✅ 분리 (Haiku) | ✅ 분리 (Haiku) |
| **하드 리밋** | 없음 | `max_iterations` | 100회 + 자동 연장 | 비용 한도 | `maxTurns`, `maxBudgetUsd` |
| **실패 시** | 루프 재시작 (bash) | iteration 차감 후 재시도 | 재시도 + 3회 후 사람 핸드오프 | `unmet`/`budget-limited` | `error_max_turns` 등 |
| **영속 상태** | `fix_plan.md` (FS) | `RALPH_STATE_FILE` | `prd.json` (FS) | thread state | session state + Tasks |

---

## 7. 인용 가능한 한 줄 요약 (학습/발표용)

| 시스템 | 인용 |
|---|---|
| **Ralph 원본** | *"Ralph is a Bash loop."* — Huntley |
| **Ralph 종료 조건** | *"In practice this means... having to press CTRL+C."* — Huntley |
| **Codex (프로토콜)** | *"A Turn yielding no output terminates the Task."* — protocol_v1.md |
| **Codex `/goal`** | *"Completion must be evidence-based."* — Cookbook 2026-05-09 |
| **Claude Code 기본** | *"The loop runs until Claude finishes on its own."* — agent-loop docs |
| **Claude `/goal`** | *"completion is decided by a fresh model rather than the one doing the work."* — /goal docs |
| **산업 통찰** | *"LLMs are poor self-assessors: Models confidently assert completion when tasks remain incomplete."* — alternef.garden |

---

## 8. 핵심 인사이트

### 8-1. "Self-assessor 문제" — Codex/Claude `/goal` 동시 등장의 근본 이유

LLM이 **자기가 한 일을 자기가 평가**할 때 신뢰성이 떨어진다는 산업적 합의가 2026-05에 형성됐다.
근거:

- Claude Code 조기 종료 버그 (#6159, #599) — 모델이 미완료 TODO를 두고 종료
- Claude Code 무한 루프 버그 (#52362, "Puttering") — 모델이 멈출 시점을 모름
- Codex 의 `task_complete` 미발행 hang 버그 ([#13475](https://github.com/openai/codex/issues/13475))

해법은 동일: **작업 모델 ≠ 평가 모델**. OpenAI도 Anthropic도 거의 같은 시기에 외부 evaluator 패턴(`/goal`)을 도입.
**oh-my-claudecode의 tiered Reviewer는 이보다 앞서 같은 철학을 구현한 사례.**

### 8-2. Fresh context vs persistent context — Ralph의 잃어버린 원칙

Huntley 원본의 핵심은 **매 iteration fresh context**였다. 이유:

- 이전 시도의 잘못된 가정이 남지 않음
- LLM의 attention dilution(긴 대화에서 초반 지시 망각) 회피
- 파일시스템 상태가 유일한 진실

그러나 Anthropic 공식 `ralph-wiggum` 플러그인은 **단일 세션 Stop hook**으로 구현 → fresh context 원칙 상실.
HumanLayer/thetrav.substack 등 커뮤니티가 이를 비판하며 "진짜 Ralph"를 강조.

### 8-3. Claude Code Tasks (2026-01) — Ralph의 native 대체재

[VentureBeat 2026-01-26](https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across)는 Tasks를 "Ralph workaround의 native 대체재"로 평가.

- `~/.claude/tasks/` 파일시스템 영속
- DAG 의존성 (`addBlockedBy`)
- `CLAUDE_CODE_TASK_LIST_ID` 환경변수로 멀티 세션 공유

→ Ralph가 외부 파일(`fix_plan.md`)로 했던 일을 Anthropic이 1급 시민으로 흡수.

---

## 9. 1차 출처 (URL 모음)

### Ralph
- 원본 블로그: <https://ghuntley.com/ralph/>
- 철학 확장: <https://ghuntley.com/loop/>
- 플레이북: <https://github.com/ghuntley/how-to-ralph-wiggum>
- HumanLayer 역사: <https://www.humanlayer.dev/blog/brief-history-of-ralph>
- Anthropic 공식 플러그인 (ralph-loop): <https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop>
  - `stop-hook.sh`: <https://github.com/anthropics/claude-plugins-official/blob/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/hooks/stop-hook.sh>
- oh-my-claudecode SKILL.md: <https://github.com/yeachan-heo/oh-my-claudecode/blob/main/skills/ralph/SKILL.md>

### OpenAI Codex
- 프로토콜 v1: <https://github.com/openai/codex/blob/de9c5c0/codex-rs/docs/protocol_v1.md>
- 상태 머신: <https://github.com/openai/codex/blob/de9c5c0/codex-rs/core/src/agent/status.rs>
- 에이전트 루프: <https://github.com/openai/codex/blob/de9c5c0/codex-cli/src/utils/agent/agent-loop.ts>
- `/goal` Cookbook: <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex>
- Follow a goal: <https://developers.openai.com/codex/use-cases/follow-goals>
- Long-horizon 블로그: <https://openai.com/index/run-long-horizon-tasks-with-codex>

### Claude Code
- `/goal` 문서: <https://code.claude.com/docs/en/goal>
- Agent Loop 문서: <https://code.claude.com/docs/en/agent-sdk/agent-loop>
- Todo tracking: <https://code.claude.com/docs/en/agent-sdk/todo-tracking>
- Hooks 문서: <https://docs.anthropic.com/en/docs/claude-code/hooks>
- Tasks 출시 기사: <https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across>

### 토론/비판
- The Real Ralph Wiggum Loop: <https://thetrav.substack.com/p/the-real-ralph-wiggum-loop-what-everyone>
- Engineering Discipline: <https://writing.alteredcraft.com/p/the-ralph-wiggum-agent-loop-is-really>
- Ralph Loop 정리: <https://alternef.garden/knowledge/tools-and-technology/specialized-intelligence/artificial-intelligence/ralph-loop>
- Claude Code "Puttering" 버그: <https://github.com/anthropics/claude-code/issues/52362>
- Codex `task_complete` hang 버그: <https://github.com/openai/codex/issues/13475>

---

## 10. 더 다뤘으면 하는 부분 (사용자가 채워나갈 영역)

> 아래 항목들은 사용자가 "이 부분 더 자세히"로 짚어주면 깊게 파고들 후보다.

- [ ] **Fresh context vs persistent context의 trade-off 분석** — 토큰 비용, 일관성, 디버깅 가능성 측면
- [ ] **"Self-assessor 문제"의 실제 사례 deep-dive** — Claude Code #6159, #52362, Codex #13475의 구체적 실패 패턴과 재현 조건
- [ ] **oh-my-claudecode tiered Reviewer 전략** — STANDARD vs THOROUGH 선택 로직, architect/critic/codex Reviewer 역할 차이
- [ ] **Codex/Claude `/goal` 동시 등장의 산업적 의미** — 2026-05 동시성의 배경
- [ ] **Claude Code Tasks (2026-01-23) 자세히** — DAG 의존성 모델, `CLAUDE_CODE_TASK_LIST_ID` 멀티세션 패턴, Ralph 대체 정도
- [ ] **vault 내부 자료와 연결** — `presentation/harness-engineering/` 의 Sisyphus 하네스 비교 자료를 학습 노트 관점으로 재구성
