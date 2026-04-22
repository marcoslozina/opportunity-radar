# sdd-claude-template

Template de desarrollo con **Spec-Driven Development (SDD)** y **Claude Code**.

El asistente guía cada sesión: pregunta antes de codear, presenta opciones de arquitectura con tradeoffs, documenta cada decisión y nunca avanza una fase sin confirmación. No hay código sin entender el problema primero.

---

## Inicio rápido

```bash
# 1. Crear proyecto desde el template
gh repo create nombre-del-proyecto \
  --template marcoslozina/sdd-claude-template \
  --clone

# 2. Abrir con Claude Code
cd nombre-del-proyecto
claude

# 3. Iniciar sesión guiada
/start-session
```

El asistente va a preguntar lenguaje, tipo de sistema y restricciones antes de arrancar.

---

## Flujo de desarrollo

```
Problema
   │
   ▼
Exploración  →  entender antes de comprometerse
   │
   ▼
Propuesta    →  2-3 opciones con tradeoffs  →  vos elegís
   │
   ▼
Spec+Design  →  qué hace + cómo lo hace     →  en paralelo
   │
   ▼
Tasks        →  lista ordenada e implementable
   │
   ▼
Apply        →  task por task, decisiones confirmadas
   │
   ▼
Verify       →  contra el spec original
```

El asistente no avanza una fase sin tu confirmación. Ante cada decisión de arquitectura presenta opciones y espera.

---

## Skills disponibles

### Lenguajes

| Skill | Cubre |
|-------|-------|
| `lang-python` | Python 3.12+, uv, dataclasses, ports & adapters, mypy |
| `lang-java` | Java 21+, Gradle, records, Spring Boot, JUnit 5 |
| `lang-typescript` | TypeScript estricto, React, Node.js, Zod, Vitest |
| `lang-go` | Go 1.22+, stdlib, Chi, interfaces pequeñas, testcontainers |

### Product Engineering

| Skill | Cubre |
|-------|-------|
| `role-requirements` | Example Mapping, Given/When/Then, PRD mínimo, DoR/DoD, señales de requisitos problemáticos |
| `role-ddd` | Lenguaje ubicuo, Event Storming, Aggregates, Value Objects, Bounded Contexts, Context Map |

### Arquitectura y diseño

| Skill | Cubre |
|-------|-------|
| `role-architect` | Capas, ADRs, regla de dependencia, señales de alerta |
| `role-backend` | REST, paginación cursor/offset, N+1, manejo de errores, HTTP semántico |
| `role-frontend` | React, Container/Presentational, estado, a11y, performance |
| `role-code-review` | Checklist por capa, OWASP, privacidad, señales de mal diseño |
| `role-solid` | SOLID, DRY/KISS/YAGNI, design patterns, code smells, complejidad ciclomática |
| `role-app-performance` | Profiling, Big O, caché, indexing, connection pooling, memory management |
| `role-concurrency` | Async/await por lenguaje, goroutines, race conditions, deadlocks, worker pools |

### UX/UI y diseño responsable

| Skill | Cubre |
|-------|-------|
| `role-ux` | Jobs-to-be-done, flujos, arquitectura de información, empty/error/loading states, onboarding |
| `role-ui` | Design tokens, tipografía, color semántico, dark mode, estados de componentes, sistema 4pt |
| `role-accessibility` | WCAG 2.2 AA, ARIA, foco y teclado, formularios accesibles, testing con screen readers |
| `role-responsible-design` | Dark patterns, diseño ético de IA, privacidad en UX, bienestar digital, lenguaje inclusivo |

### Calidad y operaciones

| Skill | Cubre |
|-------|-------|
| `role-testing` | Pirámide, fakes vs mocks, Testcontainers, naming conventions |
| `role-performance` | Load/stress/soak testing con k6 y Locust, SLOs, profiling |
| `role-observability` | Logging estructurado, métricas OpenTelemetry, tracing distribuido, alertas |
| `role-cicd` | GitHub Actions, Blue/Green, Canary, Docker, secrets en pipeline |
| `role-environments` | Multi-ambiente, feature flags, config tipada, zero-downtime migrations |

### Seguridad y privacidad

| Skill | Cubre |
|-------|-------|
| `role-security` | OWASP Top 10, JWT, authn/authz, input validation, headers HTTP |
| `role-privacy` | Clasificación de datos, PII en logs/responses, cifrado, detección de secrets, retención |

### IA y Machine Learning

| Skill | Cubre |
|-------|-------|
| `role-ai-engineer` | Claude API oficial: tool use, prompt caching, streaming, batch API |
| `role-rag` | Chunking, embeddings, reranking — basado en docs oficiales Anthropic |
| `role-ml` | Pipelines, embeddings, serving con FastAPI, monitoreo de drift |

### Infraestructura

