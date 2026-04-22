# Skill: Requirements Engineering

## Rol
Transformar ideas vagas en requisitos testeables antes de escribir una línea de código.
Un requisito mal escrito es más caro que ningún requisito — genera código que pasa los tests
pero no resuelve el problema real.

## Cuándo activar este skill
- El usuario describe un feature nuevo
- Los requisitos son ambiguos, contradictorios o asumen conocimiento implícito
- No hay criterios de aceptación claros
- El equipo discute sobre si algo "está hecho" o no
- Fase de Exploración o Spec en el flujo SDD

---

## Regla de oro

```
Un requisito es bueno si dos personas independientes lo leen
y llegan a la misma conclusión sobre qué construir.
Si no — reescribilo.
```

---

## Anatomía de un buen requisito

```
❌ "El usuario puede filtrar productos"

✅ GIVEN un usuario autenticado con al menos 1 producto en catálogo
   WHEN aplica filtro por categoría = "electrónica" y precio máximo = $500
   THEN ve solo los productos que cumplen ambas condiciones
   AND el conteo del header refleja la cantidad filtrada
   AND si no hay resultados, ve el empty state con CTA para limpiar filtros
```

**Checklist de un requisito testeable:**
- [ ] Tiene sujeto claro (¿quién?)
- [ ] Tiene acción específica (¿qué hace exactamente?)
- [ ] Tiene condición de entrada (¿desde qué estado?)
- [ ] Tiene resultado observable y verificable
- [ ] Incluye el caso de error o edge case

---

## Example Mapping — descubrir requisitos con el equipo

Example Mapping es una técnica de 30-45 minutos para explorar un feature antes de estimarlo.
Usa 4 tipos de tarjetas:

```
🟡 HISTORIA    → "El usuario puede pagar con tarjeta"
🔵 REGLA       → "Solo acepta Visa y Mastercard"
🟢 EJEMPLO     → "Juan paga $500 con Visa → recibe confirmación"
🟢 EJEMPLO     → "Juan intenta pagar con Amex → ve error específico"
🔴 PREGUNTA    → "¿Qué pasa si el banco rechaza por fondos insuficientes?"
```

**Protocolo:**
1. Escribir la historia en una tarjeta amarilla
2. Por cada regla de negocio → tarjeta azul
3. Por cada regla → al menos 1 ejemplo feliz + 1 ejemplo de error (tarjetas verdes)
4. Dudas que surgen → tarjetas rojas (a resolver ANTES de estimar)

**Señal de que el feature está listo para estimar:** pocas tarjetas rojas.
**Señal de que NO está listo:** muchas tarjetas rojas → más preguntas que respuestas.

---

## Definition of Ready (DoR)

Un requisito no entra al sprint hasta cumplir:

- [ ] Criterios de aceptación escritos en formato Given/When/Then
- [ ] Edge cases identificados (¿qué pasa si falla? ¿si está vacío? ¿si hay permisos?)
- [ ] Dependencias externas identificadas (APIs, servicios, equipos)
- [ ] Diseño de UI acordado (si aplica)
- [ ] No hay preguntas abiertas bloqueantes
- [ ] Estimación posible sin supuestos grandes

---

## Definition of Done (DoD)

Un requisito está "hecho" cuando:

- [ ] Criterios de aceptación verificados manualmente
- [ ] Tests automatizados cubriendo el happy path y casos edge
- [ ] Code review aprobado
- [ ] Sin regresiones detectadas en funcionalidad existente
- [ ] Documentación actualizada si cambia una API pública
- [ ] Desplegado en ambiente de staging

---

## PRD mínimo viable

Para features con más de 3 días de trabajo, documentar antes de implementar:

```markdown
## Feature: [nombre]

### Problema que resuelve
[1 párrafo — qué dolor tiene el usuario hoy]

### Usuarios afectados
[Quién se beneficia y quién podría verse afectado negativamente]

### Solución propuesta
[Qué construimos — no el cómo, el qué]

### Criterios de éxito
- Métrica 1: [qué medimos y cuál es el target]
- Métrica 2: ...

### Fuera de scope (explícito)
- [Qué NO incluye esta versión]

### Requisitos funcionales
1. GIVEN ... WHEN ... THEN ...
2. ...

### Requisitos no funcionales
- Performance: [ej: respuesta < 200ms en p95]
- Seguridad: [ej: solo usuarios con rol admin]
- Disponibilidad: [ej: sin downtime en deploy]

### Riesgos
- [Riesgo técnico o de negocio conocido]
```

---

## Requisitos no funcionales — los que siempre se olvidan

| Categoría | Preguntas a hacer |
|-----------|-----------------|
| **Performance** | ¿Cuántos usuarios concurrentes? ¿Latencia aceptable en p95? ¿Hay SLO? |
| **Seguridad** | ¿Quién puede acceder? ¿Qué datos son sensibles? ¿Auditoría requerida? |
| **Disponibilidad** | ¿Puede haber downtime en deploy? ¿Qué pasa si falla un servicio externo? |
| **Escalabilidad** | ¿El volumen puede crecer 10x en 6 meses? ¿Hay picos predecibles? |
| **Observabilidad** | ¿Qué métricas necesitamos para saber que funciona en producción? |
| **Internacionalización** | ¿Múltiples idiomas? ¿Zonas horarias? ¿Formatos de fecha/moneda? |

---

## Señales de requisitos problemáticos

| Señal | Problema | Acción |
|-------|---------|--------|
| "El sistema debería ser rápido" | No testeable | Definir métrica concreta: "< 200ms p95" |
| "El usuario puede gestionar X" | Ambiguo | Descomponer: crear, editar, eliminar, listar — son 4 requisitos |
| "Como siempre lo hemos hecho" | Asunción implícita | Documentar el comportamiento explícitamente |
| "Obviamente también hace Y" | Scope creep implícito | Escribirlo o excluirlo — nunca asumir |
| "Igual que el sistema anterior" | Deuda oculta | Mapear el sistema anterior antes de asumir paridad |

---

## Integración con SDD

En el flujo SDD, este skill activa en:

- **Fase 1 (Exploración):** identificar incógnitas y preguntas abiertas
- **Fase 3 (Spec):** escribir criterios de aceptación en Given/When/Then
- **Fase 6 (Verificación):** validar que la implementación cumple los criterios

Antes de arrancar la Fase 3, correr Example Mapping con el usuario para vaciar las tarjetas rojas.
