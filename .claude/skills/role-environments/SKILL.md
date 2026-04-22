# Skill: Multi-Ambiente y Feature Flags

## Principio base
El código es el mismo en todos los ambientes. Lo que cambia es la configuración.
Nunca `if ENV == "production"` en lógica de negocio.

---

## Estrategia de ambientes

```
local → dev → staging → production
  │       │       │          │
  │       │       │          └── tráfico real, datos reales
  │       │       └── mirror de prod, datos anonimizados
  │       └── integración continua, datos de test
  └── máquina del desarrollador
```

### Reglas por ambiente

| Regla | Local | Dev | Staging | Prod |
|-------|-------|-----|---------|------|
| Datos reales de usuarios | ❌ | ❌ | ❌ | ✅ |
| Datos anonimizados | ✅ | ✅ | ✅ | ❌ |
| Migrations automáticas | ✅ | ✅ | ❌ | ❌ |
| Debug logs | ✅ | ✅ | ❌ | ❌ |
| Feature flags activos | Todos | Todos | Seleccionados | Graduales |
| Deploy manual | ✅ | ❌ | ❌ | ❌ |

---

## Gestión de configuración

### Patrón: config tipada por ambiente

```python
# config/settings.py
from pydantic_settings import BaseSettings
from enum import Enum

class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    env: Environment = Environment.LOCAL
    debug: bool = False
    database_url: str
    redis_url: str
    api_key: str
    log_level: str = "info"

    # Valores que cambian por ambiente
    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION

    @property
    def allow_migrations(self) -> bool:
        return self.env in (Environment.LOCAL, Environment.DEV)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Archivos de configuración por ambiente

```
.env.example          # template sin valores reales → commiteado
.env.local            # valores locales → en .gitignore
.env.dev              # valores dev → en .gitignore o secrets manager
.env.staging          # valores staging → secrets manager
.env.production       # NUNCA en filesystem → solo secrets manager
```

```bash
# .env.example — commiteado, sin valores reales
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
REDIS_URL=redis://localhost:6379
API_KEY=your-api-key-here
LOG_LEVEL=info
```

---

## Feature Flags

### Cuándo usar feature flags

| Caso | Usar |
|------|------|
| Deploy sin activar feature | ✅ |
| A/B testing | ✅ |
| Rollout gradual (1% → 10% → 100%) | ✅ |
| Kill switch de emergencia | ✅ |
| Config que cambia por usuario/segmento | ✅ |
| Lógica permanente de negocio | ❌ usar config normal |

### Implementación simple (sin librería)

```python
# domain/ports/feature_flags.py
from abc import ABC, abstractmethod

class FeatureFlags(ABC):
    @abstractmethod
    def is_enabled(self, flag: str, user_id: str | None = None) -> bool: ...

# infrastructure/adapters/env_feature_flags.py
class EnvFeatureFlags(FeatureFlags):
    def is_enabled(self, flag: str, user_id: str | None = None) -> bool:
        return os.environ.get(f"FEATURE_{flag.upper()}", "false").lower() == "true"

# uso en use case
class CheckoutUseCase:
    def __init__(self, flags: FeatureFlags):
        self._flags = flags

    def execute(self, cart: Cart) -> Order:
        if self._flags.is_enabled("NEW_PAYMENT_FLOW", cart.user_id):
            return self._new_payment_flow(cart)
        return self._legacy_payment_flow(cart)
```

### Con LaunchDarkly / GrowthBook (producción)

```python
import ldclient
from ldclient.config import Config

ldclient.set_config(Config(os.environ["LAUNCHDARKLY_SDK_KEY"]))
client = ldclient.get()

def is_feature_enabled(flag: str, user_id: str) -> bool:
    context = ldclient.Context.builder(user_id).build()
    return client.variation(flag, context, default=False)
```

---

## Rollout gradual

```
Fase 1: 0% usuarios    → feature off, solo en dev/staging
Fase 2: 1% usuarios    → smoke test en prod con tráfico real mínimo
Fase 3: 10% usuarios   → monitorear métricas, errores, latencia
Fase 4: 50% usuarios   → A/B testing, comparar métricas
Fase 5: 100% usuarios  → feature completamente activa
Fase 6: eliminar flag  → cleanup del código (deuda técnica)
```

**Nunca dejar flags viejos en el código.** Cada flag tiene fecha de expiración.

---

## Migrations — estrategia por ambiente

### Zero-downtime migrations (producción)

```
❌ Renombrar columna en un paso:
   ALTER TABLE users RENAME COLUMN user_name TO name;
   → rompe el código en producción que usa user_name

✅ En tres deploys:
   Deploy 1: agregar columna nueva `name`, escribir en ambas
   Deploy 2: leer desde `name`, seguir escribiendo en ambas
   Deploy 3: eliminar columna `user_name`
```

```python
# Expand-Contract pattern
# Paso 1: Expand — agregar, no cambiar
def upgrade():
    op.add_column('users', sa.Column('name', sa.String))
    op.execute("UPDATE users SET name = user_name")

# Paso 2 (deploy siguiente): Contract — eliminar lo viejo
def upgrade():
    op.drop_column('users', 'user_name')
```

---

## Checklist antes de deploy a producción

- [ ] Feature testeada en staging con datos anonimizados
- [ ] Feature flag configurado para rollout gradual
- [ ] Migrations backward-compatible (no rompen la versión anterior)
- [ ] Rollback plan definido (¿cómo revertimos si algo falla?)
- [ ] Alertas configuradas para las métricas relevantes de la feature
- [ ] Runbook actualizado si la operación es compleja

---

## Decisiones comunes en Multi-Ambiente

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Feature flags:** homebrew vs LaunchDarkly vs GrowthBook vs Unleash
- **Config management:** env vars vs AWS Parameter Store vs Vault
- **Staging data:** anonimización vs datos sintéticos vs subset de prod
- **Deploy strategy:** blue/green vs canary vs rolling (ver `role-cicd`)
