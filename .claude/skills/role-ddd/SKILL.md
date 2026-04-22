# Skill: Domain-Driven Design (DDD)

## Rol
Construir software cuyo modelo refleja el negocio real, no la base de datos ni el framework.
El código debe hablar el idioma del negocio — si un desarrollador y un experto del dominio
leen el código y no entienden lo mismo, el modelo está mal.

## Cuándo activar este skill
- El sistema tiene lógica de negocio no trivial
- Hay múltiples equipos trabajando en el mismo sistema
- Los términos del negocio y el código son diferentes ("order" en negocio = "transaction" en código)
- El sistema crece y los cambios en un área rompen otras áreas no relacionadas
- Fase de Exploración o Propuesta de Arquitectura en SDD

---

## Lenguaje Ubicuo (Ubiquitous Language)

El vocabulario del negocio y el código deben ser idénticos. Sin traducciones.

```python
# ❌ Lenguaje técnico desconectado del negocio
class Transaction:
    def execute(self): ...          # ¿qué significa "ejecutar"?
    def update_status(self): ...    # ¿qué status? ¿por qué cambia?

# ✅ Lenguaje del dominio
class Order:
    def place(self): ...            # el negocio "coloca" un pedido
    def confirm(self): ...          # el negocio "confirma" cuando hay stock
    def cancel(self, reason): ...   # el negocio "cancela" con una razón
    def fulfill(self): ...          # el negocio "despacha" cuando está listo
```

**Cómo construir el lenguaje ubicuo:**
1. Reunirse con el experto del dominio (no solo el PM — el que conoce el negocio)
2. Escuchar los términos que usan naturalmente
3. Documentar el glosario — una definición por término, sin ambigüedad
4. Si dos personas usan el mismo término para cosas distintas → hay dos conceptos, nombrarlos diferente

---

## Event Storming — descubrir el dominio

Event Storming es un workshop de 2-4 horas para mapear un dominio completo con todos los involucrados.

### Tipos de tarjetas (colores estándar)

```
🟠 DOMAIN EVENT     → "Pedido confirmado", "Pago procesado", "Stock agotado"
🔵 COMMAND          → "Confirmar pedido", "Procesar pago", "Reservar stock"
🟡 AGGREGATE        → "Pedido", "Pago", "Inventario"
🟣 POLICY           → "Cuando pago falla → notificar al usuario"
🔴 HOTSPOT          → Dudas, conflictos, zonas de riesgo
🟢 EXTERNAL SYSTEM  → "Pasarela de pago", "Servicio de email"
```

### Protocolo de Event Storming

**Fase 1 — Caos creativo (20 min)**
Todos escriben Domain Events en naranjado. Sin orden, sin discusión. Solo eventos.
Formato obligatorio: **pasado participio** — "Pedido CONFIRMADO", no "Confirmar pedido".

**Fase 2 — Ordenar la línea de tiempo (20 min)**
Pegar los eventos en orden cronológico en una pared/miro.
Identificar duplicados y conflictos.

**Fase 3 — Commands y Aggregates (30 min)**
Para cada evento, ¿qué comando lo causó? ¿Qué entidad lo procesa?

**Fase 4 — Policies (20 min)**
¿Qué reacciones automáticas hay? "Cuando X ocurre → hacer Y"

**Fase 5 — Hotspots (10 min)**
Marcar en rojo todo lo que genera discusión, duda o riesgo.

**Resultado:** mapa visual del dominio que todos entienden — business y tech.

---

## Building Blocks de DDD

### Entity
Tiene identidad propia que persiste en el tiempo. Dos entidades con los mismos datos son distintas si tienen distinto ID.

```python
@dataclass
class Order:
    id: OrderId          # identidad
    customer_id: CustomerId
    items: list[OrderItem]
    status: OrderStatus

    def confirm(self) -> None:
        if self.status != OrderStatus.PENDING:
            raise OrderNotConfirmableError(self.id)
        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmed(order_id=self.id))
```

### Value Object
Sin identidad — se define por sus atributos. Inmutable. Dos Value Objects con los mismos datos SON el mismo objeto.

```python
@dataclass(frozen=True)  # inmutable
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchError()
        return Money(self.amount + other.amount, self.currency)

# ✅ Money(100, "USD") == Money(100, "USD") → True
# ✅ No tiene ID — es el valor, no una entidad
```

### Aggregate
Cluster de entidades y value objects tratado como unidad. Tiene una raíz (Aggregate Root) que es el único punto de entrada.

```python
class Order:  # Aggregate Root
    def add_item(self, product_id: ProductId, quantity: int) -> None:
        # La lógica de negocio vive aquí, no en el controller
        if self.status != OrderStatus.DRAFT:
            raise OrderNotEditableError()
        item = OrderItem(product_id=product_id, quantity=quantity)
        self.items.append(item)

    def total(self) -> Money:
        return sum(item.subtotal() for item in self.items)
```

