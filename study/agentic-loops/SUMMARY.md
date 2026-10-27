# SUMMARY — 에이전틱 루프 3대 시스템 4줄 요약

> 자세한 메커니즘은 각 해부 노트와 [`README.md`](./README.md) 참조.

---

## ralph

- 사람이 멈추거나 정해진 횟수에 도달할 때까지 무한 반복
- 사람이 플랜 혹은 AI와 논의 끝에 나온 결과 목표를 설정
- 메인 에이전트와 서브 에이전트를 통해 컨텍스트 오염 방지
- 반복할 때마다 개선 사항들을 문서로 남겨서 사용

**예시 (사용 모습)**:
```bash
./loop.sh           # 빌드 모드, 무한 반복
./loop.sh plan 5    # 계획 모드, 최대 5회
# 멈추려면 Ctrl+C
```

→ 자세히: [`01-ralph-original-dissection.md`](./01-ralph-original-dissection.md)

## claude - ralph

- AI가 목표(미리 약속한 문구)에 도달했다고 선언할 때까지 반복
- hook과 script를 통해 같은 세션 안에서 반복
- session id로 다른 Claude 세션과의 간섭 방지 (한 머신에 ralph 안 도는 다른 세션이 stop-hook에 휘말리지 않게 격리)
- 루프 메타데이터 상태 파일(`.claude/ralph-loop.local.md`)이 손상되면 루프 종료 ("의심스러우면 죽인다" 정책 — 자가 복구 아님)

**예시 (사용 모습)**:
```
/ralph-loop "Fix auth bug" --completion-promise "FIXED" --max-iterations 10

# AI가 작업하다 다음 문구를 출력하면 종료:
<promise>FIXED</promise>

# 강제 취소:
/cancel-ralph
```

→ 자세히: [`02-ralph-plugin-dissection.md`](./02-ralph-plugin-dissection.md)

## codex, claude `/goal`

- goal을 위해 새 메커니즘 추가 — **Claude는 hook 시스템에 prompt 타입을 새로 추가**, **Codex는 영속 스레드 상태 + 자동 이어달리기**(둘이 구조는 다르지만 푸는 문제는 같음)
- 종료 판정 방식이 두 갈래로 갈라짐 — **Claude는 별도 평가자 모델(Haiku)이 yes/no 판정**, **Codex는 작업 모델 본인이 강한 audit 프롬프트(`continuation.md`)를 받고 self-evaluate**
- Claude는 평가자가 이유와 함께 no를 주면 다음 차례 가이드로 주입돼 부족한 부분을 채우게 만들고, Codex는 작업 모델이 audit 후 `update_goal(status: "complete")` 도구를 호출해야 종료
- 조건은 **검증 가능한 종료 상태**로 써야 함 — "성능 개선" ❌ / "테스트 전부 통과 + 빌드 성공" ✅

**예시 (사용 모습)**:
```
# Codex CLI:
/goal Reduce p95 latency below 120 ms while keeping correctness tests green
/goal pause / resume / clear

# Claude Code:
/goal all tests in test/auth pass and the lint step is clean
/goal           # 현재 상태 조회
/goal clear     # 강제 종료
```

**Codex vs Claude 핵심 차이**:
- **종료 판정 주체**: Codex는 작업 모델이 자기 일을 self-audit (prompt-level 가드), Claude는 별도 Haiku 모델로 분리 (architecture-level 분리)
- **종료 라이프사이클**: Codex는 4단계 (`active`/`paused`/`complete`/`budget-limited` — 마지막은 ★완료 아님). Claude는 `achieved` 또는 사용자 `clear`
- **조건 길이**: Claude는 최대 4000자, "or stop after 20 turns" 같이 한도까지 조건 안에 박는 스타일. Codex는 길이 명시 없음

→ 자세히: [`03-goal-dissection.md`](./03-goal-dissection.md)

---

## 진화의 한 줄

