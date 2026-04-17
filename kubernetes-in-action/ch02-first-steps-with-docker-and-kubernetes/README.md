---
tags: [kubernetes, ch02, docker]
---

# Chapter 2: First steps with Docker and Kubernetes

## Key Concepts

- Docker 이미지는 **읽기 전용 레이어들의 스택**이다
- Dockerfile의 각 명령어(`FROM`, `RUN`, `COPY` 등)가 하나의 레이어를 생성한다
- 레이어가 변경되면 그 **아래의 모든 레이어 캐시가 무효화**된다
- 컨테이너는 이미지 위에 **쓰기 가능한 레이어** 하나를 추가한 것이다
- `kubectl create deployment`으로 Deployment를 생성하고, `kubectl expose`로 Service를 만들어 외부에 노출한다
- Kubernetes는 Pod를 어떤 워커 노드에 배치할지 **스케줄링**한다 — 개발자는 신경 쓸 필요 없다
- **Deployment → ReplicaSet → Pod** 3계층 구조가 현재 표준이다 (1판의 ReplicationController는 레거시)

---

## 2.1 컨테이너 이미지 생성, 실행, 공유

### 2.1.1 Docker 설치와 Hello World

```bash
docker run busybox echo "Hello world"
```

실행 흐름:

```
docker run busybox echo "Hello world"
    │
    ├─ 1) 로컬에 busybox 이미지가 있는지 확인
    ├─ 2) 없으면 Docker Hub에서 pull
    ├─ 3) 이미지로부터 컨테이너 생성
    ├─ 4) 컨테이너 안에서 echo "Hello world" 실행
    └─ 5) 프로세스 종료 → 컨테이너 중지
```

#### BusyBox란?

> "The Swiss Army Knife of Embedded Linux" — 수백 개의 Unix 유틸리티를 **단일 바이너리 (~1.2MB)** 에 담은 초경량 도구

**일반 Linux vs BusyBox**:

```
일반 Linux:                          BusyBox:
  /bin/ls    (120KB)                   /bin/busybox (~1.2MB)
  /bin/cp    (140KB)                     ← 이 하나에 300+ 명령어 내장
  /bin/cat   (50KB)
  /bin/grep  (200KB)
  /bin/sh    (1.2MB)
  ... 수백 개 → 합계 수십 MB
```

**동작 원리** — 자신이 어떤 이름으로 호출되었는지(argv[0]) 보고 해당 명령을 실행:

```bash
ln -s /bin/busybox /bin/ls    # 심볼릭 링크 생성
ls -la                         # busybox가 argv[0]="ls"를 보고 ls 모드로 실행
busybox ls -la                 # 직접 호출도 가능
```

**포함된 명령어 (300+)**:

| 카테고리 | 예시 |
|----------|------|
| 파일 | `ls`, `cp`, `mv`, `rm`, `find`, `tar`, `gzip` |
| 텍스트 | `cat`, `grep`, `sed`, `awk`, `sort`, `head`, `tail` |
| 네트워크 | `wget`, `ping`, `nc`, `ifconfig`, `traceroute` |
| 시스템 | `ps`, `top`, `kill`, `mount`, `df`, `du`, `free` |
| 셸 | `sh` (ash), `vi`, `cron`, `syslog` |

단, GNU 버전의 모든 옵션을 지원하진 않음 — 자주 쓰는 옵션 위주로 경량 구현.

**컨테이너 이미지로서의 BusyBox**:

| 이미지 | 크기 | 셸 | 패키지 매니저 | 용도 |
|--------|------|-----|-------------|------|
| `busybox` | ~1.2MB | ash | ❌ | 디버깅, init container |
| `alpine` | ~5MB | ash | apk | 범용 경량 베이스 (BusyBox + musl libc + apk) |
| `distroless` | ~2-20MB | ❌ | ❌ | 프로덕션 보안 (공격 표면 최소) |
| `scratch` | 0MB | ❌ | ❌ | Go/Rust 정적 바이너리 전용 |

**Kubernetes에서의 활용**:

```bash
# 디버그 Pod으로 네트워크/DNS 확인
kubectl run debug --image=busybox -it --rm -- sh

# Pod 안에서:
wget -qO- http://my-service:8080/health   # HTTP 요청
nslookup my-service                        # DNS 확인
nc -zv my-db 5432                          # 포트 열림 확인
```

