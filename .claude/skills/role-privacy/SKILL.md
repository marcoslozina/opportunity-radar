# Skill: Seguridad y Privacidad en Código

## Principio base
Privacy by design. La privacidad no se agrega al final — es una restricción de diseño desde el inicio.
Un leak de datos no es solo un bug. Es un incidente con consecuencias legales y de confianza.

---

## Clasificación de datos sensibles

Antes de escribir cualquier código que maneje datos, clasificar:

| Nivel | Tipo de dato | Ejemplos | Tratamiento |
|-------|-------------|---------|-------------|
| 🔴 Crítico | Credenciales | Passwords, API keys, tokens, certificados | Nunca en código, logs ni DB sin hash |
| 🔴 Crítico | PII sensible | DNI, pasaporte, datos médicos, biometría | Cifrado en reposo, acceso auditado |
| 🟡 Sensible | PII básica | Nombre, email, teléfono, dirección | Cifrado en tránsito, no loggear completo |
| 🟡 Sensible | Financiero | Tarjetas, CBU, montos de transacciones | PCI-DSS si aplica, tokenizar |
| 🟢 Interno | Datos de negocio | IDs internos, métricas | Acceso controlado por rol |
| ⚪ Público | Datos públicos | Precios, catálogos | Sin restricciones especiales |

---

## Reglas de código — no negociables

### Secrets — detección automática

```python
# ❌ Patrones que NUNCA deben aparecer en código
API_KEY = "sk-..."
SECRET = "eyJ..."
PASSWORD = "hunter2"
DATABASE_URL = "postgres://user:pass@..."

# ✅ Siempre desde el entorno
import os
API_KEY = os.environ["API_KEY"]          # falla en startup si no existe → intencional
DATABASE_URL = os.environ["DATABASE_URL"]
```

**Patrones a detectar en code review (regex):**
```
(api[_-]?key|secret|password|token|pwd)\s*=\s*["'][^"']{8,}["']
(sk-|pk_live_|Bearer\s+ey)[A-Za-z0-9+/]{20,}
postgres://[^:]+:[^@]+@
```

### PII — nunca loggear completo

```python
# ❌ PII completa en logs
logger.info(f"User logged in: {user.email} from {request.ip}")
logger.error(f"Payment failed for card {card_number}")

# ✅ Solo lo necesario para trazabilidad
logger.info(f"User logged in: user_id={user.id}")
logger.error(f"Payment failed: user_id={user.id} last4={card_number[-4:]}")
```

### Masking de datos en responses

```python
# ❌ Exponer datos innecesarios en API
return UserResponse(
    id=user.id,
    email=user.email,
    password_hash=user.password_hash,  # NUNCA
    internal_score=user.risk_score,    # dato interno
)

# ✅ Solo lo que el cliente necesita
return UserResponse(
    id=user.id,
    email=user.email,
    name=user.name,
)
```

### Cifrado de datos sensibles en DB

```python
from cryptography.fernet import Fernet

class EncryptedField:
    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode()).decode()

# DNI, número de tarjeta, datos médicos → siempre cifrados en DB
```

---

## Detección de secrets antes de commit

### Pre-commit hook (agregar al proyecto)

```bash
# .git/hooks/pre-commit o via pre-commit framework
#!/bin/bash
echo "🔍 Escaneando secrets..."

# Patrones que bloquean el commit
patterns=(
  'api[_-]?key\s*=\s*["\x27][^"\x27]{8,}'
  'secret\s*=\s*["\x27][^"\x27]{8,}'
  'password\s*=\s*["\x27][^"\x27]{4,}'
  'sk-[A-Za-z0-9]{20,}'
  'pk_live_[A-Za-z0-9]+'
  'postgres://[^:]+:[^@]+@'
  'mysql://[^:]+:[^@]+@'
  'BEGIN (RSA |EC )?PRIVATE KEY'
)

for pattern in "${patterns[@]}"; do
  if git diff --cached | grep -qiE "$pattern"; then
    echo "❌ SECRET DETECTADO: patrón '$pattern'"
    echo "Remové el secret y usá variables de entorno."
    exit 1
  fi
done

echo "✅ Sin secrets detectados"
```

### Con gitleaks (recomendado para CI)

```yaml
# .github/workflows/ci.yml — agregar job
secret-scan:
  name: Secret Scan
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Privacidad en APIs

### Data minimization — pedir solo lo necesario

```python
# ❌ Recibir y guardar todo
class RegistrationInput(BaseModel):
    name: str
    email: str
    phone: str
    birth_date: date
    address: str
    # ... 20 campos más que no usamos

# ✅ Solo lo necesario para el caso de uso
class RegistrationInput(BaseModel):
    name: str
    email: str
```

### Retención de datos — política explícita

```python
# Datos que se deben eliminar o anonimizar después de N días
class DataRetentionPolicy:
    AUDIT_LOGS_DAYS = 90
    SESSION_TOKENS_DAYS = 30
    DELETED_USER_PII_DAYS = 7    # después de delete, anonimizar PII
    ANALYTICS_RAW_DAYS = 365
```

### Anonimización para logs y analytics

```python
import hashlib

def anonymize_email(email: str) -> str:
    # Identificable internamente pero no reversible externamente
    return hashlib.sha256(email.encode()).hexdigest()[:12]

def mask_ip(ip: str) -> str:
    # Conservar solo los primeros 3 octetos
    parts = ip.split(".")
    return f"{'.'.join(parts[:3])}.0"
```

---

## Checklist de privacidad por feature

Antes de implementar cualquier feature que maneje datos de usuarios:

- [ ] ¿Qué datos realmente necesito? ¿Puedo minimizarlos?
- [ ] ¿Los datos sensibles están cifrados en reposo?
- [ ] ¿Los datos viajan siempre por HTTPS?
- [ ] ¿Los logs no contienen PII completo?
- [ ] ¿Las respuestas de API no exponen campos innecesarios?
- [ ] ¿Hay política de retención definida?
- [ ] ¿Los usuarios pueden eliminar sus datos? (right to erasure)
- [ ] ¿Hay auditoría de acceso a datos sensibles?
- [ ] ¿Los secrets están en env vars / secrets manager?
- [ ] ¿El código nuevo pasa el scan de secrets?

---

## Qué hacer si se detecta un secret commiteado

```bash
# 1. REVOCAR el secret INMEDIATAMENTE (antes de cualquier otra cosa)
#    → Rotar API key, cambiar password, invalidar token

# 2. Eliminar del historial de git
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file" \
  --prune-empty --tag-name-filter cat -- --all

# O con BFG (más rápido)
bfg --delete-files file-with-secret.env
git push --force

# 3. Notificar al equipo
# 4. Auditar si el secret fue usado por terceros
```

**Nunca asumir que un secret commiteado no fue visto**, aunque el repo sea privado.
