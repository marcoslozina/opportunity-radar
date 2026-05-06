"""Transactional emails via Resend. Non-fatal — failures never block billing."""
import asyncio
import os

import structlog

logger = structlog.get_logger()


async def send_welcome_email(
    email: str,
    tier: str,
    api_key_raw: str,
    order_id: str,
) -> None:
    """Send a welcome email with the API key after a successful subscription.

    Non-fatal: if RESEND_API_KEY is not configured or the send fails,
    only a warning is logged — billing is never blocked.
    """
    api_key_val = os.getenv("RESEND_API_KEY", "")
    if not api_key_val:
        logger.warning("resend_api_key_not_configured_skipping_email", order_id=order_id)
        return

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bienvenido a Opportunity Radar</title>
  <style>
    body {{ margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e2e8f0; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 40px 24px; }}
    .header {{ text-align: center; margin-bottom: 40px; }}
    .header h1 {{ font-size: 28px; font-weight: 700; color: #a78bfa; margin: 0; letter-spacing: -0.5px; }}
    .header p {{ color: #94a3b8; margin: 8px 0 0; font-size: 14px; }}
    .card {{ background-color: #1e293b; border-radius: 12px; padding: 32px; margin-bottom: 24px; border: 1px solid #334155; }}
    .card h2 {{ margin: 0 0 16px; font-size: 18px; color: #f1f5f9; }}
    .tier-badge {{ display: inline-block; background-color: #7c3aed; color: #fff; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }}
    .api-key-block {{ background-color: #0f172a; border: 1px solid #a78bfa; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
    .api-key-block code {{ font-family: 'Courier New', Courier, monospace; font-size: 14px; color: #a78bfa; word-break: break-all; display: block; margin-bottom: 12px; }}
    .api-key-block .warning {{ font-size: 12px; color: #f59e0b; font-weight: 600; }}
    .quickstart {{ background-color: #0f172a; border-radius: 8px; padding: 16px 20px; margin-top: 16px; overflow-x: auto; }}
    .quickstart pre {{ margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 12px; color: #86efac; white-space: pre-wrap; word-break: break-all; }}
    .links {{ margin-top: 24px; }}
    .btn {{ display: inline-block; background-color: #7c3aed; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-right: 12px; margin-bottom: 12px; }}
    .btn-outline {{ background-color: transparent; border: 1px solid #a78bfa; color: #a78bfa; }}
    .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 32px; }}
    .footer a {{ color: #a78bfa; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Opportunity Radar</h1>
      <p>AI-powered opportunity discovery</p>
    </div>

    <div class="card">
      <span class="tier-badge">{tier}</span>
      <h2>Tu suscripción está activa</h2>
      <p style="color: #94a3b8; margin: 0 0 8px;">Tu API key está lista para usar:</p>

      <div class="api-key-block">
        <code>{api_key_raw}</code>
        <span class="warning">Guardá esta key — no te la volveremos a mostrar</span>
      </div>
    </div>

    <div class="card">
      <h2>Quickstart</h2>
      <p style="color: #94a3b8; margin: 0 0 12px; font-size: 14px;">Hacé tu primera consulta:</p>
      <div class="quickstart">
        <pre>curl -X POST https://api.radar.marcoslozina.com/api/pipeline/run \\
  -H "X-API-Key: {api_key_raw}" \\
  -d '{{"category": "saas", "mode": "content"}}'</pre>
      </div>
      <div class="links">
        <a href="https://api.radar.marcoslozina.com/docs" class="btn">Documentación</a>
        <a href="https://app.marcoslozina.com" class="btn btn-outline">Portal</a>
      </div>
    </div>

    <div class="footer">
      <p>¿Preguntas? Escribinos a <a href="mailto:marcoslozina@gmail.com">marcoslozina@gmail.com</a></p>
      <p style="margin-top: 8px; color: #475569;">© 2025 Opportunity Radar · Order {order_id}</p>
    </div>
  </div>
</body>
</html>"""

    try:
        import resend
        resend.api_key = api_key_val

        params: resend.Emails.SendParams = {
            "from": "Opportunity Radar <noreply@marcoslozina.com>",
            "to": [email],
            "subject": "Bienvenido a Opportunity Radar — tu API key está lista",
            "html": html_body,
        }

        await asyncio.to_thread(resend.Emails.send, params)
        logger.info("welcome_email_sent", order_id=order_id, email=email, tier=tier)

    except Exception as exc:
        logger.warning(
            "welcome_email_failed_nonfatal",
            order_id=order_id,
            email=email,
            error=str(exc),
        )