```yaml
# Init Container — 메인 컨테이너 전에 사전 작업 수행
initContainers:
  - name: wait-for-db
    image: busybox:1.36
    command: ["sh", "-c", "until nc -zv postgres 5432; do sleep 2; done"]
```

### 2.1.2 간단한 Node.js 앱 만들기

책에서 사용하는 예제 앱 (`app.js`):

```javascript
const http = require('http');
const os = require('os');

console.log("Kubia server starting...");

var handler = function(request, response) {
  console.log("Received request from " + request.connection.remoteAddress);
  response.writeHead(200);
  response.end("You've hit " + os.hostname() + "\n");
};

var www = http.createServer(handler);
www.listen(8080);
```

- HTTP 요청을 받으면 **자신의 호스트네임**을 응답한다
- 나중에 여러 Pod로 스케일링하면 각 Pod의 호스트네임이 다르게 나온다 → 로드밸런싱 확인용

### 2.1.3 Dockerfile 작성

```dockerfile
FROM node:7
ADD app.js /app.js
ENTRYPOINT ["node", "app.js"]
```

| 명령 | 의미 |
|------|------|
| `FROM node:7` | node:7 이미지를 베이스 레이어로 사용 |
| `ADD app.js /app.js` | 로컬 app.js를 이미지의 /app.js로 복사 |
| `ENTRYPOINT` | 컨테이너 시작 시 실행할 명령 |

### 2.1.4 이미지 빌드

```bash
docker build -t kubia .
```

```
빌드 과정:

  Dockerfile + 빌드 컨텍스트(현재 디렉토리)
         │
         ▼
  Docker 데몬으로 전송
         │
    ┌────┴────┐
    │ Layer 1 │  FROM node:7 (pull)
    ├─────────┤
    │ Layer 2 │  ADD app.js
    ├─────────┤
    │ Layer 3 │  ENTRYPOINT
    └─────────┘
         │
         ▼
    이미지: kubia:latest
```

**중요**: 빌드 컨텍스트 전체가 Docker 데몬에 전송되므로 불필요한 파일은 `.dockerignore`로 제외해야 한다.

### 2.1.5 컨테이너 실행

```bash
docker run --name kubia-container -p 8080:8080 -d kubia
```

| 옵션 | 의미 |
|------|------|
| `--name kubia-container` | 컨테이너 이름 지정 |
| `-p 8080:8080` | 호스트 8080 → 컨테이너 8080 포트 매핑 |
| `-d` | 백그라운드(detached) 실행 |

```bash
curl localhost:8080
# You've hit 44d76963e8e1   ← 컨테이너 ID가 호스트네임
```

### 2.1.6 실행 중인 컨테이너 내부 탐색

```bash
# 컨테이너 안에서 셸 실행
docker exec -it kubia-container bash

# 컨테이너 내부에서 프로세스 목록 확인
root@44d76963e8e1:/# ps aux
# PID 1 = node app.js (컨테이너의 메인 프로세스)
```

**컨테이너의 격리**:
- 컨테이너 안의 프로세스는 **자신만의 PID 네임스페이스**에서 실행된다
- 컨테이너 안에서 `ps aux`하면 자신의 프로세스만 보인다
- 호스트에서 `ps aux`하면 컨테이너 프로세스도 보인다 (다른 PID로)

```
호스트 OS 관점:
  PID 1    : systemd
  PID 3150 : node app.js    ← 컨테이너 프로세스

컨테이너 관점:
  PID 1    : node app.js    ← 자신이 PID 1이라고 생각함
```

이것이 가능한 이유: **Linux 네임스페이스 (namespace)** — 프로세스, 네트워크, 파일시스템 등을 격리

### 2.1.7 컨테이너 중지 및 삭제

```bash
docker stop kubia-container
docker rm kubia-container
```

### 2.1.8 이미지 레지스트리에 푸시

```bash
# Docker Hub 이미지 태깅 규칙: <Docker Hub ID>/<이미지명>
docker tag kubia luksa/kubia

docker login
docker push luksa/kubia
```

```
push 후 아무 머신에서나:
  docker run -p 8080:8080 -d luksa/kubia
→ Docker Hub에서 pull → 실행
```

---

## 2.2 Kubernetes 클러스터 구성

### 2.2.1 Minikube로 로컬 단일 노드 클러스터

```bash
minikube start

# 클러스터 정보 확인
kubectl cluster-info

# 노드 확인
kubectl get nodes
```

