---
name: Kubernetes Agent
description: Manages deployment, service, autoscaling, and ingress for the bot on a Kubernetes cluster.
usage: |
  The k8s agent provides manifests in `k8s/`:
  - `deployment.yaml`: Pod specs with resource limits and probes
  - `service.yaml`: ClusterIP exposing health and metrics ports
  - `hpa.yaml`: Horizontal Pod Autoscaler for CPU/Memory
  - `ingress.yaml`: HTTP routes to health/metrics endpoints
  - `configmap.yaml` and `secret.yaml`: configuration and credentials
  - `pvc.yaml`: persistent storage for the SQLite DB
examples:
  - Deploy all: `kubectl apply -f k8s/`
  - Check status: `kubectl get pods,svc,ingress,hpa -l app=tiger-trade-bot`
reference: k8s/, README.md (Kubernetes Deployment section)
---