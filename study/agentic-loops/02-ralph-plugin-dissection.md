# 02 — Anthropic 공식 Ralph Loop 플러그인 해부

> **3줄 요약**:
> 1. 사용자가 `/ralph-loop "작업 내용" --completion-promise "DONE"` 같이 시작하면, 셋업 스크립트가 `.claude/ralph-loop.local.md`라는 상태 파일을 만들어 두고, **같은 Claude 세션 안에서** 작업이 시작된다 (1장처럼 새 프로세스 띄우는 게 아님).
> 2. Claude가 한 차례 작업하고 종료를 시도할 때마다 **종료 훅(Stop hook)이 가로채서**, 마지막 발화에 `<promise>DONE</promise>`이 있는지 확인하고, 없으면 **같은 프롬프트를 다시 주입**해서 다음 차례를 강제로 이어가게 만든다.
> 3. 이 루프는 **Claude 본인이 `<promise>DONE</promise>`을 출력**하거나 `--max-iterations`에 도달하거나 사용자가 `/cancel-ralph`을 누를 때까지 계속된다 — 즉 **종료 권한이 LLM 본인에게 있다**는 게 1장과의 결정적 차이 (1장은 LLM에게 종료 권한이 없었음).
>
> ---
>
> **목적**: ghuntley의 외부 bash 루프를 Anthropic이 어떻게 **세션 내부**(종료 훅 / Stop hook)로 옮겼는지, 5개 파일을 원본 텍스트(raw text)로 직접 읽어 추적한다.
>
> **출처 저장소**: [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official)
> **플러그인 경로**: `plugins/ralph-loop/`
> **고정 SHA**: `b5a156b6ecd2f69c418184b7c093930ddabaf9c0`
> **수집일**: 2026-05-18
>
> **읽는 순서**: §0 (왜 같은 Ralph인데 구조가 다른가) → §1(setup) → §2(상태 파일) → §3(stop-hook.sh, 핵심) → §4(명령 파일) → §5(통합 메커니즘) → §6(원본과의 비교 + 잃은 것 / 얻은 것)

---

## 0. 핵심 차이 한 줄

| 원본 (ghuntley) | 공식 플러그인 (Anthropic) |
|---|---|
| 외부 `while true; do cat PROMPT.md \| claude -p; done` | **세션 안에서** 종료 훅(Stop hook)이 종료 시도를 가로채 같은 프롬프트를 다시 주입 |

