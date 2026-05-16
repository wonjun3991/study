---
tags: [kubernetes, ch07, configmap, secret, configuration]
---

# Chapter 7: ConfigMaps and Secrets — configuring applications

> 앱 코드와 설정을 분리하라. 같은 이미지를 dev/staging/prod에서 재사용하려면 설정을 외부에서 주입해야 한다.

## 핵심 한 줄 요약

**ConfigMap = 일반 설정, Secret = 민감 설정.** 둘 다 Pod에 **env** 또는 **볼륨 파일**로 주입. 이미지 재빌드 없이 환경별 설정 교체 가능.

---

## 1. 설정 주입의 네 가지 레벨

| 방법 | 용도 | 예시 |
|------|------|------|
| **1. command/args** | 이미지의 `ENTRYPOINT`/`CMD` 오버라이드 | `args: ["2"]` |
| **2. env 하드코딩** | 환경변수 직접 값 | `env: [{name: X, value: "10"}]` |
| **3. ConfigMap/Secret → env** | 외부화된 설정 주입 | `valueFrom.configMapKeyRef` |
| **4. ConfigMap/Secret → 볼륨** | 파일로 마운트 (설정 파일, 인증서) | `volumes.configMap.name` |

**선택 기준**:
- 값 1~3개, 간단 → env
- 값 여러 개, 관련성 있음 → envFrom + ConfigMap 전체
- 설정 파일 형식 필요 (nginx.conf, application.yaml) → 볼륨 마운트
- 런타임 업데이트 필요 → 반드시 볼륨 마운트 (env는 Pod 재생성해야 바뀜)

---

## 2. 이미지의 ENTRYPOINT/CMD 이해 (기초)

### Dockerfile
```dockerfile
ENTRYPOINT ["/bin/fortuneloop.sh"]   # 실행할 명령 (바꾸지 말 것)
CMD ["10"]                           # 기본 인자 (덮어쓸 수 있음)
```

### Pod YAML에서 오버라이드
```yaml
containers:
- image: luksa/fortune:args
  command: ["/bin/fortuneloop.sh"]  # ENTRYPOINT 덮어쓰기 (드물게)
  args: ["2"]                        # CMD 덮어쓰기 (자주)
```

**규칙**: `command` → Dockerfile의 `ENTRYPOINT` 대체. `args` → `CMD` 대체.

---

## 3. ConfigMap

### 생성 방법 3가지

#### 3.1 리터럴로
```bash
kubectl create configmap fortune-config \
  --from-literal=sleep-interval=25 \
  --from-literal=disable-cache=true
```

#### 3.2 파일로
```bash
kubectl create configmap fortune-config \
  --from-file=my-nginx-config.conf        # 파일명이 key
kubectl create configmap fortune-config \
  --from-file=customkey=my-nginx-config.conf  # key 지정
```

#### 3.3 디렉토리로
```bash
kubectl create configmap fortune-config \
  --from-file=./configmap-files/          # 각 파일이 key가 됨
```

#### 3.4 YAML로
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fortune-config
data:
  sleep-interval: "25"
  my-nginx-config.conf: |
    server {
      listen 80;
      ...
    }
```

### Pod에 주입하는 3가지 방법

#### A. 개별 env 변수로 (valueFrom)
```yaml
env:
- name: INTERVAL
  valueFrom:
    configMapKeyRef:
      name: fortune-config
      key: sleep-interval
```

#### B. ConfigMap 전체를 env로 (envFrom)
```yaml
envFrom:
- prefix: CONFIG_           # optional, 충돌 방지용
  configMapRef:
    name: fortune-config
