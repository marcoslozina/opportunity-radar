# Skill: Security

## Principio base
Security by design. No es un layer que se agrega al final — es una dimensión de cada decisión de arquitectura.

---

## OWASP Top 10 — aplicado al código

### A01 — Broken Access Control
```python
# ❌ Confiar en el cliente
def get_order(order_id: str, user_id: str = request.query["user_id"]):
    return db.find_order(order_id)  # cualquiera puede ver cualquier orden

# ✅ Verificar en el servidor
def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    order = db.find_order(order_id)
    if order.user_id != current_user.id:
        raise ForbiddenError()
    return order
```

### A02 — Cryptographic Failures
```python
# ❌ Datos sensibles en texto plano o hash débil
password_hash = md5(password)

# ✅ Hash seguro con salt
import bcrypt
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

### A03 — Injection
```python
# ❌ SQL injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# ✅ Parametrizado
query = "SELECT * FROM users WHERE name = :name"
db.execute(query, {"name": user_input})
```

### A07 — Auth failures
- Tokens JWT: validar firma + expiración + audience
- Sesiones: regenerar ID después de login
- Passwords: mínimo 12 chars, sin restricciones absurdas de caracteres especiales
- MFA en cuentas con privilegios elevados

### A09 — Logging failures
```python
# ❌ Loggear datos sensibles
logger.info(f"Login: user={email} password={password}")

# ✅ Solo lo necesario
logger.info(f"Login attempt: user_id={user_id} success={success}")
```

---

## Secrets — reglas no negociables

```bash
# ❌ Nunca en código
API_KEY = "<secret-key-here>"
DATABASE_URL = "postgres://<user>:<pass>@<host>/<db>"

# ✅ Siempre en env vars
import os
API_KEY = os.environ["API_KEY"]  # falla en startup si no está → intencional
```

- `.env` en `.gitignore` siempre
- Secrets rotan periódicamente (< 90 días en producción)
- Principio de menor privilegio: cada servicio tiene solo los secrets que necesita
- Usar AWS Secrets Manager / Vault para producción, no env vars del OS

---

## Autenticación y Autorización

### JWT — validación correcta
```python
import jwt

def validate_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],       # especificar algoritmo explícito
            audience="my-api",          # validar audience
            options={"verify_exp": True} # verificar expiración
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expirado")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Token inválido")
```

### RBAC básico
```python
from enum import Enum

class Permission(Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"

def require_permission(permission: Permission):
    def decorator(func):
        def wrapper(current_user: User, *args, **kwargs):
            if permission not in current_user.permissions:
                raise ForbiddenError(f"Requiere permiso: {permission.value}")
            return func(current_user, *args, **kwargs)
        return wrapper
    return decorator
```

---

## Input validation — en el borde

```python
# Toda validación en entry point, antes de llegar al dominio
from pydantic import BaseModel, validator, constr

class CreateUserInput(BaseModel):
    name: constr(min_length=1, max_length=100, strip_whitespace=True)
    email: str
    age: int

    @validator("email")
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email inválido")
        return v.lower().strip()

    @validator("age")
    def validate_age(cls, v):
        if not 0 < v < 150:
            raise ValueError("Edad inválida")
        return v
```

---

## Headers de seguridad HTTP

```python
# Para cualquier API/web — configurar en el entry point
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

---

## Threat Modeling — preguntas a hacer por feature

Ante cada feature nueva que tenga datos o acceso:

1. **¿Quién puede acceder a esto?** → definir autenticación + autorización
2. **¿Qué pasa si el input es malicioso?** → validar + sanitizar
3. **¿Qué datos sensibles maneja?** → cifrado + logging seguro
4. **¿Qué puede salir mal en infra?** → timeouts, circuit breakers, fallbacks
5. **¿Cómo auditamos accesos?** → logs de acceso a datos sensibles

---

## Checklist de seguridad por PR

- [ ] Sin secrets en código o logs
- [ ] Input validado antes de usarse
- [ ] Autorización verificada en el servidor
- [ ] Queries parametrizadas (sin concatenación)
- [ ] Datos sensibles cifrados en reposo
- [ ] Dependencias sin vulnerabilidades críticas conocidas
- [ ] Errores no exponen detalles de implementación al cliente