| Skill | Cubre |
|-------|-------|
| `infra-aws` | CDK, servicios AWS, IAM least privilege, arquitecturas comunes |
| `infra-docker` | Multi-stage builds por lenguaje, Compose local, seguridad de imágenes |

### Orquestación de agentes

| Skill | Cubre |
|-------|-------|
| `role-orchestrator` | Arquitectura de agentes, delegación paralela, protocolo de contexto con Engram |

---

## Arquitectura de agentes

El template incluye un sistema de sub-agentes que corren en paralelo para reducir tiempos y tokens.

```
Orchestrator  (contexto mínimo — solo coordina)
      │
      ├── sdd-explore          →  sync
      ├── sdd-propose          →  sync
      │
      ├── sdd-spec  ───────────┐
      │                        ├──  PARALELO  (~50% menos tiempo)
      ├── sdd-design ──────────┘
      │
      ├── sdd-tasks            →  sync
      │
      ├── apply task-A ────────┐
      ├── apply task-B ────────┤
      ├── apply task-C ────────┼──  PARALELO  (tasks independientes)
      └── apply task-D ────────┘
```

### Dónde está el ahorro real

| Mecanismo | Qué ahorra |
|-----------|-----------|
| Sub-agentes aislados | Cada agente carga solo el skill y contexto que necesita |
| Spec + Design en paralelo | Tiempo a la mitad en la fase más larga |
| Apply en paralelo | Tasks independientes corren simultáneas |
| Engram entre sesiones | No re-explicás contexto ni decisiones ya tomadas |
| Prompt caching | El contenido de los skills se cachea en la sesión (~90% menos costo en re-lecturas) |

### Comandos de orquestación

| Comando | Qué hace |
|---------|----------|
| `/parallel-phases` | Lanza spec y design como agentes simultáneos |
| `/parallel-apply` | Analiza dependencias y ejecuta tasks en paralelo donde es posible |
| `/gc` | Guarda sesión en Engram y compacta el contexto — limpiar ruido acumulado |

---

## Comandos disponibles

| Comando | Qué hace |
|---------|----------|
| `/start-session` | Setup guiado: lenguaje, tipo de sistema, restricciones |
| `/status` | Estado actual del flujo SDD y tasks pendientes |
| `/new-adr` | Crear nuevo Architecture Decision Record |
| `/parallel-phases` | Spec + Design en paralelo (fase 3) |
| `/parallel-apply` | Apply con análisis de dependencias y paralelismo (fase 5) |

---

## CI/CD — Gates bloqueantes

El pipeline bloquea el merge si falla lint, tests, security scan o build.

### Activar branch protection en GitHub

```
Settings → Branches → Add rule → Branch name: main
✅ Require status checks to pass before merging
✅ Require branches to be up to date before merging
```

Status checks requeridos (exactamente como aparecen en Actions):

| Status check | Qué verifica |
|---|---|
| `Lint` | Ruff/mypy, ESLint/tsc, Checkstyle, go vet |
| `Unit Tests` | Tests unitarios por lenguaje |
| `Integration Tests` | Tests de integración con Postgres + Redis reales |
| `Security Scan` | Gitleaks (secrets), pip-audit, npm audit, govulncheck |
| `Build` | Compilación + Docker build si hay Dockerfile |
| `Format (Python/Java/TypeScript/Go)` | Formato correcto según lenguaje detectado |
| `Check links in markdown` | Links rotos en archivos `.md` |

### Detección automática de lenguaje

El CI detecta el lenguaje del proyecto por los archivos raíz y ejecuta solo los pasos relevantes:

| Archivo detectado | Lenguaje activado |
|---|---|
| `pyproject.toml` / `requirements.txt` | Python |
| `pom.xml` / `build.gradle*` | Java |
| `tsconfig.json` | TypeScript |
| `go.mod` | Go |

---

## GitHub Actions AI Workflows

Cinco workflows que integran Claude directamente en el ciclo de desarrollo del equipo.

> **Sin setup requerido:** los workflows de AI usan `GITHUB_TOKEN`, disponible automáticamente en cada run. No necesitás ningún secret adicional.

| Workflow | Trigger | Modelo | Qué hace |
|----------|---------|--------|----------|
| `ai-issue-triage.yml` | Issue abierto | gpt-4o-mini | Clasifica tipo, prioridad y esfuerzo — aplica labels automáticamente |
| `ai-pr-description.yml` | PR abierto (body vacío) | gpt-4o-mini | Genera descripción estructurada si el PR no tiene una |
| `ai-pr-review.yml` | PR abierto / push | gpt-4o-mini | Code review con prioridades 🔴🟡🔵 — detecta secrets, PII, N+1, auth |
| `adr-check.yml` | PR abierto / push | gpt-4o-mini | Detecta cambios de arquitectura y avisa si falta un ADR |
| `changelog.yml` | Push a main | gpt-4o-mini | Genera entrada de CHANGELOG agrupada por tipo desde los commits |

