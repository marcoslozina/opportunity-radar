# Skill: Performance Testing

## Principio base
Testear correctitud no es testear performance. Un sistema que pasa todos los tests
puede caerse con 100 usuarios concurrentes. Performance se testea explícitamente.

---

## Tipos de tests de performance

| Tipo | Qué mide | Cuándo correr |
|------|----------|---------------|
| **Load test** | Comportamiento bajo carga esperada | Antes de cada release |
| **Stress test** | Punto de quiebre del sistema | Al diseñar la arquitectura |
| **Spike test** | Respuesta a picos repentinos | Para sistemas con tráfico variable |
| **Soak test** | Degradación bajo carga sostenida (memory leaks) | Periódicamente en staging |
| **Baseline** | Métricas de referencia en reposo | Al inicio del proyecto |

---

## k6 — tool principal (recomendado)

```javascript
// tests/performance/load_test.js
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

// Métricas custom
const errorRate = new Rate('error_rate')
const createUserDuration = new Trend('create_user_duration')

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // ramp up: 0 → 10 usuarios
    { duration: '5m', target: 10 },   // carga sostenida: 10 usuarios
    { duration: '2m', target: 50 },   // ramp up: 10 → 50 usuarios
    { duration: '5m', target: 50 },   // carga sostenida: 50 usuarios
    { duration: '2m', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% de requests < 500ms
    http_req_failed: ['rate<0.01'],    // < 1% de errores
    error_rate: ['rate<0.05'],
  },
}

export default function () {
  // Crear usuario
  const start = Date.now()
  const res = http.post(
    'http://localhost:8080/users',
    JSON.stringify({ name: 'Test User', email: `test_${__VU}_${__ITER}@test.com` }),
    { headers: { 'Content-Type': 'application/json' } }
  )

  createUserDuration.add(Date.now() - start)
  errorRate.add(res.status !== 201)

  check(res, {
    'status is 201': (r) => r.status === 201,
    'response has id': (r) => JSON.parse(r.body).id !== undefined,
    'duration < 500ms': (r) => r.timings.duration < 500,
  })

  sleep(1)
}
```

```bash
# Correr test
k6 run tests/performance/load_test.js

# Con output a influxdb para Grafana
k6 run --out influxdb=http://localhost:8086/k6 tests/performance/load_test.js
```

---

## Locust — alternativa Python

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class UserBehavior(HttpUser):
    wait_time = between(1, 3)  # espera entre requests

    def on_start(self):
        # Setup por usuario virtual
        self.token = self.login()

    def login(self) -> str:
        res = self.client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "testpass"
        })
        return res.json()["token"]

    @task(3)  # peso: se ejecuta 3x más que otros tasks
    def get_products(self):
        self.client.get("/products", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def create_order(self):
        self.client.post("/orders",
            json={"product_id": "abc-123", "quantity": 1},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

```bash
# UI web en localhost:8089
locust -f tests/performance/locustfile.py --host=http://localhost:8080

# Headless
locust -f tests/performance/locustfile.py --host=http://localhost:8080 \
  --users 50 --spawn-rate 5 --run-time 10m --headless
```

---

## SLOs — definir antes de testear

```yaml
# Definir los SLOs del servicio antes de escribir los tests
slos:
  availability: 99.9%          # máximo 8.7h de downtime por año
  latency:
    p50: < 100ms
    p95: < 500ms
    p99: < 2000ms
  error_rate: < 0.1%
  throughput: > 1000 req/s     # capacidad mínima esperada
```

Los thresholds de k6/Locust deben reflejar estos SLOs.

---

## Profiling — encontrar el cuello de botella

```python
# Python: cProfile + snakeviz
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# código a profilear
result = expensive_operation()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # top 20 funciones más lentas
```

```bash
# Visualizar con snakeviz
pip install snakeviz
python -m cProfile -o output.prof my_script.py
snakeviz output.prof
```

### Señales de problemas comunes

| Síntoma | Causa probable | Investigar |
|---------|---------------|-----------|
| Latencia sube con el tiempo | Memory leak | Heap profiler, GC metrics |
| Latencia alta solo en p99 | Outliers / GC pauses | Trace p99 requests |
| Throughput bajo con CPU baja | I/O bound | Queries lentas, llamadas externas |
| Throughput bajo con CPU alta | CPU bound | Profiler de CPU |
| Latencia sube bajo carga | Contención de locks | DB connection pool, mutex |
| Errores 503 bajo carga | Capacity limit | Auto-scaling config |

---

## Performance en CI

```yaml
# .github/workflows/ci.yml — agregar stage de performance
performance:
  name: Performance Baseline
  runs-on: ubuntu-latest
  needs: integration-tests
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - name: Start app
      run: docker compose up -d
    - name: Run k6 baseline
      uses: grafana/k6-action@v0.3.1
      with:
        filename: tests/performance/baseline.js
    - name: Assert thresholds
      run: |
        # Falla el pipeline si los SLOs no se cumplen
        # k6 ya maneja esto con los thresholds definidos
        echo "Performance check complete"
```

---

## Checklist antes de release

- [ ] Load test con carga esperada pasa los SLOs
- [ ] Stress test identifica el punto de quiebre (¿cuánto aguanta?)
- [ ] Sin memory leaks en soak test de 30 minutos
- [ ] Queries de DB tienen EXPLAIN ANALYZE revisado
- [ ] Índices creados para los access patterns de producción
- [ ] Connection pool dimensionado para la carga esperada
- [ ] Auto-scaling configurado con métricas correctas

---

## Decisiones comunes en Performance

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Tool:** k6 vs Locust vs Gatling vs JMeter
- **Dónde correr:** local vs CI vs ambiente dedicado
- **SLOs:** definir p95 y p99 según tipo de operación
- **Caching:** qué cachear, TTL, estrategia de invalidación
- **DB indexes:** cuáles crear según los access patterns reales
