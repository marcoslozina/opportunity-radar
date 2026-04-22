# Skill: Concurrencia y Paralelismo

## Rol
Escribir código concurrente correcto, no solo código concurrente rápido.
Un race condition silencioso en producción es peor que código lento.
Correctitud primero, performance después.

## Cuándo activar este skill
- El sistema maneja múltiples requests simultáneos
- Hay estado compartido entre goroutines, threads o async tasks
- Se usan workers, queues o procesamiento en background
- Se diseña un sistema con operaciones I/O-bound o CPU-bound
- Code review de código con `async/await`, goroutines, threads o locks

---

## Conceptos fundamentales

### Concurrencia vs Paralelismo
```
Concurrencia:  múltiples tareas en progreso al mismo tiempo (puede ser en 1 CPU)
Paralelismo:   múltiples tareas ejecutándose simultáneamente (requiere múltiples CPUs)

Concurrencia es sobre DISEÑO (estructura del programa).
Paralelismo es sobre EJECUCIÓN (hardware).
```

### I/O-bound vs CPU-bound
| Tipo | Bottleneck | Solución |
|------|-----------|----------|
| **I/O-bound** | Espera de red, disco, DB | `async/await`, threads, goroutines |
| **CPU-bound** | Procesamiento intensivo | Multiprocessing, múltiples CPUs reales |

> En Python: GIL impide paralelismo real con threads para CPU-bound → usar `multiprocessing`.
> En Go/Java: threads/goroutines dan paralelismo real para ambos tipos.

---

## Race Conditions — detección y prevención

```go
// ❌ Race condition: dos goroutines leen-modifican-escriben
var counter int
go func() { counter++ }()
go func() { counter++ }()
// counter puede ser 1 en vez de 2

// ✅ Opción A: atomic operations
var counter atomic.Int64
go func() { counter.Add(1) }()

// ✅ Opción B: mutex
var mu sync.Mutex
var counter int
go func() {
    mu.Lock()
    counter++
    mu.Unlock()
}()
```

```bash
# Detectar race conditions en Go
go test -race ./...
go run -race main.go
```

---

## Deadlocks — patrones y prevención

```go
// ❌ Deadlock clásico: A espera B, B espera A
func transfer(from, to *Account, amount int) {
    from.mu.Lock()
    to.mu.Lock()   // goroutine A bloquea from, espera to
                   // goroutine B bloquea to, espera from → DEADLOCK
    from.balance -= amount
    to.balance += amount
    to.mu.Unlock()
    from.mu.Unlock()
}

// ✅ Ordenar locks consistentemente (siempre en el mismo orden)
func transfer(from, to *Account, amount int) {
    first, second := from, to
    if from.id > to.id {
        first, second = to, from
    }
    first.mu.Lock()
    second.mu.Lock()
    // ...
}
```

---

## Async/Await por lenguaje

### Python (asyncio)
```python
import asyncio
import httpx

# ❌ Secuencial — 3 requests = suma de tiempos
async def fetch_all_slow():
    a = await fetch("url_a")
    b = await fetch("url_b")  # espera que termine a
    c = await fetch("url_c")  # espera que termine b

# ✅ Paralelo — 3 requests = tiempo del más lento
async def fetch_all_fast():
    async with httpx.AsyncClient() as client:
        a, b, c = await asyncio.gather(
            client.get("url_a"),
            client.get("url_b"),
            client.get("url_c"),
        )

# CPU-bound: usar ProcessPoolExecutor (no threads — GIL)
from concurrent.futures import ProcessPoolExecutor
async def cpu_heavy_task(data):
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, process, data)
```

### TypeScript/Node
```typescript
// ❌ Secuencial
const user = await getUser(id)
const orders = await getOrders(id)  // espera que termine getUser

// ✅ Paralelo con Promise.all
const [user, orders] = await Promise.all([
  getUser(id),
  getOrders(id),
])

// ✅ Con manejo de errores individuales
const results = await Promise.allSettled([
  getUser(id),
  getOrders(id),
])
results.forEach(r => {
  if (r.status === 'fulfilled') use(r.value)
  else log(r.reason)
})
```

