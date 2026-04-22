# Skill: Observabilidad

## Los tres pilares

```
Logs    → QUÉ pasó (eventos discretos)
Metrics → CUÁNTO / QUÉ TAN SEGUIDO (series de tiempo)
Traces  → POR DÓNDE pasó (flujo distribuido)
```

Sin los tres, estás volando a ciegas en producción.

---

## Logging estructurado

Nunca logs de texto libre. Siempre JSON estructurado.

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger()

# ✅ Estructurado — buscable, filtrable
log.info("user.login", user_id=user.id, ip=mask_ip(request.ip), success=True)
log.error("payment.failed", user_id=user.id, error_code="INSUFFICIENT_FUNDS", amount_cents=1000)

# ❌ Texto libre — imposible de analizar en volumen
logging.info(f"User {user.email} logged in from {request.ip}")
```

### Campos obligatorios en cada log

```python
{
    "timestamp": "2026-04-20T14:32:00Z",  # ISO 8601
    "level": "info",
    "service": "user-service",             # nombre del servicio
    "version": "1.4.2",                    # versión deployada
    "request_id": "uuid",                  # trazabilidad por request
    "user_id": "abc",                      # contexto de negocio (si aplica)
    "event": "user.login",                 # qué pasó (dominio.acción)
    "duration_ms": 45                      # latencia cuando aplica
}
```

### Niveles — cuándo usar cada uno

| Nivel | Cuándo | Ejemplo |
|-------|--------|---------|
| `debug` | Solo en dev, nunca en prod | Estado interno, variables intermedias |
| `info` | Eventos de negocio normales | Login, pago procesado, orden creada |
| `warn` | Algo raro pero no crítico | Retry intento 2/3, config fallback |
| `error` | Fallo que requiere atención | Exception, timeout, dato inválido |
| `critical` | Sistema comprometido | DB caída, secret rotado, servicio down |

---

## Métricas con OpenTelemetry

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

provider = MeterProvider()
metrics.set_meter_provider(provider)
meter = metrics.get_meter("user-service")

# Contadores
requests_total = meter.create_counter(
    "http_requests_total",
    description="Total HTTP requests",
)

# Histogramas (latencia)
request_duration = meter.create_histogram(
    "http_request_duration_ms",
    description="HTTP request duration in milliseconds",
)

# Gauges (estado actual)
active_connections = meter.create_up_down_counter(
    "db_connections_active",
    description="Active database connections",
)

# Uso
def handle_request(method: str, path: str):
    start = time.time()
    try:
        result = process()
        requests_total.add(1, {"method": method, "path": path, "status": "200"})
        return result
    except Exception as e:
        requests_total.add(1, {"method": method, "path": path, "status": "500"})
        raise
    finally:
        duration = (time.time() - start) * 1000
        request_duration.record(duration, {"method": method, "path": path})
```

### Métricas mínimas por servicio

```
http_requests_total{method, path, status}       # volumen y error rate
http_request_duration_ms{method, path}          # latencia (p50, p95, p99)
db_query_duration_ms{query_type}                # latencia de DB
db_connections_active                           # pool de conexiones
cache_hits_total / cache_misses_total           # hit rate de cache
queue_depth{queue_name}                         # profundidad de cola
business_events_total{event_type}              # métricas de negocio
```

---

## Tracing distribuido con OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("user-service")

# Cada operación significativa = un span
def create_user(name: str, email: str) -> UserId:
    with tracer.start_as_current_span("create_user") as span:
        span.set_attribute("user.email_domain", email.split("@")[1])

        with tracer.start_as_current_span("db.save_user"):
            user_id = db.save(name, email)

        with tracer.start_as_current_span("email.send_welcome"):
            email_service.send_welcome(email)

        span.set_attribute("user.id", str(user_id))
        return user_id
```

**Propagación de trace entre servicios:**
```python
# Inyectar en headers HTTP salientes
from opentelemetry.propagate import inject
headers = {}
inject(headers)
requests.post(url, headers=headers)

# Extraer en headers HTTP entrantes (middleware)
from opentelemetry.propagate import extract
context = extract(request.headers)
```

---

## Stack recomendado

| Herramienta | Qué hace | Cuándo usar |
|-------------|----------|-------------|
| OpenTelemetry | Instrumentación estándar | Siempre — es el estándar |
| Prometheus | Scraping de métricas | Self-hosted / Kubernetes |
| Grafana | Dashboards | Self-hosted |
| Datadog | APM + logs + métricas | Managed, enterprise |
| AWS CloudWatch | Logs + métricas en AWS | Si ya usás AWS |
| Jaeger / Tempo | Tracing | Self-hosted |

---

## Alertas — qué monitorear siempre

```yaml
# Reglas mínimas de alerta
- name: HighErrorRate
  condition: rate(http_requests_total{status="5xx"}[5m]) > 0.05
  message: "Error rate > 5% en los últimos 5 minutos"

- name: HighLatency
  condition: histogram_quantile(0.99, http_request_duration_ms) > 2000
  message: "p99 latencia > 2s"

- name: DBConnectionPoolExhausted
  condition: db_connections_active / db_connections_max > 0.9
  message: "Pool de conexiones al 90%"

- name: QueueDepthHigh
  condition: queue_depth > 10000
  message: "Cola acumulando — posible consumer caído"
```

---

## Health checks

```python
from fastapi import FastAPI
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@app.get("/health/live")   # ¿El proceso está vivo? (Kubernetes liveness)
async def liveness():
    return {"status": HealthStatus.HEALTHY}

@app.get("/health/ready")  # ¿Puede recibir tráfico? (Kubernetes readiness)
async def readiness():
    checks = {
        "database": await check_db(),
        "cache": await check_redis(),
    }
    status = HealthStatus.HEALTHY if all(checks.values()) else HealthStatus.UNHEALTHY
    return {"status": status, "checks": checks}
```

---

## Decisiones comunes en Observabilidad

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Stack:** OpenTelemetry + Grafana/Prometheus vs Datadog vs CloudWatch
- **Log aggregation:** ELK (Elasticsearch) vs Loki vs CloudWatch Logs
- **Alerting:** PagerDuty vs OpsGenie vs AlertManager
- **Sampling de traces:** 100% vs probabilístico vs tail-based
