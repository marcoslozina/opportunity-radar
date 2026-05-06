# Monitoring Guide — Opportunity Radar

---

## 1. UptimeRobot — uptime monitoring

UptimeRobot free plan: 50 monitors, checks cada 5 minutos, alertas por email y Telegram.

### Setup

1. Crear cuenta en [uptimerobot.com](https://uptimerobot.com)
2. Dashboard → **Add New Monitor** → tipo **HTTP(s)**
3. Crear los dos monitors:

| Monitor name | URL | Interval | Expected status |
|---|---|---|---|
| Radar API | `https://api.radar.marcoslozina.com/health` | 5 min | 200 |
| Radar Frontend | `https://radar.marcoslozina.com` | 5 min | 200 |

### Alertas

**Email (obligatorio):**
- My Settings → Alert Contacts → Add Alert Contact → E-mail → `marcoslozina@gmail.com`
- Asignar a ambos monitors

**Telegram (recomendado):**
- Crear bot con [@BotFather](https://t.me/BotFather) → copiar token
- Obtener chat ID: `https://api.telegram.org/bot{TOKEN}/getUpdates`
- Alert Contacts → Tipo: Telegram → token + chat ID

**Umbral:** alertar después de 2 fallos consecutivos (10 minutos caído) para evitar falsos positivos.

---

## 2. Sentry — error tracking

Radar ya tiene Sentry integrado en `src/main.py` con `FastApiIntegration` y `SqlalchemyIntegration`.

### Configurar DSN

```bash
# .env de producción
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

### Alertas recomendadas

Ir a Sentry → proyecto `opportunity-radar` → **Alerts → Create Alert Rule**:

| Condición | Umbral | Acción |
|---|---|---|
| Error rate | >1% en 5 minutos | Email + Slack |
| New issue created | cualquiera | Email inmediato |
| p95 latency | >2s en 10 minutos | Email |

**Error rate alert:**
- Alert type: **Metric Alert**
- Metric: `Number of Errors`
- Threshold: `> 10 errors in 5 minutes`
- Action: send email to `marcoslozina@gmail.com`

**Latency alert:**
- Alert type: **Metric Alert**
- Metric: `p95(transaction.duration)`
- Threshold: `> 2000ms`
- Filter: `transaction:/api/*`

**New issue:**
- Alert type: **Issue Alert**
- Condición: `A new issue is created`
- Action: send email

---

## 3. Billing crítico — recovery ante webhook fallido

### Flujo de detección

1. Sentry muestra error con tag `component: webhook`
2. Lemon Squeezy → Settings → Webhooks → **Recent Deliveries** — buscar el evento fallido

### Tabla `audit_log` — diagnóstico en Supabase SQL Editor

```sql
-- Últimos 20 eventos de billing
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;

-- Verificar que cada subscription_created tiene su api_key
SELECT al.order_id, al.tier, al.created_at, ak.key_prefix
FROM audit_log al
LEFT JOIN api_keys ak ON ak.order_id = al.order_id
WHERE al.action = 'subscription_created'
  AND al.created_at > NOW() - INTERVAL '7 days'
ORDER BY al.created_at DESC;
```

Señales de alerta:
- `subscription_created` sin `api_key` correspondiente → cliente pagó pero no tiene acceso
- Ausencia de eventos en más de 24hs durante período activo de ventas

### Recovery manual

Si el webhook falló y el cliente no tiene API key:

```bash
# Re-disparar webhook desde Lemon Squeezy UI (Settings → Webhooks → Resend)
# O provisionar manualmente:
curl -X POST https://api.radar.marcoslozina.com/api/admin/provision \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "...", "tier": "starter", "email": "cliente@example.com"}'
```

### Tabla `api_keys` — verificar estado de una key específica

```sql
-- Verificar que la key existe y está activa
SELECT key_prefix, tier, is_active, quota_used, quota_limit, created_at
FROM api_keys
WHERE order_id = 'LS_ORDER_ID_AQUI';
```

---

## 4. Logs de producción

### Docker Compose (producción recomendada)

```bash
# Logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f api

# Solo errores
docker compose -f docker-compose.prod.yml logs api | grep '"level":"error"'

# Últimas 100 líneas
docker compose -f docker-compose.prod.yml logs --tail=100 api

# Filtrar por correlation ID (request_id del header de respuesta)
docker compose -f docker-compose.prod.yml logs api | grep '"request_id":"REQ_ID_AQUI"'
```

### systemd (bare metal)

```bash
# Seguir logs en tiempo real
journalctl -u opportunity-radar -f

# Errores de la última hora
journalctl -u opportunity-radar --since "1 hour ago" | grep -i error

# Desde un timestamp específico
journalctl -u opportunity-radar --since "2026-01-15 10:00:00"
```

### Patrones críticos a vigilar

| Pattern en logs | Urgencia | Acción |
|---|---|---|
| `circuit_breaker_open` | ALTO | Redis inaccesible — fail-open activo, quota no se aplica |
| `quota_redis_unavailable` | ALTO | Redis caído — clientes pueden exceder quota |
| `webhook_secret_not_configured` | CRITICO | Ningún pago puede procesarse — setear `LS_WEBHOOK_SECRET` |
| `brute_force_check_failed` | MEDIO | Redis intermitente — revisar conectividad |
| `STARTUP ERROR` | CRITICO | Variables de entorno faltantes — servidor no arranca |

---

## 5. Dashboard SQL semanal

Ejecutar en Supabase → SQL Editor:

```sql
-- Usuarios activos (con quota usada en la última semana)
SELECT ak.tier, COUNT(*) as active_users, AVG(ak.quota_used) as avg_usage
FROM api_keys ak
WHERE ak.is_active = true
  AND ak.updated_at > NOW() - INTERVAL '7 days'
GROUP BY ak.tier ORDER BY active_users DESC;
```

```sql
-- Distribución de tiers (snapshot actual)
SELECT tier, COUNT(*) as total, SUM(quota_used) as total_calls
FROM api_keys
WHERE is_active = true
GROUP BY tier ORDER BY tier;
```

```sql
-- Nuevas suscripciones esta semana
SELECT tier, COUNT(*) as new_subs, MAX(created_at) as last_signup
FROM audit_log
WHERE action = 'subscription_created'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY tier ORDER BY new_subs DESC;
```

```sql
-- Clientes que alcanzaron el 80% de su quota
SELECT key_prefix, tier, quota_used, quota_limit,
       ROUND(quota_used::numeric / quota_limit * 100, 1) as pct_used
FROM api_keys
WHERE is_active = true
  AND quota_used > quota_limit * 0.8
ORDER BY pct_used DESC;
```

---

## 6. Checklist semanal

- [ ] UptimeRobot dashboard — ambos monitors en verde (API + frontend)
- [ ] Sentry — revisar error rate, ningún issue nuevo sin triagear
- [ ] Ejecutar dashboard SQL de billing en Supabase (sección 5)
- [ ] Verificar Redis keys activas: `redis-cli keys "failed_auth:*" | wc -l`
- [ ] Revisar Lemon Squeezy → Recent Deliveries — todos los webhooks en 200
- [ ] `uvx pip-audit` si se actualizaron dependencias esa semana
- [ ] Dependabot PRs — revisar y mergear los que pasen CI
