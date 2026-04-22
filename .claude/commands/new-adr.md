Creá un nuevo ADR siguiendo estos pasos:

1. Contá los archivos existentes en `docs/adr/` (excluyendo ADR-000-template.md) para determinar el próximo número.

2. Pedile al usuario el título de la decisión si no lo proporcionó.

3. Creá el archivo `docs/adr/ADR-{NNN}-{titulo-en-kebab-case}.md` copiando la estructura de `docs/adr/ADR-000-template.md` con:
   - Número correlativo (001, 002, etc.)
   - Estado: "Propuesto"
   - Fecha: hoy
   - Título proporcionado por el usuario

4. Dejá los campos de contenido vacíos para que el usuario los complete, excepto si hay contexto suficiente en la conversación — en ese caso completá Contexto y Opciones evaluadas con lo que ya se discutió.

5. Confirmá: "ADR-{NNN} creado en docs/adr/. ¿Lo completamos ahora o continuamos con la implementación?"
