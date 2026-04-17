---
tags: [kubernetes, ch02, docker]
---

# Chapter 2: First steps with Docker and Kubernetes

## Key Concepts

- Docker 이미지는 **읽기 전용 레이어들의 스택**이다
- Dockerfile의 각 명령어(`FROM`, `RUN`, `COPY` 등)가 하나의 레이어를 생성한다
- 레이어가 변경되면 그 **아래의 모든 레이어 캐시가 무효화**된다
- 따라서 변경 빈도가 낮은 것을 위에, 높은 것을 아래에 배치해야 한다

## Notes

### Docker 레이어 구조

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

# 소스 전체를 먼저 복사
COPY . .

# 코드가 1줄만 바뀌어도 npm install이 다시 실행됨!
RUN npm install

EXPOSE 3000
ENTRYPOINT ["node", "app.js"]
```

**문제**: `COPY . .`에서 소스코드가 변경되면 → 그 아래 모든 레이어 캐시 무효화 → `npm install`이 매번 재실행 (수 분 소요)

### 좋은 예: 레이어 캐시를 활용하는 Dockerfile

```dockerfile
FROM node:20-alpine
WORKDIR /app

# 1) 의존성 파일만 먼저 복사 (잘 안 바뀜)
COPY package.json package-lock.json ./

# 2) 의존성 설치 (package.json이 안 바뀌면 캐시 히트!)
RUN npm ci --production

# 3) 소스코드 복사 (자주 바뀜 → 맨 아래에 배치)
COPY . .

EXPOSE 3000
ENTRYPOINT ["node", "app.js"]
```

캐시 흐름 (소스코드만 수정했을 때):

| Layer | 명령 | 결과 |
|-------|------|------|
| 1 | `FROM node:20-alpine` | ✅ 캐시 히트 |
| 2 | `COPY package*.json` | ✅ 캐시 히트 (package.json 안 바뀜) |
| 3 | `RUN npm ci` | ✅ 캐시 히트 (의존성 안 바뀜) |
| 4 | `COPY . .` | 🔄 재빌드 (소스 변경) |
| 5 | `ENTRYPOINT` | 🔄 재빌드 (상위 레이어 변경) |

→ npm install 스킵! 빌드 시간 **수 분 → 수 초**

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

빌드 도구는 최종 이미지에 필요 없다. 빌드 스테이지와 런타임 스테이지를 분리:

```dockerfile
# ── Stage 1: Build ──
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build        # dist/ 생성

# ── Stage 2: Runtime ──
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production  # devDependencies 제외
COPY --from=builder /app/dist ./dist

EXPOSE 3000
ENTRYPOINT ["node", "dist/main.js"]
```

```
Single-stage:  ~800MB  (node_modules + devDeps + 소스 + 빌드도구)
Multi-stage:   ~150MB  (런타임 deps + 빌드 결과물만)
```

### Docker 대안: Podman

| 특징 | Docker | Podman |
|------|--------|--------|
| 데몬 | dockerd 필요 | Daemonless (데몬 없음) |
| 권한 | 기본 root | Rootless (root 불필요) |
| CLI | `docker ...` | `podman ...` (호환) |
| Pod 지원 | 없음 (Compose 사용) | 네이티브 Pod 지원 |
| 기본 탑재 | 대부분 | RHEL/Fedora |

`alias docker=podman` 하면 거의 그대로 사용 가능.

## Questions

