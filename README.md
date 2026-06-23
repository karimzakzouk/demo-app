# demo-app

A small FastAPI demo service for testing K8s deployments.

## Endpoints

- `GET /` — service info
- `GET /healthz` — liveness probe
- `GET /readyz` — readiness probe
- `GET /pay?amount=N` — fake payment endpoint

## Run

```bash
docker build -t demo-app .
docker run -p 8000:8000 demo-app
```
