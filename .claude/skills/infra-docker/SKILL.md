# Skill: Docker

## Principios
- Imágenes mínimas: solo lo necesario en producción
- Multi-stage builds: separar build de runtime
- Usuario no root en producción
- Un proceso por contenedor
- Inmutable: sin cambios en runtime, toda config por env vars

---

## Multi-stage builds por lenguaje

### Python
```dockerfile
# Stage 1: dependencias
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Stage 2: runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY src/ src/
RUN useradd -r -s /bin/false appuser
USER appuser
CMD [".venv/bin/python", "-m", "app"]
```

### Go
```dockerfile
# Stage 1: build
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server ./cmd/api

# Stage 2: runtime mínimo
FROM scratch
COPY --from=builder /app/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
USER 65534:65534
ENTRYPOINT ["/server"]
```

### Node / TypeScript
```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --include=dev
COPY . .
RUN npm run build

# Stage 2: runtime
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/dist ./dist
USER appuser
CMD ["node", "dist/index.js"]
```

### Java
```dockerfile
# Stage 1: build
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /app
COPY gradle/ gradle/
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN ./gradlew dependencies --no-daemon
COPY src/ src/
RUN ./gradlew bootJar --no-daemon

# Stage 2: runtime (JRE, no JDK)
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
RUN useradd -r -s /bin/false appuser
USER appuser
ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## .dockerignore — siempre presente

```
.git
.github
.claude
docs/
tests/
*.md
.env
.env.*
node_modules/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
dist/
build/
*.log
```

---

## Docker Compose — desarrollo local

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgresql://postgres:dev@db:5432/app
      REDIS_URL: redis://cache:6379
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    volumes:
      - ./src:/app/src  # hot reload en dev

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## Checklist de seguridad

- [ ] Usuario no root (`USER appuser`)
- [ ] Sin secrets en Dockerfile ni en imagen (usar `--secret` o env vars en runtime)
- [ ] Imagen base con tag específico, no `latest`
- [ ] `.dockerignore` presente y completo
- [ ] Sin herramientas de build en imagen final
- [ ] Escaneo de vulnerabilidades en CI (Trivy / Snyk)

```yaml
# CI: escanear imagen con Trivy
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: app:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: '1'
```

---

## Tamaños de imagen orientativos

| Stack | Base | Multi-stage |
|-------|------|-------------|
| Go | ~300MB (golang) | ~10MB (scratch) |
| Python | ~200MB (python:slim) | ~120MB |
| Node | ~180MB (node:alpine) | ~100MB |
| Java | ~400MB (jdk) | ~200MB (jre) |

---

## Decisiones comunes en Docker

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Base image:** distroless vs alpine vs slim vs scratch
- **Orquestación:** Docker Compose vs ECS vs Kubernetes
- **Registry:** ECR vs GHCR vs Docker Hub
- **Secrets en runtime:** env vars vs Docker secrets vs AWS Secrets Manager
- **Volúmenes en dev:** bind mount vs named volume