```
→ `CONFIG_sleep-interval`, `CONFIG_disable-cache` 같이 전부 주입.

⚠️ **하이픈 함정** (실습에서 확인): 현재 Kubernetes는 하이픈이 포함된 env 이름도 기술적으로는 설정하지만, **shell에서 참조 불가능**함:
- `$CONFIG_sleep-interval` → shell이 `$CONFIG_sleep`으로 파싱, 뒤 `-interval`은 리터럴
- `printenv CONFIG_sleep-interval` → exit code 1 (invalid name)

실전에서는 **ConfigMap key 이름을 SCREAMING_SNAKE_CASE로 쓰는 게 안전**. 하이픈 있는 key는 `envFrom` 대신 `valueFrom`으로 개별 주입하면서 env 이름을 재지정.

#### C. args에 $(VAR) 치환
```yaml
env:
- name: INTERVAL
  valueFrom: { configMapKeyRef: { name: fortune-config, key: sleep-interval } }
args: ["$(INTERVAL)"]
```

#### D. 볼륨으로 파일 마운트
```yaml
volumes:
- name: config
  configMap:
    name: fortune-config
containers:
- volumeMounts:
  - name: config
    mountPath: /etc/nginx/conf.d
    readOnly: true
```
→ ConfigMap의 각 key가 **별도 파일**로 마운트됨.

### items로 선택적 마운트
```yaml
volumes:
- name: config
  configMap:
    name: fortune-config
    items:
    - key: my-nginx-config.conf
      path: gzip.conf            # 파일명 rename
```

### subPath로 단일 파일만 덮어쓰기
⚠️ **중요**: `mountPath`에 디렉토리 전체를 마운트하면 기존 파일이 **숨겨짐**. 특정 파일만 오버레이하려면:
```yaml
volumeMounts:
- name: config
  mountPath: /etc/someservice/config.json
  subPath: myconfig.json
```

### defaultMode로 권한 지정
```yaml
configMap:
  name: fortune-config
  defaultMode: 0660            # 기본 0644
```

---

## 4. 런타임 업데이트 (중요 포인트)

### env vs 볼륨
- **env**: Pod 재생성해야만 반영. 런타임 변경 불가.
- **볼륨 마운트**: **자동 반영** (최대 60초 + kubelet sync 지연)

```bash
# ConfigMap 수정
kubectl edit configmap fortune-config

# 잠시 후 Pod 내부에서 확인
kubectl exec <pod> -- cat /etc/nginx/conf.d/my-nginx-config.conf
```

⚠️ **nginx는 파일이 바뀌어도 reload 안 함.** 애플리케이션 쪽에서 파일 watch 또는 SIGHUP 필요.

### subPath의 함정
`subPath`로 마운트된 파일은 **업데이트되지 않음** (inode가 고정됨). 런타임 업데이트 필요하면 subPath 쓰지 말 것.

---

## 5. Secret

### ConfigMap과 차이점

| 항목 | ConfigMap | Secret |
|------|-----------|--------|
| 인코딩 | plain text | base64 |
| 저장 | etcd 그대로 | etcd에 base64 (선택적 암호화) |
| 메모리 | 디스크 | **tmpfs (RAM)** |
| 크기 제한 | 1MB | 1MB |
| 용도 | 일반 설정 | 비밀번호, 토큰, 인증서 |

⚠️ **base64 ≠ 암호화.** `echo "xxx" | base64 -d`로 복호화됨. 진짜 암호화하려면 [Encryption at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/) 설정 또는 SealedSecret, External Secrets 사용.

### 생성 방법

```bash
# 파일로 (권장, 자동 base64)
kubectl create secret generic fortune-https \
  --from-file=https.key \
  --from-file=https.cert \
  --from-file=foo
```

### Secret 타입 (TYPE 필드)

| 타입 | 용도 |
|------|------|
| `Opaque` | 기본값, 임의 데이터 |
| `kubernetes.io/tls` | TLS 인증서 (키: `tls.crt`, `tls.key`) |
| `kubernetes.io/dockerconfigjson` | 프라이빗 레지스트리 접근 |
| `kubernetes.io/service-account-token` | SA 토큰 (자동 생성) |

### YAML에 넣을 때는 stringData 쓰기
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:                   # 자동으로 data(base64)로 변환됨
  username: admin
  password: s3cret
```

### 주입 방법 (ConfigMap과 거의 동일)

