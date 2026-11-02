# 관측 저장소의 인덱스와 압축 알고리즘

> **함께 보기**: [인터랙티브 시뮬레이터 (Artifact)](https://claude.ai/artifact/Foqt3GWDvEG6HBf56corwF) · 로컬 파일 [index-compression-algorithms.html](index-compression-algorithms.html) · [저장 엔진: B-tree, LSM, MergeTree](README.md)
>
> **연결 주차**: W2 ClickHouse/VictoriaLogs 저장 구조, W3 TSDB 압축
>
> **출처**: Bloom, "Space/Time Trade-offs in Hash Coding with Allowable Errors" (1970) · Kirsch & Mitzenmacher, "Less Hashing, Same Performance" (2006) · Pelkonen et al., "Gorilla: A Fast, Scalable, In-Memory Time Series Database" (VLDB 2015) · [ClickHouse — Primary indexes](https://clickhouse.com/docs/guides/best-practices/sparse-primary-indexes) · [ClickHouse — Skip indexes](https://clickhouse.com/docs/optimize/skipping-indexes) · [ClickHouse — Text indexes](https://clickhouse.com/docs/engines/table-engines/mergetree-family/textindexes) · [VictoriaLogs FAQ](https://docs.victoriametrics.com/victorialogs/faq/)

---

## 0. 네 알고리즘이 맡는 일

저장소가 쿼리를 빨리 처리하는 방법은 결국 **덜 읽는 것**이고, 디스크를 아끼는 방법은 **덜 쓰는 것**이다.

| 알고리즘 | 하는 일 | 답의 형태 | 대표 사용처 |
|---|---|---|---|
| **Bloom filter** | 블록을 건너뛴다 | "확실히 없음" / "있을 수도" | VictoriaLogs, ClickHouse `bloom_filter`, RocksDB |
| **Sparse primary index** | 읽을 범위를 좁힌다 | "이 granule 사이에 있다" | ClickHouse `primary.idx` |
| **역인덱스** | 위치를 바로 찾는다 | "이 행들에 있다" | ClickHouse text index, Elasticsearch |
| **Gorilla 압축** | 저장 크기를 줄인다 | 샘플당 ~1.4바이트 | Prometheus, ClickHouse codec |

---

## 1. Bloom filter

### 동작
- 크기 m인 비트 배열과 해시 함수 k개를 쓴다. 처음엔 전부 0이다.
- **넣기**: 값을 해시 k개로 돌려 나온 위치 k개를 1로 켠다. 원래 값은 저장하지 않는다.
- **확인**: 같은 위치 k개를 본다.
  - 하나라도 0 → **확실히 없음.** (넣었다면 1이었을 것이므로)
  - 모두 1 → **있을 수도.** 다른 값들이 켠 비트와 우연히 겹쳤을 수 있다 (false positive).

```
m = 16, k = 3

넣기 "error"   → 위치 2, 7, 13 을 1로
넣기 "GET"     → 위치 4, 7, 11 을 1로
                 0 0 1 0 1 0 0 1 0 0 0 1 0 1 0 0
확인 "timeout" → 위치 2, 9, 13 → 9가 0 → 확실히 없음
확인 "panic"   → 위치 4, 11, 13 → 모두 1 → 있을 수도 (실제론 없음 = 오탐)
```

### 수식

| 항목 | 식 | 의미 |
|---|---|---|
| false positive 확률 | p ≈ (1 − e^(−kn/m))^k | n = 넣은 값 개수 |
| 최적 해시 개수 | k = (m/n) · ln 2 | 이때 비트의 절반이 1 |
| 필요한 비트 | m/n ≈ −1.44 · log₂ p | p = 1%면 원소당 약 9.6비트 |

원소당 10비트면 오탐이 약 1%, 20비트면 약 0.01%다. **값의 길이와 상관없이** 크기가 정해진다.

### 해시 k개 만들기
해시를 k번 따로 계산하지 않고, 두 해시로 `gᵢ(x) = h₁(x) + i · h₂(x) mod m`을 만든다 (Kirsch–Mitzenmacher, 2006). 오탐률은 거의 같고 계산은 두 번이면 된다.

### 왜 관측 저장소에 맞나
- 블록·part는 **불변**이다. bloom filter는 원소를 지울 수 없지만, 블록을 만들 때 한 번 만들면 끝이라 문제가 없다.
- "없음"은 절대 틀리지 않는다. 그래서 **읽지 않아도 되는 블록을 거르는 용도**로 안전하다.
- 로그 검색은 대부분 "이 단어가 있는 줄"을 찾는다. 드문 단어(trace_id, 에러 코드)일수록 대부분의 블록이 "없음"으로 걸러진다.

### 사용처별 차이
- **VictoriaLogs**: 블록마다 필드별 토큰 bloom filter를 둔다. 블록 헤더의 시간 범위로 먼저 거르고, bloom filter로 한 번 더 거른 뒤 남은 블록만 읽는다.
- **ClickHouse**: `bloom_filter` skip index는 granule 묶음마다 값의 bloom filter를 둔다. 토큰 단위인 `tokenbf_v1` · `ngrambf_v1`은 deprecated이고 text index로 대체되었다.
- **RocksDB**: SSTable마다 키 bloom filter를 두어 점 조회(GET) 시 파일을 건너뛴다.

---

## 2. Sparse primary index (ClickHouse)

### 구조
- part의 행은 `ORDER BY` 키 순서로 **정렬**되어 있다.
- 행을 **granule** 단위로 묶는다. 기본 `index_granularity = 8192`행.
- `primary.idx`에는 **각 granule 첫 행의 키**만 저장한다. 행마다 항목을 두는 B-tree와 다르다.
- 컬럼마다 **mark 파일**이 있다. mark = (압축 블록이 시작하는 파일 오프셋, 압축 해제한 블록 안의 오프셋). granule 번호를 실제 파일 위치로 바꿔 준다.

```
ORDER BY (service, ts)

primary.idx       mark 0      mark 1      mark 2      mark 3
                  api 10:01   api 10:25   auth 10:03  cart 10:07 ...
                     │           │           │           │
granule           [0: 8192행] [1: 8192행] [2: 8192행] [3: 8192행] ...
```

### 조회 과정
`WHERE service = 'checkout'`이면:
1. `primary.idx`(메모리에 상주)를 **이진 탐색**한다.
   - 시작: 첫 키가 `'checkout'` 이상인 mark의 바로 앞 granule. 앞 granule 뒤쪽에 `'checkout'`이 있을 수 있어서 포함한다.
   - 끝: 첫 키가 `'checkout'`보다 큰 첫 mark.
2. 범위 안의 granule 번호를 mark 파일로 컬럼 파일 위치로 바꾼다.
3. **필요한 컬럼의 필요한 granule만** 읽고 압축을 푼 뒤 조건을 다시 확인한다.

### 왜 효율적인가
- 1억 행 part도 인덱스 항목은 약 12,200개다. 메모리에 전부 올릴 수 있다.
- 결과가 granule 단위라 조금 더 읽지만, 그 읽기는 **연속된 순차 읽기**다.
- 인덱스가 작으니 INSERT 때 만드는 비용도 작다.

### 한계와 보완
- 정렬 키의 **앞쪽 컬럼**일수록 잘 걸러진다. `ORDER BY (service, ts)`에서 `ts`만으로 조회하면 service마다 흩어져 있어서 효과가 떨어진다.
- 정렬 키에 없는 컬럼(`status`)은 granule을 전부 읽는다. **skip index**로 보완한다.

| skip index | granule 묶음마다 저장하는 것 | 잘 맞는 경우 |
|---|---|---|
| `minmax` | 최솟값 · 최댓값 | 값이 특정 구간에 몰려 있을 때 (시간, 증가하는 ID) |
| `set(N)` | 서로 다른 값 최대 N개 | 묶음 안의 값 종류가 적을 때 |
| `bloom_filter` | 값의 bloom filter | 고유 값이 많은 컬럼의 같다 비교 (trace_id) |
| `text` | 토큰 역인덱스 | 로그 본문 전문 검색 |

skip index는 **데이터가 정렬 키와 상관관계가 있을 때만** 효과가 있다. 에러가 모든 granule에 고르게 퍼져 있으면 minmax는 아무것도 걸러내지 못한다.

---

## 3. 역인덱스 (Inverted index)

### 구조
- **토크나이저**로 텍스트를 토큰으로 자른다. 예: 영문자·숫자가 아닌 문자로 나누기.
- **사전(dictionary)**: 정렬된 토큰 목록.
- **posting list**: 토큰마다 그 토큰이 나온 행 번호의 정렬된 목록.

```
0  db timeout on checkout
1  POST /checkout 500 db error
2  db connection timeout retry

사전          posting list
checkout   →  [0, 1]
db         →  [0, 1, 2]
timeout    →  [0, 2]
...
```

### 검색
- `hasAllTokens(message, ['db', 'timeout'])` → `[0,1,2] ∩ [0,2]` = `[0, 2]`
- `hasAnyTokens(message, ['error', 'retry'])` → `[1] ∪ [2]` = `[1, 2]`

정렬된 목록 두 개는 포인터 두 개로 동시에 훑으면 O(a+b)에 교집합이 나온다.

### 왜 효율적인가
- 검색 비용이 **전체 로그 양이 아니라 posting list 길이**에 비례한다.
- posting list는 정렬된 정수라 **차이값 + 비트 패킹**이나 **Roaring bitmap**으로 작게 압축된다.
- 로그 본문을 한 줄도 훑지 않고 행 번호를 얻는다.

### Bloom filter와 비교

| | 블록별 token bloom filter | 역인덱스 |
|---|---|---|
| 답 | "이 블록엔 없다" | "이 행들에 있다" |
| 이후 작업 | "있을 수도"인 블록을 읽고 행마다 비교 | 해당 행만 읽음 |
| 인덱스 크기 | 작음 (원소당 ~10비트) | 큼 (토큰 사전 + 행 목록) |
| 흔한 토큰 (`GET`, `200`) | 거의 모든 블록이 "있을 수도" → 효과 없음 | posting list가 길어짐 |
| 드문 토큰 (trace_id) | 잘 걸러짐 | 아주 빠름 |
| 사용처 | VictoriaLogs, ClickHouse `tokenbf_v1`(deprecated) | ClickHouse text index (26.2 GA), Elasticsearch |

시뮬레이터의 "같은 검색을 bloom filter로"를 누르면 이 차이가 보인다. 한 블록 안의 **서로 다른 행**에 `db`와 `timeout`이 나뉘어 있으면 bloom filter는 "있을 수도"라고 답하고, 블록을 읽어 봐야 없다는 걸 안다.

### 토크나이저가 결과를 정한다
- `user_42`를 `user`, `42`로 나누면 `42`로도 검색되지만, `user_42` 한 덩어리로 검색하면 토큰 두 개의 AND로 바뀐다.
- 검색어도 **같은 토크나이저**로 잘라야 한다.
- 구문(phrase) 검색은 순서 정보가 필요하다. ClickHouse text index에서는 아직 실험 기능이다.

---

## 4. Gorilla 압축

Facebook이 2015년 발표한 인메모리 TSDB 논문의 방식이다. 시계열 샘플은 원래 **타임스탬프 64비트 + float64 값 64비트 = 128비트(16바이트)**다.

### 타임스탬프: delta-of-delta
수집 간격은 거의 일정하다. 그래서 간격(Δ)의 변화(ΔΔ)는 거의 항상 0이다.

```
t    1000  1015  1030  1045  1061  1075
Δ          15    15    15    16    14
ΔΔ               0     0     +1    −2
```

| ΔΔ 범위 | 저장 | 비트 |
|---|---|---|
| 0 | `0` | 1 |
| [−63, 64] | `10` + 7비트 | 9 |
| [−255, 256] | `110` + 9비트 | 12 |
| [−2047, 2048] | `1110` + 12비트 | 16 |
| 그 밖 | `1111` + 32비트 | 36 |

블록 시작 타임스탬프는 원본, 첫 Δ는 14비트로 저장한다. 논문 데이터에서 타임스탬프의 약 96%가 1비트였다.

Prometheus는 **밀리초** 타임스탬프를 쓰고 수집 지연이 ms 단위로 흔들리므로 구간을 14 · 17 · 20비트로 넓혀 쓴다.

### 값: 이전 값과 XOR
천천히 변하는 float64는 부호·지수·가수 앞부분이 이전 값과 같다. XOR하면 같은 비트는 0이 되어 **앞뒤로 0이 길게 붙은 결과**가 나온다.

```
12.5   = 0 10000000010 1001000000000000...0
12.75  = 0 10000000010 1001100000000000...0
XOR    = 0 00000000000 0000100000000000...0
         └ 앞쪽 0: 16개 ┘│└─ 뒤쪽 0: 47개 ─┘
                         의미 있는 비트 1개
```

| 경우 | 저장 | 비트 |
|---|---|---|
| XOR = 0 (같은 값) | `0` | 1 |
| 의미 있는 비트가 이전 범위 안에 들어감 | `10` + 이전 범위 길이만큼 | 2 + n |
| 새 범위 | `11` + 앞쪽 0 개수(5비트) + 길이(6비트) + 의미 있는 비트 | 13 + n |

이전 범위를 재사용하면 범위 정보(11비트)를 다시 적지 않아도 된다. 논문 데이터에서 값의 약 51%가 1비트(같은 값)였다.

### 결과
- 논문 데이터에서 평균 **1.37바이트/샘플** (원래 16바이트, 약 12배).
- 압축이 잘 되는 경우: 수집 간격이 일정함, 값이 그대로이거나 천천히 변함, 정수형 카운터.
- 안 되는 경우: 소수점 아래가 무작위로 바뀌는 값. XOR에 의미 있는 비트가 50개 넘게 남는다. 시뮬레이터의 "랜덤 소수"로 확인할 수 있다.

### 다른 구현
| 시스템 | 방식 |
|---|---|
| **Prometheus** | Gorilla 방식의 XOR chunk. 시리즈당 약 120샘플 단위 chunk. 샘플당 약 1.3바이트 수준 |
| **ClickHouse** | 컬럼 codec으로 고른다. `CODEC(DoubleDelta)`는 타임스탬프, `CODEC(Gorilla)`는 float 값, 뒤에 `ZSTD`/`LZ4`를 이어 붙일 수 있다 |
| **VictoriaMetrics** | float를 소수 자릿수를 맞춘 정수로 바꾼 뒤 delta 계열 인코딩과 zstd로 압축한다. Gorilla보다 작게 나온다고 주장한다 (W3에서 다룸) |

---

## 5. 같이 쓰일 때

로그 조회 하나가 지나가는 경로로 보면 네 가지가 차례로 쓰인다.

```
SELECT ... WHERE service = 'checkout' AND ts > now() - 1h AND hasAllTokens(body, ['timeout'])

1. 파티션 / part 선택      시간 범위로 part를 고름 (part의 min/max)
2. sparse primary index    service, ts로 granule 범위를 좁힘
3. skip index              bloom filter 또는 text index로 granule을 더 거름
4. 컬럼 읽기 + 압축 해제    필요한 컬럼의 필요한 granule만, codec(Delta/Gorilla/ZSTD)을 풀어서
5. 조건 재확인              실제 값으로 최종 필터
```

VictoriaLogs도 같은 순서다. 시간 범위 → stream → 블록 헤더 → bloom filter → 필드 컬럼 읽기.

---

## 6. 확인 질문

1. bloom filter에서 m = 1000비트, n = 100개일 때 최적 k와 대략의 오탐률은?
2. bloom filter의 "있을 수도"는 왜 블록을 읽어야만 확인할 수 있나? "없음"은 왜 틀리지 않나?
3. VictoriaLogs에서 `GET` 같은 흔한 단어 검색이 bloom filter로 빨라지지 않는 이유는?
4. ClickHouse primary index가 행마다 항목을 두지 않아도 되는 전제 조건은?
5. `ORDER BY (service, ts)` 테이블에서 `WHERE ts > ...`만 걸면 primary index가 잘 동작하나?
6. minmax skip index가 아무 효과가 없는 데이터 분포는?
7. text index(역인덱스)가 bloom filter보다 나은 경우와 비용이 더 큰 경우를 하나씩 들면?
8. Gorilla에서 수집 간격이 15초로 일정하고 값이 변하지 않으면 샘플당 몇 비트가 드나?
9. 소수점 아래가 무작위인 값은 왜 XOR 압축이 거의 안 되나? 어떻게 개선할 수 있나?
10. Prometheus가 Gorilla 논문과 다른 타임스탬프 비트 구간을 쓰는 이유는?