```
Minikube 구조:

  ┌─── 로컬 머신 ──────────────────┐
  │                                 │
  │   ┌─── Minikube VM ─────────┐  │
  │   │  Master + Worker Node   │  │
  │   │  (단일 노드에 전부)       │  │
  │   └─────────────────────────┘  │
  │                                 │
  │   kubectl ◄──── 사용자          │
  └─────────────────────────────────┘
```

### 2.2.2 GKE (Google Kubernetes Engine)로 클러스터 구성

```bash
# 3-노드 클러스터 생성
gcloud container clusters create kubia --num-nodes 3 --machine-type f1-micro

kubectl get nodes
# NAME                           STATUS   ROLES    AGE
# gke-kubia-default-pool-xxx-1   Ready    <none>   1m
# gke-kubia-default-pool-xxx-2   Ready    <none>   1m
# gke-kubia-default-pool-xxx-3   Ready    <none>   1m
```

---

## 2.3 Kubernetes에서 첫 번째 앱 실행

### 2.3.1 앱 배포

> **⚠️ 1판과의 차이**: 1판에서는 `kubectl run --generator=run/v1`로 ReplicationController를 생성했다.
> 현재(K8s 1.18+)에서는 `--generator` 플래그가 **삭제**되었고, `kubectl run`은 **Pod만 생성**한다.
> Deployment를 만들려면 `kubectl create deployment`를 사용해야 한다.

```bash
# 1판 방식 (현재 에러 발생)
# kubectl run kubia --image=luksa/kubia --port=8080 --generator=run/v1

# 현재 방식 — Deployment 생성
kubectl create deployment kubia --image=luksa/kubia --port=8080
```

이 명령이 하는 일:

```
kubectl create deployment kubia
    │
    ├─ 1) Deployment 'kubia' 생성
    │     (desired replicas = 1)
    │
    ├─ 2) Deployment가 ReplicaSet 생성
    │
    ├─ 3) ReplicaSet이 Pod 'kubia-xxxxxxxxxx-xxxxx' 생성
    │
    ├─ 4) Scheduler가 Pod를 워커 노드에 배정
    │
    └─ 5) 해당 노드의 Kubelet이 컨테이너 런타임(containerd)에게 실행 지시
          └─ crictl pull luksa/kubia
          └─ 컨테이너 실행
```

```bash
# Pod 확인
kubectl get pods

# NAME                     READY   STATUS    RESTARTS   AGE
# kubia-6b7b8d4f9c-xxxxx   1/1     Running   0          30s
#       ^^^^^^^^^^
#       ReplicaSet 해시가 이름에 포함됨
```

> **참고**: `kubectl run kubia --image=luksa/kubia`는 여전히 작동하지만, Deployment가 아닌 **단독 Pod**만 생성한다. ReplicaSet/스케일링 없이 일회성 테스트용으로만 사용.

### Pod란?

- Kubernetes가 관리하는 **최소 배포 단위**
- 하나 이상의 컨테이너를 포함한다
- 같은 Pod의 컨테이너들은 **같은 네트워크 네임스페이스** (같은 IP, 같은 포트 공간)를 공유
- Pod에는 자체 **내부 IP 주소**가 있지만 클러스터 외부에서는 접근 불가

```
┌─── Pod ─────────────────┐
│  IP: 10.244.0.5         │
│                         │
│  ┌─ Container ────────┐ │
│  │ luksa/kubia:latest │ │
│  │ port: 8080         │ │
│  └────────────────────┘ │
└─────────────────────────┘
```

### 2.3.2 웹 앱에 접근하기 — Service

Pod의 내부 IP로는 외부에서 접근할 수 없다. **Service**를 만들어 노출해야 한다.

```bash
# 1판: kubectl expose rc kubia ...
# 현재: Deployment를 expose
kubectl expose deployment kubia --type=LoadBalancer --name kubia-http
```

```bash
kubectl get services  # 또는 kubectl get svc

# NAME       TYPE           CLUSTER-IP     EXTERNAL-IP    PORT(S)
# kubia-http LoadBalancer   10.3.246.185   104.155.74.57  8080:31348/TCP
```

```bash
curl 104.155.74.57:8080
# You've hit kubia-xxxxx
```

```
외부 트래픽 흐름:

  인터넷 → LoadBalancer (104.155.74.57:8080)
              │
              ▼
          Service (kubia-http)
              │
              ▼
          Pod (kubia-xxxxx)
              │
              ▼
          Container (luksa/kubia → port 8080)
```

