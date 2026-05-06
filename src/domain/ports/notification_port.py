from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.briefing import Briefing
    from domain.value_objects.alert_payload import AlertPayload


class NotificationPort(ABC):
    @abstractmethod
    async def send_briefing(self, briefing: Briefing, niche_name: str) -> bool:
        """
        Envía un resumen del briefing al canal configurado.

        Args:
            briefing: El objeto briefing con las oportunidades encontradas.
            niche_name: El nombre del nicho para el asunto/contexto.

        Returns:
            bool: True si el envío fue exitoso, False en caso contrario.
        """
        ...

    @abstractmethod
    async def send_alert(self, payload: AlertPayload) -> bool:
        """
        Send a targeted threshold alert.

        Args:
            payload: The alert payload with opportunity details.

        Returns:
            bool: True if dispatch was successful, False otherwise.
        """
        ...
