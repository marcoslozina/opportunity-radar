# Skill: Architect

## Rol
Diseñar sistemas antes de implementarlos. Nunca hay código sin decisión de arquitectura documentada.

## Cuándo activar este skill
- El usuario describe un sistema nuevo
- Hay que elegir entre patrones o frameworks
- Se detecta acoplamiento entre capas
- La solución actual no va a escalar

---

## Principios fundamentales (agnósticos)

### Regla de dependencia
```
Entry Points → Application → Domain ← Infrastructure
```
Las flechas apuntan hacia adentro. El dominio no conoce nada externo. Nunca.

### Separación de responsabilidades
| Capa | Responsabilidad | Lo que NO hace |
|------|-----------------|----------------|
| Domain | Lógica de negocio, reglas | Conocer DB, HTTP, frameworks |
| Application | Orquestar casos de uso | Implementar detalles técnicos |
| Infrastructure | Adaptadores técnicos | Contener lógica de negocio |
| Entry Points | Recibir requests | Lógica de negocio |

### Inversión de dependencia
```
Domain define la interfaz (Port)
Infrastructure implementa la interfaz (Adapter)
Application usa la interfaz, no la implementación
```

---

## Cuándo aplicar qué arquitectura

| Complejidad | Patrón | Cuándo |
|-------------|--------|--------|
| Script / CLI simple | Flat + funciones | 1-2 responsabilidades |
| App pequeña | MVC o Layered | CRUD básico, equipo chico |
| App mediana | Clean Architecture | Lógica de negocio real |
| App compleja | Hexagonal / Ports & Adapters | Múltiples integraciones |
| Distribuida | Microservicios + eventos | Escala de equipos / dominios |

**Regla:** empezá simple. Migrá cuando el dolor sea real, no anticipado.

---

## Protocolo de decisión de arquitectura

Ante cada decisión significativa:

```
🏗️ DECISIÓN: [título]

Contexto: [fuerza que genera la decisión]

Opción A — [nombre]
  ✓ [ventaja]
  ✗ [desventaja]

Opción B — [nombre]
  ✓ [ventaja]
  ✗ [desventaja]

Recomendación: [opción] porque [razón técnica]

¿Confirmás?
```

Después de confirmar → crear ADR.

---

## ADR (Architecture Decision Record)

Carpeta: `docs/adr/ADR-XXX-titulo-kebab.md`

```markdown
# ADR-001: [Título]

**Estado:** Aceptado | Propuesto | Deprecado
**Fecha:** YYYY-MM-DD

## Contexto
[Qué fuerza o problema genera esta decisión]

## Decisión
[Qué decidimos hacer]

## Consecuencias
### Positivas
- ...
### Negativas / Tradeoffs
- ...

## Alternativas descartadas
- [Alternativa A]: descartada porque ...
```

---

## Señales de alerta arquitectónica

| Señal | Problema | Solución |
|-------|---------|---------|
| Lógica de negocio en controller/route | Violación de capas | Mover a use case |
| Use case que importa ORM directamente | Violación de dependencia | Extraer port + adapter |
| Entidad que conoce el framework | Dominio contaminado | Separar entity de model ORM |
| Servicio que hace todo | God Object | Dividir por responsabilidad |
| Tests que mockean la DB en use cases | Test acoplado a infra | Usar fake repository |

---

## Patrones clave

### Port & Adapter (Hexagonal)
```
[Test / API / CLI]  →  [Use Case]  →  [Port interface]
                                            ↑
                                    [Adapter: real impl]
```

### CQRS básico
```
Commands → Write side → Domain → Events
Queries  → Read side  → Projections (optimizadas para lectura)
```

### Event-driven (cuando hay múltiples consumidores)
```
Producer → Event Bus → Consumer A
                    → Consumer B
                    → Consumer C
```

---

## Checklist antes de implementar

- [ ] ¿Entendemos el problema completamente?
- [ ] ¿Hay un ADR para las decisiones no obvias?
- [ ] ¿Las capas tienen responsabilidades claras?
- [ ] ¿El dominio está libre de dependencias externas?
- [ ] ¿Los tests pueden correr sin infra externa?
- [ ] ¿La solución es la más simple que resuelve el problema?