**왜 Service가 필요한가?**
- Pod는 일시적(ephemeral)이다 — 죽으면 새 Pod가 새 IP로 생긴다
- Service는 **고정된 엔드포인트**를 제공한다
- Service가 뒤에 있는 Pod들로 트래픽을 분산(로드밸런싱)한다

### 2.3.3 시스템의 논리적 구성

```
┌─ Deployment ────────────────────────────────┐
│  name: kubia                                │
│                                             │
│  ┌─ ReplicaSet ──────────────────────────┐  │
│  │  name: kubia-6b7b8d4f9c               │  │
│  │  replicas: 1                          │  │
│  │                                       │  │
│  │  ┌─ Pod ────────────────────────────┐ │  │
│  │  │  ┌─ Container ────────────────┐  │ │  │
│  │  │  │ image: luksa/kubia         │  │ │  │
│  │  │  │ port: 8080                 │  │ │  │
│  │  │  └────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────┘ │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
              │
              │ label selector: app=kubia
              ▼
┌─ Service ──────────────────┐
│  name: kubia-http          │
│  type: LoadBalancer        │
│  port: 8080                │
│  external IP: 104.155.74.57│
└────────────────────────────┘
```

> **⚠️ 1판과의 차이**: 1판에서는 RC(ReplicationController) 하나였지만,
> 현재는 **Deployment → ReplicaSet → Pod** 3계층 구조가 표준이다.
> Deployment가 롤링 업데이트를 관리하고, ReplicaSet이 Pod 수를 유지한다.

3가지 오브젝트의 역할:

| 오브젝트 | 역할 |
|----------|------|
| **Deployment** | 선언적 업데이트 관리 (롤링 업데이트, 롤백). ReplicaSet을 생성/관리 |
| **ReplicaSet** | Pod의 수를 원하는 만큼 유지 (Pod이 죽으면 재생성) |
| **Pod** | 실제 컨테이너가 돌아가는 단위 |
| **Service** | 고정 IP/DNS로 외부 트래픽을 Pod에 라우팅 |

### 심화: 각 오브젝트의 동작 방식

#### ReplicaSet (RS) — Pod 수를 유지하는 컨트롤러

ReplicaSet의 역할은 단 하나: **"이 label을 가진 Pod가 항상 N개 실행되도록 보장"**

```
ReplicaSet 제어 루프 (Control Loop):

  ┌──────────────────────────────────────────────┐
  │                                              │
  │  1) 현재 label=app:kubia인 Pod 수 확인       │
  │       │                                      │
  │       ├─ 부족하면 → Pod 생성                  │
  │       ├─ 초과하면 → Pod 삭제                  │
  │       └─ 딱 맞으면 → 아무것도 안 함           │
  │       │                                      │
  │  2) 반복 (watch로 실시간 감시)                │
  │                                              │
  └──────────────────────────────────────────────┘
```

```yaml
# ReplicaSet은 직접 만들 일이 거의 없다 — Deployment가 자동 생성함
# 이해를 위한 YAML:
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: kubia-6b7b8d4f9c
spec:
  replicas: 3                    # 원하는 Pod 수
  selector:
    matchLabels:
      app: kubia                 # 이 label을 가진 Pod를 관리
  template:                      # Pod 생성 시 사용할 템플릿
    metadata:
      labels:
        app: kubia
    spec:
      containers:
        - name: kubia
          image: luksa/kubia
          ports:
            - containerPort: 8080
```

**자가 치유(Self-healing) 시나리오**:

```
상태: replicas=3, 현재 Pod 3개 정상 실행 중

  Pod-1 (Running) ──┐
  Pod-2 (Running) ──┤── RS: "3개 필요, 3개 있음. OK"
  Pod-3 (Running) ──┘

노드 장애로 Pod-3 죽음:

  Pod-1 (Running) ──┐
  Pod-2 (Running) ──┤── RS: "3개 필요, 2개밖에 없음!"
  Pod-3 (Dead)  ✗   │
                    └── → Pod-4 생성 (다른 노드에 스케줄링)

결과:

  Pod-1 (Running) ──┐
  Pod-2 (Running) ──┤── RS: "3개 필요, 3개 있음. OK"
  Pod-4 (Running) ──┘
```

#### ReplicaSet vs ReplicationController (레거시)

