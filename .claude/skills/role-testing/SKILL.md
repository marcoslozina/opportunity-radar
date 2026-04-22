# Skill: Testing Strategy

## Principio base
Los tests verifican COMPORTAMIENTO, no implementación.
Un test que pasa cuando el código está roto no es un test — es ruido.

---

## Pirámide de tests

```
           /\
          /  \
         / E2E \          ← pocos, lentos, costosos (flujos críticos)
        /--------\
       /Integration\      ← adapters contra infra real
      /--------------\
     /   Unit Tests   \   ← mayoría, rápidos, aislados
    /------------------\
```

**Regla:** si tenés muchos E2E y pocos unitarios, la pirámide está invertida. Es frágil y lenta.

---

## Unit Tests — use cases y dominio

```python
# ✅ Testear comportamiento, no implementación
def test_create_user_assigns_unique_id():
    repo = FakeUserRepository()
    use_case = CreateUserUseCase(repo)

    id1 = use_case.execute(name="Ana", email="ana@test.com")
    id2 = use_case.execute(name="Luis", email="luis@test.com")

    assert id1 != id2

def test_create_user_raises_when_email_already_exists():
    repo = FakeUserRepository(existing_emails={"ana@test.com"})
    use_case = CreateUserUseCase(repo)

    with pytest.raises(DuplicateEmailError):
        use_case.execute(name="Ana2", email="ana@test.com")

# ✅ Fake en lugar de mock cuando el contrato es simple
class FakeUserRepository(UserRepository):
    def __init__(self, existing_emails: set[str] = None):
        self._users: dict[UserId, User] = {}
        self._existing_emails = existing_emails or set()

    async def save(self, user: User) -> None:
        if user.email in self._existing_emails:
            raise DuplicateEmailError(user.email)
        self._users[user.id] = user

    async def find_by_id(self, user_id: UserId) -> User | None:
        return self._users.get(user_id)
```

**Fakes vs Mocks:**
- **Fake:** implementación simplificada del contrato (preferido)
- **Mock:** verificación de llamadas (solo cuando el comportamiento observable ES la llamada)

---

## Integration Tests — adapters

```python
# Testear el adapter contra infraestructura real
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
def repo(postgres):
    engine = create_engine(postgres.get_connection_url())
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield PostgresUserRepository(session)

def test_save_and_find_user(repo):
    user = User.create("Ana", "ana@test.com")
    repo.save(user)
    found = repo.find_by_id(user.id)
    assert found.email == "ana@test.com"
```

**Nunca H2/SQLite en lugar de Postgres en producción.** El comportamiento difiere. Usá Testcontainers.

---

## E2E / API Tests

```python
# Testear el contrato de la API completa
import httpx
from fastapi.testclient import TestClient

def test_create_user_returns_201(client: TestClient):
    response = client.post("/users", json={"name": "Ana", "email": "ana@test.com"})
    assert response.status_code == 201
    assert "id" in response.json()

def test_create_user_with_invalid_email_returns_422(client: TestClient):
    response = client.post("/users", json={"name": "Ana", "email": "not-an-email"})
    assert response.status_code == 422

def test_get_nonexistent_user_returns_404(client: TestClient):
    response = client.get("/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

---

## Naming — convenciones

```
test_<qué>_when_<condición>_then_<resultado>

test_create_user_when_email_exists_then_raises_duplicate_error
test_find_user_when_id_not_found_then_returns_none
test_post_user_when_input_invalid_then_returns_422
```

Cada nombre debe poder leerse como documentación. Si no queda claro, el test hace demasiado.

---

## Qué NO testear

- Getters/setters triviales sin lógica
- El framework (FastAPI ya testea que el routing funciona)
- Infraestructura de terceros (no testees que Postgres funciona)
- Implementación interna (refactor no debería romper tests)

---

## Cobertura — perspectiva correcta

**Cobertura alta no es igual a tests buenos.**

- 100% cobertura con tests triviales = falsa seguridad
- 70% cobertura con tests de comportamiento real = mucho más valor

**Lo que SÍ medir:** cuántos bugs escapan a producción.

---

## Test doubles — cuándo usar qué

| Tipo | Qué hace | Cuándo |
|------|----------|--------|
| **Fake** | Implementación simplificada | Port con contrato simple |
| **Stub** | Devuelve valor fijo | Dependencia con un solo path relevante |
| **Mock** | Verifica que fue llamado | Cuando el efecto ES la llamada (emails, eventos) |
| **Spy** | Registra llamadas sin cambiar comportamiento | Debugging de tests complejos |

---

## Decisiones comunes en Testing

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Fakes vs Mocks:** para cada port del dominio
- **Testcontainers vs embedded DB:** para adapters de base de datos
- **Coverage threshold:** qué % mínimo imponer en CI
- **Test isolation:** base de datos limpia entre tests vs transacciones que se revierten