### Flujo completo

```
Issue creado    →  triage automático: type / priority / effort / labels
PR abierto      →  descripción generada (si está vacía)
                →  code review con niveles de severidad
                →  ADR check (¿cambio de arquitectura sin documentar?)
Merge a main    →  entrada de changelog generada automáticamente
```

### Personalización

Cada workflow tiene el prompt del sistema en el paso de Python — editá el contenido del `system=` para ajustar criterios, idioma o formato a las convenciones de tu equipo.

---

## Archivos incluidos

| Archivo | Propósito |
|---------|-----------|
| `CLAUDE.md` | Instrucciones completas del asistente + reglas de seguridad |
| `AGENTS.md` | Contexto del proyecto para cualquier agente AI |
| `Makefile` | Comandos unificados: `make test`, `make lint`, `make build` |
| `docs/adr/ADR-000-template.md` | Template para Architecture Decision Records |
| `.github/workflows/ci.yml` | Pipeline CI: lint → unit → integration → security scan → build |
| `.github/workflows/ai-issue-triage.yml` | AI triage de issues |
| `.github/workflows/ai-pr-description.yml` | AI generación de descripción de PR |
| `.github/workflows/ai-pr-review.yml` | AI code review en PRs |
| `.github/workflows/adr-check.yml` | Detección de cambios de arquitectura sin ADR |
| `.github/workflows/changelog.yml` | AI generación de changelog en merge a main |
| `.github/pull_request_template.md` | Checklist de arquitectura, seguridad y tests |
| `.github/dependabot.yml` | Actualizaciones automáticas de dependencias (Python, Node, Go, Docker, Actions) |

---

## Pre-commit hooks

Detecta problemas **antes de commitear** — no cuando ya rompiste el CI.

```bash
pip install pre-commit

# Instalar ambos hooks
pre-commit install                          # formato y secrets en cada commit
pre-commit install --hook-type commit-msg   # conventional commits
```

### Qué corre en cada commit

| Hook | Lenguaje | Qué hace |
|------|----------|----------|
| `detect-private-key` | todos | bloquea si detecta un private key |
| `gitleaks` | todos | escanea secrets con entropía |
| `ruff` + `ruff-format` | Python | lint + formato automático |
| `prettier` | TS / JS / JSON / MD | formato automático |
| `gofmt` + `go-vet` | Go | formato + análisis estático |
| `pretty-format-java` | Java | google-java-format automático |
| `conventional-pre-commit` | todos (commit-msg) | valida formato del mensaje |

### Conventional Commits — tipos válidos

```
feat      nueva funcionalidad
fix       corrección de bug
docs      solo documentación
style     formato (sin cambio lógico)
refactor  refactor sin fix ni feature
test      tests
chore     mantenimiento (deps, config)
perf      mejora de performance
ci        cambios en CI/CD
build     sistema de build
revert    revertir un commit
```

**Ejemplos:**
```bash
git commit -m "feat(auth): add JWT refresh token rotation"
git commit -m "fix(api): handle null response from payment gateway"
git commit -m "chore(deps): bump ruff to 0.4.4"
```

---

## CODEOWNERS

`CODEOWNERS` define qué miembros del equipo deben aprobar cambios en partes críticas del repo. GitHub lo usa para requerir reviews automáticamente.

Editá el archivo `CODEOWNERS` en la raíz y reemplazá `@tech-lead`, `@security-lead`, `@devops-lead` con los usernames reales del equipo.

Para que funcione activá en branch protection:
```
✅ Require review from Code Owners
```

---

## Reglas de seguridad

El template tiene reglas que se aplican siempre, sin excepciones:

- **`git push` requiere confirmación explícita** — el asistente muestra los commits y espera tu OK
- **Escaneo de secrets antes de cada commit** — busca API keys, tokens, passwords hardcodeados
- **Operaciones destructivas requieren confirmación** — `reset --hard`, `rm -rf`, `DROP TABLE`
- **PII en código** — el asistente señala y pide reemplazar por datos ficticios

---

## Agregar un nuevo skill

```bash
# 1. Crear el archivo
mkdir -p .claude/skills/{nombre}
touch .claude/skills/{nombre}/SKILL.md

# 2. Registrar en CLAUDE.md (tabla de skills disponibles)
# 3. Registrar en AGENTS.md
```

---

## Skills de IA — fuentes oficiales

Los skills `role-ai-engineer` y `role-rag` están basados exclusivamente en documentación oficial de Anthropic:

- [Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [RAG Guide](https://docs.anthropic.com/en/docs/build-with-claude/rag)
- [Batch API](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing)
- [Streaming](https://docs.anthropic.com/en/docs/build-with-claude/streaming)

---

## Licencia

MIT
