---
tags: [kubernetes, ch06, volumes, storage, aws]
---

# Chapter 6: Volumes — attaching disk storage to containers

> 컨테이너는 기본적으로 휘발성. 재시작/재스케줄되면 `/var/lib/...`의 데이터는 증발함.
> → "어떻게 데이터를 유지할 것인가?" 를 푸는 장(章).

## 핵심 한 줄 요약

**Volume은 Pod에 붙고, PersistentVolume은 클러스터에 붙는다.**
개발자는 PVC로 "얼마나 필요해"만 말하고, 실제 스토리지(EBS/EFS/…)는 인프라가 알아서 붙여준다.

---

## 1. 레이어 구조

ch06은 스토리지 추상화를 4개 레이어로 점진적으로 소개함:

```
[Pod Spec] ─ volumes[] ──┐
                         │
          ┌──────────────┴──────────────┐
          │                             │
    (직접 연결)                    (간접 연결)
    emptyDir                       PersistentVolumeClaim
    hostPath                             │
    gitRepo                              ▼
    nfs                            PersistentVolume
    awsEBS / gcePD / azureDisk          │
                                         ▼
                                   StorageClass (동적 프로비저닝)
```

**왜 레이어가 늘어나냐**: 개발자(앱 담당)와 운영자(인프라 담당)의 관심사 분리.

---

## 2. Pod 내부 볼륨 (휘발성 또는 로컬)

### 2.1 emptyDir — 같은 Pod 내 컨테이너 간 공유

- Pod 생성 시 빈 디렉토리, Pod 삭제 시 사라짐
- 용도: **사이드카 패턴** (fortune 예제: html-generator가 파일 쓰고 nginx가 서빙)

```yaml
volumes:
- name: html
  emptyDir: {}              # 노드의 기본 디스크
  # emptyDir: { medium: Memory }  # tmpfs(RAM)
```

### 2.2 gitRepo — deprecated

- Pod 시작 시 git clone, 이후 갱신 안됨
- 책에 나오지만 현재는 init container + git 조합을 권장

### 2.3 hostPath — 노드의 파일시스템

- **위험**: Pod이 어느 노드에 뜨느냐에 따라 다른 데이터를 봄
- 용도는 시스템 Pod(로그 수집기 등)만. 앱에 쓰면 안됨.

---

## 3. Pod에 직접 붙이는 네트워크 스토리지 (구식 패턴)

책에서 소개는 하지만 **지금은 거의 안 씀**. PV/PVC로 추상화하는 게 현대적.

| 볼륨 타입 | 클라우드 | 비고 |
|-----------|----------|------|
| `gcePersistentDisk` | GCP | GCE Persistent Disk |
| `awsElasticBlockStore` | **AWS** | **EBS 볼륨** |
| `azureDisk` | Azure | - |
| `nfs` | 온프렘 | NFS 서버 |

### ⚠️ 현재 상태 (2020+)

이 in-tree 볼륨 타입들은 **CSI(Container Storage Interface)로 마이그레이션됨**.

- `awsElasticBlockStore` (in-tree) → `ebs.csi.aws.com` (CSI driver)
- k8s 1.27+ 부터 in-tree AWS 플러그인은 제거됨
- 실전에서는 무조건 CSI + StorageClass 조합 사용

---

## 4. PersistentVolume + PersistentVolumeClaim (핵심 패턴)

```
[Admin]                    [Developer]
   │                           │
   ▼                           ▼
┌──────┐  bind  ┌───────┐  uses  ┌─────┐
│  PV  │ ◄───── │  PVC  │ ◄───── │ Pod │
└──────┘        └───────┘        └─────┘
   ▲
   │
실제 스토리지
(EBS / EFS / NFS / …)
```

### 4.1 관심사 분리

| 역할 | 작성하는 리소스 | 신경 쓰는 것 |
|------|----------------|-------------|
| 클러스터 관리자 | **PersistentVolume** | EBS 볼륨 ID, 용량, 접근 모드, 재사용 정책 |
| 앱 개발자 | **PersistentVolumeClaim** | "1Gi가 필요함. RWO 모드로." |
| k8s | 바인딩 | 조건 맞는 PV를 찾아서 PVC에 붙여줌 |

### 4.2 accessModes (면접 단골)

| 모드 | 의미 | AWS 매핑 |
|------|------|---------|
| **ReadWriteOnce (RWO)** | 단일 노드에서 read/write | **EBS** (노드 1개에만 붙음) |
| **ReadOnlyMany (ROX)** | 여러 노드에서 read-only | EFS, S3-CSI |
| **ReadWriteMany (RWX)** | 여러 노드에서 read/write | **EFS**, FSx |
| ReadWriteOncePod | 단일 Pod만 접근 (신규) | 모든 스토리지 |

⚠️ **EBS는 RWO만 됨** — 한 AZ, 한 노드에만 붙는 블록 디바이스.
여러 Pod에서 동시에 쓰려면 **EFS(NFS 기반)** 필요.

