# GOLIVE — Opportunity Radar

Guía de deploy para producción comercial.

---

## Variables de entorno requeridas

Copiar `.env.example` a `.env` y completar todos los valores.

```env
# Base de datos (PostgreSQL en producción)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/opportunity_radar

# Redis — quota mensual y caché de rate limiting
REDIS_URL=redis://localhost:6379

# Anthropic (briefings, sugerencias de keywords y nichos)
ANTHROPIC_API_KEY=sk-ant-...

# Lemon Squeezy — pagos
LS_API_KEY=            # API key del store
LS_STORE_ID=           # ID numérico del store
LS_WEBHOOK_SECRET=     # Secret para validar webhooks
LS_VARIANT_STARTER=    # ID del product variant Starter
LS_VARIANT_PROFESSIONAL=
LS_VARIANT_ENTERPRISE=
LS_SUCCESS_URL=https://tu-dominio.com/success
LS_FAILURE_URL=https://tu-dominio.com/cancel

# Fuentes de datos
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=opportunity-radar/1.0
YOUTUBE_API_KEY=
SERP_API_KEY=
PRODUCT_HUNT_TOKEN=

# Notificaciones (Resend)
RESEND_API_KEY=
NOTIFICATION_EMAIL=alerts@tu-dominio.com

# Scheduler (cron — cuándo corre el pipeline por defecto)
PIPELINE_SCHEDULE=0 8 * * 1
```

---

## Tiers y precios sugeridos

| Tier         | Precio/mes | Oportunidades/mes | Nichos | Briefings | Product Discovery | CSV |
|--------------|------------|-------------------|--------|-----------|-------------------|-----|
| Starter      | $49 USD    | 100               | 3      | No        | No                | No  |
| Professional | $149 USD   | 1,000             | 15     | Sí        | Sí                | Sí  |
| Enterprise   | $399 USD   | Ilimitado         | —      | Sí        | Sí                | Sí  |

Rate limits (requests/minuto): Starter 20 · Professional 60 · Enterprise 300.

---

## Comandos de deploy

```bash
# 1. Instalar dependencias
uv sync

# 2. Aplicar migraciones de base de datos
cd /ruta/al/proyecto
uv run alembic upgrade head

# 3. Iniciar el servidor
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1

# Producción con Gunicorn + Uvicorn workers (recomendado)
uv run gunicorn src.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w 2 \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

> Con workers > 1, el TTLCache en `api_key.py` es por proceso. Esto es seguro (el peor caso es
> una DB lookup extra). Redis sí es compartido y correcto entre todos los workers.

---

## Checklist post-deploy

### Endpoints a verificar

```bash
BASE=https://tu-dominio.com
KEY=tu-api-key

# Health
curl $BASE/health

# Auth (debe devolver 401 sin key)
curl $BASE/opportunities?niche_id=cualquier-cosa

# Auth con key válida (debe devolver 200 o lista vacía)
curl -H "X-API-Key: $KEY" "$BASE/opportunities?niche_id=<niche-uuid>"

# Billing usage (verifica quota Redis)
curl -H "X-API-Key: $KEY" $BASE/billing/usage

# Checkout (crea sesión en Lemon Squeezy)
curl -X POST $BASE/billing/checkout \
     -H "Content-Type: application/json" \
     -d '{"tier": "starter", "email": "test@test.com"}'

# Webhook (debe devolver 401 sin firma)
curl -X POST $BASE/billing/webhook -d '{}'

# Rate limit (50+ requests rápidos deben devolver 429)
for i in $(seq 1 25); do
  curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $KEY" "$BASE/opportunities?niche_id=test"
done
```

### Verificaciones manuales

- [ ] `alembic upgrade head` corrió sin errores
- [ ] Redis accesible (`redis-cli ping` → `PONG`)
- [ ] Al menos una API key creada en DB con tier asignado
- [ ] Lemon Squeezy webhook URL configurada en el dashboard de LS apuntando a `POST /billing/webhook`
- [ ] Variables de entorno de fuentes de datos completas (Reddit, YouTube, SERP, Product Hunt)
- [ ] `GET /billing/usage` devuelve `queries_used`, `queries_limit`, `reset_date`
- [ ] `POST /billing/checkout` con tier=starter retorna una URL de checkout válida de LS

---

## Notas de arquitectura

- **Quota Redis**: fails open. Si Redis no está disponible, el contador retorna `-1` y se omite la
  verificación. El servicio sigue funcionando pero sin enforcement de quota.
- **TTLCache de API keys**: 5 minutos. Al revocar una key en DB, puede tardar hasta 5 min en
  propagarse. Para revocación inmediata, reiniciar el proceso.
- **Rate limiting (slowapi)**: por API key (header `X-API-Key`) o por IP si no hay key. Dinámico
  por tier via `get_rate_limit()`.
- **Webhooks de LS**: validados por HMAC-SHA256 contra `LS_WEBHOOK_SECRET`. Sin firma = 401.
