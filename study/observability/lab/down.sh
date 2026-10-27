#!/usr/bin/env bash
# Observability 실습 클러스터 삭제 (kind 클러스터만 지운다. 다른 클러스터·컨테이너는 건드리지 않음)
set -euo pipefail
kind delete cluster --name observability
