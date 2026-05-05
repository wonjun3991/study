---
title: "v4 qwen3-coder-plus"
tags:
  - 벤치마크
  - sisyphus
  - qwen3-coder-plus
  - prompt-caching
created: 2026-04-24
parent: "[[Sisyphus 벤치마크 전체 여정]]"
---

# v4 — qwen3-coder-plus로 4-way 교차 비교

> **교훈**: 모델 선택과 orchestration은 **직교**하며, **prompt caching**이 토큰 수치를 근본적으로 바꾼다.

## 실험 설계

v3-fair와 **동일한 하네스 + 같은 H1-H5 태스크**, 모델만 `qwen3-coder-plus`로 교체. 환경변수 하나 변경 (`BENCH_MODEL=qwen3-coder-plus`).

## 4-way 최종 결과

| 구성 | Wall s | Fresh tokens | 품질 |
|---|---:|---:|:-:|
| qwen3.6-plus Vanilla | 883.7 | 6,526,369 | 5/5 |
| qwen3.6-plus Sisyphus | 319.4 | 2,691,626 | 5/5 |
| qwen3-coder-plus Vanilla | 453.1 | 369,792 | 5/5 |
| **qwen3-coder-plus Sisyphus** | **159.6** | **317,690** | **5/5** |

Fresh tokens = `input + output + cache_creation` (실제 모델이 처음 처리한 토큰). 모델 간 부하 공정 비교 지표. Caching 효과는 아래 §🔍에서 별도 논의.

## 🏆 Sisyphus + qwen3-coder-plus = 절대 최고

baseline (Vanilla + qwen3.6-plus) 대비:
- Wall-clock: **5.5× 빠름**
- Fresh tokens: **20.5× 적음** (95% 절감)
- 실제 과금은 caching 할인으로 Fresh보다 더 낮음 (자세한 건 §🔍)

## 🔍 Prompt Caching 발견

**같은 DashScope 엔드포인트인데 모델별로 caching 동작이 다름**:

| | qwen3.6-plus | qwen3-coder-plus |
|---|---|---|
| cache_read 비중 | 0% (전혀 안 작동) | 87-93% |
| 원인 추정 | thinking 모드 때문 | thinking 없음 → caching 정상 작동 |
| 효과 | 매 iter input 전액 과금 | 2번째 iter부터 90% 할인 |

이 차이가 **"같은 태스크 토큰 20× 차이"** 의 주 원인. Sisyphus가 토큰 절감한 것처럼 보이지만, 실은 **qwen3-coder-plus의 caching이 더 많이 기여**.

## 직교성 검증

| 변화 | Wall-clock 효과 |
|---|---|
| 모델만 변경 (V → V) | 49% 단축 |
| Orchestration만 추가 (3.6 V → 3.6 S) | 64% 단축 |
| 둘 다 결합 (3.6 V → coder S) | **82% 단축 (5.5×)** |

두 전략이 **상호 간섭 없이 곱해짐** → orchestration과 모델 선택은 독립적 레버.

## qwen3-coder-plus 특성

| 특성 | qwen3.6-plus | qwen3-coder-plus |
|---|---|---|
| Thinking 단계 | 있음 (길게) | 없음 (직접 답변) |
| H1 wall-clock | 120.7s | 47.4s (2.5× 빠름) |
| H1 정답 | 28/28 (Order.java 내부 포함) | 24/28 (외부 caller만) |
| 답변 스타일 | 설명적, 때로는 self-verification | 간결, 결정론적 |
| 탐색 스타일 | 광범위 | 실용적 |

**실무 리팩터링 관점에선 coder-plus의 "외부 caller만 보고" 해석이 더 실용적**.

## 중요한 caveat — 품질 차이는 여전히 없음

- 4개 조합 모두 5/5 goal (탐색형 태스크)
- Orchestration의 "품질 이점" 주장 여전히 **미검증**
- → v5에서 실행 검증 태스크로 해결

## 참조
- [[Sisyphus 벤치마크 전체 여정]]
- [[v3-fair 공정 조건]] — 비교 기준
- [[v5 실행 검증]] — 품질 차이 드디어 입증
- `bench-v3/results/final-4way-report.md`
