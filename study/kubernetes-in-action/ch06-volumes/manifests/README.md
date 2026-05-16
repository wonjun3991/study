---
tags: [kubernetes, ch06, volumes, practice]
---

# Chapter 6 실습 가이드

> 순서대로 01 → 06까지 진행. 각 섹션은 독립 실행 가능.
> 개념 정리는 [[../README|ch06 README]] 참고.

## 사전 준비

### 1) 클러스터 확인

```bash
kubectl config current-context   # minikube 여야 함
kubectl get nodes                # Ready 상태 확인
```

### 2) fortune 이미지 minikube 로드 (01-emptydir 전에 필수)

로컬 Docker에만 빌드된 이미지라 minikube가 못 봄. 로드 필요.

**⚠️ 멀티노드 minikube 주의**: `minikube image load`는 노드가 여러 개면 매우 느림(15분+). 2가지 선택지:

**옵션 A (권장) — tar import로 각 노드에 직접 로드 (빠름)**
```bash
docker save fortune:v1 -o /tmp/fortune-v1.tar

# control plane
minikube ssh -n minikube -- 'sudo ctr -n=k8s.io images import -' < /tmp/fortune-v1.tar

# worker 노드들 (m02, m03, m04)
for node in minikube-m02 minikube-m03 minikube-m04; do
  minikube cp /tmp/fortune-v1.tar $node:/tmp/fortune-v1.tar
  minikube ssh -n $node -- 'sudo ctr -n=k8s.io images import /tmp/fortune-v1.tar'
done

# 확인
for node in minikube minikube-m02 minikube-m03 minikube-m04; do
  echo "-- $node --"
  minikube ssh -n $node -- 'sudo crictl images | grep fortune'
done
```

**옵션 B — 간단한 방법: control plane 노드에만 pin**

현재 `minikube` 노드에만 이미지 있는 상태면 `fortune-pod.yaml`에 nodeSelector 추가:
```yaml
spec:
  nodeSelector:
    kubernetes.io/hostname: minikube   # control plane 노드로 고정
  containers:
  ...
```

---

## 01. emptyDir — Pod 내 컨테이너 간 공유

**배우는 것**: 사이드카 패턴, Pod 수명과 함께 사라지는 볼륨.

```bash
cd manifests/01-emptydir
kubectl apply -f fortune-pod.yaml -f fortune-service.yaml

# Pod 상태 확인 (두 컨테이너 모두 Ready 되어야 함)
kubectl get pod fortune -w
# Ctrl+C로 watch 종료

# 접속 테스트 (minikube)
minikube service fortune --url
curl $(minikube service fortune --url)

# 10초마다 바뀌는 명언 확인
for i in {1..3}; do curl -s $(minikube service fortune --url); sleep 11; done
```

**관찰 포인트**:
- `html-generator` 컨테이너가 `/var/htdocs/index.html` 작성
- `web-server` 컨테이너가 `/usr/share/nginx/html`에서 서빙
- 두 컨테이너가 **같은 emptyDir 볼륨**을 공유

**정리**:
```bash
kubectl delete -f fortune-pod.yaml -f fortune-service.yaml
```

---

## 02. gitRepo — Git 저장소를 볼륨으로

**⚠️ Deprecated**: 실전에선 init container + git 조합 사용. 개념 이해용.

```bash
cd manifests/02-gitrepo
kubectl apply -f gitrepo-volume-pod.yaml

kubectl port-forward gitrepo-volume-pod 8080:80 &
curl localhost:8080
kill %1
```

**관찰 포인트**: Pod 생성 시점에만 git clone. 이후 repo 갱신돼도 반영 안 됨.

```bash
kubectl delete -f gitrepo-volume-pod.yaml
```

---

## 03. hostPath — 노드 로컬 디렉토리

**⚠️ 주의**: 멀티노드 클러스터(지금 minikube 4노드)에서 Pod가 다른 노드로 뜨면 **다른 데이터 봄**. hostPath의 한계 체험.

```bash
cd manifests/03-hostpath
kubectl apply -f mongodb-pod-hostpath.yaml

# Pod가 어느 노드에 떴는지 확인
kubectl get pod mongodb -o wide

# 데이터 쓰기
kubectl exec -it mongodb -- mongosh --eval '
  db.test.insertOne({hello: "from hostPath"});
  db.test.find();
'

# Pod 삭제 후 재생성 → 같은 노드에 뜨면 데이터 유지, 다른 노드면 데이터 없음
kubectl delete pod mongodb
kubectl apply -f mongodb-pod-hostpath.yaml
kubectl get pod mongodb -o wide   # 노드 위치 비교

kubectl exec -it mongodb -- mongosh --eval 'db.test.find()'
```

**관찰 포인트**: hostPath는 **노드에 묶임**. 실전에서 앱 데이터엔 쓰지 말 것.

