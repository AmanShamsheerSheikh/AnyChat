# AnyChat

A multi-tenant LLM chat gateway — API-key-based tenant isolation, Redis-backed rate limiting, and a stateless GPU inference worker, deployed and tested on a local Kubernetes cluster.

This project exists specifically to demonstrate container orchestration (Docker → Kubernetes) alongside the multi-tenancy/backend depth already covered in a separate project. It is intentionally scoped narrow — one endpoint, no chat product depth — in favor of proving out auth, fair-usage enforcement, and deployment mechanics cleanly.

## Architecture

```
Client
  │  X-API-Key header
  ▼
chat_service (FastAPI)
  │  ├─ AuthMiddleWare        → resolves API key to user_id via Postgres
  │  ├─ RateLimitMiddleWare   → Redis, atomic Lua fixed-window script
  │  └─ job persistence       → Postgres (jobs table), per-request record
  │
  ├──► Postgres (via PgBouncer)   — users, jobs
  ├──► Redis                     — rate limit counters
  └──► Modal (gpu_worker)        — stateless vLLM inference, called via RPC
           │
           └─ streamed tokens ──► SSE back to client
```

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Auth | API-key → `user_id` resolution, allowlisted routes |
| Rate limiting | Redis, atomic Lua fixed-window script |
| Database | PostgreSQL + PgBouncer (connection pooling) |
| Inference | vLLM on Modal, `@modal.concurrent` for continuous batching |
| Local infra | Docker Compose (Postgres, PgBouncer, Redis) |
| Orchestration | Kubernetes (minikube) — Deployment, Service, ConfigMap, Secret, HPA |

## Endpoints

- `POST /register_user` — creates a user, returns an API key
- `POST /generate` — authenticated, rate-limited; streams tokens via SSE, persists a job record (`PENDING` → `DONE`/`FAILED`)
- `GET /health` — unauthenticated, unrated; liveness/readiness target for Kubernetes probes

## Multi-tenancy

Every `/generate` call is tied to a `user_id`, resolved once at the auth layer and persisted with the request in the `jobs` table (`user_id`, `prompt`, `status`, `result`/`error`, timestamps). This is what makes tenancy a checkable, queryable property rather than an assumption — each tenant's usage is independently attributable and isolated by `user_id`.

## Rate limiting

A single atomic Redis Lua script (`fixed_window.lua`) enforces a fixed-window limit per `api_key + IP` (5 requests / 60s for `/generate`; 1 request / hour by IP for `/register_user`). Atomicity matters here: a check-then-increment done as two separate Redis calls has a race condition under concurrent requests from the same tenant — the Lua script makes it one atomic server-side operation.

**Fail-open by design.** If Redis is unreachable, the rate limiter allows the request through rather than blocking it — a deliberate availability-over-strict-enforcement tradeoff. A stricter SLA would instead fail closed, with alerting.

## Local development (Docker Compose)

```bash
docker compose up -d --build
```

Brings up Postgres, PgBouncer, Redis, and `chat_service` together. Test:

```bash
curl -X POST http://localhost:8080/register_user \
  -H "Content-Type: application/json" \
  -d '{"user_name": "test_user"}'

curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api_key_from_above>" \
  -d '{"prompt": "hello"}'
```

## Kubernetes deployment (minikube)

`chat_service` runs as a Kubernetes Deployment (3 replicas), fronted by a `Service`, configured via `ConfigMap`/`Secret`, with a `HorizontalPodAutoscaler` on top. Postgres and Redis stay in Docker Compose, outside the cluster — `chat_service` pods reach them via `host.minikube.internal`. This was a deliberate scope decision: running Postgres/Redis *inside* Kubernetes is a materially different problem (StatefulSets, PersistentVolumeClaims, data durability across restarts) than what this project sets out to prove, and is noted as future work rather than blocking today's deployment story.

```bash
minikube start --driver=docker
minikube addons enable metrics-server

eval $(minikube docker-env)
docker build -t anychat-chat_service -f chat_service/Dockerfile .

kubectl apply -f kubernetes_setup/configmap.yaml
kubectl apply -f kubernetes_setup/secret.yaml
kubectl apply -f kubernetes_setup/deployment.yaml
kubectl apply -f kubernetes_setup/service.yaml
kubectl apply -f kubernetes_setup/hpa.yaml
```

### HPA finding: CPU is a weak signal for this workload

The HPA is CPU-based, since that's what Kubernetes' `metrics-server` supports out of the box with no additional infrastructure. Under an initial burst of 200 concurrent requests (rate limiter active), observed CPU moved from a baseline of 1% to 4% — nowhere near the 60% scaling threshold, and replica count correctly stayed at 3 rather than scaling up.

That first test has a confound worth naming honestly: most of the 200 requests were rejected almost immediately by the rate limiter, so the CPU reading likely reflects the limiter absorbing the burst more than it reflects what `/generate` costs under real, sustained traffic. A follow-up test with the rate limiter temporarily disabled is planned, to isolate whether CPU usage climbs meaningfully under genuine unthrottled load or stays low regardless — either result is informative and will be recorded here once run.

Independent of that number, the underlying reasoning holds regardless of outcome: `/generate` is mostly I/O-bound (waiting on Modal and Postgres, not computing), so **CPU-based autoscaling is a structurally weak signal for a streaming, I/O-bound workload like this one** — even a higher CPU reading under unthrottled load wouldn't change that request-count or active-connection-count per pod is the more meaningful metric here. That requires a custom metrics pipeline (Prometheus + `prometheus-adapter`) — noted below as future work rather than solved here.

## Out of scope (deliberate, not incomplete)

- **Multi-turn conversation history** — would require conversation/message tables, resending full history to the stateless Modal worker per call (context window/truncation strategy), and frontend threading. A product feature, not an infra one — doesn't serve tenant isolation, rate limiting, or the deployment story this project is built around.
- **Per-tenant configuration / billing** — not needed to demonstrate the core architecture.
- **Postgres/Redis inside Kubernetes** (StatefulSet + PersistentVolumeClaim) — a genuinely harder, separate problem (data durability across pod restarts) than the stateless `chat_service` Deployment this project focuses on.

## Future work

- **Retest HPA behavior with the rate limiter disabled** — to get a cleaner read on whether CPU usage rises under sustained, unthrottled load, isolated from the confound above.
- **Prometheus + `prometheus-adapter`** — to enable HPA scaling on request/connection count instead of CPU, the more meaningful metric for this I/O-bound workload regardless of what the retest shows.
- **Multi-turn chat history** — as a deliberate v2, after the above.

## Known limitations

- Rate limiting is fail-open on Redis failure — availability prioritized over strict enforcement.
- Local Kubernetes deployment is a learning/practice setup, not a production deployment pattern — Modal handles orchestration in the companion project, so this exists specifically to cover the Docker/Kubernetes gap.