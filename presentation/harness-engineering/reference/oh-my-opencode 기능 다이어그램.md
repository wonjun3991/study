---
title: "oh-my-opencode 기능·작업흐름 다이어그램"
tags:
  - 하네스엔지니어링
  - oh-my-opencode
  - 다이어그램
  - 발표자료
created: 2026-04-24
parent: "[[Sisyphus 벤치마크 전체 여정]]"
related:
  - "[[claude vs Sisyphus 하네스 아키텍처 비교]]"
  - "[[발표 자료 정리 - 간단하게 하네스 구축하기]]"
---

# oh-my-opencode 기능·작업흐름 다이어그램

> **핵심 메시지**: OMO는 "AI에게 일을 시키는 전체 흐름"을 5단계 — **의도 파악 → 플랜 → 작업 분배 → 검증 → 루프(Ralph)** — 로 파이프라인화한 제품.

---

## 🎬 전체 작업 흐름 (사람이 읽는 관점)

```mermaid
flowchart TB
    USER[👤 사용자<br/>'N+1 버그 찾아서 고쳐줘']

    subgraph S1 ["1️⃣ 의도 파악 (Intent)"]
        KW[한/영/일/중 키워드 감지<br/>→ 분석/검색/ultrawork 모드 자동 선택]
        CTX[AGENTS.md / rules /<br/>이전 세션 메모 자동 주입]
    end

    subgraph S2 ["2️⃣ 플랜 수립 (Plan)"]
        PROM[Prometheus<br/>전체 계획 수립]
        MET[Metis<br/>사전 분석<br/>'놓친 요구사항 있나?']
        MOM[Momus<br/>계획 비평<br/>'이 플랜 허술하지 않나?']
    end

    subgraph S3 ["3️⃣ 작업 분배 (Dispatch)"]
        SIS[Sisyphus<br/>오케스트레이터]
        SUB1[Explore<br/>코드 탐색]
        SUB2[Librarian<br/>문서/OSS 조사]
        SUB3[Sisyphus-Junior<br/>실제 수정 실행]
        SUB4[Atlas<br/>긴 계획 실행]
    end

    subgraph S4 ["4️⃣ 검증 (Verify)"]
        ORC[Oracle<br/>고난도 품질 검토]
        AUTO[자동 복구<br/>edit 실패 · JSON 깨짐<br/>· context 초과 · 모델 오류<br/>→ 모두 자동 재시도]
        TEST[컴파일/테스트<br/>실패 감지]
    end

    subgraph S5 ["5️⃣ Ralph Loop (실패해도 끝까지)"]
        CHECK{성공?}
        RETRY[실패 원인 분석<br/>→ 다음 iter 프롬프트<br/>자동 생성 → 재실행]
        DONE[✅ 최종 완료]
    end

    USER --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> CHECK
    CHECK -->|실패| RETRY
    RETRY --> S3
    CHECK -->|성공| DONE

    style S1 fill:#fff3cd
    style S2 fill:#d4edda
    style S3 fill:#d1ecf1
    style S4 fill:#f8d7da
    style S5 fill:#e2d9f3
```

---

## 1️⃣ 의도 파악 — "사용자가 뭘 원하는지 자동으로 해석"

**하는 일**: 사용자 메시지를 그대로 모델에 던지지 않고, **한 번 가공**해서 필요한 컨텍스트를 얹음.

```mermaid
flowchart LR
    IN["'N+1 버그 찾아줘'"]

    subgraph AUTO ["자동 주입되는 것들"]
        KW["🌐 다국어 키워드 감지<br/>'찾아줘' → [search-mode]<br/>'분석해' → [analyze-mode]"]
        RULE["📋 프로젝트 규칙<br/>.claude/rules/*.md 중<br/>파일 glob 매칭되는 것"]
        DOC["📄 AGENTS.md<br/>프로젝트 메타 정보"]
        MEMO["🧠 Sisyphus 메모<br/>이전 세션에서<br/>배운 것들"]
    end

    OUT[강화된 메시지<br/>모델에게 전달]

    IN --> KW --> OUT
    IN --> RULE --> OUT
    IN --> DOC --> OUT
    IN --> MEMO --> OUT

    style AUTO fill:#fff3cd
```

