---
tags: [kubernetes, ch08, practice]
---

# Chapter 8 실습 가이드

> Downward API + Pod 내부에서 apiserver 접근.
> 개념은 [[../README|ch08 README]].

## 사전 준비

```bash
kubectl config current-context   # minikube
kubectl get nodes                # Ready
```

---

## 01. Downward API → env

```bash
cd manifests/01-downward-env
kubectl apply -f downward-api-env.yaml
sleep 5

kubectl exec downward -- env | grep -E "POD_|NODE_|SERVICE_ACCOUNT|CONTAINER_" | sort
```

예상 출력:
```
CONTAINER_CPU_REQUEST_MILLICORES=15        # requests.cpu=15m / divisor=1m
CONTAINER_MEMORY_LIMIT_KIBIBYTES=8192      # limits.memory=8Mi / divisor=1Ki
NODE_NAME=minikube
POD_IP=10.244.0.x
POD_NAME=downward
POD_NAMESPACE=default
SERVICE_ACCOUNT=default
```

**⚠️ 책 예제는 `limits.memory: 4Mi`지만 현대 Docker runc는 최소 6MB 요구**. `8Mi`로 수정됨.

```bash
kubectl delete pod downward
```

---

## 02. Downward API → 볼륨

```bash
cd manifests/02-downward-volume
kubectl apply -f downward-api-volume.yaml
sleep 5

# 각 필드가 파일 하나
kubectl exec downward -- ls /etc/downward/
# annotations, containerCpuRequestMilliCores, containerMemoryLimitBytes,
# labels, podName, podNamespace

# labels는 env로는 못했던 것
kubectl exec downward -- cat /etc/downward/labels
# foo="bar"

# multi-line annotation도 정상
kubectl exec downward -- cat /etc/downward/annotations | head -5
```

**런타임 업데이트 테스트**:
```bash
kubectl label pod downward env=test --overwrite
sleep 5
kubectl exec downward -- cat /etc/downward/labels
# env="test"
# foo="bar"         ← 자동 반영됨
```

env는 불가능, 볼륨은 가능.

```bash
kubectl delete pod downward
```

---

## 03. API 서버 직접 접근 + RBAC

### 3-1. SA 토큰 자동 마운트 확인
```bash
cd manifests/03-api-direct
kubectl apply -f curl.yaml
sleep 5

kubectl exec curl -- ls /var/run/secrets/kubernetes.io/serviceaccount/
# ca.crt  namespace  token
```

### 3-2. 인증 없이 호출 (실패)
```bash
kubectl exec curl -- curl -sk https://kubernetes.default.svc/api
# "forbidden: User \"system:anonymous\" cannot get path \"/api\""
# code: 403
```

### 3-3. Bearer token으로 인증 (성공)
```bash
kubectl exec curl -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  curl -s --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api
'
# {"kind":"APIVersions","versions":["v1"],...}
```

### 3-4. 권한 없는 API 호출 → forbidden
```bash
kubectl exec curl -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  curl -s --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    -H "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api/v1/namespaces/default/pods
'
# "pods is forbidden: User \"system:serviceaccount:default:default\" cannot list resource \"pods\"..."
```

### 3-5. RBAC 부여 후 재시도 → 성공
```bash
kubectl apply -f rbac.yaml

kubectl exec curl -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  curl -s --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    -H "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api/v1/namespaces/default/pods
' | head -10
# {"kind":"PodList","apiVersion":"v1","items":[...]}
```

### 3-6. RBAC 범위 검증 (pods만 허용 → services는 여전히 forbidden)
```bash
kubectl exec curl -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  curl -s --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    -H "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api/v1/namespaces/default/services
' | head -5
# "services is forbidden: ..."
```

```bash
kubectl delete pod curl
kubectl delete -f rbac.yaml
```

---

## 04. Ambassador 패턴 (kubectl proxy 사이드카)

```bash
cd manifests/04-kubectl-proxy
kubectl apply -f curl-with-ambassador.yaml
sleep 15

# main 컨테이너에서 plain HTTP로 호출 (인증 로직 없음)
kubectl exec curl-with-ambassador -c main -- curl -s http://localhost:8001/api
# {"kind":"APIVersions","versions":["v1"],...}

# pods list도 직접 (ambassador가 인증 처리)
kubectl exec curl-with-ambassador -c main -- curl -s http://localhost:8001/api/v1/namespaces/default/pods | head -10
```

**관찰 포인트**:
- `main` 컨테이너: `tutum/curl` 책 예제 → `curlimages/curl:latest`로 교체
- `ambassador` 컨테이너: `luksa/kubectl-proxy:1.6.2` (2018 k8s 1.8) → `bitnami/kubectl:latest`로 교체
- main은 인증 없이 plain HTTP만 호출 — 복잡도 앱에서 사이드카로 이동

```bash
kubectl delete pod curl-with-ambassador
```

---

## 트러블슈팅

### `Minimum memory limit allowed is 6MB`
책의 `limits.memory: 4Mi`는 최근 Docker runc에서 거부됨. `8Mi`로 올릴 것.

### RBAC 에러 `forbidden`
```bash
# 현재 SA로 특정 액션 되는지 테스트
kubectl auth can-i list pods --as=system:serviceaccount:default:default
# yes or no

# Role 내용 확인
kubectl describe role pod-reader
```

### `curlimages/curl` 이미지 pull 실패
인터넷 확인. 대체로 `alpine` + `apk add curl` 사용 가능.

---

## 전체 정리

```bash
kubectl delete pod,role,rolebinding --all -n default 2>/dev/null
```
