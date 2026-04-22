# Skill: UX Design

## Principio base

El diseño empieza por el problema del usuario, no por la pantalla. Antes de proponer cualquier flujo, entender: ¿quién lo usa, cuándo, con qué objetivo, y qué alternativa tiene hoy?

---

## Descubrimiento — preguntas obligatorias antes de diseñar

```
¿Quién es el usuario? (rol, contexto, nivel técnico)
¿Cuál es el job-to-be-done? (no "quiero hacer X" sino "para poder Y")
¿Con qué frecuencia ocurre esta tarea?
¿Qué pasa si no puede completarla?
¿Qué hace hoy para resolver esto?
```

No empieces wireframes hasta tener respuestas claras.

---

## Arquitectura de información

### Jerarquía de contenido
```
1. ¿Qué puede hacer el usuario aquí? (acción principal)
2. ¿Qué necesita saber para decidir? (información de soporte)
3. ¿Qué puede explorar después? (secundario)
```

### Principio de una pantalla, una acción primaria
Cada pantalla tiene UNA acción principal clara. Si hay dos acciones igual de importantes, hay un problema de arquitectura, no de diseño.

---

## Flujos de usuario

### Mapear el camino feliz primero
```
Entrada → Acción 1 → Acción 2 → ... → Estado de éxito
```

### Luego los estados de error y edge cases
- ¿Qué pasa si el usuario no tiene datos todavía? (empty state)
- ¿Qué pasa si la acción falla? (error state)
- ¿Qué pasa si tarda más de lo esperado? (loading state)
- ¿Qué pasa si el usuario se va a la mitad? (interrupción)

### Señales de flujo roto
- El usuario necesita ir "para atrás" para completar una tarea
- Hay más de 3 pantallas para una tarea simple
- El usuario pregunta "¿y ahora qué hago?"

---

## Principios de usabilidad (Nielsen)

| Principio | Qué significa en la práctica |
|-----------|------------------------------|
| Visibilidad del estado | El sistema siempre muestra qué está pasando (loading, éxito, error) |
| Match con el mundo real | Usar vocabulario del usuario, no del sistema |
| Control y libertad | Siempre hay un "deshacer" o "cancelar" |
| Consistencia | El mismo elemento hace lo mismo siempre |
| Prevención de errores | Mejor prevenir que mostrar mensajes de error |
| Reconocimiento > Recuerdo | El usuario no debería tener que memorizar cosas |
| Flexibilidad | Atajos para usuarios avanzados sin complicar para novatos |
| Estética minimalista | Nada que no contribuya directamente al objetivo |
| Recuperación de errores | Mensajes claros + solución concreta |
| Ayuda y documentación | Si necesita explicación, el diseño falló primero |

---

## Empty states — uno de los más olvidados

```
❌ Estado vacío genérico: "No hay datos"
✅ Estado vacío útil:
   - Ilustración contextual (no decorativa)
   - Explicar POR QUÉ está vacío
   - CTA para que deje de estar vacío
   - Ejemplo de cómo se vería con datos
```

---

## Micro-interacciones

Las transiciones y feedback inmediato reducen la carga cognitiva:

- **Feedback de acción**: el botón reacciona al click (visual + timing)
- **Progreso**: si tarda >1s, mostrar progreso; si tarda >3s, dar estimación
- **Confirmación de éxito**: el usuario sabe que funcionó sin leer texto
- **Error in-context**: el error aparece donde ocurrió, no en una alerta genérica

---

## Onboarding

```
❌ Tour de 8 pasos con tooltips en todo
✅ Onboarding efectivo:
   - Mostrar valor antes de pedir esfuerzo
   - Una acción a la vez
   - El usuario aprende haciendo, no leyendo
   - Skip siempre disponible
   - El usuario puede volver a ver el onboarding después
```

---

## Entregables por fase

| Fase | Entregable | Herramienta sugerida |
|------|-----------|---------------------|
| Descubrimiento | User journey map, JTBD | Miro, FigJam |
| Arquitectura | Sitemap, flujos de pantalla | Whimsical, FigJam |
| Exploración | Wireframes de baja fidelidad | Figma (sin estilos) |
| Validación | Prototipo clickeable | Figma prototype |
| Especificación | Anotaciones + estados | Figma + Dev Mode |