```bash
kubectl delete -f mongodb-pod-hostpath.yaml
```

---

## 04. PV + PVC — 관심사 분리

**배우는 것**: 관리자(PV)와 개발자(PVC) 역할 분리. 정적 프로비저닝.

```bash
cd manifests/04-pv-pvc

# 1) 관리자 역할: PV 먼저 생성
kubectl apply -f mongodb-pv-hostpath.yaml
kubectl get pv                          # STATUS: Available

# 2) 개발자 역할: PVC 생성 → 자동으로 PV에 바인딩됨
kubectl apply -f mongodb-pvc.yaml
kubectl get pv,pvc                      # PV: Bound, PVC: Bound

# 3) Pod이 PVC를 참조
kubectl apply -f mongodb-pod-pvc.yaml
kubectl get pod mongodb

# 데이터 쓰기
kubectl exec -it mongodb -- mongosh --eval '
  db.test.insertOne({hello: "from PVC"});
  db.test.find();
'
```

**관찰 포인트**:
- `kubectl describe pvc mongodb-pvc` → Events에서 바인딩 과정 확인
- PVC의 요구사항(1Gi, RWO)이 PV 스펙에 맞는지 매칭

**정리 순서 중요** (역순):
```bash
kubectl delete -f mongodb-pod-pvc.yaml
kubectl delete -f mongodb-pvc.yaml
kubectl get pv                          # Released 상태 (reclaimPolicy: Retain 때문)
kubectl delete -f mongodb-pv-hostpath.yaml
```

---

## 05. StorageClass — 동적 프로비저닝

**배우는 것**: 관리자가 PV를 미리 안 만들어도 PVC가 자동으로 PV 생성.

minikube는 기본 `standard` StorageClass가 이미 있음:

```bash
kubectl get storageclass
# NAME                 PROVISIONER                RECLAIMPOLICY   ...
# standard (default)   k8s.io/minikube-hostpath   Delete          ...
```

책 예제는 `fast`라는 별도 StorageClass를 만듦:

```bash
cd manifests/05-storageclass
kubectl apply -f storageclass-fast-hostpath.yaml
kubectl get storageclass                # fast 추가 확인

# PVC 생성 → 자동으로 PV까지 생성됨
kubectl apply -f mongodb-pvc-dp.yaml
kubectl get pv,pvc
# PVC는 바로 Bound. PV는 자동 생성된 pvc-xxx 이름.

# 상세 확인
kubectl describe pvc mongodb-pvc
```

**관찰 포인트**:
- PV를 직접 안 만들었는데 생겨있음
- PV 이름이 `pvc-<uuid>` 패턴 (자동 생성)

**정리**:
```bash
kubectl delete pvc mongodb-pvc          # reclaimPolicy: Delete → PV도 자동 삭제
kubectl delete -f storageclass-fast-hostpath.yaml
```

---

## 06. AWS EBS (참고용, EKS 전용)

로컬 minikube에선 **실행 안 됨**. EKS 클러스터 있을 때만.

[[06-aws-ebs/eks-ebs-gp3-dynamic.yaml|eks-ebs-gp3-dynamic.yaml]] 열어서 현대 CSI 기반 패턴 읽어보기:

- `provisioner: ebs.csi.aws.com` (in-tree 아님)
- `volumeBindingMode: WaitForFirstConsumer` (AZ mismatch 방지)
- `accessModes: ReadWriteOnce` (EBS의 근본 제약)
- `allowVolumeExpansion: true` (PVC 확장 지원)

EKS 실습하려면 별도 세팅 필요:
1. EKS 클러스터 생성 (eksctl 등)
2. `aws-ebs-csi-driver` 애드온 설치
3. IRSA로 `ebs-csi-controller-sa`에 `AmazonEBSCSIDriverPolicy` 연결

---

## 트러블슈팅

### Pod이 `ImagePullBackOff` (fortune 이미지)

```bash
minikube image load fortune:v1
kubectl delete pod fortune && kubectl apply -f manifests/01-emptydir/fortune-pod.yaml
```

### PVC가 `Pending` 상태

```bash
kubectl describe pvc <name>
# Events에서 이유 확인:
#   - "no persistent volumes available" → PV 없음 (정적) or StorageClass 없음 (동적)
#   - "waiting for first consumer" → WaitForFirstConsumer 모드, Pod 생성 대기
```

### PV가 `Released` 상태로 재사용 안 됨

`reclaimPolicy: Retain`이면 수동 정리 필요:
```bash
kubectl edit pv <name>
# spec.claimRef 삭제 → Available로 복귀
```

### mongodb Pod가 `CrashLoopBackOff`

hostPath 경로 권한 이슈 가능:
```bash
minikube ssh -- sudo chmod 777 /tmp/mongodb
```

---

## 전체 리셋

```bash
kubectl delete pod,pvc,pv --all -n default
kubectl delete storageclass fast 2>/dev/null
```