### 4.3 reclaimPolicy

PVC가 삭제되면 PV(와 뒷단 EBS)는 어떻게 될까?

- `Retain` — PV 유지, 수동 정리 (실수 방지, 프로덕션 권장)
- `Delete` — PV와 **실제 EBS 볼륨까지 자동 삭제** (동적 프로비저닝 기본값)
- `Recycle` — deprecated

---

## 5. StorageClass + 동적 프로비저닝 (실전)

**문제**: PV를 사람이 미리 만들어두는 건 귀찮음. PVC마다 EBS 볼륨을 손으로 만들어야 함.

**해결**: StorageClass → PVC가 생성되면 **자동으로 EBS 볼륨을 생성해서 PV를 만들고 붙여줌**.

```yaml
# StorageClass (관리자가 1회 세팅)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: ebs.csi.aws.com   # AWS EBS CSI 드라이버
parameters:
  type: gp3                    # gp3 / io2 / st1 등
  encrypted: "true"
---
# PVC (개발자가 쓸 때마다)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongodb-pvc
spec:
  storageClassName: fast
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 100Gi
```

→ PVC가 applied 되는 순간 AWS에서 **100Gi gp3 EBS 볼륨이 생성**되고, 노드에 attach되고, Pod에 마운트됨. 전부 자동.

---

## 6. 🎯 AWS 매핑 총정리 (질문의 핵심)

### 6.1 스토리지 타입별 매핑

| 책의 개념 | AWS 서비스 | 특징 | 언제 씀 |
|-----------|-----------|------|---------|
| `hostPath` | EC2 인스턴스 로컬 디스크 | 노드 죽으면 데이터 날아감 | ❌ 앱에 쓰지 말기 |
| `emptyDir` | EC2 인스턴스 임시 공간 | Pod 수명 동안만 | 캐시, 사이드카 간 공유 |
| `emptyDir (Memory)` | EC2 RAM (tmpfs) | 속도 빠름, 전원 끄면 소실 | 암호 같은 민감 임시 데이터 |
| `awsElasticBlockStore` / PV | **Amazon EBS** | 블록 스토리지, 단일 AZ, RWO | DB (Postgres, MongoDB, …) |
| `nfs` / CSI | **Amazon EFS** | NFS 기반, RWX, multi-AZ | 공유 파일, 여러 Pod 동시 쓰기 |
| 책엔 없음 | **Amazon FSx** | Windows file share, Lustre | 특수 워크로드 |
| 책엔 없음 | **Amazon S3** (S3 CSI) | 오브젝트 스토리지 | 읽기 중심 데이터 lake |
| 책엔 없음 | **Instance Store** | NVMe 로컬, 초고속, 휘발성 | 캐시, shuffle |

### 6.2 책의 YAML → 실전 AWS YAML

#### 책의 예제 (mongodb-pod-aws.yaml):
```yaml
volumes:
- name: mongodb-data
  awsElasticBlockStore:
    volumeID: my-volume     # 미리 AWS에서 만들어둔 EBS ID
    fsType: ext4
```

이건 구식. 지금은:

#### 현대 AWS EKS 패턴:
```yaml
# 1) StorageClass (관리자가 한 번만)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com          # ← CSI driver
volumeBindingMode: WaitForFirstConsumer  # ← AZ-aware (Pod 뜨는 AZ에 EBS 생성)
parameters:
  type: gp3
  encrypted: "true"
---
# 2) PVC (개발자)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongodb-pvc
spec:
  storageClassName: gp3
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 100Gi
---
# 3) Pod/Deployment (개발자)
volumes:
- name: mongodb-data
  persistentVolumeClaim:
    claimName: mongodb-pvc
```

### 6.3 실전에서 꼭 알아야 할 AWS 특유 이슈

#### 이슈 1: **AZ 제약**
- EBS 볼륨은 **단일 AZ**에만 존재
- Pod이 다른 AZ 노드로 스케줄되면 attach 불가
- 해결: StorageClass에 `volumeBindingMode: WaitForFirstConsumer`
  → Pod이 뜰 AZ를 먼저 정하고, 그 AZ에 EBS 생성

#### 이슈 2: **EBS CSI Driver 설치 필요**
- EKS 클러스터에 기본 포함 안 됨 (1.23+)
- `aws-ebs-csi-driver` 애드온 설치 + IRSA(IAM Role for Service Account)로 권한 연결 필요

#### 이슈 3: **EBS vs EFS 선택 기준**

| 기준 | EBS | EFS |
|------|-----|-----|
| 접근 모드 | RWO | RWX |
| AZ | 단일 | 멀티 |
| 지연 시간 | 낮음 (블록) | 높음 (NFS) |
| 비용 | 저렴 | 비쌈 (3~4x) |
| 용도 | DB, 단일 Pod 상태 | 공유 파일, 여러 Pod |