**Reglas de Aggregates:**
- Solo modificar el estado a través del Aggregate Root
- No referenciar entidades internas de otro aggregate — solo por ID
- Mantener el aggregate pequeño — si crece mucho, probablemente son dos aggregates

### Domain Event
Algo significativo que ocurrió en el dominio. En tiempo pasado. Inmutable.

```python
@dataclass(frozen=True)
class OrderConfirmed:
    order_id: OrderId
    customer_id: CustomerId
    total: Money
    confirmed_at: datetime
```

### Domain Service
Lógica de negocio que no pertenece a ninguna entidad específica.

```python
class PricingService:
    def calculate_discount(self, order: Order, customer: Customer) -> Money:
        # Lógica que involucra Order Y Customer — no pertenece a ninguno solo
        if customer.is_premium() and order.total() > Money(1000, "USD"):
            return order.total() * Decimal("0.1")
        return Money(0, "USD")
```

### Repository (Port)
Abstracción para persistir y recuperar aggregates. El dominio define la interfaz.

```python
class OrderRepository(Protocol):
    def find_by_id(self, order_id: OrderId) -> Order | None: ...
    def save(self, order: Order) -> None: ...
    def find_pending_by_customer(self, customer_id: CustomerId) -> list[Order]: ...
```

---

## Bounded Contexts

Un sistema grande tiene múltiples modelos, cada uno válido dentro de su contexto.
El mismo concepto puede significar cosas distintas en contextos distintos.

```
"Producto" en Catálogo:    nombre, descripción, imágenes, SEO
"Producto" en Inventario:  SKU, stock, ubicación en almacén
"Producto" en Facturación: precio, impuestos, código fiscal

Son el MISMO producto en el negocio, pero MODELOS DISTINTOS en el software.
No forzar un único modelo — crear uno por contexto.
```

### Context Map — cómo se relacionan los contextos

```
[Catálogo] ──── Published Language ────▶ [Inventario]
[Pedidos]  ──── Anti-Corruption Layer ──▶ [Pago externo]
[Pedidos]  ◀─── Conformist ─────────────  [Logística]
```

| Relación | Cuándo | Qué implica |
|----------|--------|-------------|
| **Shared Kernel** | Equipo chico, contextos muy acoplados | Modelo compartido — coordinación obligatoria |
| **Customer/Supplier** | Un contexto depende del otro | El supplier se adapta a las necesidades del customer |
| **Anti-Corruption Layer** | Integración con sistema externo o legacy | Traducir el modelo externo al interno — nunca dejar que contamine |
| **Published Language** | API pública consumida por muchos | Contrato estable y versionado |

---

## Integración con Clean Architecture

```
Domain Layer:
  entities/          → Order, Customer, Product (Aggregates + Entities)
  value_objects/     → Money, OrderId, Email
  events/            → OrderConfirmed, PaymentFailed
  services/          → PricingService (Domain Service)
  repositories/      → OrderRepository (Port/Interface)

Application Layer:
  use_cases/         → PlaceOrderUseCase, ConfirmOrderUseCase

Infrastructure Layer:
  repositories/      → PostgresOrderRepository (Adapter)
  events/            → KafkaEventPublisher
```

---

## Anti-patterns DDD

| Anti-pattern | Síntoma | Fix |
|-------------|---------|-----|
| **Anemic Domain Model** | Entidades con solo getters/setters, lógica en servicios | Mover lógica al aggregate |
| **Fat Service** | Un servicio con toda la lógica del negocio | Distribuir en aggregates y domain services |
| **Shared Database** | Dos bounded contexts leen la misma tabla | Separar schemas o eventualmente bases |
| **God Aggregate** | Un aggregate con 20 entidades adentro | Dividir — probablemente son 3 aggregates |
| **Primitive Obsession** | `String orderId`, `int price` en vez de Value Objects | Crear tipos semánticos |

---

## Checklist DDD

- [ ] ¿El código usa los mismos términos que el negocio?
- [ ] ¿Hay un glosario de dominio documentado?
- [ ] ¿La lógica de negocio vive en el aggregate, no en el controller o service?
- [ ] ¿Los Value Objects son inmutables y se validan en construcción?
- [ ] ¿Los aggregates se modifican solo a través de la raíz?
- [ ] ¿Los repositorios son interfaces en el dominio, implementaciones en infra?
- [ ] ¿Los Domain Events están en tiempo pasado y son inmutables?
- [ ] ¿Los bounded contexts están identificados y sus límites son claros?
- [ ] ¿Las integraciones externas pasan por Anti-Corruption Layer?
