# Proposal: Expansion - Email Notifications

## Intent
Proveer una forma proactiva de entrega de insights a los usuarios. Actualmente, el "Opportunity Radar" requiere que el usuario consulte activamente el dashboard. Con este módulo, el sistema enviará automáticamente un resumen del briefing semanal por email una vez completado el pipeline.

## Scope
- Definición de `NotificationPort` en la capa de dominio.
- Implementación de `ResendEmailAdapter` en la capa de infraestructura usando la API de Resend.
- Diseño de un template HTML responsivo y estético para el briefing (nicho PropFlow y ESG específicos).
- Integración en `RunPipelineUseCase` como una tarea de post-procesamiento opcional.
- Configuración vía variables de entorno (`RESEND_API_KEY`, `NOTIFICATION_EMAIL`).

## Out of Scope
- Gestión de suscripciones (opt-in/opt-out) compleja — se asume un único destinatario configurado inicialmente.
- Historial de emails enviados en la base de datos.
- Reintentos persistentes (si falla el envío, se loggea y se continúa).

## Success Criteria
- [ ] Email enviado exitosamente al finalizar un `make run-pipeline`.
- [ ] El email contiene el Top 3 de oportunidades con sus acciones recomendadas.
- [ ] El diseño del email es consistente con la marca PropFlow/ESG.
- [ ] Si la API Key de Resend no está presente, el sistema lo ignora sin fallar.
