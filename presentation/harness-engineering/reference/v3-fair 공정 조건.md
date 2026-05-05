---
title: "v3-fair 공정 조건"
tags:
  - 벤치마크
  - sisyphus
  - qwen36
  - 공정성
created: 2026-04-24
parent: "[[Sisyphus 벤치마크 전체 여정]]"
---

# v3-fair — 공정 조건에서의 재측정

> **교훈**: 공정성 없는 비교는 orchestration의 가치를 과대평가한다.

## v3의 문제 → v3-fair의 교정

**v3 (폐기됨)**: 어려운 태스크(H1-H5) 설계 성공했으나, **Vanilla에는 AGENTS.md/skill을 안 주고 Sisyphus에만 줬음**. Vanilla가 실제 OpenCode build agent보다 더 열악한 조건 → 억지 차이.

**v3-fair**: 양쪽 모두 동일한 **AGENTS.md (101 lines) + task-specific skills** 주입. 유일한 차이는 **Sisyphus의 parallel + isolated context**.

## 태스크 (H1-H5, 어려운 분석형)

| # | 태스크 | 함정 |
|---|---|---|
| H1 | `Order.getFirstShipment()` 모든 호출처 | 파일 수(13) vs 호출 수(28) 혼동 |
| H2 | `OrderRepository` (22 methods) ISP 분할 + 파일 생성 | 22 methods, 19 callers |
| H3 | `AuthenticationService` DIP 위반 + UserPort 생성 | UserRepository는 이미 port에 있음 (이름만 바꿔선 안 됨) |
| H4 | `RouteCandidateMapper` unused 검증 | grep 1개로 "unused" 결론 함정 (build/generated에 Impl 있음) |
| H5 | `DeleteRouteService`의 UnsupportedOperation 메서드 처리 | caller=0이 정답 (제거) |

## 실측 결과

| 지표 | Vanilla (fair) | Sisyphus (fair) | 비율 |
|---|---:|---:|---:|
| **Wall-clock** | **883.7 s** | **319.4 s** | **0.36× (64% 단축)** |
| Parallel segment | — | 196.7 s | — |
| **Total tokens** | **6,526,369** | **2,691,626** | **0.41× (59% 절감)** |
| Tool calls | 111 | 138 | 1.24× (Sisyphus가 더 많이 탐색) |
| **Goal (육안)** | **5/5** | **5/5** | **동률** |

## Per-task 메트릭

| Task | V wall | V tokens | S wall | S tokens |
|---|---:|---:|---:|---:|
| H1 | 120.7s | 287K | 122.7s | 228K |
| H2 | 248.7s | 1.22M | 196.7s | 1.00M |
| H3 | 272.1s | 2.16M | 154.9s | 724K |
| H4 | 92.9s | 969K | 103.6s | 381K |
| H5 | 149.4s | 1.89M | 105.9s | 357K |

**주목**: Vanilla H3가 input 2.16M로 폭증 (T1/T2 누적 context). Sisyphus H3는 격리되어 724K만.

## H4 Rate-limit 사건

Sisyphus 4-way 병렬이 DashScope 동시성 한도(HTTP 429) 초과 → H4만 단독 재실행 후 병합. **운영 시사점**: 병렬 fan-out은 provider rate limit에 취약. retry/backoff 필수.

## 품질 검증 (육안)

양쪽 모두 5개 태스크 기준 충족:
- H1: 28개 call site 모두 정확히 잡음 (양쪽 동일, false positive 8개도 동일)
- H4: build/generated/ MapStruct Impl 확인 후 unused 결론 도출 (함정 회피)
- H5: remove 결정 + caller=0 증거 제시

## 핵심 발견

1. **공정 조건에서도 Sisyphus가 wall 64% / tokens 59% 절감**
2. **그러나 품질은 동률** — Qwen3.6-plus가 단일 context로도 어려운 분석 해냄
3. **Output tokens는 거의 동일** (33K vs 27K) — 답변 분량은 비슷, 도달 경로만 다름
4. **이 결과로는 "품질 이점" 주장 불가** → v5 실행 검증 태스크로 넘어감

## 참조
- [[Sisyphus 벤치마크 전체 여정]]
- [[v4 qwen3-coder-plus]]
- [[v5 실행 검증]]
- `bench-v3/results/final-fair-report.md`