```yaml
# env
env:
- name: PASSWORD
  valueFrom:
    secretKeyRef:
      name: my-secret
      key: password

# 볼륨 (tmpfs로 마운트)
volumes:
- name: certs
  secret:
    secretName: fortune-https
```

### imagePullSecrets (프라이빗 이미지)

```bash
kubectl create secret docker-registry mydockerhubsecret \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=my@example.com
```

```yaml
spec:
  imagePullSecrets:
  - name: mydockerhubsecret
  containers:
  - image: username/private:tag
```

⚠️ ServiceAccount에 `imagePullSecrets` 추가하면 모든 Pod에 자동 적용됨 (편의).

---

## 5.5 External Secrets — 실전 비밀 관리 (책에 없는 현대 패턴)

### 5.5.1 왜 네이티브 Secret만으로는 부족한가

네이티브 Secret의 한계:

| 문제 | 설명 |
|------|------|
| **Git 커밋 불가** | 평문을 Git에 올리면 유출. base64는 암호화 아님 |
| **회전(rotation) 수동** | 외부 시스템에서 DB 비밀번호 바꾸면 k8s Secret도 수동 갱신 필요 |
| **감사(audit) 제한** | 누가 언제 어떤 비밀을 봤는지 추적 어려움 |
| **멀티 클러스터 동기화** | 10개 클러스터에 같은 비밀? 10번 apply 또는 복사 스크립트 |
| **소스 불일치** | "실제 진실"은 AWS Secrets Manager/Vault에 있는데 k8s에 복제본 존재 |

**핵심 아이디어**: 비밀의 **source of truth는 외부 시스템**(Vault, AWS Secrets Manager 등)에 두고, k8s Secret은 **그 투영(projection)**으로만 존재.

### 5.5.2 해법 3가지

| 방법                            | 핵심 아이디어                                 | 대표 도구                      |
| ----------------------------- | --------------------------------------- | -------------------------- |
| **SealedSecret**              | 공개키로 Git에 암호화 저장 → 클러스터 내 컨트롤러가 복호화     | `bitnami/sealed-secrets`   |
| **External Secrets Operator** | 외부 스토어(Vault, ASM, GCP SM 등)에서 주기적 sync | `external-secrets.io`      |
| **Vault Agent Injector**      | Pod에 사이드카가 Vault에서 직접 fetch             | HashiCorp Vault            |
| **CSI Secrets Store**         | 볼륨 마운트 시점에 외부에서 가져옴 (k8s Secret 경유 안 함) | `secrets-store.csi.k8s.io` |
|                               |                                         |                            |

### 5.5.3 External Secrets Operator (ESO) — 가장 널리 쓰임

#### 구조

```
┌──────────────────────────┐
│  외부 Secret Store       │
│  (AWS Secrets Manager,   │
│   HashiCorp Vault,       │
│   GCP Secret Manager,    │
│   Azure Key Vault, ...)  │
└────────┬─────────────────┘
         │ fetch (auth: IRSA / Vault Token / ...)
         ▼
┌──────────────────────────┐
│  ExternalSecrets         │
│  Controller              │   ← ESO가 여기서 동기화
└────────┬─────────────────┘
         │ create/update
         ▼
┌──────────────────────────┐
│  Kubernetes Secret       │  ← 일반 Pod은 여기만 봄 (기존 코드 호환)
└──────────────────────────┘
```

**장점**: 앱 코드는 그대로 네이티브 Secret만 참조하면 됨. ESO가 뒤에서 자동으로 최신 값 유지.

#### 핵심 리소스 3종

1. **`SecretStore`** / **`ClusterSecretStore`** — 외부 스토어 연결 정의 (네임스페이스 범위 / 클러스터 범위)
2. **`ExternalSecret`** — "이 외부 key들을 이 이름의 k8s Secret으로 동기화해줘"
3. (자동 생성) **`Secret`** — ESO가 생성/갱신

#### 예시 1: AWS Secrets Manager 연동

