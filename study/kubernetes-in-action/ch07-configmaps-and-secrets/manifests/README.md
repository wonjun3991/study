---
tags: [kubernetes, ch07, practice]
---

# Chapter 7 실습 가이드

> 순서대로 01 → 10까지. 각 섹션 독립 실행.
> 개념은 [[../README|ch07 README]].

## 사전 준비

### 1) 클러스터
```bash
kubectl config current-context   # minikube
kubectl get nodes                # Ready
```

### 2) fortune 이미지 2종 빌드 (minikube docker-env)
```bash
eval $(minikube docker-env)

# args 버전 (CMD ["10"])
cd manifests/00-images/fortune-args
docker build -t luksa/fortune:args .

# env 버전 ($INTERVAL)
cd ../fortune-env
docker build -t luksa/fortune:env .

docker images | grep luksa/fortune
```

첫 빌드는 apt repo 다운로드로 7~10분. 캐시되면 1분 내.

---

## 01. args — Pod에서 CMD 덮어쓰기

```bash
cd manifests/01-args
kubectl apply -f fortune-pod-args.yaml
sleep 5
kubectl logs fortune2s -c html-generator | head -1
# Configured to generate new fortune every 2 seconds
```

**관찰**: `args: ["2"]`가 컨테이너 `$1`로 전달. Dockerfile의 `CMD ["10"]` 덮어씀.

```bash
kubectl delete -f fortune-pod-args.yaml
```

---

## 02. env — Pod에서 환경변수 주입

```bash
cd manifests/02-env
kubectl apply -f fortune-pod-env.yaml
kubectl exec fortune-env -c html-generator -- env | grep INTERVAL
# INTERVAL=30
kubectl logs fortune-env -c html-generator | head -1
# Configured to generate new fortune every 30 seconds
```

```bash
kubectl delete -f fortune-pod-env.yaml
```

---

## 03. ConfigMap → env (valueFrom)

```bash
cd manifests/03-configmap-literal
kubectl apply -f fortune-config.yaml
kubectl describe configmap fortune-config
# sleep-interval: 25

kubectl apply -f fortune-pod-env-configmap.yaml
kubectl exec fortune-env-from-configmap -c html-generator -- env | grep INTERVAL
# INTERVAL=25
```

```bash
kubectl delete -f fortune-pod-env-configmap.yaml
# ConfigMap은 유지 — 다음 섹션에서 재사용
```

---

## 04. ConfigMap → envFrom (전체 주입)

```bash
cd manifests/04-configmap-envfrom
kubectl apply -f fortune-envfrom.yaml

kubectl exec fortune-envfrom -c html-generator -- env | grep -E "CONFIG_|INTERVAL" | sort
# CONFIG_APP_ENV=development
# CONFIG_APP_NAME=fortune-demo
# CONFIG_LOG_LEVEL=debug
# CONFIG_sleep-interval=15    ← 설정되긴 함
# INTERVAL=15
```

**하이픈 함정 실증**:
```bash
# 이건 작동 안 함 (shell이 $CONFIG_sleep에서 멈춤)
kubectl exec fortune-envfrom -c html-generator -- sh -c 'echo $CONFIG_sleep-interval'
# 출력: "-interval"

# printenv도 실패
kubectl exec fortune-envfrom -c html-generator -- printenv CONFIG_sleep-interval
# exit code 1
```

교훈: ConfigMap key는 **SCREAMING_SNAKE_CASE**로 쓰는 게 안전.

```bash
kubectl delete -f fortune-envfrom.yaml
```

---

## 05. ConfigMap → args에 $(VAR) 치환

```bash
cd manifests/05-configmap-args
kubectl apply -f fortune-config.yaml        # (이미 있으면 unchanged)
kubectl apply -f fortune-pod-args-configmap.yaml

kubectl get pod fortune-args-from-configmap -o jsonpath='{.spec.containers[0].args}'
# ["$(INTERVAL)"]      ← YAML에는 리터럴, 컨테이너 내부에서 "25"로 치환됨

kubectl logs fortune-args-from-configmap -c html-generator | head -1
# Configured to generate new fortune every 25 seconds
```

```bash
kubectl delete pod fortune-args-from-configmap
```

---

## 06. ConfigMap → 볼륨 마운트 (nginx.conf 주입)