**효과**:
- 사용자는 *"이 프로젝트는 Spring Boot고 헥사고날이야..."* 반복 입력 불필요
- 한국어로 말해도 자동으로 AI 친화적인 프롬프트로 변환

---

## 2️⃣ 플랜 수립 — "계획부터 검증하고 시작"

**하는 일**: 바로 코드 수정 들어가지 않고, **플래너 에이전트 3명**이 계획의 품질을 교차 검증.

```mermaid
flowchart LR
    REQ[강화된 요청]

    REQ --> PROM[🧠 Prometheus<br/>━━━━<br/>1차 계획 수립<br/>'이렇게 해보자']
    PROM --> MET[🔍 Metis<br/>━━━━<br/>사전 분석<br/>'빠진 요구사항,<br/>숨은 제약 있나?']
    MET --> MOM[⚖️ Momus<br/>━━━━<br/>계획 비평<br/>'검증 기준이<br/>명확한가?']
    MOM --> FINAL[✅ 최종 실행 계획]

    style PROM fill:#d4edda
    style MET fill:#fff3cd
    style MOM fill:#f8d7da
```

**왜 3명?**:
- Prometheus가 짠 계획에는 **blind spot**이 있음
- Metis가 *"이 요건 놓쳤는데?"* 지적
- Momus가 *"검증 방법이 구체적이지 않다"* 비평
- 3명 합의 후에야 실행 단계로 넘어감

**.claude/와 다른 점**: `.claude`는 보통 1명(feature-implementer)이 계획+실행 다 함 → blind spot 걸러지지 않음.

---

## 3️⃣ 작업 분배 — "1명이 다 하지 말고 전문가에게"

**하는 일**: 메인 에이전트(Sisyphus)가 **작업을 쪼개서 전문가에게 위임**, 병렬 실행.

```mermaid
flowchart TB
    SIS[🎯 Sisyphus<br/>오케스트레이터]

    SIS -.->|병렬| EXP[🔍 Explore<br/>'해당 코드 위치 찾아줘']
    SIS -.->|병렬| LIB[📚 Librarian<br/>'JPA 공식 문서 확인']
    SIS -.->|병렬| SJ[👷 Sisyphus-Junior<br/>'실제 파일 수정 실행']

    EXP -->|찾은 위치 보고| SIS
    LIB -->|문서 요약 보고| SIS
    SJ -->|수정 결과 보고| SIS

    subgraph ISO ["🔒 핵심: Context Isolation"]
        NOTE[각 전문가는<br/>독립된 깨끗한 대화<br/>━━━━━━<br/>메인 Sisyphus context 오염 X<br/>+<br/>병렬 실행 → 빠름]
    end

    style SIS fill:#e2d9f3
    style EXP fill:#d1ecf1
    style LIB fill:#d1ecf1
    style SJ fill:#d1ecf1
    style ISO fill:#fff3cd
```

**효과** (v5 벤치에서 실증):
- Vanilla(혼자 다 함): 한 세션에 모든 탐색+수정 누적 → 디테일 놓침
- Sisyphus(위임): 각 전문가가 자기 일만 집중 → 품질 ↑, 토큰 ↓

---

## 4️⃣ 검증 — "실패하면 자동으로 복구"

**하는 일**: 수정 결과를 검증하고, **예상 가능한 실패들은 자동으로 처리**.

```mermaid
flowchart LR
    RESULT[수정 완료]

    subgraph CHECKS ["자동 감지되는 실패들"]
        F1[❌ 파일 편집 실패<br/>오래된 내용 기준]
        F2[❌ JSON 응답 깨짐]
        F3[❌ Context 200K 초과]
        F4[❌ 모델 5xx / rate limit]
        F5[❌ 없는 툴 호출]
        F6[❌ 빈 응답]
    end

    subgraph FIX ["자동 복구"]
        R1[파일 다시 읽고 재시도]
        R2[JSON 재생성 요청]
        R3[compaction 자동 트리거<br/>todo 상태는 보존]
        R4[대체 모델로 재시도]
        R5[agent 설정 수정 안내]
        R6[재요청]
    end

    subgraph HUMAN ["품질 검토 (선택)"]
        ORC[🧙 Oracle<br/>고난도 문제 리뷰<br/>'이 설계 맞나?']
    end

    RESULT --> CHECKS
    F1 --> R1
    F2 --> R2
    F3 --> R3
    F4 --> R4
    F5 --> R5
    F6 --> R6

    RESULT -->|복잡한 작업| ORC

    style CHECKS fill:#f8d7da
    style FIX fill:#d4edda
    style HUMAN fill:#e2d9f3
```