**DB → EBS, 공유 콘텐츠 → EFS**. 혼동 금물.

#### 이슈 4: **gp2 vs gp3**
- `gp3`가 신규 default. 더 싸고 IOPS 독립 조정 가능
- 신규 StorageClass는 gp3 쓰기

---

## 7. 책 vs 현실 차이점 (놓치기 쉬운 것)

| 책(2018) | 현재(2024+) |
|----------|------------|
| `gcePersistentDisk`, `awsElasticBlockStore` in-tree | **CSI 드라이버**로 마이그레이션 완료 |
| `Recycle` reclaim policy | deprecated |
| `gitRepo` 볼륨 | deprecated, init container 사용 |
| StorageClass 선택적 | **사실상 필수** (동적 프로비저닝) |
| - | `volumeBindingMode: WaitForFirstConsumer` (AZ-aware) |
| - | Volume Snapshot (CSI) |
| - | Volume Expansion (PVC 용량 늘리기) |

---

## 8. 실습 체크리스트

- [x] fortune 컨테이너 이미지 빌드 ([[fortune/Dockerfile|빌드 완료]]) — `luksa/fortune:latest` + `fortune:v1` 태그
- [x] `fortune-pod.yaml` apply → emptyDir 동작 확인 — html-generator가 쓴 파일을 web-server가 서빙
- [ ] `gitrepo-volume-pod.yaml` 실습 (참고만, 현재 비권장)
- [x] `mongodb-pod-hostpath.yaml` → Pod 삭제 후 재생성 → 데이터 유지 확인 (단일 노드 기준)
- [x] `mongodb-pv-hostpath.yaml` + `mongodb-pvc.yaml` + `mongodb-pod-pvc.yaml` → PV/PVC 바인딩 확인
- [x] `kubectl get pv,pvc` → STATUS 컬럼 (Bound, Released) 이해 — Retain reclaimPolicy 동작 확인
- [x] minikube standard/fast StorageClass + PVC로 동적 프로비저닝 확인 — PV 이름 `pvc-<uuid>` 자동 생성, Delete 정책 검증
- [ ] (EKS 있다면) gp3 StorageClass + PVC로 동적 프로비저닝 확인

### 실습 환경 메모 (2026-05-05)

- **minikube 단일 노드**: `--nodes=1 --cpus=4 --memory=4g --driver=docker`
- **Docker Desktop**: CPU 4, Memory 6 GB 이상 필수 (2 GB로는 kicbase 로딩도 불가)
- **멀티노드 minikube의 함정**: 1.928 GiB Docker VM에 4노드 쑤셔 넣으면 apiserver OOM loop. dmesg에서 `Out of memory: Killed process` 로 확인
- **fortune 이미지 이름 매칭**: 빌드 시 `luksa/fortune:latest`로 나오면 `docker tag ... fortune:v1` 추가 필요 (Pod YAML이 `fortune:v1` 참조)

---

## 9. 면접 예상 질문

1. **emptyDir vs hostPath vs PV 차이**
   - emptyDir: Pod 수명, hostPath: 노드 고정, PV: 클러스터 수명 + 이식성
2. **PV와 PVC를 왜 분리?**
   - 관심사 분리 + 동적 프로비저닝 가능
3. **EBS를 Pod 2개에서 공유할 수 있나?**
   - ❌ 불가. RWO만 지원. 필요하면 EFS.
4. **PVC가 Pending 상태면 왜?**
   - 조건 맞는 PV 없음 / StorageClass 못 찾음 / 프로비저너 에러 / AZ mismatch
5. **reclaimPolicy Retain vs Delete?**
   - 프로덕션은 Retain(실수로 DB 날리는 거 방지), 일회용은 Delete
6. **StorageClass의 `volumeBindingMode: WaitForFirstConsumer` 의미?**
   - Pod가 스케줄될 노드가 정해진 뒤에야 볼륨 생성 → AZ mismatch 방지

---

## Key Concepts

- **Volume**: Pod spec에 정의, Pod 수명 주기와 연결
- **PersistentVolume (PV)**: 클러스터 리소스, Pod 수명과 독립
- **PersistentVolumeClaim (PVC)**: 개발자의 스토리지 "청구서"
- **StorageClass**: 동적 프로비저닝 템플릿
- **CSI**: 스토리지 벤더 플러그인 표준 인터페이스
- **accessModes**: RWO / ROX / RWX / RWOP

## Notes

- ch06 예제는 `kubernetes-in-action/examples/Chapter06/` 원본 참고
- fortune 이미지는 `fortune:v1`로 로컬 빌드됨 → `ch06-volumes/fortune/`
- EKS 실습하려면 EBS CSI driver + IRSA 세팅 먼저

## Questions

- EBS Snapshot을 PVC로 복원하는 워크플로우? (CSI VolumeSnapshot)
- EFS Access Point vs 그냥 mount?
- StatefulSet + volumeClaimTemplate과 PVC의 관계 (ch10 예고편)
