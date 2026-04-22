# Skill: Orchestrator — Agent Team Architecture

## Rol
El orquestador NO ejecuta trabajo. Coordina, delega y sintetiza.
Todo trabajo real (leer código, escribir código, análisis) va a sub-agentes.

---

## Principio fundamental

```
Orquestador = contexto mínimo + coordinación
Sub-agentes  = contexto aislado + trabajo real

Beneficios:
  ⏱  Tiempo:   fases paralelas reducen wall clock hasta 50%
  🪙  Tokens:   cada sub-agente procesa solo lo que necesita
  🧠  Memoria:  Engram persiste entre agentes y sesiones
  🔒  Aislado:  un agente que falla no contamina el contexto principal
```

---

## Reglas del orquestador

| Regla | Descripción |
|-------|-------------|
| No inline work | Leer/escribir código → siempre sub-agente |
| Delegate-first | Preferir `delegate` (async) sobre `task` (sync) |
| Parallel by default | Si dos fases no se bloquean → lanzarlas juntas |
| Context injection | El orquestador busca en Engram y pasa contexto al sub-agente |
| Write to Engram | Los sub-agentes guardan descubrimientos antes de terminar |

**Anti-patterns — nunca hacer:**
- Leer archivos de código "para entender" → delegá
- Escribir código directamente → delegá
- Hacer análisis inline "rápido" → delegá
- Pasar el contenido completo de artefactos entre agentes → pasá el ID de Engram

---

## Flujo de delegación

### Delegate (async — default)
```
Orquestador: "Voy a lanzar spec y design en paralelo"
    → delegate: sdd-spec  (corre en background)
    → delegate: sdd-design (corre en background)
    → [esperá ambos]
    → sintetizá resultados
    → mostrá al usuario
```

### Task (sync — solo si necesitás el resultado antes de continuar)
```
Orquestador: "Necesito la exploración antes de proponer"
    → task: sdd-explore
    → [esperá resultado]
    → usá resultado para construir la propuesta
```

---

## Protocolo de contexto para sub-agentes

### Lo que el orquestador hace ANTES de lanzar un sub-agente

```
1. Buscar contexto relevante en Engram:
   mem_search(query: "topic keywords", project: "nombre-proyecto")

2. Si hay resultado → mem_get_observation(id) para contenido completo

3. Incluir en el prompt del sub-agente:
   - Ruta exacta del skill a cargar
   - Artefactos previos relevantes (topic keys de Engram, no el contenido)
   - Instrucción explícita de guardar descubrimientos en Engram
```

### Estructura del prompt de sub-agente

```markdown
SKILL: Lee `.claude/skills/{nombre}/SKILL.md` antes de empezar.

CONTEXTO (de sesiones anteriores):
  - Propuesta aprobada: topic key `sdd/{cambio}/proposal` en Engram
  - Stack elegido: Python + FastAPI + PostgreSQL

TAREA:
  [descripción específica de lo que tiene que hacer]

OUTPUT ESPERADO:
  [qué formato, qué artefacto producir]

MEMORIA:
  Si hacés descubrimientos importantes, decisiones o encontrás bugs,
  guardalos en Engram con mem_save antes de terminar.
  project: "{nombre-proyecto}"
```

---

## Fases SDD — qué corre en paralelo

```
sdd-explore         → sync (necesitás resultado antes de proponer)
       ↓
sdd-propose         → sync (necesitás propuesta para spec y design)
       ↓
sdd-spec  ──────────┐
                    ├── PARALELO (independientes entre sí)
sdd-design ─────────┘
       ↓
sdd-tasks           → sync (necesita spec + design)
       ↓
sdd-apply task-1 ───┐
sdd-apply task-2 ───┤
sdd-apply task-3 ───┼── PARALELO (si las tasks son independientes)
sdd-apply task-4 ───┘
       ↓
sdd-verify          → sync (verifica todo junto)
```

### Cuándo NO paralelizar apply

Tasks que se bloquean entre sí NO van en paralelo:
```
❌ Paralelo incorrecto:
   task-1: crear tabla users
   task-2: agregar foreign key que depende de users
   → task-2 falla si task-1 no terminó

✅ Secuencial:
   task-1 → task-2

✅ Paralelo correcto:
   task-A: implementar UserRepository
   task-B: implementar ProductRepository
   → independientes, van juntas
```

---

## Engram — topic keys por proyecto

```
sdd-init/{proyecto}              → contexto inicial del proyecto
sdd/{cambio}/explore             → artefacto de exploración
sdd/{cambio}/proposal            → propuesta elegida
sdd/{cambio}/spec                → especificación
sdd/{cambio}/design              → diseño técnico
sdd/{cambio}/tasks               → lista de tasks
sdd/{cambio}/apply-progress      → progreso de implementación
sdd/{cambio}/verify-report       → reporte de verificación
```

Recuperar artefacto:
```
1. mem_search(query: "sdd/{cambio}/spec")  → obtener ID
2. mem_get_observation(id: {id})           → contenido completo
```

---

## Estimación de ahorro con paralelización

| Fase | Sin paralelismo | Con paralelismo |
|------|----------------|----------------|
| explore → propose | 2 min | 2 min (sync) |
| spec + design | 4 min | 2 min (paralelo) |
| tasks | 1 min | 1 min (sync) |
| apply (4 tasks) | 8 min | 2-3 min (paralelo) |
| verify | 1 min | 1 min (sync) |
| **Total** | **16 min** | **8-9 min** |

El ahorro real depende de la complejidad. En proyectos grandes la diferencia es mayor.

---

## Ejemplo de orquestación completa

```
Usuario: "Necesito implementar autenticación JWT"

Orquestador:
  1. mem_search("jwt auth {proyecto}") → nada previo

  2. [task] sdd-explore "autenticación JWT en este proyecto"
     → resultado: contexto del sistema, stack, patrones existentes

  3. Presenta propuesta (2-3 opciones) → usuario elige opción B

  4. [delegate] sdd-spec  "auth JWT según propuesta B"
     [delegate] sdd-design "auth JWT según propuesta B"
     → ambos en paralelo, ambos escriben en Engram

  5. Espera ambos → presenta resumen → usuario confirma

  6. [task] sdd-tasks "auth JWT"
     → lista de 5 tasks

  7. Usuario confirma → analiza dependencias:
     task-1 (User entity) → independiente
     task-2 (JWT utils)   → independiente
     task-3 (middleware)  → depende de task-1 y task-2
     task-4 (routes)      → depende de task-3
     task-5 (tests)       → depende de todas

  8. [delegate] sdd-apply task-1
     [delegate] sdd-apply task-2
     → paralelo

  9. Espera → [task] sdd-apply task-3 → [task] sdd-apply task-4

  10. [task] sdd-verify → reporte final → presenta al usuario
```

---

## Decisiones de arquitectura de agentes

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Sync vs async:** ¿necesito el resultado antes de continuar?
- **Granularidad de tasks:** tasks muy chicas = overhead de agentes; muy grandes = no paralelizables
- **Qué guardar en Engram:** decisiones, bugs, descubrimientos — no estado efímero
- **Cuántos agentes en paralelo:** más de 4-5 simultáneos puede ser contraproducente