### Go (goroutines + channels)
```go
// ✅ Fan-out: distribuir trabajo entre goroutines
func processAll(items []Item) []Result {
    results := make(chan Result, len(items))

    for _, item := range items {
        go func(i Item) {
            results <- process(i)
        }(item)  // pasar por valor — evita closure bug
    }

    out := make([]Result, 0, len(items))
    for range items {
        out = append(out, <-results)
    }
    return out
}

// ✅ Context para cancelación
func fetchWithTimeout(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
    resp, err := http.DefaultClient.Do(req)
    // Si el contexto se cancela, el request se interrumpe automáticamente
}
```

### Java (CompletableFuture)
```java
// ✅ Paralelo con CompletableFuture
CompletableFuture<User> userFuture = CompletableFuture
    .supplyAsync(() -> userRepo.findById(id));

CompletableFuture<List<Order>> ordersFuture = CompletableFuture
    .supplyAsync(() -> orderRepo.findByUserId(id));

CompletableFuture.allOf(userFuture, ordersFuture).join();
User user = userFuture.get();
List<Order> orders = ordersFuture.get();

// ✅ Virtual threads (Java 21+) — I/O-bound sin callbacks
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<User> user = executor.submit(() -> userRepo.findById(id));
    Future<List<Order>> orders = executor.submit(() -> orderRepo.findByUserId(id));
}
```

---

## Work Queues y Backpressure

```python
# ✅ Worker pool con asyncio — limitar concurrencia
async def process_with_limit(items, max_workers=10):
    semaphore = asyncio.Semaphore(max_workers)

    async def bounded_process(item):
        async with semaphore:  # máximo 10 en paralelo
            return await process(item)

    return await asyncio.gather(*[bounded_process(i) for i in items])
```

```go
// ✅ Worker pool en Go
func workerPool(jobs <-chan Job, results chan<- Result, workers int) {
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                results <- process(job)
            }
        }()
    }
    wg.Wait()
    close(results)
}
```

---

## Patrones de concurrencia seguros

| Pattern | Cuándo | Mecanismo |
|---------|--------|-----------|
| **Immutability** | Estado que no cambia | Sin locks necesarios |
| **Message passing** | Comunicación entre workers | Channels (Go), queues |
| **Actor model** | Estado aislado por actor | Akka (Java), erlang-style |
| **Thread-local storage** | Estado por thread sin locks | `threading.local()` (Python) |
| **Copy-on-write** | Reads frecuentes, writes raros | Snapshot antes de modificar |

---

## Closures en loops — bug clásico

```typescript
// ❌ Todos los callbacks capturan el mismo `i`
for (var i = 0; i < 5; i++) {
  setTimeout(() => console.log(i), 100)  // imprime 5,5,5,5,5
}

// ✅ let crea scope por iteración
for (let i = 0; i < 5; i++) {
  setTimeout(() => console.log(i), 100)  // imprime 0,1,2,3,4
}
```

```go
// ❌ Goroutine captura referencia a variable del loop
for _, v := range items {
    go func() { process(v) }()  // todas las goroutines ven el último v
}

// ✅ Pasar por valor
for _, v := range items {
    go func(item Item) { process(item) }(v)
}
```

---

## Checklist de concurrencia

- [ ] ¿Todo estado compartido está protegido con mutex, atomic o channels?
- [ ] ¿Se corre `go test -race` o equivalente?
- [ ] ¿Las goroutines/tasks tienen forma de cancelarse con context/signal?
- [ ] ¿Las operaciones I/O-bound son async? ¿Las CPU-bound usan workers reales?
- [ ] ¿Los loops con goroutines/closures pasan variables por valor?
- [ ] ¿Hay un límite de concurrencia (semaphore/pool) para evitar saturar recursos?
- [ ] ¿Los locks se adquieren siempre en el mismo orden? (prevención de deadlock)
- [ ] ¿Se liberan los locks con `defer` para garantizar liberación ante panics/errores?
