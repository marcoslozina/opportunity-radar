# Skill: Backend

## Aplica a
APIs REST y GraphQL, agnóstico de lenguaje y framework.

---

## Diseño de API REST

### Convenciones de URLs
```
GET    /users              → listar (con paginación)
GET    /users/:id          → obtener uno
POST   /users              → crear
PUT    /users/:id          → reemplazar completo
PATCH  /users/:id          → actualizar parcial
DELETE /users/:id          → eliminar

# Recursos anidados (máximo 2 niveles)
GET    /users/:id/orders
POST   /users/:id/orders

# Acciones que no son CRUD → verbos como sub-recurso
POST   /users/:id/activate
POST   /orders/:id/cancel
```

### Códigos HTTP semánticos
| Situación | Código |
|-----------|--------|
| Creación exitosa | 201 Created |
| Operación sin respuesta | 204 No Content |
| Recurso no encontrado | 404 Not Found |
| Input inválido | 422 Unprocessable Entity |
| Sin permisos | 403 Forbidden |
| No autenticado | 401 Unauthorized |
| Conflicto de estado | 409 Conflict |
| Error del servidor | 500 Internal Server Error |

### Formato de error consistente
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "No se encontró un usuario con id abc-123",
    "details": []
  }
}
```

---

## Paginación

```json
// Cursor-based (preferido para datasets grandes o que cambian)
GET /users?cursor=eyJpZCI6MTAwfQ&limit=20

{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIwfQ",
    "has_more": true
  }
}

// Offset (simple, para tablas admin estáticas)
GET /users?page=2&per_page=20

{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 340
  }
}
```

**Cursor-based** para feeds, listas grandes, datos que se actualizan.
**Offset** para admin panels, reportes, datasets estáticos.

---

## Base de datos

### Reglas de esquema
- Primary keys: UUIDs (no autoincrement expuesto en API)
- Timestamps: `created_at`, `updated_at` en toda tabla
- Soft delete: columna `deleted_at` en lugar de DELETE físico cuando hay auditoría
- Índices en: foreign keys, campos de búsqueda frecuente, campos de ordenamiento

### Migraciones
- Siempre migraciones versionadas (Alembic, Flyway, Liquibase)
- Cada migración: un cambio atómico
- Sin lógica de negocio en migraciones
- Migraciones backwards-compatible cuando sea posible

### N+1 — detectar y eliminar
```
❌ N+1:
  for user in users:         # 1 query
      print(user.orders)     # N queries

✅ Eager loading:
  users = db.query(User).options(joinedload(User.orders)).all()
```

---

## Manejo de errores

```
                  ┌─────────────────────────────┐
Request inválido  │ Validar en entry point (422) │
                  └─────────────┬───────────────┘
                                │ input limpio
                  ┌─────────────▼───────────────┐
Error de negocio  │ Excepción de dominio         │ → 409 / 404 / 422
                  └─────────────┬───────────────┘
                                │
                  ┌─────────────▼───────────────┐
Error de infra    │ Adapter captura y traduce    │ → 500 + log
                  └─────────────────────────────┘
```

Nunca dejar que excepciones de infraestructura (SQL, HTTP, timeout) lleguen al cliente sin traducir.

---

## Observabilidad mínima

```python
# Cada request debe loggear:
{
  "request_id": "uuid",          # trazabilidad
  "method": "POST",
  "path": "/users",
  "status": 201,
  "duration_ms": 45,
  "user_id": "abc"               # contexto de negocio
}

# Nunca loggear:
# - passwords, tokens, API keys
# - datos personales completos (PII)
# - payloads completos en producción
```

---

## Decisiones comunes en Backend

Aplicar protocolo de decisión del CLAUDE.md ante:
- **API style:** REST vs GraphQL vs gRPC vs tRPC
- **Auth:** JWT vs sesiones vs OAuth2
- **Paginación:** cursor vs offset
- **Queue:** sync vs async con cola
- **Cache:** dónde y qué cachear, invalidación
- **Rate limiting:** por usuario vs por IP vs por endpoint
