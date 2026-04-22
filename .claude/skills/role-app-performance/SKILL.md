# Skill: Application Performance

## Rol
Identificar y eliminar cuellos de botella reales, no percibidos. Sin profiling no hay optimización —
la intuición sobre performance falla el 90% del tiempo. Medir primero, optimizar después.

## Cuándo activar este skill
- La aplicación es lenta y no se sabe por qué
- Se va a diseñar un sistema con requerimientos de latencia o throughput
- Code review de código que toca DB, red o procesamiento intensivo
- Se detectan queries N+1, caché ausente o estructuras de datos incorrectas

---

## Regla de oro

```
NUNCA optimizar sin medir primero.
Profile → identifica el cuello de botella real → optimiza → mide de nuevo.
```

La optimización prematura es la raíz de todos los males (Knuth). El código lento y correcto
es mejor que el código rápido e incorrecto.

---

## Complejidad algorítmica — Big O

| Complejidad | Nombre | Escala con N=1M |
|-------------|--------|-----------------|
| O(1) | Constante | 1 op |
| O(log n) | Logarítmica | ~20 ops |
| O(n) | Lineal | 1.000.000 ops |
| O(n log n) | Linealítmica | ~20.000.000 ops |
| O(n²) | Cuadrática | 1.000.000.000.000 ops — PELIGRO |
| O(2ⁿ) | Exponencial | No escala |

**Señales de alerta en código:**
```python
# ❌ O(n²) — loop dentro de loop sobre colecciones
for user in users:
    for order in orders:  # si orders crece, esto explota
        if order.user_id == user.id: ...

# ✅ O(n) — lookup en O(1) con dict/map
orders_by_user = {o.user_id: o for o in orders}
for user in users:
    order = orders_by_user.get(user.id)
```

---

## Perfilado por lenguaje

### Python
```bash
# CPU profiling
python -m cProfile -s cumulative app.py
python -m cProfile -o output.prof app.py && snakeviz output.prof

# Memory profiling
pip install memory-profiler
@profile  # decorador en la función a medir
python -m memory_profiler app.py

# Line-by-line
pip install line_profiler
@profile
def hot_function(): ...
kernprof -l -v app.py
```

### Go
```go
import _ "net/http/pprof"
// Exponer en :6060/debug/pprof
go tool pprof http://localhost:6060/debug/pprof/profile
go tool pprof http://localhost:6060/debug/pprof/heap
```

### Java
```bash
# JVM flags para profiling
-XX:+FlightRecorder -XX:StartFlightRecording=duration=60s,filename=app.jfr
# Visualizar con JDK Mission Control
```

### TypeScript/Node
```bash
node --prof app.js
node --prof-process isolate-*.log > processed.txt
# O usar clinic.js
npx clinic doctor -- node app.js
```

---

## Database performance

### N+1 — el problema más común

```python
# ❌ N+1: 1 query para users + N queries para orders
users = db.query(User).all()
for user in users:
    print(user.orders)  # query por cada usuario

# ✅ Eager loading: 2 queries total
users = db.query(User).options(joinedload(User.orders)).all()
```

### Indexing — reglas base

```sql
-- Indexar columnas usadas en WHERE, JOIN, ORDER BY
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Índice compuesto: columna más selectiva primero
CREATE INDEX idx_orders_status_user ON orders(status, user_id);

-- EXPLAIN para verificar que el índice se usa
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;
```

### Query optimization

```sql
-- ❌ SELECT * trae columnas innecesarias
SELECT * FROM users WHERE active = true;

-- ✅ Solo las columnas necesarias
SELECT id, email, name FROM users WHERE active = true;

-- ❌ LIKE con wildcard al inicio no usa índice
SELECT * FROM users WHERE email LIKE '%@gmail.com';

-- ✅ Wildcard solo al final usa índice
SELECT * FROM users WHERE email LIKE 'marco%';
```

---

## Caching — estrategias

| Estrategia | Cuándo | TTL recomendado |
|-----------|--------|-----------------|
| **Cache-aside** | Reads frecuentes, datos cambian poco | Minutos-horas |
| **Write-through** | Consistencia crítica | Sin TTL, invalidar on write |
| **Write-behind** | Writes frecuentes, consistencia eventual ok | Segundos |
| **Read-through** | Transparente para el cliente | Minutos |

```python
# Cache-aside con Redis
def get_user(user_id: str) -> User:
    cached = redis.get(f"user:{user_id}")
    if cached:
        return User.from_json(cached)

    user = db.query(User).filter_by(id=user_id).first()
    redis.setex(f"user:{user_id}", ttl=300, value=user.to_json())
    return user

# Invalidar en writes
def update_user(user_id: str, data: dict) -> User:
    user = db.update(user_id, data)
    redis.delete(f"user:{user_id}")  # invalidar caché
    return user
```

---

## Connection pooling

```python
# ❌ Nueva conexión por request — caro
def get_user(id):
    conn = psycopg2.connect(DATABASE_URL)  # costoso
    ...
    conn.close()

# ✅ Pool de conexiones reutilizables
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
```

```go
// Go: configurar pool en sql.DB
db, _ := sql.Open("postgres", dsn)
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(10)
db.SetConnMaxLifetime(5 * time.Minute)
```

---

## Memory management

### Python
```python
# Generators en vez de listas para grandes volúmenes
# ❌ Carga todo en memoria
def get_all_users():
    return db.query(User).all()  # 1M users en RAM

# ✅ Streaming con generator
def get_all_users():
    yield from db.query(User).yield_per(1000)
```

### Go
```go
// Reusar buffers con sync.Pool
var bufPool = sync.Pool{
    New: func() interface{} { return new(bytes.Buffer) },
}

func process() {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()
}
```

---

## HTTP performance

```typescript
// Compresión — reducir tamaño de respuesta
app.use(compression())

// HTTP caching headers
res.set('Cache-Control', 'public, max-age=3600')
res.set('ETag', hash(data))

// Paginación con cursor (más eficiente que offset en tablas grandes)
// ❌ OFFSET escala mal
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 10000;

// ✅ Cursor-based pagination
SELECT * FROM orders WHERE id > :last_id ORDER BY id LIMIT 20;
```

---

## Checklist de performance review

- [ ] ¿Hay loops anidados sobre colecciones grandes? (señal de O(n²))
- [ ] ¿Las queries tienen índices en las columnas del WHERE y JOIN?
- [ ] ¿Se está usando SELECT * donde no corresponde?
- [ ] ¿Hay N+1 queries en operaciones sobre listas?
- [ ] ¿Los datos frecuentemente leídos tienen caché?
- [ ] ¿Se invalida el caché correctamente en writes?
- [ ] ¿Hay connection pooling configurado?
- [ ] ¿Las operaciones I/O-bound son asíncronas?
- [ ] ¿Se perfiló antes de optimizar?