| | ReplicationController (1판) | ReplicaSet (현재) |
|---|---|---|
| label selector | `equality` 만 (`app = kubia`) | `set-based`도 가능 (`app in (kubia, test)`) |
| 직접 사용 | 직접 생성해서 사용 | Deployment가 자동 관리 |
| 롤링 업데이트 | `kubectl rolling-update` (클라이언트 측) | Deployment가 서버 측에서 처리 |
| API | `apiVersion: v1` (레거시, 제거 예정 없지만 비권장) | `apiVersion: apps/v1` |

**결론**: ReplicaSet을 직접 만들 일은 없다. Deployment를 만들면 RS가 자동 생성된다.

#### Deployment — ReplicaSet을 관리하는 상위 컨트롤러

Deployment가 필요한 이유: **이미지 업데이트 시 롤링 업데이트와 롤백**

```
이미지 업데이트 시 Deployment 동작:

kubectl set image deployment/kubia kubia=luksa/kubia:v2

  Deployment: "v1 → v2로 업데이트"
       │
       ├─ 1) 새 ReplicaSet 생성 (kubia-새해시, image=v2)
       │     replicas: 0 → 1 → 2 → 3   (점진적 증가)
       │
       ├─ 2) 기존 ReplicaSet 축소 (kubia-구해시, image=v1)
       │     replicas: 3 → 2 → 1 → 0   (점진적 감소)
       │
       └─ 3) 완료 후 기존 RS는 replicas=0으로 보존 (롤백용)

  kubectl rollout undo deployment/kubia  ← 이전 RS를 다시 scale up
```

```
롤링 업데이트 과정:

  시점 1:  RS-v1(3)  RS-v2(0)   ← 업데이트 시작
  시점 2:  RS-v1(2)  RS-v2(1)   ← v2 Pod 1개 올라옴
  시점 3:  RS-v1(1)  RS-v2(2)   ← 순차 교체 중
  시점 4:  RS-v1(0)  RS-v2(3)   ← 업데이트 완료

→ 서비스 중단 없이 버전 교체 (Zero Downtime)
```

#### Service — Pod를 외부에 노출하는 방법

##### `kubectl expose`가 하는 일

```bash
kubectl expose deployment kubia --type=LoadBalancer --name kubia-http --port=8080
```

이 명령은 아래 YAML을 자동 생성하는 것과 동일하다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kubia-http
spec:
  type: LoadBalancer
  selector:
    app: kubia              # ← Deployment의 Pod label과 매칭
  ports:
    - port: 8080            # Service가 받는 포트
      targetPort: 8080      # Pod로 전달하는 포트
```

**핵심**: Service는 **label selector**로 Pod를 찾는다. Deployment/ReplicaSet과 직접 연결되지 않는다.

```
kubectl expose 동작:

  1) Deployment 'kubia'의 Pod template에서 label 확인
     → app: kubia

  2) Service 생성
     → selector: app=kubia
     → 이 label을 가진 모든 Pod로 트래픽 분산

  3) Endpoints 자동 생성
     → label이 매칭되는 Pod의 IP:Port 목록 관리
```

##### Service 타입별 외부 노출 방식

```
ClusterIP (기본) — 클러스터 내부에서만 접근 가능
   Client (Pod 내부) → ClusterIP (10.96.xxx.xxx) → Pod

NodePort — 모든 노드의 특정 포트로 접근 가능
   Client → <NodeIP>:31348 → Service → Pod

LoadBalancer — 클라우드 로드밸런서 + NodePort + ClusterIP
   Client → LB (104.155.74.57) → NodePort → Service → Pod
```

| 타입 | 접근 범위 | 사용처 |
|------|----------|--------|
| `ClusterIP` | 클러스터 내부만 | Pod 간 통신 (기본값) |
| `NodePort` | 노드IP:포트 | 개발/테스트 환경 |
| `LoadBalancer` | 외부 IP | 프로덕션 (클라우드) |
| `ExternalName` | DNS CNAME | 외부 서비스 연결 |

##### Service → Pod 트래픽 흐름 (상세)

```
curl 104.155.74.57:8080
    │
    ▼
LoadBalancer (클라우드 제공)
    │
    ▼
NodePort :31348 (임의 노드로 전달)
    │
    ▼
kube-proxy (iptables/IPVS 규칙)
    │  Service ClusterIP: 10.96.0.100:8080
    │
    │  Endpoints:
    │    - 10.244.0.5:8080  (Pod-1)
    │    - 10.244.1.3:8080  (Pod-2)
    │    - 10.244.0.6:8080  (Pod-3)
    │
    ▼
