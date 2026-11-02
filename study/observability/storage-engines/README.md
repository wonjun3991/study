# 저장 엔진: B-tree, LSM-tree, ClickHouse MergeTree

> **함께 보기**: [인터랙티브 시뮬레이터 (Artifact)](https://claude.ai/artifact/7VwAWp4jrH9xULwU5HETks) · 로컬 파일 [lsm-btree-animation.html](lsm-btree-animation.html) · [인덱스와 압축 알고리즘](index-compression-algorithms.md)
>
> **연결 주차**: W2 ClickHouse/VictoriaLogs 저장 구조, W3 Prometheus TSDB · VictoriaMetrics
>
> **출처**: *Designing Data-Intensive Applications* 3장 · O'Neil et al., "The Log-Structured Merge-Tree" (1996) · [RocksDB Wiki — Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction) · [ClickHouse — MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree) · [ClickHouse — Primary indexes](https://clickhouse.com/docs/guides/best-practices/sparse-primary-indexes)

---

## 1. 무엇을 비교하나

두 계열은 **디스크에 쓰는 방식**이 다르다.

| | B-tree 계열 | LSM 계열 |
|---|---|---|
| 기본 전략 | 데이터가 있어야 할 페이지를 찾아 **그 자리에서 고친다** | 새 데이터를 **새 파일로 쓰고**, 나중에 합친다 |
| 디스크 I/O | 랜덤 쓰기 | 순차 쓰기 |
| 강점 | 읽기가 빠르고 예측 가능 | 쓰기 처리량이 높음 |
| 대가 | 작은 변경에도 페이지 전체를 씀 | 읽을 때 여러 파일 확인, 배경 병합 비용 |

관측 데이터(로그, 트레이스, 메트릭)는 **쓰기가 압도적으로 많고, 수정은 거의 없고, 시간 순으로 쌓인다.** 그래서 ClickHouse, VictoriaLogs, Prometheus TSDB 모두 LSM 쪽 구조를 쓴다.

---

## 2. B-tree (B+tree)

### 구조
- 디스크를 **고정 크기 페이지**로 나눈다. InnoDB는 16KB, PostgreSQL은 8KB.
- 내부 노드는 키 범위와 자식 페이지 포인터만 가진다. 실제 값은 **리프**에 있다 (B+tree).
- 한 페이지에 자식 포인터가 수백 개 들어간다(fanout). fanout 500, 높이 4면 약 500⁴ = 625억 개 키를 다룬다.
- 리프끼리 연결 리스트로 이어져 있어 **범위 스캔**은 리프를 옆으로 따라가면 된다.

```
            [ 30 ]                 ← 루트
          /        \
     [ 10 20 ]    [ 40 50 ]        ← 내부 노드
     /   |   \     /  |   \
   [5] [10,15] [20,25] ...         ← 리프 (→ 옆 리프로 연결)
```

### 검색
루트에서 시작해 키 범위를 비교하며 자식으로 내려간다. **읽는 페이지 수 = 트리 높이.** 데이터가 늘어도 높이는 log_fanout(N)으로 아주 천천히 커진다.

### 삽입
1. 루트에서 리프까지 내려가 넣을 리프를 찾는다.
2. 리프에 키를 정렬된 위치로 넣고, **그 페이지를 디스크의 원래 자리에 다시 쓴다.**
3. 페이지가 넘치면 **분할(split)**: 두 페이지로 나누고 가운데 키를 부모에 올린다. 부모도 넘치면 위로 반복한다.
4. 루트가 분할되면 새 루트가 생기고 높이가 1 늘어난다. B-tree는 **위로 자란다.**

### 갱신 · 삭제
같은 페이지를 찾아가서 직접 고친다. 삭제로 페이지가 너무 비면 형제와 합치거나 키를 재분배한다.

### 안전장치
페이지를 덮어쓰다가 중간에 죽으면 페이지가 깨진다. 그래서 B-tree DB도 **WAL(redo log)**을 먼저 쓴다. 다만 WAL은 복구용이고, 최종 데이터는 결국 페이지 제자리 갱신으로 반영된다.

### 비용
- **쓰기 증폭**: 100바이트 행 하나를 바꿔도 16KB 페이지를 쓴다. 분할이 나면 여러 페이지를 쓴다.
- **랜덤 I/O**: 키가 흩어져 있으면 쓰는 페이지도 디스크 곳곳에 흩어진다.
- **단편화**: 분할 후 페이지가 절반만 차 있는 경우가 많아 공간이 남는다.

---

## 3. LSM-tree (Log-Structured Merge-tree)

### 구성 요소

| 요소 | 위치 | 역할 |
|---|---|---|
| **WAL** | 디스크 | 쓰기 요청을 파일 끝에 append. 장애 시 memtable 복구용 |
| **memtable** | 메모리 | 최근 쓰기를 정렬된 상태로 보관 (skip list, red-black tree 등) |
| **SSTable** | 디스크 | memtable을 flush한 **정렬된 불변 파일**. 키 범위, sparse index, bloom filter를 함께 가짐 |
| **레벨 (L0, L1, …)** | 디스크 | SSTable을 계층으로 관리. 아래로 갈수록 크다 |

### 쓰기 경로
1. WAL 끝에 append (순차 쓰기).
2. memtable에 삽입. **여기서 쓰기가 끝난다.** 디스크의 데이터 파일은 건드리지 않는다.
3. memtable이 차면 정렬된 SSTable 하나로 **flush** (큰 순차 쓰기 한 번). 해당 WAL은 버린다.
4. 파일이 쌓이면 **compaction**: 여러 파일을 병합 정렬해 새 파일로 쓰고 옛 파일을 지운다.

### 갱신 · 삭제
- 갱신: 같은 키의 **새 버전**을 그냥 쓴다. 옛 버전은 아래 레벨에 남아 있다가 compaction에서 사라진다.
- 삭제: **tombstone**(삭제 표시)을 쓴다. compaction이 가장 아래 레벨까지 tombstone을 가져가야 실제로 지워진다.

### 읽기 경로
최신 데이터가 위에 있으므로 **위에서 아래로** 찾고, 찾으면 멈춘다.

```
GET k
 → memtable            (메모리, 있으면 끝)
 → L0 파일들 (최신순)   L0는 파일끼리 키 범위가 겹친다 → 여러 개 확인
 → L1                  범위가 안 겹친다 → 파일 최대 1개
 → L2 ...
```

파일마다 확인 비용을 줄이는 장치가 두 가지다.
- **키 범위(fence)**: 파일의 min/max 밖이면 열지 않는다.
- **bloom filter**: "확실히 없음"이면 열지 않는다. "있을 수도"일 때만 읽는다. 10비트/키면 false positive 약 1%.

### Compaction 전략

| 전략 | 방식 | 장점 | 단점 | 예 |
|---|---|---|---|---|
| **Leveled** | 레벨마다 크기 한도(보통 10배씩). 넘치면 아래 레벨의 겹치는 파일과 병합 | 읽기·공간 효율 좋음 | 같은 데이터를 레벨마다 다시 써서 쓰기 증폭 큼 | RocksDB 기본, LevelDB |
| **Size-tiered** | 비슷한 크기 파일 N개가 모이면 하나로 병합 | 쓰기 증폭 작음 | 같은 키가 여러 파일에 → 읽기·공간 비용 큼 | Cassandra STCS |

RocksDB는 L0 파일이 4개(`level0_file_num_compaction_trigger` 기본값)가 되면 L1으로 compaction을 시작한다.

### 세 가지 증폭
LSM 튜닝은 이 셋의 균형이다. 하나를 줄이면 다른 하나가 는다.

| 증폭 | 의미 | 원인 |
|---|---|---|
| **쓰기 증폭** | 실제 디스크에 쓴 양 ÷ 사용자가 쓴 양 | compaction이 같은 데이터를 여러 번 다시 씀 |
| **읽기 증폭** | 조회 1번에 읽는 파일·블록 수 | 여러 레벨·파일 확인 |
| **공간 증폭** | 실제 디스크 사용량 ÷ 살아 있는 데이터 양 | 옛 버전·tombstone이 병합 전까지 남음 |

### 왜 쓰기에 유리한가
- 사용자 쓰기는 메모리 + append로 끝나서 지연이 짧다.
- 디스크에는 큰 덩어리를 순차로 쓴다. HDD는 탐색 시간이 없어지고, SSD도 큰 순차 쓰기가 더 효율적이다.
- 파일이 **정렬되어 있고 불변**이라 압축이 잘 되고, 동시성 제어가 단순하다.

---

## 4. ClickHouse MergeTree

이름에 "Merge"가 들어가지만 교과서적인 LSM-tree와는 다르다. **불변 파일 + 배경 병합**이라는 핵심만 같다.

### 쓰기
- **memtable과 WAL이 없다.** INSERT 한 번이 곧 디스크의 **part** 하나다.
- part 안의 데이터는 `ORDER BY` 키로 정렬되어 컬럼별 파일로 저장된다.
- 그래서 작은 INSERT를 자주 하면 part가 폭증한다. 배치로 묶거나 `async_insert`로 서버에서 모아야 한다. 파티션당 활성 part 수가 `parts_to_throw_insert`를 넘으면 `Too many parts` 에러가 난다.

### part 이름
`<partition>_<최소 블록>_<최대 블록>_<level>` 형식이다.

```
all_1_1_0   ← 1번째 INSERT, 아직 병합 안 됨 (level 0)
all_2_2_0
all_3_3_0
  ↓ merge
all_1_3_1   ← 블록 1~3을 합친 part, level 1
```

병합은 **블록 번호가 이어지는 인접 part끼리**만 한다. 어떤 part를 합칠지는 크기 기반 휴리스틱으로 고른다. LSM처럼 고정된 레벨 계층이 있는 게 아니고, level은 "몇 번 합쳐졌는가"를 나타낸다.

### 읽기
- 모든 활성 part가 대상이다. LSM처럼 "최신 값을 찾으면 멈춤"이 없다. 분석 쿼리는 원래 여러 행을 모아 집계하기 때문이다.
- part마다 **sparse primary index**(granule 8192행마다 키 하나)로 읽을 granule을 고르고, skip index(minmax, set, bloom_filter, text)로 더 거른다.
- part 수가 많을수록 쿼리가 열어야 할 파일이 늘어난다. 배경 merge가 이 수를 줄인다.

### 갱신 · 중복
- 기본 MergeTree는 **merge할 때 아무것도 지우지 않는다.** 같은 키의 행이 그대로 남는다.
- 병합 시 특별한 처리를 하는 엔진이 따로 있다.

| 엔진 | merge 시 동작 |
|---|---|
| `ReplacingMergeTree` | 같은 정렬 키의 행 중 최신(또는 version 컬럼 최대)만 남김 |
| `CollapsingMergeTree` | sign +1/-1 쌍을 상쇄 |
| `AggregatingMergeTree` | 집계 상태를 합침 |
| `SummingMergeTree` | 숫자 컬럼을 합산 |

- merge는 언제 끝날지 보장되지 않는다. 조회 시점에 중복이 없어야 하면 `FINAL`을 붙인다 (비용이 든다).
- `ALTER TABLE ... UPDATE/DELETE`(mutation)는 영향받는 part를 **통째로 다시 쓴다.** 비싼 작업이다.

### LSM-tree와 비교

| | LSM-tree (RocksDB) | ClickHouse MergeTree |
|---|---|---|
| 메모리 버퍼 | memtable | 없음 (`async_insert`·Buffer 엔진으로 보완) |
| WAL | 있음 | 없음 (INSERT가 part를 쓰고 나서 응답) |
| 파일 단위 | SSTable (키-값 행) | part (컬럼별 파일 + primary.idx + marks) |
| 계층 | 고정 레벨 L0~Ln | 인접 part 병합, level은 병합 횟수 |
| 같은 키 처리 | 최신 버전만 남김 | 기본은 남김, 엔진에 따라 처리 |
| 읽기 | 위→아래, 찾으면 멈춤 | 모든 part 조회 후 합침 |
| 목적 | 키 단위 조회·갱신 (OLTP 성격) | 대량 스캔·집계 (OLAP) |

---

## 5. 관측 저장소와의 연결

| 시스템 | 구조 | 대응 |
|---|---|---|
| **ClickHouse** (로그·트레이스) | MergeTree | 4장 |
| **VictoriaLogs** | 스트림별로 데이터를 블록에 쓰고 배경에서 병합. 필드별 컬럼 + bloom filter | MergeTree와 비슷한 part 병합 구조 |
| **Prometheus TSDB** (W3) | WAL + head block(메모리, 최근 2시간) → 불변 block으로 flush → block끼리 compaction | memtable·WAL·flush·compaction이 그대로 대응되는 LSM 구조 |
| **VictoriaMetrics** (W3) | 데이터와 인덱스를 part로 쓰고 배경에서 병합 | MergeTree에서 영향을 받은 구조 |

공통점은 셋이다.
1. 쓰기는 **불변 파일을 새로 만드는 것**으로 처리한다.
2. 파일 안은 **정렬**되어 있어서 sparse index와 압축이 잘 먹힌다.
3. 파일이 늘어나는 문제는 **배경 병합**이 해결한다.

---

## 6. 시뮬레이터에서 확인할 것

[시뮬레이터](https://claude.ai/artifact/7VwAWp4jrH9xULwU5HETks)에서 아래를 직접 확인해 본다.

- B+tree에서 키를 계속 넣어 루트 분할이 일어나는 순간과 트리 높이 변화.
- B+tree 검색의 "페이지 읽기 수"가 항상 트리 높이와 같다는 것.
- LSM에서 PUT 4번 동안 디스크 파일이 그대로이다가 flush로 한 번에 생기는 것.
- 같은 키를 두 번 PUT했을 때 `v2`가 생기고, compaction 후 옛 버전이 사라지는 것.
- LSM 쓰기 증폭 숫자가 compaction이 반복될수록 1보다 커지는 것.
- LSM GET에서 bloom filter와 키 범위로 건너뛴 파일 수.
- MergeTree 모드에서 `all_1_3_1` 같은 part 이름이 생기는 규칙, 중복 키가 merge 후에도 남는 것, SELECT가 찾은 뒤에도 모든 part를 확인하는 것.

---

## 7. 확인 질문

1. B+tree에서 높이가 4일 때 키 하나를 검색하려면 페이지를 몇 개 읽나? 범위 스캔은 어떻게 하나?
2. B-tree DB도 WAL을 쓰는데, LSM의 WAL과 역할이 어떻게 다른가?
3. LSM의 L0는 파일끼리 키 범위가 겹치는데 L1부터는 왜 안 겹치나? 읽기에 어떤 차이가 생기나?
4. Leveled compaction과 size-tiered compaction은 쓰기·읽기·공간 증폭 중 무엇을 맞바꾸나?
5. LSM에서 삭제가 즉시 공간을 돌려주지 않는 이유는?
6. ClickHouse MergeTree에 작은 INSERT를 초당 수백 번 보내면 무슨 일이 생기나? 해결책 두 가지는?
7. `ReplacingMergeTree`를 써도 조회 결과에 중복이 보일 수 있는 이유는?
8. Prometheus TSDB의 head block, WAL, block compaction을 LSM 용어로 바꿔 말하면?
