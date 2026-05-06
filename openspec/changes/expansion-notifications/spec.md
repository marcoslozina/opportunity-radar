# Specification: Email Notifications

## User Stories

### Story: Recibir reporte semanal
- **AS** un usuario del Radar (Inversor Inmobiliario o Consultor ESG)
- **I WANT** recibir un email con los hallazgos más importantes de la semana
- **SO THAT** no tenga que entrar al dashboard manualmente para saber si hay una oportunidad crítica.

## Functional Requirements

### Requirement: Email Trigger
El sistema MUST disparar el envío de una notificación solo después de que el briefing haya sido generado y guardado exitosamente.

### Requirement: Content Selection
El email MUST incluir al menos:
- Nombre del Nicho.
- Top 3 oportunidades por `score_total`.
- Para cada una: Topic, Score y Acción Recomendada.
- Link directo al Dashboard local.

### Requirement: Failure Tolerance
Si el envío de email falla (timeout, error de API), el pipeline MUST marcarse como completado igualmente y loggear el error. La notificación es un "best effort".

## Contract: NotificationPort

```python
class NotificationPort(ABC):
    @abstractmethod
    async def send_briefing(self, briefing: Briefing, niche_name: str) -> bool:
        """Envía el briefing vía el canal configurado."""
        ...
```
