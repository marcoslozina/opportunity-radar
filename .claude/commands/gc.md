# Comando: /gc — Context Garbage Collection

Sanitizá y compactá el contexto de la sesión actual.

## Qué hace

1. Guardá en Engram todo lo que vale la pena recordar de esta sesión
2. Compactá el contexto con `/compact`

## Pasos obligatorios

### Paso 1 — Guardar en Engram antes de perder contexto

Llamá `mem_session_summary` con este formato:

```
## Goal
[Qué estábamos haciendo en esta sesión]

## Instructions
[Preferencias o restricciones del usuario descubiertas — omitir si ninguna]

## Discoveries
- [Hallazgos técnicos, gotchas, comportamientos no obvios]

## Accomplished
- [Items completados con detalles clave]

## Next Steps
- [Qué queda por hacer — para la próxima sesión]

## Relevant Files
- path/to/file — [qué hace o qué cambió]
```

### Paso 2 — Compactar

Después de confirmar que `mem_session_summary` fue exitoso, ejecutá `/compact`.

## Cuándo usarlo

- La sesión lleva más de 1 hora
- Hay muchos tool results largos acumulados (diffs, logs, traces)
- Antes de empezar una tarea nueva en la misma sesión
- Sentís que el contexto está "lleno" de ruido