> Ralph는 **LLM에게 종료 권한을 안 줬다** → claude-ralph는 **LLM 본인이 선언하게** 했다 → `/goal`은 두 갈래로 갈라짐: **Codex는 같은 LLM에게 강한 audit 프롬프트를 강제**(prompt 수준), **Claude는 다른 LLM에게 판정을 맡김**(architecture 수준).
>
> 같은 문제(언제 멈출 것인가)에 산업이 두 가지 다른 층위로 답한 흔적.

---

## 📌 self-assessor 문제, 어떻게 막으려 했나 — 1차 자료 위치

작업한 LLM이 자기 일을 자기가 평가할 때 거짓 완료를 선언하는 문제. 두 회사가 어디에서 어떻게 막았는지 정확한 위치.

### Codex — 프롬프트 강제 (prompt-level guard)

작업 모델 자체가 평가하므로 **prompt에 audit 절차를 강제**해서 막으려 함. 핵심 자료 3개:

#### ① `continuation.md` — 매 차례 끝마다 작업 모델에 자동 주입되는 프롬프트

**위치**: [`codex-rs/core/templates/goals/continuation.md`](https://github.com/openai/codex/blob/82061660ae2adf10dfd5ea5286f5871a8199fdf3/codex-rs/core/templates/goals/continuation.md)

6개 섹션으로 모델 행동을 강제:

1. **Continuation behavior** — *"Keep the full objective intact. If it cannot be finished now, make concrete progress... and do not redefine success around a smaller or easier task."*
   → 한국어: **목표를 통째로 유지하라. 지금 못 끝내겠으면 실제 요청된 종료 상태로 향하는 구체적 진척을 만들고, 더 작거나 쉬운 작업으로 성공을 재정의하지 마라.**

2. **Work from evidence** — *"Use the current worktree and external state as authoritative. Previous conversation context can help locate relevant work, but inspect the current state before relying on it."*
   → 한국어: **현재 작업 트리와 외부 상태를 권위 있는 출처로 써라. 이전 대화 컨텍스트는 관련 작업을 찾는 데 도움이 될 뿐, 의존하기 전에 현재 상태를 검사하라.** (모델 자기 기억 신뢰 금지 → 파일을 다시 보라는 명령)

3. **Fidelity** — *"Do not substitute a narrower, safer, smaller, merely compatible, or easier-to-test solution because it is more likely to pass current tests."*
   → 한국어: **현재 테스트를 통과시키기 더 쉬운 좁고 안전하고 작거나 그저 호환되거나 테스트하기 쉬운 해법으로 대체하지 마라.** (LLM이 "테스트 통과만" 노리고 도망가는 것을 직접 차단)

4. **Completion audit** ⭐ 가장 강한 가드 — *"Before deciding that the goal is achieved, **treat completion as unproven** and verify it against the actual current state."*
   → 한국어: **목표 달성 결정 전에 완료를 *증명되지 않은 것*으로 취급하고, 실제 현재 상태와 대조해 검증하라.**

   그리고: *"The audit must prove completion, not merely fail to find obvious remaining work."*
   → 한국어: **감사는 명백히 남은 작업이 *없음*을 보이는 것이 아니라 완료를 *적극적으로 증명*해야 한다.**

5. **마지막 강제** — *"Do not rely on intent, partial progress, memory of earlier work, or a plausible final answer as proof of completion."*
   → 한국어: **의도, 부분 진척, 이전 작업의 기억, 그럴듯해 보이는 최종 답을 완료의 증거로 삼지 마라.**

6. **`update_goal` 호출 가드** — *"Do not call update_goal unless the goal is complete. Do not mark a goal complete merely because the budget is nearly exhausted or because you are stopping work."*
   → 한국어: **목표가 완료된 게 아니면 update_goal을 부르지 마라. 예산이 거의 떨어졌다거나 작업을 멈추려 한다는 이유로 완료 마크하지 마라.**

#### ② `update_goal.rs` — 도구 스키마 수준의 권한 차단

**위치**: [`codex-rs/core/src/tools/handlers/goal/update_goal.rs:54-58`](https://github.com/openai/codex/blob/82061660ae2adf10dfd5ea5286f5871a8199fdf3/codex-rs/core/src/tools/handlers/goal/update_goal.rs#L54-L58)

```rust
if args.status != ThreadGoalStatus::Complete {
    return Err(FunctionCallError::RespondToModel(
        "update_goal can only mark the existing goal complete; pause, resume,
         and budget-limited status changes are controlled by the user or system"
    ));
}
```

→ 한국어: **모델이 부를 수 있는 상태는 `Complete` 하나뿐. `Pause`/`Resume`/`BudgetLimited`는 사용자/시스템 전용.** 즉 모델이 "작업을 멈추려고 budget-limited로 마크" 같은 우회 종료를 코드 수준에서 차단.

ralph-loop의 `<promise>DONE</promise>` 같은 string 매칭보다 한 단계 강한 가드 — **JSON Schema 스키마로 권한이 잠겨 있음**.

#### ③ `budget_limit.md` — 예산 도달 시 별도 시스템 프롬프트

**위치**: [`codex-rs/core/templates/goals/budget_limit.md`](https://github.com/openai/codex/blob/82061660ae2adf10dfd5ea5286f5871a8199fdf3/codex-rs/core/templates/goals/budget_limit.md)

전체 본문 짧음. 핵심:

> *"The system has marked the goal as budget_limited, so do not start new substantive work for this goal. Wrap up this turn soon: summarize useful progress, identify remaining work or blockers, and leave the user with a clear next step."*
>
> *"Do not call update_goal unless the goal is actually complete."*

→ 한국어: **시스템이 이 목표를 budget_limited로 마크했으니 새 본격 작업을 시작하지 마라. 이번 차례를 곧 마무리하라: 유용한 진척을 요약하고, 남은 작업이나 차단 요인을 식별하고, 사용자에게 명확한 다음 단계를 남겨라.** + **목표가 실제로 완료된 게 아니면 update_goal을 부르지 마라.**

이게 두 번째 호출 가드 — 예산 떨어진 LLM이 "어차피 끝났다고 치자" 하고 거짓 마크하는 경로 차단.

#### ④ Cookbook의 사용자용 원칙 명시

**위치**: [Codex Cookbook — Using Goals in Codex (2026-05-09)](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)

> *"Completion must be evidence-based. A Goal should not be marked complete because the model believes it is probably done. It should be complete only after the objective is checked against the relevant files, tests, logs, benchmark output, generated artifacts, or other concrete evidence."*

→ 한국어: **완료는 증거 기반이어야 한다. 모델이 "아마 끝났을 것"이라 믿는다고 Goal을 완료로 표시해선 안 된다. 관련 파일, 테스트, 로그, 벤치마크 출력, 생성된 산출물, 기타 구체적 증거에 대조해 확인된 후에만 완료여야 한다.**

→ Cookbook은 사용자(Goal을 작성하는 사람)에게 *왜* 위 prompt 가드들이 박혀있는지 설명. 가드의 진짜 목적은 LLM이 자기 믿음을 근거로 끝내는 걸 막는 것.

**한계 (정직한 정리)**:
- 위 4가지 모두 **prompt-level 강제** + **도구 스키마 잠금**. 모델이 prompt를 무시하거나 환각으로 audit 했다고 잘못 믿으면 그래도 거짓 `update_goal` 호출 가능.
- OpenAI는 이 한계를 알고 audit 절차를 6단계로 정교화했지만, 같은 모델이 작업하고 평가하는 인지 동조에서 자유로울 수 없음.

---

### Claude — 별도 모델 (architecture-level separation)

작업 모델과 다른 LLM에게 평가를 맡겨 **인지 동조 자체를 끊어** 막으려 함. 핵심 자료 3개:

#### ① Claude Code `/goal` 도큐먼트 — 핵심 한 줄

**위치**: [`code.claude.com/docs/en/goal`](https://code.claude.com/docs/en/goal) 의 "How evaluation works" 섹션

> *"`/goal` is a wrapper around a session-scoped prompt-based Stop hook. Each time Claude finishes a turn, the condition and the conversation so far are sent to your configured **small fast model, which defaults to Haiku**. The model returns a yes-or-no decision and a short reason."*

→ 한국어: **`/goal`은 세션 단위 프롬프트 기반 종료 훅을 감싸는 래퍼다. Claude가 차례를 끝낼 때마다, 조건과 그때까지의 대화가 설정된 *소형 고속 모델(기본은 Haiku)*로 전송된다. 모델은 yes/no 결정과 짧은 이유를 반환한다.**

→ 단일 줄에 architecture 분리가 명시: **다른 모델(Haiku)이 yes/no 반환**.

#### ② 같은 도큐먼트 — "fresh model" 표현으로 분리 의도 강조

> *"`/goal` adds a separate evaluator that checks your condition after every turn, so **completion is decided by a fresh model rather than the one doing the work**."*

→ 한국어: **`/goal`은 매 차례 후 조건을 확인하는 별도 평가자를 추가한다. 그래서 완료 여부는 *작업 중인 모델이 아니라 새 모델*이 결정한다.**

→ "the one doing the work"와 "fresh model"을 명시적으로 대비. **Anthropic이 self-assessor 문제를 직접 인지하고 architecture 분리로 답했다는 자기 설명**.

#### ③ Hooks reference — 평가자 메커니즘의 일반화된 자리

**위치**: [`docs.anthropic.com/en/docs/claude-code/hooks`](https://docs.anthropic.com/en/docs/claude-code/hooks) — "Hook handler fields" 섹션, 5개 hook type 중

> *"Prompt hooks (type: 'prompt'): send a prompt to a Claude model for single-turn evaluation. The model returns a yes/no decision as JSON."*

→ 한국어: **프롬프트 훅 (`type: 'prompt'`): 단일 차례 평가를 위해 Claude 모델에 프롬프트를 보낸다. 모델은 yes/no 결정을 JSON으로 반환한다.**

→ `/goal`은 이 prompt hook의 사용자용 단축 명령. **평가자 분리가 시스템 1급 시민으로 hook 시스템에 통합된 자리**가 여기. ralph-loop 플러그인은 같은 hook 시스템의 `type: "command"` 사용 — 같은 인프라 위에 다른 타입.

**더 강한 가드의 흔적** — `type: "agent"`:

> *"Agent hooks (type: 'agent'): spawn a subagent that can use tools like Read, Grep, and Glob to verify conditions before returning a decision. **Agent hooks are experimental and may change.**"*

→ 한국어: **에이전트 훅 (`type: 'agent'`): Read, Grep, Glob 같은 도구를 쓸 수 있는 서브에이전트를 띄워 결정을 반환하기 전에 조건을 검증한다. 에이전트 훅은 실험적이며 변경될 수 있다.**

→ Anthropic도 **prompt hook의 한계를 인정**(평가자가 도구를 못 쓰니 작업 모델 출력 텍스트만 보고 판단해야 함). 도구 사용 가능 평가자(agent hook)가 다음 진화로 이미 실험 중.

**한계 (정직한 정리)**:
- Haiku도 결국 LLM이라 환각 가능. "테스트 통과 안 했는데 통과했다고 판정"하면 그래도 종료.
- 평가자가 도구를 못 쓰니 작업 모델이 대화에 거짓 텍스트(*"All tests pass!"*)를 남기면 속을 수 있음. 도구 사용 가능 평가자(agent hook)가 다음 진화로 이미 실험 중인 이유.

---

### 신뢰도 한 줄 비교

| 가드 위치 | Codex | Claude `/goal` |
|---|---|---|
| **모델 분리** | ❌ (같은 작업 모델) | ✅ (Haiku 별도) |
| **Prompt 강제** | ✅ (`continuation.md` 6개 섹션) | 부분적 (조건 자체) |
| **도구 스키마 잠금** | ✅ (`update_goal`은 `Complete`만 허용) | — |
| **예산 한도 별도 처리** | ✅ (`budget_limit.md` 별도 시스템 프롬프트) | 부분적 (조건에 "or stop after N turns") |
| **도구 사용 가능 평가자** | ❌ | 실험 중 (`type: "agent"` hook) |

→ **Codex는 prompt-level + tool schema 두 층으로 무장, Claude는 architecture 분리 + 다음 진화(agent hook)로 가는 중**. 둘 다 self-assessor 문제를 *완벽히* 풀지 못하고 다른 층위에서 답함.
