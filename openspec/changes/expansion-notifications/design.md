# Technical Design: Email Notifications (Resend)

## Architecture

Seguiremos el patrón de adaptadores.

### 1. Domain (Ports)
- `src/domain/ports/notification_port.py`: Interfaz abstracta.

### 2. Infrastructure (Adapters)
- `src/infrastructure/adapters/resend_email.py`: Implementación del cliente HTTP para Resend.
- Usaremos `httpx` para hacer los requests async a la API de Resend (`https://api.resend.com/emails`).

### 3. Application (Use Cases)
- `RunPipelineUseCase`: Inyectar `notification_port`. Al final de `execute`, llamar a `send_briefing`.

## UI Design: Email Template

El email será un documento HTML con CSS inline para máxima compatibilidad.
Estética:
- Fondo oscuro (`#0F172A`)
- Cards para oportunidades con borde sutil.
- Score en color acento (`#3B82F6`).

### Estructura del Template:
```html
<div style="background: #0F172A; color: #fff; padding: 20px;">
  <h1>PropFlow Report: {{ niche_name }}</h1>
  <p>Encontramos {{ total }} oportunidades. Acá está el Top 3:</p>
  {% for opp in opportunities %}
    <div style="border: 1px solid #334155; padding: 15px; margin-bottom: 10px;">
      <strong>{{ opp.topic }}</strong> (Score: {{ opp.score.total }})
      <p>{{ opp.recommended_action }}</p>
    </div>
  {% endfor %}
  <a href="http://localhost:8501">Ir al Dashboard</a>
</div>
```

## Data Mapping
- Mapear `domain_applicability` (o Implicación) en el template según el modo del nicho.
