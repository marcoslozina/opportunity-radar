# Skill: CI/CD

## Principios
- El pipeline es código. Se versiona, se revisa, se testea.
- Fail fast: los checks más rápidos primero.
- Ningún deploy a producción sin pasar por staging.
- Todo deploy debe ser reversible (rollback < 5 min).

---

## Estructura de pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # 1. Checks rápidos primero (< 2 min)
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: make lint

  # 2. Tests unitarios (< 5 min)
  unit-tests:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Unit tests
        run: make test-unit

  # 3. Tests de integración (con servicios)
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - name: Integration tests
        run: make test-integration

  # 4. Build y push de imagen
  build:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t app:${{ github.sha }} .
      - name: Push to registry
        run: docker push app:${{ github.sha }}
```

---

## Estrategias de deploy

### Blue/Green
```
Traffic → Load Balancer → Blue (activo)
                       → Green (nuevo, sin traffic)

1. Deploy en Green
2. Run smoke tests en Green
3. Shift traffic Blue → Green
4. Mantener Blue como rollback
```
**Cuándo:** apps stateless, rollback crítico, zero-downtime obligatorio.

### Canary
```
Traffic → 95% → Stable
        →  5% → Canary (nuevo)

Monitorear métricas → si OK → aumentar % → 100%
                   → si KO → 0% canary → rollback
```
**Cuándo:** quieras validar en producción con riesgo controlado.

### Rolling
```
Pod 1 → actualizar → healthy
Pod 2 → actualizar → healthy
Pod 3 → actualizar → healthy
```
**Cuándo:** Kubernetes, updates graduales, no necesitás zero-downtime total.

---

## Secrets — reglas

```yaml
# ✅ Usar GitHub Secrets
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}

# ❌ NUNCA
env:
  DATABASE_URL: "postgres://user:password@host/db"
```

- Secrets rotan periódicamente
- Principio de menor privilegio: cada job usa solo los secrets que necesita
- Nunca loggear secrets (`echo $SECRET` → error de pipeline)

---

## Docker — buenas prácticas

```dockerfile
# Multi-stage build para imagen mínima
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync --frozen

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY src/ src/
USER nonroot
CMD [".venv/bin/python", "-m", "app"]
```

- Imagen final sin herramientas de build
- Usuario no root
- `.dockerignore` para excluir `.git`, `tests/`, `docs/`
- Tag con SHA del commit, no `latest` en producción

---

## Checklist antes de mergeear a main

- [ ] Lint pasa
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Cobertura no bajó
- [ ] Security scan (Dependabot / Trivy) sin críticos
- [ ] Code review aprobado
- [ ] Changelog / release notes actualizados

---

## Observabilidad mínima en pipeline

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "❌ Pipeline falló en ${{ github.ref }} — ${{ github.run_url }}"
      }
```

---

## Decisiones de arquitectura comunes en CI/CD

Aplicar protocolo de decisión del CLAUDE.md ante:
- **CI platform:** GitHub Actions vs GitLab CI vs CircleCI vs Jenkins
- **Deploy strategy:** Blue/Green vs Canary vs Rolling
- **Container registry:** ECR vs GCR vs Docker Hub vs GitHub Packages
- **IaC:** Terraform vs CDK vs Pulumi vs CloudFormation
- **Secrets management:** GitHub Secrets vs AWS Secrets Manager vs Vault