**.claude/와 결정적 차이**: `.claude`는 compile-check 1개만 있음. 나머지 실패는 사용자가 수동으로 "다시 해줘" 입력.

---

## 5️⃣ Ralph Loop — "성공할 때까지 포기 안 함"

**하는 일**: 한 번 실패했다고 멈추지 않고, **완료 조건 만족까지 자동 반복**.

```mermaid
flowchart TB
    START["/ralph 시작<br/>또는 장시간 작업 자동 감지"] --> SAVE[현재 상태<br/>저장]

    SAVE --> WORK[Sisyphus 작업]
    WORK --> TEST{테스트 통과?<br/>컴파일 통과?<br/>사용자 조건 만족?}

    TEST -->|❌ 실패| ANALYZE[실패 원인 분석<br/>━━━━<br/>무엇이 왜 안 됐나?]
    ANALYZE --> BUILD[다음 iteration<br/>프롬프트 자동 생성<br/>━━━━<br/>'지난번 X가 문제였으니<br/>이번엔 Y를 시도']
    BUILD --> RESET[context 일부 초기화<br/>todo는 보존]
    RESET --> WORK

    TEST -->|✅ 성공| RECORD[모든 iteration<br/>기록 저장]
    RECORD --> END[최종 완료 보고]

    subgraph GUARD ["무한 루프 방지"]
        TIMEOUT[최대 시간 제한]
        MAX[최대 iteration 수]
    end

    WORK -.-> GUARD
    GUARD -.->|제한 초과| END

    style TEST fill:#fff3cd
    style ANALYZE fill:#f8d7da
    style BUILD fill:#d1ecf1
    style END fill:#d4edda
```

**사용 예시**:
- 테스트 3개 실패 → 자동 수정 → 2개 실패 → 자동 재수정 → 0개 실패 ✅
- 컴파일 에러 20개 → 자동 수정 → 5개 → 0개 ✅
- 사용자는 최초 명령 한 번만 하고 커피 타러 감

---

## 📊 한 장 요약 — 5단계 vs `.claude/`

| 단계 | OMO가 주는 것 | `.claude`로 직접 구현 |
|---|---|---|
| **1️⃣ 의도 파악** | 다국어 키워드 감지, 자동 context 주입, 메모 기억 | rules 자동 주입은 가능, 나머지는 불가 |
| **2️⃣ 플랜 수립** | Prometheus+Metis+Momus 3명 교차 검증 | feature-implementer 혼자 계획+실행 |
| **3️⃣ 작업 분배** | Sisyphus+전문 에이전트 10+, 병렬 fan-out | Task tool로 수동 위임 (병렬 제어 없음) |
| **4️⃣ 검증** | 6종류 자동 복구 + Oracle 리뷰 | compile-check 1개만 |
| **5️⃣ Ralph 루프** | 성공까지 자동 반복, todo 보존 | 없음 (사용자 수동 재실행) |

---

## 💬 발표에서 할 말

> **"`.claude/`는 '부품 창고'고, OMO는 '완성된 작업실'입니다.**
>
> 부품 창고에는 좋은 망치·톱·못이 다 있어요. 근데 의자 만들려면 제가 조립 순서를 짜야 해요. 실수하면 제가 다시 짜고.
>
> OMO는 다릅니다. *'의자 만들어줘'* 한마디면 — 계획 짜는 사람이 계획 짜고, 비평가가 검토하고, 목수가 톱질하고, 품질 검사관이 확인하고, 안 되면 다시 시도까지 — 5단계가 자동으로 돕니다.
>
> 그래서 저처럼 바쁜 엔지니어한테는 OMO가 더 맞는 겁니다."

---

## 🔗 관련 노트

- [[claude vs Sisyphus 하네스 아키텍처 비교]] — `.claude` vs OMO 구조 비교
- [[v5 실행 검증]] — 3️⃣ 작업 분배의 context isolation이 품질 차이 만든 실증
- [[발표 자료 정리 - 간단하게 하네스 구축하기]] — 이 다이어그램 §3에서 활용