```yaml
# 1) ClusterSecretStore (관리자가 1회)
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
# 2) ExternalSecret (개발자)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: prod
spec:
  refreshInterval: 1h          # 1시간마다 외부에서 pull
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials       # 이 이름의 k8s Secret이 생성됨
    creationPolicy: Owner      # ESO가 삭제 시 k8s Secret도 지움
  data:
  - secretKey: username                     # k8s Secret의 key
    remoteRef:
      key: prod/db              # AWS Secrets Manager의 secret ARN
      property: username        # JSON 내부 field
  - secretKey: password
    remoteRef:
      key: prod/db
      property: password
---
# 3) 앱은 기존 방식 그대로
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:v1
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials   # ← ESO가 동기화한 Secret
              key: password
```

#### 예시 2: dataFrom으로 전체 가져오기

```yaml
spec:
  data: []     # 개별 지정 대신
  dataFrom:
  - extract:
      key: prod/db             # AWS의 secret 하나가 JSON 전체
  # → JSON의 모든 top-level key가 자동으로 k8s Secret key로 변환
```

#### 예시 3: 템플릿으로 포맷 변환

```yaml
spec:
  target:
    name: mongo-connection-string
    template:
      data:
        uri: "mongodb://{{ .username }}:{{ .password }}@mongo:27017/mydb"
  data:
  - secretKey: username
    remoteRef: { key: prod/db, property: username }
  - secretKey: password
    remoteRef: { key: prod/db, property: password }
```
→ 외부엔 username/password로 저장, k8s Secret엔 조합된 connection string으로 저장.

### 5.5.4 IRSA (AWS 환경에서 ESO 인증)

ESO가 AWS Secrets Manager를 호출하려면 IAM 권한 필요. IRSA(IAM Role for ServiceAccount) 패턴:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/ExternalSecretsRole
```

IAM Role의 trust policy에서 EKS OIDC provider + ServiceAccount 매칭. 비밀 관리용 별도 role을 쓰고 `secretsmanager:GetSecretValue` 최소 권한만 부여.

### 5.5.5 Vault 연동

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "myapp-role"
          serviceAccountRef:
            name: vault-auth-sa
```

Vault의 Kubernetes Auth Method와 연결 — Pod의 SA 토큰으로 Vault 인증.

### 5.5.6 SealedSecret vs ESO — 언제 뭘 쓸까

| 기준 | SealedSecret | External Secrets Operator |
|------|--------------|---------------------------|
| 비밀 저장 위치 | **Git 저장소** (암호화된 YAML) | **외부 KMS/Vault** |
| 회전 | Git commit 필요 | 외부에서 바꾸면 자동 sync |
| 외부 의존성 | 없음 (controller만) | 외부 secret store 필요 |
| 인프라 비용 | 저렴 | KMS 비용 (API 호출당) |
| 감사 | Git 히스토리 | 외부 스토어의 감사 로그 |
| GitOps 친화도 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (ExternalSecret은 commit, 실제 값은 외부) |
| 적합한 규모 | 소~중형 | 중~대형, 멀티 클러스터 |

**혼합 전략이 일반적**: 애플리케이션 비밀은 ESO로, 인프라 부트스트래핑 비밀(ESO가 Vault 접속하기 위한 초기 토큰 등)은 SealedSecret으로.

### 5.5.7 CSI Secrets Store — k8s Secret을 아예 안 거치는 방법

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-secrets
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "prod/db"
        objectType: "secretsmanager"
---
# Pod에서 볼륨으로 마운트
volumes:
- name: secrets
  csi:
    driver: secrets-store.csi.k8s.io
    readOnly: true
    volumeAttributes:
      secretProviderClass: db-secrets
```

**장점**:
- k8s Secret 객체 자체가 생성 안 됨 → etcd에 비밀 안 저장됨 (최상위 보안)
- Pod에서만 보임

**단점**:
- 환경변수로 주입하려면 추가 설정 필요 (syncSecret)
- 러닝 커브 높음

### 5.5.8 실무 선택 가이드

```
질문 1: 비밀 회전이 자주 필요한가?
  → YES: ESO (또는 Vault Agent)
  → NO: SealedSecret도 OK

질문 2: 이미 Vault/AWS SM 쓰고 있나?
  → YES: ESO (통합 ROI 높음)
  → NO: SealedSecret부터 시작