```bash
cd manifests/06-configmap-volume

# ConfigMap 재생성 (my-nginx-config.conf 포함)
kubectl delete configmap fortune-config
kubectl create configmap fortune-config \
  --from-file=my-nginx-config.conf \
  --from-file=sleep-interval

kubectl apply -f fortune-pod-configmap-volume.yaml

# CM이 파일로 보이는지
kubectl exec fortune-configmap-volume -c web-server -- ls /etc/nginx/conf.d/
# my-nginx-config.conf  sleep-interval  (둘 다 symlink)

# gzip이 실제로 활성화됐는지
kubectl exec fortune-configmap-volume -c web-server -- \
  curl -sI -H "Accept-Encoding: gzip" http://localhost/ | grep -i encoding
# Content-Encoding: gzip
```

**관찰**: ConfigMap은 `..data/` 심볼릭 링크 구조로 마운트됨 (원자적 업데이트 위해).

```bash
kubectl delete -f fortune-pod-configmap-volume.yaml
```

---

## 07. ConfigMap 볼륨 → items로 선택/rename

```bash
cd manifests/07-configmap-volume-items
kubectl apply -f fortune-pod-configmap-volume-with-items.yaml

kubectl exec fortune-configmap-volume-with-items -c web-server -- ls /etc/nginx/conf.d/
# gzip.conf only   ← my-nginx-config.conf만 선택 + 이름 변경, sleep-interval 제외
```

```bash
kubectl delete -f fortune-pod-configmap-volume-with-items.yaml
```

---

## 08. 런타임 ConfigMap 업데이트

```bash
cd manifests/08-configmap-update
kubectl apply -f fortune-cm-update-test.yaml

# BEFORE: gzip 포함된 config 있음
kubectl exec fortune-cm-update-test -- grep -c "gzip on" /etc/nginx/conf.d/my-nginx-config.conf
# 1

# ConfigMap 수정 — gzip 제거
kubectl patch configmap fortune-config --type merge -p \
  '{"data":{"my-nginx-config.conf":"server { listen 80; server_name www.example.com; location / { root /usr/share/nginx/html; index index.html; } }\n"}}'

# 약 60초 후 파일 업데이트 확인
for i in 1 2 3 4 5 6; do
  sleep 10
  count=$(kubectl exec fortune-cm-update-test -- grep -c "gzip on" /etc/nginx/conf.d/my-nginx-config.conf 2>/dev/null)
  echo "[${i}0s] gzip lines: $count"
  [ "$count" = "0" ] && break
done

# 그런데 nginx 응답은 여전히 gzip
kubectl exec fortune-cm-update-test -- curl -sI -H "Accept-Encoding: gzip" http://localhost/ | grep -i encoding
# Content-Encoding: gzip    ← nginx 프로세스는 reload 안 됨
```

**교훈**:
- 볼륨 마운트된 CM은 **~60초 후 파일 업데이트**
- 그러나 **앱이 파일 reload 안 하면 효과 없음**. nginx는 SIGHUP 신호 받아야 reload.

```bash
kubectl delete -f fortune-cm-update-test.yaml
kubectl delete configmap fortune-config
```

---

## 09. Secret → TLS 인증서

```bash
cd manifests/09-secret-tls

# ConfigMap + Secret 생성
kubectl create configmap fortune-config \
  --from-literal=sleep-interval=25 \
  --from-file=my-nginx-config.conf=ssl.conf

kubectl create secret generic fortune-https \
  --from-file=https.key \
  --from-file=https.cert \
  --from-file=foo

# Secret은 base64
kubectl get secret fortune-https -o jsonpath='{.data.https\.cert}' | head -c 80
# LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t... (= "-----BEGIN CERTIFICATE-----...")

# Pod 생성
kubectl apply -f fortune-pod-https.yaml

# Secret 볼륨은 tmpfs (메모리)
kubectl exec fortune-https -c web-server -- mount | grep certs
# tmpfs on /etc/nginx/certs type tmpfs (ro,relatime,size=...)

# HTTPS 작동
kubectl exec fortune-https -c web-server -- sh -c 'apk add --no-cache curl; curl -sk https://localhost/'
# You have taken yourself too seriously.   ← fortune text
```

```bash
kubectl delete -f fortune-pod-https.yaml
kubectl delete secret fortune-https
kubectl delete configmap fortune-config
```

---

## 10. imagePullSecret (참고만)

실제 private registry 필요하므로 실행 안 함. YAML만 확인:

```bash
cat manifests/10-private-image/pod-with-private-image.yaml
```

실전에서 private image 쓸 때:
```bash
kubectl create secret docker-registry mydockerhubsecret \
  --docker-username=<user> \
  --docker-password=<pass> \
  --docker-email=<email>
```

---

## 전체 정리

```bash
kubectl delete pod,cm,secret --all -n default 2>/dev/null
```