→ 가장 큰 결과: **매 반복마다 새 컨텍스트(fresh context per iteration)가 사라진다**. 매 반복이 동일한 Claude 세션 안에서 일어나므로 이전 차례(turn)가 전부 컨텍스트에 남음. 이것이 [HumanLayer 비판](https://www.humanlayer.dev/blog/brief-history-of-ralph)의 핵심.

> ⚠️ **기존 README 정정 사항**:
> 기존 [`README.md`](./README.md) §3-B는 이 플러그인을 `anthropics/claude-code/plugins/ralph-wiggum/hooks/stop-hook.sh` 로 적었지만, 2026-05 시점 실제 위치는:
> - **저장소**: `anthropics/claude-plugins-official` (별도 저장소)
> - **디렉토리 이름**: `ralph-loop` (`ralph-wiggum` 아님)
>
> 즉 `anthropics/claude-plugins-official/plugins/ralph-loop/hooks/stop-hook.sh`가 정답. 디렉토리 이름이 `ralph-wiggum` → `ralph-loop`로 변경된(rename) 흔적으로 보임. README §3-B와 §9의 URL을 갱신해야 함.

---

## 1. 플러그인 파일 구조

```
plugins/ralph-loop/
├── commands/
│   ├── ralph-loop.md        # /ralph-loop 슬래시 명령
│   ├── cancel-ralph.md      # /cancel-ralph 슬래시 명령
│   └── help.md              # 사용자 설명용
├── hooks/
│   ├── hooks.json           # 종료 훅(Stop hook) 등록
│   └── stop-hook.sh         # ★ 핵심: 종료를 가로채 프롬프트 재주입
└── scripts/
    └── setup-ralph-loop.sh  # 상태 파일 생성
```

ghuntley의 5개 파일 vs Anthropic의 6개 파일이지만, **책임 분배가 완전히 다름**.

| 파일 | 한 일 | 누가 만드나 |
|---|---|---|
| `commands/*.md` | 슬래시 명령 정의 (프론트매터 + 프롬프트) | 플러그인 작성자 (Anthropic) |
| `hooks/hooks.json` | 종료 훅을 Claude Code에 등록 | 플러그인 작성자 |
| `hooks/stop-hook.sh` | 종료 가로채기 + 프롬프트 재주입 | 플러그인 작성자 |
| `scripts/setup-ralph-loop.sh` | 인자 파싱 + 상태 파일 작성 | 플러그인 작성자 |
| `.claude/ralph-loop.local.md` | **실행 중 생성**되는 상태 파일 | setup 스크립트가 생성 |

→ 사용자가 직접 작성하는 파일은 **없다**. ghuntley 패턴은 "사용자가 PROMPT.md 직접 씀"이 전제였는데, 여기서는 슬래시 명령 인자로 프롬프트를 전달.

> **읽어낸 의도**: 진입 장벽 낮추기. bash, git, claude CLI 설정 없이 `/ralph-loop "..."` 한 줄로 시작.

---

## 2. `.claude/ralph-loop.local.md` — 실행 중 상태 파일

### 2-A. 형태 (setup-ralph-loop.sh가 생성)

```markdown
---
active: true
iteration: 1
session_id: <CLAUDE_CODE_SESSION_ID>
max_iterations: 0
completion_promise: "DONE"
started_at: "2026-05-18T03:14:00Z"
---

<여기가 사용자가 /ralph-loop 뒤에 입력한 프롬프트 본문>
```

YAML 프론트매터(frontmatter) + 마크다운 본문. **단 한 개 파일이 모든 상태를 담음**.

### 2-B. 필드별 의미

| 필드 | 누가 갱신 | 용도 |
|---|---|---|
| `active: true` | setup이 한 번 씀, 사용 안 됨 | 사람이 grep으로 확인할 용도 |
| `iteration: N` | stop-hook이 매 반복마다 +1 | 종료 임계 비교 |
| `session_id` | setup이 `CLAUDE_CODE_SESSION_ID` 환경변수에서 캡처 | **세션 격리**(§3-D) |
| `max_iterations` | setup이 `--max-iterations` 인자에서 | 0이면 무한 |
| `completion_promise` | setup이 `--completion-promise` 인자에서 | 종료 신호 텍스트 |
| `started_at` | setup이 `date -u` | 디버깅용 |
| 본문 | setup이 `$PROMPT` 변수에서 | 매 반복 재주입될 본문 |

### 2-C. 위치 — `.claude/` 안에 있음

`.claude/`는 Claude Code의 프로젝트별 로컬 설정 디렉토리. `.gitignore`에 들어가는 게 일반적.

> **함의**: 이 상태 파일은 **git에 안 들어간다**. 즉 git push로 다른 머신에 전파되는 ghuntley의 `IMPLEMENTATION_PLAN.md`와 정반대. **로컬 세션 한정 상태**.

---

## 3. `hooks/stop-hook.sh` — 진짜 핵심 (라인 단위 해부)

### 3-A. 훅 등록 (`hooks.json`)

```json
{
  "description": "Ralph Loop plugin stop hook for self-referential loops",
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-hook.sh\""
          }
        ]
      }
    ]
  }
}
```

**Stop 이벤트** = Claude가 차례(turn)를 끝내고 종료하려는 순간. Claude Code는 이 시점에 등록된 훅 명령을 실행. 훅이 특정 JSON을 반환하면 종료를 막고 "다음 프롬프트를 이 텍스트로 시작"으로 명령할 수 있음.

→ 이게 Ralph 루프의 외피. 외부 `while`이 아니라 Claude Code의 훅 시스템이 그 역할.

### 3-B. 첫 가드(보호 장치) — 상태 파일 없으면 통과

```bash
RALPH_STATE_FILE=".claude/ralph-loop.local.md"

if [[ ! -f "$RALPH_STATE_FILE" ]]; then
  exit 0
fi
```

`exit 0`은 종료 훅 컨텍스트에서 "종료를 막지 마, 정상 종료해"라는 뜻. 즉 **ralph-loop이 시작 안 된 일반 세션에서는 훅이 아무것도 안 함**.

> **세부 트릭**: 종료 훅은 Ralph와 무관한 모든 Claude 세션에서도 실행된다. 그래서 "상태 파일 존재 = ralph 활성"으로 판정. 이게 플러그인이 광역으로 설치돼도 다른 세션을 망가뜨리지 않는 비결.

### 3-C. 프론트매터 파싱

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$RALPH_STATE_FILE")
ITERATION=$(echo "$FRONTMATTER" | grep '^iteration:' | sed 's/iteration: *//')
MAX_ITERATIONS=$(echo "$FRONTMATTER" | grep '^max_iterations:' | sed 's/max_iterations: *//')
COMPLETION_PROMISE=$(echo "$FRONTMATTER" | grep '^completion_promise:' | sed 's/completion_promise: *//' | sed 's/^"\(.*\)"$/\1/')
```

YAML 파서를 안 쓰고 `sed`+`grep`으로 처리. 이유: bash 훅은 추가 의존성을 깔지 않는 게 안전. `yq` 같은 도구 부재 환경에서도 돌아야 함.

### 3-D. 세션 격리 — 이게 깔끔한 디테일

```bash
STATE_SESSION=$(echo "$FRONTMATTER" | grep '^session_id:' | sed 's/session_id: *//' || true)
HOOK_SESSION=$(echo "$HOOK_INPUT" | jq -r '.session_id // ""')
if [[ -n "$STATE_SESSION" ]] && [[ "$STATE_SESSION" != "$HOOK_SESSION" ]]; then
  exit 0
fi
```

같은 프로젝트에서 **두 개의 Claude Code 세션을 동시에 띄웠을 때**:
- 한 세션이 ralph-loop을 시작 → 상태 파일 생성
- 다른 세션은 ralph와 무관 → 그런데 종료 훅은 양쪽에서 실행
- 격리 없으면 무관 세션도 같이 ralph 루프에 끌려들어감

→ `session_id` 비교로 본인 세션이 아니면 훅이 통과. **다중 세션 안전성(multi-session safety)**.

> **연결**: ghuntley 원본은 단일 프로세스 단일 cwd라서 이런 문제가 없었지만, Claude Code는 다중 세션이 일반적이라 추가 가드가 필요. 환경 차이가 코드 차이로 드러남.

### 3-E. iteration / max_iterations 검증

```bash
if [[ ! "$ITERATION" =~ ^[0-9]+$ ]]; then
  echo "⚠️  Ralph loop: State file corrupted" >&2
  ...
  rm "$RALPH_STATE_FILE"
  exit 0
fi
```

상태 파일이 손상됐으면 **삭제하고 정상 종료**. 즉 손상 = 종료. 보수적인 안전장치(fail-safe).

> **읽어낸 의도**: 무한 루프 안에서 상태 파일이 깨지면 자칫 자가 루프(끝없이 훅 실패)가 될 수 있음. 그래서 "의심스러우면 죽인다" 정책.

### 3-F. 최대 반복 도달 시 종료

```bash
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  echo "🛑 Ralph loop: Max iterations ($MAX_ITERATIONS) reached."
  rm "$RALPH_STATE_FILE"
  exit 0
fi
```

상태 파일을 **`rm`으로 삭제**. 다음 Stop 이벤트 때는 §3-B의 가드가 통과시킴. 깔끔.

### 3-G. 대화 기록(transcript) 읽기 — 마지막 AI 발화 추출

```bash
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')

LAST_LINES=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -n 100)
LAST_OUTPUT=$(echo "$LAST_LINES" | jq -rs '
  map(.message.content[]? | select(.type == "text") | .text) | last // ""
' 2>&1)
```

Claude Code는 매 차례를 JSONL(줄 단위 JSON)로 대화 기록 파일에 기록. 종료 훅은 그 파일 경로를 입력으로 받음. 핵심:

1. assistant 역할(role) 라인만 grep
2. 최근 100줄로 제한 (장기 세션 대응)
3. jq로 `content[].type == "text"`만 골라 마지막 텍스트 블록 추출

> **흥미점**: Claude Code는 한 차례에서도 콘텐츠 블록이 여러 개(text, tool_use, thinking) 나올 수 있어 JSONL 라인이 여러 줄. 그 중 마지막 `text` 블록이 "최종 발화"임. 도구 사용 후 마지막 코멘트가 약속(promise) 토큰일 가능성이 높으므로 이 추출 로직이 자연스러움.

### 3-H. ⭐ 완료 약속(completion promise) 검출 — 종료 신호의 정체

```bash
if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  PROMISE_TEXT=$(echo "$LAST_OUTPUT" | perl -0777 -pe \
    's/.*?<promise>(.*?)<\/promise>.*/$1/s; s/^\s+|\s+$//g; s/\s+/ /g' 2>/dev/null || echo "")

  if [[ -n "$PROMISE_TEXT" ]] && [[ "$PROMISE_TEXT" = "$COMPLETION_PROMISE" ]]; then
    echo "✅ Ralph loop: Detected <promise>$COMPLETION_PROMISE</promise>"
    rm "$RALPH_STATE_FILE"
    exit 0
  fi
fi
```

세 단계:

1. **Perl로 여러 줄 정규식** — `-0777`이 입력 전체를 한 문자열로 빨아들임(슬러프), `s` 플래그가 `.`을 줄바꿈에도 매치. `<promise>` 태그가 여러 줄 걸쳐도 잡힘.
2. **공백 정규화** — `\s+`를 단일 공백으로. LLM이 줄바꿈/공백을 다양하게 출력해도 매치되도록.
3. **글자 그대로(literal) 비교 (`=`)** — `==`가 아니라 `=` 사용. `==`는 bash `[[ ]]`에서 글로브 패턴 매칭이라 약속 텍스트에 `*`,`?`,`[`가 들어가면 깨짐. 일부러 글자 그대로 비교.

> **디테일**: 주석에도 적혀 있음 — *"== in [[ ]] does glob pattern matching which breaks with *, ?, [ characters"*. 한국어 풀이: **`[[ ]]` 안의 `==`는 글로브 패턴 매칭이라 *, ?, [ 문자에서 깨진다.** 약속을 `"DONE"` 같은 단순 텍스트로 두는 게 권장이지만 여러 단어도 안전하게 되어있음.

### 3-I. 매치 안 되면 — 반복 횟수 +1 후 같은 프롬프트 재주입

```bash
NEXT_ITERATION=$((ITERATION + 1))

PROMPT_TEXT=$(awk '/^---$/{i++; next} i>=2' "$RALPH_STATE_FILE")

# atomic update
TEMP_FILE="${RALPH_STATE_FILE}.tmp.$$"
sed "s/^iteration: .*/iteration: $NEXT_ITERATION/" "$RALPH_STATE_FILE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$RALPH_STATE_FILE"

if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  SYSTEM_MSG="🔄 Ralph iteration $NEXT_ITERATION | To stop: output <promise>$COMPLETION_PROMISE</promise> (ONLY when statement is TRUE - do not lie to exit!)"
else
  SYSTEM_MSG="🔄 Ralph iteration $NEXT_ITERATION | No completion promise set - loop runs infinitely"
fi

jq -n \
  --arg prompt "$PROMPT_TEXT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'
```

핵심 행동:

1. **iteration += 1** — 원자적 쓰기(atomic write, 임시 파일 + mv)로 경쟁 없음(race-free).
2. **프롬프트 본문 추출** — `awk '/^---$/{i++; next} i>=2'` — 첫 `---`을 만나면 카운터 1, 두 번째면 2, 그 이후 모든 줄 출력. 즉 **두 번째 `---` 이후가 프롬프트 본문**.
3. **JSON으로 반환** — 종료 훅의 응답 프로토콜:
   - `decision: "block"` → 종료 막음
   - `reason: <프롬프트 본문>` → 다음 차례의 사용자 입력으로 사용 (즉 **같은 프롬프트 재주입**)
   - `systemMessage` → UI에 표시되는 알림 (사용자가 반복 횟수 볼 수 있게)

> ⭐ **이게 "자기 참조 루프(self-referential loop)"의 진짜 메커니즘**: Claude가 종료하려 하면, 훅이 `decision: block` + `reason: <원래 프롬프트>`를 반환 → Claude는 자기가 막 끝낸 차례 바로 뒤에 **같은 프롬프트를 다시 받음** → 새로 작업 시작.

### 3-J. ❗ "Do not lie to exit" — 시스템 메시지에 박힌 프롬프트 인젝션

```
🔄 Ralph iteration $NEXT_ITERATION | To stop: output <promise>$COMPLETION_PROMISE</promise>
(ONLY when statement is TRUE - do not lie to exit!)
```

→ 한국어 풀이: **🔄 Ralph 반복 N회차 | 멈추려면 `<promise>완료문구</promise>`를 출력해라 (오직 그 문장이 참일 때만 — 빠져나가려고 거짓말하지 마라!)**

매 반복마다 시스템 메시지로 LLM에게 "거짓말로 빠져나가지 마"를 강조. 또한 `setup-ralph-loop.sh`의 마지막에서도:

```
STRICT REQUIREMENTS (DO NOT VIOLATE):
  ✓ Use <promise> XML tags EXACTLY as shown above
  ✓ The statement MUST be completely and unequivocally TRUE
  ✓ Do NOT output false statements to exit the loop
  ✓ Do NOT lie even if you think you should exit
```

→ 한국어 풀이: **엄격 요구사항 (위반 금지):**
- ✓ `<promise>` XML 태그를 위에 보인 그대로 사용
- ✓ 문장은 완전히, 분명히 참이어야 한다
- ✓ 루프를 빠져나가려고 거짓 문장을 출력하지 말라
- ✓ 빠져나가야 한다고 생각해도 거짓말하지 말라

> **읽어낸 의도**: LLM은 "지치면 거짓말로 빠져나가려는 경향"이 있음 (긴 컨텍스트 동안 작업 회피 경향). 이를 프롬프트로 명시적으로 차단. **프롬프트 수준의 적대적 방어(adversarial defense)**.
>
> 효과는 의문. 진짜 LLM이 "지친다"고 거짓말 약속(promise) 출력하면 막을 길이 없음. **구조적 가드가 아니라 도덕적 호소**. → 이게 README §8-1 "스스로 평가자(self-assessor) 문제"의 한 발현. 결국 [`/goal`](./03-goal-dissection.md)이 외부 평가자(evaluator)로 이걸 구조적으로 해결하려 함.

---

## 4. 명령(command) 파일들 — 슬래시 명령의 명세

### 4-A. `/ralph-loop` — 시작 명령

```markdown
---
description: "Start Ralph Loop in current session"
argument-hint: "PROMPT [--max-iterations N] [--completion-promise TEXT]"
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup-ralph-loop.sh:*)"]
hide-from-slash-command-tool: "true"
---

# Ralph Loop Command

Execute the setup script to initialize the Ralph loop:

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/setup-ralph-loop.sh" $ARGUMENTS
```

Please work on the task. When you try to exit, the Ralph loop will feed
the SAME PROMPT back to you for the next iteration. You'll see your
previous work in files and git history, allowing you to iterate and improve.

CRITICAL RULE: If a completion promise is set, you may ONLY output it when
the statement is completely and unequivocally TRUE. Do not output false
promises to escape the loop, even if you think you're stuck or should exit
for other reasons. The loop is designed to continue until genuine completion.
```

#### 줄 단위 해부

| 부분 | 의미 |
|---|---|
| `description` | 슬래시 메뉴에서 보일 짧은 설명 |
| `argument-hint` | 사용자에게 보여줄 인자 형식 |
| `allowed-tools` | **이 명령이 호출할 수 있는 도구의 화이트리스트** — `Bash` 호출도 특정 스크립트로 한정. 보안 가드 |
| `hide-from-slash-command-tool: "true"` | **슬래시 메뉴에서 숨김**. Claude가 자기가 부를 일은 거의 없음. 사용자가 명시적으로 입력해야 작동. |

> **흥미점**: `hide-from-slash-command-tool: true`가 의미심장. Claude가 자율적으로 "ralph-loop 돌릴까?"하고 자기 자신을 무한 루프에 가두는 사태를 방지. **사용자만 호출 가능**으로 강제.

본문은 두 부분:
1. **명령 실행**(```!...```) — 백틱+`!`이 Claude Code의 인라인 bash 실행 문법.
2. **LLM에게 주는 인라인 지시** — *"Same prompt will be fed back. Do not lie."* (같은 프롬프트가 되돌아온다. 거짓말하지 말라.) 매 반복의 첫 차례에서 LLM이 이 텍스트를 본다.

본문의 영어 본문 한국어 풀이:

> **이 작업을 수행하시오. 종료를 시도하면 Ralph 루프가 다음 반복을 위해 같은 프롬프트를 다시 줄 것이다. 파일과 git 기록(history)에서 이전 작업을 볼 수 있으며, 반복하며 개선할 수 있다.**
>
> **결정적 규칙: 완료 약속이 설정돼 있으면, 문장이 완전히 분명히 참일 때만 출력할 수 있다. 막혔다고 느끼거나 다른 이유로 종료해야 한다고 생각해도 루프를 탈출하려고 거짓 약속을 출력하지 말라. 이 루프는 진짜 완료까지 지속되도록 설계되었다.**

### 4-B. `/cancel-ralph` — 취소 명령

```markdown
---
description: "Cancel active Ralph Loop"
allowed-tools: [
  "Bash(test -f .claude/ralph-loop.local.md:*)",
  "Bash(rm .claude/ralph-loop.local.md)",
  "Read(.claude/ralph-loop.local.md)"
]
hide-from-slash-command-tool: "true"
---

# Cancel Ralph

To cancel the Ralph loop:

1. Check if `.claude/ralph-loop.local.md` exists using Bash:
   `test -f .claude/ralph-loop.local.md && echo "EXISTS" || echo "NOT_FOUND"`

2. **If NOT_FOUND**: Say "No active Ralph loop found."

3. **If EXISTS**:
   - Read `.claude/ralph-loop.local.md` to get the current iteration number
   - Remove the file using Bash: `rm .claude/ralph-loop.local.md`
   - Report: "Cancelled Ralph loop (was at iteration N)"
```

극단적으로 단순. 상태 파일 삭제가 곧 취소. 다음 Stop 이벤트 때 §3-B의 가드가 통과시킴.

> **디자인 우아함**: "취소"라는 별도 메커니즘이 없음. 그냥 파일 삭제. **상태 = 파일 존재**라는 불변식(invariant)이 모든 동작을 지배. 코드가 짧다는 것이 곧 신뢰성.

### 4-C. `/ralph-loop-help` — 사용자 교육

```markdown
**Core concept:**
```bash
while :; do
  cat PROMPT.md | claude-code --continue
done
```

The same prompt is fed to Claude repeatedly. The "self-referential" aspect
comes from Claude seeing its own previous work in the files and git history,
not from feeding output back as input.
```

→ 영어 본문 한국어 풀이:

> **핵심 개념**:
> ```bash
> while :; do
>   cat PROMPT.md | claude-code --continue
> done
> ```
> **같은 프롬프트가 Claude에게 반복적으로 주입된다. "자기 참조(self-referential)"라는 측면은 Claude가 출력을 입력으로 다시 받는 데서 오는 게 아니라, 파일과 git 기록에서 자기 이전 작업을 보는 데서 온다.**

> ⭐ **결정적 정정**: *자기 참조의 본질은 출력을 입력으로 다시 주입하는 게 아니라, 파일과 git 기록에서 자기 작업을 보는 것.*
>
> 많은 사람이 Ralph를 "출력→입력 루프"로 오해함. 공식 도큐먼트가 직접 정정. **상태는 LLM 메모리가 아니라 파일시스템에**. 이건 ghuntley 원본과 동일한 철학을 명시.

또한:

```
**Each iteration:**
1. Claude receives the SAME prompt
2. Works on the task, modifying files
3. Tries to exit
4. Stop hook intercepts and feeds the same prompt again
5. Claude sees its previous work in the files
6. Iteratively improves until completion
```

→ 한국어 풀이:

> **각 반복마다**:
> 1. Claude가 같은 프롬프트를 받음
> 2. 작업을 수행하며 파일을 수정
> 3. 종료를 시도
> 4. 종료 훅이 가로채 같은 프롬프트를 다시 줌
> 5. Claude가 파일에서 이전 작업을 봄
> 6. 완료까지 반복적으로 개선

→ §3-I의 메커니즘을 6단계로 도식화. 사용자가 멘탈 모델 잡기 좋게.

---

## 5. 통합 메커니즘 다이어그램

```
사용자: /ralph-loop "Fix auth bug" --completion-promise "FIXED" --max-iterations 10
          │
          ▼
┌──────────────────────────────────────────────────┐
│  setup-ralph-loop.sh (한 번만 실행)              │
│  - .claude/ralph-loop.local.md 생성              │
│  - 프론트매터: iteration=1, session_id=...       │
│  - 본문: "Fix auth bug"                          │
└──────────────────┬───────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────┐
│  Claude (현재 세션)                              │
│  - 프롬프트 받음: "Fix auth bug"                 │
│  - 도구 호출 여러 개 (Read/Edit/Bash)            │
│  - 마지막 텍스트 블록 출력 (예: "수정했습니다")  │
│  - 차례 종료 시도 (stop_reason: end_turn)        │
└──────────────────┬───────────────────────────────┘
                   │ ⚡ Stop 이벤트
                   ▼
┌──────────────────────────────────────────────────┐
│  stop-hook.sh (Anthropic 플러그인)               │
│                                                  │
│  ① 상태 파일 존재? → 아니오면 통과 (exit 0)     │
│  ② session_id 일치? → 아니오면 통과 (exit 0)    │
│  ③ iteration >= max? → 예면 종료 (rm + exit 0)  │
│  ④ 대화 기록에서 마지막 AI 텍스트 추출           │
│  ⑤ <promise>FIXED</promise> 매치?               │
│       ├─ 예 → "✅ 종료" + rm + exit 0           │
│       └─ 아니오 → ⑥로                            │
│  ⑥ iteration += 1                                │
│  ⑦ JSON 반환:                                    │
│     { decision: "block",                         │
│       reason: "Fix auth bug",                    │
│       systemMessage: "🔄 iter 2 | ..." }         │
└──────────────────┬───────────────────────────────┘
                   │ JSON via stdout
                   ▼
┌──────────────────────────────────────────────────┐
│  Claude Code 런타임                              │
│  - decision=block 보고 종료 막음                 │
│  - reason 텍스트를 "다음 사용자 차례"로 주입     │
│  - systemMessage UI 표시                         │
└──────────────────┬───────────────────────────────┘
                   │ 같은 세션, 같은 컨텍스트, 같은 프롬프트
                   ▼
        Claude가 그 다음 차례를 시작 (이전 작업 컨텍스트 그대로)
                   │
                   └─── 반복 ───┐
                                 │
              종료 경로:          │
              (a) <promise> 매치  │
              (b) iter >= max    │
              (c) /cancel-ralph  │
                                 ▼
                            상태 파일 삭제
                            루프 종료
```

---

## 6. ghuntley vs Anthropic — 비교

| 차원 | ghuntley 원본 | Anthropic ralph-loop |
|---|---|---|
| 루프 위치 | 외부 bash `while true` | 세션 내부 종료 훅(Stop hook) |
| 프로세스 모델 | 매 반복 **새 `claude` 프로세스** | 같은 `claude` 세션 지속 |
| **컨텍스트 윈도우** | ✅ **매 반복마다 새로(fresh)** | ❌ **누적** (이전 차례 모두 보임) |
| 종료 신호 | 사람 Ctrl+C / 최대 반복 도달 / fix_plan 비움 | `<promise>EXACT_TEXT</promise>` / 최대 반복 / `/cancel-ralph` |
| 상태 파일 | `IMPLEMENTATION_PLAN.md` (git 추적) | `.claude/ralph-loop.local.md` (gitignore) |
| 프롬프트 입력 | `cat PROMPT.md` 파일 | 슬래시 명령 인자 |
| 재현성 | 다른 머신에서 동일 PROMPT.md → 동일 동작 | 세션 종속 (이식 불가) |
| 진입 장벽 | bash + claude CLI 설정 필요 | `/ralph-loop "..."` 한 줄 |
| 다른 머신 / CI 통합 | git push 후 다른 환경에서 ralph 가능 | 단일 세션 한정 |

### 6-A. 잃은 것

1. **매 반복마다 새 컨텍스트(fresh context per iteration)** — Ralph 원본의 핵심 원칙 상실. 같은 세션 안에서 차례가 누적되므로 컨텍스트 윈도우 압박, 주의력 분산(attention dilution), 이전 잘못된 가정의 잔존 — 원본이 회피하던 실패 양상 모두 부활 가능.
2. **재현성 / 이식성** — `.claude/ralph-loop.local.md`은 로컬. CI에서 같은 ralph 돌리고 싶으면 별도 메커니즘 필요.
3. **외부 검증 트리거** — push가 매 반복 자동 발생하지 않으므로, 외부 CI 빌드/테스트로 검증하는 자연스러운 역압(backpressure) 사이클이 끊김.

### 6-B. 얻은 것

1. **사용자 진입 장벽** ↓↓ — 슬래시 명령 한 줄. bash, git, claude CLI 환경 변수 몰라도 됨.
2. **세션 격리** — `session_id` 매칭으로 다중 세션 안전.
3. **명시적 완료 신호** (`<promise>`) — 사람 Ctrl+C 의존이 줄어듦. 자동화 가능.
4. **취소가 깔끔** — `rm`이 곧 취소. `/cancel-ralph`가 추가 프로세스간 통신(IPC) 없이 동작.
5. **훅 시스템 활용** — Claude Code의 1급 시민 기능을 사용. 외부 도구 의존 없음(zero).

### 6-C. 결국 — 원본 정신과의 단절

[HumanLayer 비판](https://www.humanlayer.dev/blog/brief-history-of-ralph) 인용:

> *"공식 플러그인은 단일 세션 내 종료 훅으로 구현되어 원본의 핵심인 '매 반복마다 새 컨텍스트'를 놓쳤다."*

이건 정확한 지적. 하지만 Anthropic 입장에서는:
- 사용자 90%는 그 미묘한 차이를 모름
- "한 줄로 시작"이 압도적 가치
- 진짜 Ralph가 필요한 사람은 원본 bash 패턴 그대로 쓰면 됨

> **개인적 견해**: 두 가지가 다른 도구로 평행 존재해야 함. "Anthropic 공식 = 진짜 Ralph"라는 인식이 위험. **공식 플러그인은 Ralph의 UI 사용성 개선판**, **원본은 Ralph의 진짜 엔진**. 다음 노트(`/goal`)에서 보겠지만 결국 Anthropic 본인이 스스로 평가자(self-assessor) 문제를 인정하고 `/goal`이라는 별도 평가자(evaluator)로 보강. 그건 사실상 "공식 ralph-loop이 충분치 않다"는 자기 인정.

---

## 7. 흥미로운 디테일 모음

### 7-A. `awk '/^---$/{i++; next} i>=2'` — 한 줄짜리 프론트매터 분리기

상태 파일의 본문 추출 로직. `i==2`가 아니라 `i>=2`인 이유: 프롬프트 본문에 `---`가 들어있어도(예: 프롬프트 안에 마크다운 구분선) 두 번째 `---` 이후 모두 출력하므로 안전.

작은 디테일이지만 LLM이 프롬프트에 마크다운을 자유롭게 쓰는 환경을 고려한 설계.

### 7-B. `tail -n 100`의 의미

```bash
LAST_LINES=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -n 100)
```

장기 세션 시 대화 기록이 메가바이트 단위로 커짐. jq에 통째로 넣으면 메모리·시간 폭발. 마지막 100 AI 라인만 본다 = "약속(promise) 토큰은 마지막 차례에 있다"는 가정. 합리적.

### 7-C. `set +e` / `set -e` 토글

```bash
set +e
LAST_OUTPUT=$(echo "$LAST_LINES" | jq -rs '...' 2>&1)
JQ_EXIT=$?
set -e
```

`set -euo pipefail` 환경에서 jq 실패하면 전체 훅이 죽어 무한 루프 위험. 일시적으로 errexit를 끄고 jq 결과 확인 후 재활성화. **방어적 스크립팅(defensive scripting)**의 좋은 예.

### 7-D. `claudepluginhub` — 설치 방식

```
npx claudepluginhub anthropics/claude-plugins-official --plugin ralph-loop
```

플러그인 설치 도구가 npm 패키지로 존재. 별도 디렉토리에 플러그인 파일들을 푼 뒤 Claude Code가 자동 인식. 즉 사용자는 git clone 안 해도 됨.

---

## 8. 정정 사항 — 기존 README 갱신 항목

기존 [`README.md`](./README.md)에서 손볼 곳:

1. **§3-B 첫 줄** — `[plugins/ralph-wiggum/hooks/stop-hook.sh](https://github.com/anthropics/claude-code/blob/8bdbb72/plugins/ralph-wiggum/hooks/stop-hook.sh)` →
   `[plugins/ralph-loop/hooks/stop-hook.sh](https://github.com/anthropics/claude-plugins-official/blob/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/hooks/stop-hook.sh)`

2. **§9 "Ralph" 출처 목록** — Anthropic 공식 플러그인 URL 같은 식으로 갱신.

3. **§2 시스템별 정체성 표** — `Ralph (Anthropic 공식 플러그인)` 행의 "단일 세션 + 종료 훅" 옆에, "**(같은 세션 안에서 프롬프트 재주입, 새 컨텍스트 아님)**" 한 줄 추가하면 더 정확.

→ 마지막 노트 작성 후 별도 commit으로 정정 예정.

---

## 9. 다음 노트로의 연결

다음 [`03-goal-dissection.md`](./03-goal-dissection.md)는:
- Ralph의 스스로 평가자(self-assessor) 문제(§6-C)를 산업이 어떻게 해결하려 했는지.
- Codex `/goal` + Claude `/goal`의 프롬프트와 코드를 동일한 방식으로 원본 텍스트 해부.
- 핵심 변화: **종료 판정 = 작업 모델 ≠ 평가 모델**. 약속(promise) 토큰 같은 자기 선언에서, 외부 평가자(evaluator) 모델의 yes/no 판정으로.

---

## 부록: 1차 출처 원본 URL (영구 링크)

| 파일 | Raw URL |
|---|---|
| `commands/ralph-loop.md` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/commands/ralph-loop.md> |
| `commands/cancel-ralph.md` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/commands/cancel-ralph.md> |
| `commands/help.md` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/commands/help.md> |
| `hooks/hooks.json` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/hooks/hooks.json> |
| `hooks/stop-hook.sh` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/hooks/stop-hook.sh> |
| `scripts/setup-ralph-loop.sh` | <https://raw.githubusercontent.com/anthropics/claude-plugins-official/b5a156b6ecd2f69c418184b7c093930ddabaf9c0/plugins/ralph-loop/scripts/setup-ralph-loop.sh> |

저장소: <https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop>