랜덤 Pod 선택 (라운드 로빈)
    │
    ▼
Pod-2 (10.244.1.3:8080)
    │
    ▼
"You've hit kubia-yyyyy"
```

##### Endpoints — Service와 Pod를 연결하는 매개체

Service는 Pod를 직접 알지 못한다. **Endpoints 오브젝트**가 중간에서 연결한다.

```bash
kubectl get endpoints kubia-http

# NAME        ENDPOINTS
# kubia-http  10.244.0.5:8080,10.244.1.3:8080,10.244.0.6:8080
```

```
Pod가 생성/삭제될 때:

  1) Endpoints Controller가 label 매칭되는 Pod를 감시
  2) Pod 추가 → Endpoints에 IP:Port 추가
  3) Pod 삭제 → Endpoints에서 IP:Port 제거
  4) kube-proxy가 Endpoints 변경을 감지 → iptables 규칙 갱신

  → Service IP로 요청하면 항상 살아있는 Pod로만 라우팅됨
```

##### 전체 동작 흐름 (Deployment → Service → 외부 접근)

```
kubectl create deployment kubia --image=luksa/kubia --port=8080 --replicas=3
kubectl expose deployment kubia --type=LoadBalancer --name kubia-http --port=8080

전체 흐름:

  ┌─ API Server ──────────────────────────────────────────────┐
  │                                                           │
  │  Deployment Controller                                    │
  │    → "kubia replicas=3 확인"                              │
  │    → ReplicaSet 생성                                      │
  │                                                           │
  │  ReplicaSet Controller                                    │
  │    → "Pod 3개 필요"                                       │
  │    → Pod 3개 생성 요청                                    │
  │                                                           │
  │  Scheduler                                                │
  │    → 각 Pod를 적절한 노드에 배정                           │
  │                                                           │
  │  Endpoints Controller                                     │
  │    → label=app:kubia인 Pod IP 수집                        │
  │    → Endpoints 오브젝트 갱신                              │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌─ Node 1 ──────────┐      ┌─ Node 2 ──────────┐
  │  kubelet           │      │  kubelet           │
  │   → Pod-1 실행     │      │   → Pod-2 실행     │
  │   → Pod-3 실행     │      │                    │
  │                    │      │                    │
  │  kube-proxy        │      │  kube-proxy        │
  │   → iptables 갱신  │      │   → iptables 갱신  │
  └────────────────────┘      └────────────────────┘
         │                              │
         └──────── LoadBalancer ────────┘
                       │
                       ▼
                  외부 클라이언트
```

### 2.3.4 수평 스케일링 (Horizontal Scaling)

```bash
# replica 수를 3으로 변경
# 1판: kubectl scale rc kubia --replicas=3
kubectl scale deployment kubia --replicas=3

kubectl get pods
# NAME            READY   STATUS    RESTARTS   AGE
# kubia-xxxxx     1/1     Running   0          5m
# kubia-yyyyy     1/1     Running   0          10s
# kubia-zzzzz     1/1     Running   0          10s
```

```bash
# 여러 번 요청하면 다른 Pod가 응답한다 (로드밸런싱)
curl 104.155.74.57:8080   # You've hit kubia-xxxxx
curl 104.155.74.57:8080   # You've hit kubia-zzzzz
curl 104.155.74.57:8080   # You've hit kubia-yyyyy
```

```
스케일링 후:

  Service (kubia-http) ─── LoadBalancer
       │
       ├──► Pod kubia-xxxxx (Node 1)
       ├──► Pod kubia-yyyyy (Node 2)
       └──► Pod kubia-zzzzz (Node 1)
```

**핵심**: 애플리케이션 코드를 변경할 필요 없이, 명령어 한 줄로 스케일링이 된다. Kubernetes가 알아서 새 Pod를 적절한 노드에 배치한다.

### 2.3.5 앱이 어느 노드에서 실행되는지 확인

```bash
kubectl get pods -o wide

# NAME         READY  STATUS   IP           NODE
# kubia-xxxxx  1/1    Running  10.244.0.5   gke-kubia-...-1
# kubia-yyyyy  1/1    Running  10.244.1.3   gke-kubia-...-2
# kubia-zzzzz  1/1    Running  10.244.0.6   gke-kubia-...-1
```

**핵심 포인트**: 개발자는 Pod가 어느 노드에서 실행되는지 **신경 쓸 필요 없다**. Kubernetes 스케줄러가 각 노드의 리소스 상황을 보고 자동 배치한다. 앱 입장에서는 노드가 1개든 100개든 동일하게 동작한다.

### 2.3.6 Kubernetes Dashboard

```bash
# Minikube
minikube dashboard

