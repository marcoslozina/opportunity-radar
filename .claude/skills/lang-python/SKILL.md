# Skill: Python

## Setup de proyecto

```bash
uv init <nombre>
uv add <dep>          # nunca pip directo
uv add --dev pytest ruff mypy
```

## Convenciones obligatorias

- Python 3.12+
- `from __future__ import annotations` en cada archivo
- Type hints en todo: params, returns, variables de clase
- `X | None` en lugar de `Optional[X]`
- `X | Y` en lugar de `Union[X, Y]`

## Estructura de capas

```
src/
  domain/
    entities/        # dataclasses puras, sin deps externas
    ports/           # ABC con contratos (interfaces)
    value_objects/   # tipos inmutables con validación
  application/
    use_cases/       # orquestan dominio
    services/        # servicios reutilizables
  infrastructure/
    adapters/        # implementaciones concretas de ports
    db/              # SQLAlchemy, repos
    http/            # clientes externos
  api/
    routes/          # FastAPI routers
    schemas/         # Pydantic I/O (distintos del dominio)
tests/
  unit/
  integration/
```

## Patrones clave

### Port (interfaz de dominio)
```python
from abc import ABC, abstractmethod
from domain.entities.user import User, UserId

class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...
```

### Entidad de dominio
```python
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class User:
    id: UserId
    name: str
    email: str

    @classmethod
    def create(cls, name: str, email: str) -> User:
        return cls(id=UserId(uuid4()), name=name, email=email)

@dataclass(frozen=True)
class UserId:
    value: UUID
```

### Use Case
```python
from __future__ import annotations
from domain.ports.user_repository import UserRepository
from domain.entities.user import User, UserId

class CreateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, name: str, email: str) -> UserId:
        user = User.create(name, email)
        await self._repo.save(user)
        return user.id
```

### DI manual (sin framework)
```python
# main.py o app factory
repo = PostgresUserRepository(session)
use_case = CreateUserUseCase(repo)
```

## Testing

```bash
pytest tests/           # todos
pytest tests/unit/      # solo unitarios
pytest -v -k "test_create_user"
```

Naming: `test_<qué>_when_<condición>_then_<resultado>`

```python
def test_create_user_when_email_exists_then_raises_duplicate():
    repo = FakeUserRepository(existing_email="a@b.com")
    use_case = CreateUserUseCase(repo)
    with pytest.raises(DuplicateEmailError):
        await use_case.execute("Juan", "a@b.com")
```

- Unit: mockear ports con fakes/stubs, testear use cases
- Integration: adapters contra infra real (Docker / testcontainers)

## Linting y tipos

```bash
ruff check src/         # linting
ruff format src/        # formato
mypy src/               # tipos
```

## Cuándo usar Pydantic vs dataclass

| Caso | Usar |
|------|------|
| Entidad de dominio pura | `@dataclass` |
| Value object con validación | `pydantic.BaseModel` (frozen) |
| Schema de API (I/O) | `pydantic.BaseModel` |
| Config de la app | `pydantic-settings` |

## Decisiones de arquitectura comunes en Python

Ante estas elecciones, aplicar el protocolo de decisión del CLAUDE.md:
- **ORM:** SQLAlchemy vs SQLModel vs raw queries
- **HTTP:** FastAPI vs Flask vs aiohttp
- **Async:** asyncio nativo vs sync bloqueante
- **Tests:** pytest-mock vs fakes manuales
- **Validación:** Pydantic v2 vs attrs vs plain dataclasses
