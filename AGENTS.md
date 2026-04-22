# AGENTS.md

Guía para agentes AI que trabajan en este proyecto.

## Qué es este repositorio

Template de desarrollo con Spec-Driven Development (SDD) y Claude Code.
Cada sesión sigue un flujo guiado: explorar → proponer → spec → design → tasks → implementar → verificar.

## Cómo está organizado

```
.claude/skills/     # skills por lenguaje y rol — leer antes de escribir código
.claude/commands/   # slash commands disponibles: /start-session, /status, /new-adr
docs/adr/           # decisiones de arquitectura tomadas — leer para entender el contexto
CLAUDE.md           # instrucciones completas del flujo de trabajo
```

## Antes de escribir código

1. Leer `CLAUDE.md` completo
2. Leer el skill del lenguaje activo: `.claude/skills/lang-{lenguaje}/SKILL.md`
3. Leer los skills de rol relevantes: `.claude/skills/role-{rol}/SKILL.md`
4. Revisar ADRs existentes en `docs/adr/` para entender decisiones ya tomadas

## Convenciones obligatorias

- Nunca código sin pasar por exploración SDD primero
- Toda decisión de arquitectura no obvia → ADR en `docs/adr/`
- Commits en formato convencional: `feat:`, `fix:`, `arch:`, `refactor:`, `test:`, `docs:`
- Sin secrets en código — siempre env vars
- Tests que verifican comportamiento, no implementación

## Reglas de seguridad — HARD STOPS

- **`git push` requiere confirmación explícita del usuario** — siempre mostrar qué se va a pushear primero
- **Escanear secrets antes de cada commit** — buscar API keys, tokens, passwords, URLs con credenciales
- **Si se detecta un secret** → STOP, informar, no continuar hasta resolver
- **Operaciones destructivas** (reset --hard, rm -rf, DROP TABLE) → confirmar siempre
- **PII en código o tests** → reemplazar por datos ficticios
- **`git push --force`** → nunca sin confirmación explícita y razón justificada

## Comandos disponibles

```
/start-session   → setup guiado de sesión (lenguaje, tipo de sistema, restricciones)
/status          → estado actual del flujo SDD
/new-adr         → crear nuevo ADR desde template
```

## Stack soportado

Lenguajes: Python, Java, TypeScript, Go
Infra: AWS (CDK), Docker
Roles: Architect, Backend, Frontend, Security, Privacy, Testing, CI/CD, AI Engineer, RAG, ML