질문 3: etcd에 비밀이 저장되는 것도 부담스러운가? (최고 수준 보안)
  → YES: CSI Secrets Store
  → NO: ESO로 충분

질문 4: 멀티 클러스터인가?
  → YES: ESO + ClusterSecretStore
  → NO: 하나 선택해서 시작
```

### 5.5.9 주의사항 (실전 함정)

1. **refreshInterval 너무 짧게 설정 금지** — AWS Secrets Manager API는 비쌈 (1천 호출당 $0.05). 1h 권장, 긴급 시 `kubectl annotate es <name> force-sync=$(date +%s)`
2. **ESO 자체의 비밀은 어떻게?** — 닭과 달걀 문제. Vault는 k8s SA 인증(토큰 자동) 사용하면 해결. AWS는 IRSA로 IAM만.
3. **k8s Secret 삭제 정책** — `creationPolicy: Owner`면 ExternalSecret 삭제 시 k8s Secret도 삭제. Pod가 참조 중이면 런타임 에러 주의.
4. **Pod는 Secret 변경 반영 안 됨** — ESO가 k8s Secret을 업데이트해도 이미 env로 주입된 Pod에는 반영 X. 볼륨 마운트면 ~60초. 확실하게 하려면 **`reloader`** 같은 도구로 Pod 재시작 트리거.
5. **템플릿 오타 디버깅 어려움** — `kubectl describe externalsecret <name>` 의 Events에서 sync 상태 확인.

---

## 6. 책 vs 현실 차이점

| 책(2018)          | 현재(2024+)                                                                                    |
| ---------------- | -------------------------------------------------------------------------------------------- |
| ConfigMap이 핵심    | 여전히 유효                                                                                       |
| Secret = base64만 | **encryption at rest**, **SealedSecret**, **External Secrets Operator**, **Vault CSI** 사용 증가 |
| envFrom 없음       | envFrom으로 간결화 가능                                                                             |
| -                | **immutable ConfigMap/Secret** (`immutable: true`) — 변경 시 재생성 강제                             |
| -                | **Projected Volume**으로 CM + Secret + DownwardAPI 합침                                          |
| -                | **External Secrets Operator**가 사실상 표준 (AWS/Vault 연동)                                         |
| -                | **CSI Secrets Store**로 etcd 거치지 않는 방식 가능                                                     |

---

## 7. 면접 예상 질문

1. **ConfigMap과 Secret의 차이?**
   - 인코딩(base64), tmpfs 저장, TYPE 분화, 의도(일반 vs 민감)
2. **Secret은 안전한가?**
   - base64만으로는 ❌. Encryption at Rest, RBAC, SealedSecret 등 필요
3. **ConfigMap 바꾸면 Pod에 언제 반영?**
   - env: 안 됨 (Pod 재생성). 볼륨: 최대 ~60초 후 자동
4. **subPath의 함정?**
   - 업데이트 반영 안 됨 (inode 고정)
5. **이미지의 CMD vs args vs Pod spec의 command/args?**
   - Dockerfile ENTRYPOINT ↔ Pod command, Dockerfile CMD ↔ Pod args
6. **민감 정보를 Git에 올리지 않는 방법?**
   - SealedSecret(Git에 암호화), External Secrets(외부 스토어 참조)
7. **External Secrets Operator가 필요한 이유?**
   - Secret의 source of truth를 외부(Vault/AWS SM)로, 자동 회전, 멀티 클러스터 동기화, 감사
8. **SealedSecret vs ESO 선택 기준?**
   - 외부 스토어 없고 GitOps 중심 → SealedSecret. 회전 잦고 멀티 클러스터 → ESO
9. **ESO로 동기화한 Secret이 바뀌면 Pod는 자동 반영되나?**
   - **아니오**. env로 주입이면 Pod 재시작 필요, 볼륨이면 ~60초. `reloader` 같은 도구로 재시작 자동화
10. **CSI Secrets Store가 ESO보다 더 안전한 이유?**
    - k8s Secret 객체 자체가 생성 안 됨 → etcd에 비밀 미저장

---

## 실습 체크리스트

- [x] fortune-args 이미지 빌드 (CMD `["10"]` 기본값)
- [x] fortune-env 이미지 빌드 (env `INTERVAL` 읽음)
- [x] `01-args`: `args: ["2"]`로 sleep 간격 2초 확인
- [x] `02-env`: `env INTERVAL=30` 하드코딩
- [x] `03-configmap-literal`: ConfigMap 만들고 env valueFrom (INTERVAL=25)
- [x] `04-configmap-envfrom`: envFrom으로 전체 주입 + **하이픈 key 함정 실증**
- [x] `05-configmap-args`: $(INTERVAL) 치환
- [x] `06-configmap-volume`: CM을 파일로 마운트 (nginx gzip 활성화 확인)
- [x] `07-configmap-volume-items`: items로 특정 key만 mount, rename
- [x] `08-configmap-update`: CM 수정 후 ~60초 내 파일 자동 반영 + **nginx reload 안 되는 함정 실증**
- [x] `09-secret-tls`: TLS cert Secret + tmpfs 마운트 + HTTPS 접속
- [ ] `10-private-image`: imagePullSecret (YAML 보관, 실행 생략)

### 실습 관찰 메모 (2026-05-05)

- **envFrom 하이픈 함정**: `sleep-interval` 같은 하이픈 key가 `CONFIG_sleep-interval`로 env 설정은 되지만 shell에서 참조 불가 (`$CONFIG_sleep-interval` → `$CONFIG_sleep` + `-interval`로 파싱). ConfigMap key는 SCREAMING_SNAKE_CASE로.
- **ConfigMap 볼륨 업데이트**: 실측 60초 내 반영. 단 **앱 프로세스가 파일 reload 안 하면 무용지물**. nginx에서 gzip 설정 변경했지만 nginx는 여전히 gzip 응답 (책의 경고 실증).
- **Secret 마운트**: 항상 `tmpfs` (메모리). ConfigMap은 일반 파일시스템.
- **`..data/` 심볼릭 링크 구조**: CM/Secret 볼륨이 atomic update를 위해 사용하는 패턴.

---

## Key Concepts

- **ConfigMap**: 일반 설정 저장소
- **Secret**: 민감 설정 저장소 (tmpfs, base64)
- **env / envFrom / valueFrom**: 환경변수 주입 패턴
- **ConfigMap/Secret Volume**: 파일로 마운트 (런타임 업데이트 가능)
- **subPath**: 특정 파일만 오버레이 (업데이트 안 됨!)
- **imagePullSecrets**: 프라이빗 레지스트리 인증
- **External Secrets Operator (ESO)**: 외부 스토어(Vault, AWS SM 등) → k8s Secret 자동 동기화
- **SealedSecret**: 공개키로 Git에 암호화 저장
- **CSI Secrets Store**: k8s Secret 거치지 않고 볼륨에 직접 주입
- **IRSA**: EKS에서 ServiceAccount에 IAM Role 연결 (ESO 인증 경로)

## Notes

- fortune 이미지 2종:
  - `luksa/fortune:args` — `CMD ["10"]`, `$1`을 INTERVAL로 사용
  - `luksa/fortune:env` — `$INTERVAL` 환경변수 사용
- 예제는 `kubernetes-in-action/examples/Chapter07/` 원본 참고

## Questions

- 런타임 설정 변경: 앱이 SIGHUP 처리 안 하면 어떻게 reload?
- Kubernetes Secret vs HashiCorp Vault 사용 기준?
- immutable ConfigMap/Secret의 실전 장점?
- ESO에서 secret 변경 시 자동으로 Pod 재시작시키는 방법? (`stakater/reloader`?)
- ESO의 refreshInterval을 짧게 하면 AWS API 비용은 얼마나 나올까?
- 멀티 테넌트 환경에서 ClusterSecretStore 권한 분리는?
- CSI Secrets Store의 `syncSecret: true` 옵션은 언제 쓰나?
