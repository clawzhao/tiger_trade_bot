# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying Tiger Trade Bot.

## Prerequisites

- kubectl configured to access your cluster
- A Docker image built and pushed to a registry accessible by the cluster
- Ingress controller installed (if using Ingress)
- StorageClass configured (for PVC)

## Manifests

- `configmap.yaml`: Application configuration (non-sensitive)
- `secret.yaml`: Sensitive credentials (tiger-id, account-id, private key)
- `deployment.yaml`: Pod deployment with probes and resource limits
- `service.yaml`: Internal ClusterIP service exposing health/metrics ports
- `hpa.yaml`: Horizontal Pod Autoscaler (CPU/Memory based)
- `ingress.yaml`: Ingress routes for `/health` and `/metrics`
- `pvc.yaml`: PersistentVolumeClaim for database and logs storage

## Deployment Steps

1. **Update image and host**: Edit `deployment.yaml` and `ingress.yaml` to set your Docker image and ingress host.

2. **Create secret**:
   ```bash
   kubectl create secret generic tiger-trade-bot-secret \
     --from-literal=tiger-id='YOUR_TIGER_ID' \
     --from-literal=account-id='YOUR_ACCOUNT_ID' \
     --from-file=rsa-private-key=./path/to/rsa_private_key.pem
   ```
   Alternatively, edit `k8s/secret.yaml` with base64 encoded values and apply.

3. **Apply all manifests**:
   ```bash
   kubectl apply -f k8s/
   ```

4. **Verify**:
   ```bash
   kubectl get pods,svc,ingress,hpa -l app=tiger-trade-bot
   ```

5. **Check logs**:
   ```bash
   kubectl logs -f deployment/tiger-trade-bot
   ```

6. **Access endpoints**:
   - Health: `http://<INGRESS_HOST>/health/live` and `/health/ready`
   - Metrics: `http://<INGRESS_HOST>/metrics` (Prometheus scrape)

## Notes

- The app uses Ports 8080 (health) and 9090 (metrics) inside the container.
- The deployment mounts a PVC at `/data` to persist the SQLite DB across pod restarts. Logs are ephemeral (`emptyDir`).
- Resource limits are tuned for a Raspberry Pi (low memory). Adjust `resources` in `deployment.yaml` for your environment.
- For production, use a managed database (PostgreSQL) and update `DATABASE_URL` via ConfigMap or Secret.
- Ingress host must be configured in your DNS to point to the ingress controller's external IP.
