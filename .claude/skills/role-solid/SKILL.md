# Skill: SOLID, Clean Code y Design Patterns

## Rol
Escribir código que comunica intención, resiste el cambio y no necesita comentarios para entenderse.
El código limpio no es el que funciona — es el que el siguiente desarrollador puede cambiar sin miedo.

## Cuándo activar este skill
- Code review de cualquier clase o módulo
- Se detecta una clase con más de una razón para cambiar
- Hay duplicación de lógica entre módulos
- Un cambio en un lugar rompe otro lugar no relacionado
- Los tests son difíciles de escribir (señal de mal diseño)

---

## SOLID — principios con ejemplos reales

### S — Single Responsibility
Una clase tiene una sola razón para cambiar.

```python
# ❌ Viola SRP: procesa, valida Y envía
class OrderService:
    def process(self, order):
        if order.total < 0: raise ValueError()  # validación
        self.db.save(order)                       # persistencia
        self.email.send(order.user, "confirmed")  # notificación

# ✅ Cada responsabilidad en su lugar
class OrderValidator: ...
class OrderRepository: ...
class OrderNotifier: ...
class OrderService:
    def process(self, order):
        self.validator.validate(order)
        self.repository.save(order)
        self.notifier.notify(order)
```

### O — Open/Closed
Abierto para extensión, cerrado para modificación.

```typescript
// ❌ Cada nuevo tipo de descuento modifica la función
function applyDiscount(order: Order, type: string): number {
  if (type === 'percentage') return order.total * 0.9
  if (type === 'fixed') return order.total - 10
  // nuevo tipo = modificar esta función
}

// ✅ Extensión sin modificación
interface DiscountStrategy {
  apply(total: number): number
}
class PercentageDiscount implements DiscountStrategy { ... }
class FixedDiscount implements DiscountStrategy { ... }
// nuevo tipo = nueva clase, nada se toca
```

### L — Liskov Substitution
Un subtipo debe poder reemplazar a su supertipo sin romper el programa.

```java
// ❌ Viola LSP: Square rompe el contrato de Rectangle
class Rectangle { setWidth(w); setHeight(h); area() }
class Square extends Rectangle {
  setWidth(w) { super.setWidth(w); super.setHeight(w); } // sorpresa
}

// ✅ Modela correctamente sin herencia forzada
interface Shape { area(): double }
class Rectangle implements Shape { ... }
class Square implements Shape { ... }
```

### I — Interface Segregation
Ningún cliente debe depender de métodos que no usa.

```go
// ❌ Interfaz gorda: FileWriter obliga a implementar Read y Seek
type Storage interface {
    Read(key string) ([]byte, error)
    Write(key string, data []byte) error
    Seek(offset int) error
    Delete(key string) error
}

// ✅ Interfaces pequeñas y focalizadas
type Writer interface { Write(key string, data []byte) error }
type Reader interface { Read(key string) ([]byte, error) }
type Deleter interface { Delete(key string) error }
```

### D — Dependency Inversion
Módulos de alto nivel no dependen de módulos de bajo nivel. Ambos dependen de abstracciones.

```typescript
// ❌ Use case acoplado a implementación concreta
class CreateUserUseCase {
  constructor(private repo: PostgresUserRepository) {} // infraestructura en el dominio
}

// ✅ Depende de la abstracción (port)
interface UserRepository { save(user: User): Promise<void> }
class CreateUserUseCase {
  constructor(private repo: UserRepository) {} // el dominio define el contrato
}
```

---

## DRY, KISS, YAGNI

| Principio | Regla | Cuándo viola |
|-----------|-------|--------------|
| **DRY** — Don't Repeat Yourself | La lógica tiene una sola representación autorizada | Copy-paste de lógica, no de estructura |
| **KISS** — Keep It Simple | La solución más simple que funciona | Over-engineering, abstracciones prematuras |
| **YAGNI** — You Aren't Gonna Need It | No implementes lo que no necesitás ahora | "Por si acaso", "en el futuro" |

> DRY no es "no repetir código" — es "no repetir CONOCIMIENTO". Dos funciones con código similar pero lógica diferente NO son violación de DRY.

---

## Code smells — señales de mal diseño

| Smell | Síntoma | Refactor |
|-------|---------|----------|
| **God Object** | Clase con 500+ líneas y 20 métodos | Dividir por responsabilidad |
| **Feature Envy** | Método que usa más datos de otra clase que los propios | Mover el método a esa clase |
| **Data Clump** | Grupo de variables que siempre viajan juntas | Extraer Value Object |
| **Primitive Obsession** | `String email`, `String phone`, `int age` sin tipos | Crear tipos semánticos |
| **Long Parameter List** | Función con 5+ parámetros | Extraer objeto de configuración |
| **Shotgun Surgery** | Un cambio toca 10 archivos | Consolidar responsabilidad |
| **Divergent Change** | Una clase cambia por razones distintas frecuentemente | Separar en dos clases |
| **Dead Code** | Código comentado, métodos no llamados | Eliminar sin piedad |

---

## Design Patterns — cuándo usarlos

### Creacionales
| Pattern | Cuándo | Problema que resuelve |
|---------|--------|----------------------|
| **Factory Method** | Crear objetos sin especificar la clase exacta | Desacoplar creación de uso |
| **Builder** | Objeto complejo con muchos parámetros opcionales | Evitar constructores con 8 args |
| **Singleton** | Una sola instancia global (con precaución) | Config, logger, connection pool |

### Estructurales
| Pattern | Cuándo | Problema que resuelve |
|---------|--------|----------------------|
| **Adapter** | Integrar interfaz incompatible | Wrappear API externa al dominio |
| **Decorator** | Agregar comportamiento sin modificar clase | Logging, caching, retry transparentes |
| **Facade** | Simplificar subsistema complejo | API pública sobre lógica interna |

### Comportamiento
| Pattern | Cuándo | Problema que resuelve |
|---------|--------|----------------------|
| **Strategy** | Algoritmos intercambiables | Eliminar if/else de tipo |
| **Observer** | Notificar cambios sin acoplamiento | Eventos de dominio |
| **Command** | Encapsular operaciones como objetos | Undo/redo, colas de trabajo |
| **Chain of Responsibility** | Pipeline de procesamiento | Middlewares, validaciones en cadena |

---

## Métricas de complejidad

| Métrica | Umbral saludable | Acción si supera |
|---------|-----------------|------------------|
| **Complejidad ciclomática** | ≤ 10 por función | Extraer funciones |
| **Líneas por función** | ≤ 20 | Dividir responsabilidades |
| **Líneas por clase** | ≤ 200 | Revisar SRP |
| **Parámetros por función** | ≤ 3 | Extraer objeto |
| **Profundidad de anidamiento** | ≤ 3 niveles | Early return / extraer |

---

## Checklist de code review

- [ ] ¿Cada clase tiene una sola razón para cambiar?
- [ ] ¿Las interfaces son pequeñas y focalizadas?
- [ ] ¿Los use cases dependen de abstracciones, no implementaciones?
- [ ] ¿Hay lógica duplicada que debería extraerse?
- [ ] ¿El nombre de cada clase/función comunica exactamente qué hace?
- [ ] ¿Hay código comentado o métodos no usados?
- [ ] ¿Los parámetros primitivos podrían ser Value Objects?
- [ ] ¿Los tests son fáciles de escribir? (si no, el diseño es el problema)