# GKE
kubectl cluster-info | grep dashboard
```

Dashboard에서 Pod, Service, ReplicationController 등을 **GUI로 확인/관리**할 수 있다.

---

## 보충: Docker 이미지 레이어 심화

### 레이어 구조

```
┌─────────────────────────┐  ← 컨테이너 실행 시 추가 (R/W)
│   Writable Layer        │
├─────────────────────────┤
│   ENTRYPOINT node app   │  Layer 4 (Read-Only)
├─────────────────────────┤
│   RUN npm install       │  Layer 3 (Read-Only)
├─────────────────────────┤
│   COPY . /app           │  Layer 2 (Read-Only)
├─────────────────────────┤
│   FROM node:20-alpine   │  Layer 1 (Base - Read-Only)
└─────────────────────────┘
```

### 나쁜 예: 레이어 캐시를 못 쓰는 Dockerfile

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install
EXPOSE 3000
ENTRYPOINT ["node", "app.js"]
```

**문제**: `COPY . .`에서 소스코드가 변경되면 → 그 아래 모든 레이어 캐시 무효화 → `npm install`이 매번 재실행

### 좋은 예: 레이어 캐시를 활용하는 Dockerfile

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
ENTRYPOINT ["node", "app.js"]
```

캐시 흐름 (소스코드만 수정했을 때):

| Layer | 명령 | 결과 |
|-------|------|------|
| 1 | `FROM node:20-alpine` | ✅ 캐시 히트 |
| 2 | `COPY package*.json` | ✅ 캐시 히트 |
| 3 | `RUN npm ci` | ✅ 캐시 히트 |
| 4 | `COPY . .` | 🔄 재빌드 |
| 5 | `ENTRYPOINT` | 🔄 재빌드 |

### 레이어 최적화 원칙

| 원칙 | 이유 |
|------|------|
| 변경 빈도 낮은 것 → 위에 | 캐시 히트율 극대화 |
| 변경 빈도 높은 것 → 아래에 | 캐시 무효화 범위 최소화 |
| RUN 명령 합치기 | 불필요한 레이어 수 줄이기 |
| .dockerignore 활용 | COPY 레이어 크기 줄이기 |

### RUN 합치기

```dockerfile
# 나쁜 예 - 레이어 3개 (중간 레이어에 캐시 찌꺼기 남음)
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# 좋은 예 - 레이어 1개
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

삭제(`rm`)해도 **이전 레이어에는 여전히 존재**하기 때문에 하나의 RUN으로 합쳐야 이미지 크기가 줄어든다.

### Multi-stage Build

```dockerfile
# ── Stage 1: Build ──
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 2: Runtime ──
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY --from=builder /app/dist ./dist
EXPOSE 3000
ENTRYPOINT ["node", "dist/main.js"]
```

```
Single-stage:  ~800MB  (node_modules + devDeps + 소스 + 빌드도구)
Multi-stage:   ~150MB  (런타임 deps + 빌드 결과물만)
```

---

## 보충: Docker 대안 — Podman

| 특징 | Docker | Podman |
|------|--------|--------|
| 데몬 | dockerd 필요 | Daemonless (데몬 없음) |
| 권한 | 기본 root | Rootless (root 불필요) |
| CLI | `docker ...` | `podman ...` (호환) |
| Pod 지원 | 없음 (Compose 사용) | 네이티브 Pod 지원 |
| 기본 탑재 | 대부분 | RHEL/Fedora |

`alias docker=podman` 하면 거의 그대로 사용 가능.

---

## Questions

- 컨테이너와 VM의 근본적인 차이는? → 컨테이너는 커널을 공유하고 Linux 네임스페이스/cgroups로 격리. VM은 하이퍼바이저 위에 별도 OS 커널 실행.
- Pod이 죽으면 데이터는? → Pod 내부 파일시스템은 사라진다. 영속 데이터는 Volume을 써야 한다 (ch06).
- ReplicationController vs ReplicaSet? → RC는 레거시. ReplicaSet이 후속이며 더 유연한 label selector 지원 (ch04).
