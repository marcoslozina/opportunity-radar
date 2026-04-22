# ADR-001: Clean Architecture con Ports & Adapters

**Estado:** Aceptado
**Fecha:** 2026-04-22

## Contexto

El sistema integra 6 fuentes de datos externas con APIs distintas y potencialmente inestables. Necesitamos que el dominio sea testeable sin llamadas reales a APIs y que cada fuente sea reemplazable de forma independiente.

## Decisión

Aplicar Clean Architecture con el patrón Ports & Adapters:
- El dominio define interfaces (ports) sin conocer ninguna librería externa
- Cada fuente de datos implementa `TrendDataPort` como adapter independiente
- Los use cases orquestan sin acoplarse a implementaciones concretas

```
API (FastAPI) → Use Cases → Domain Ports ← Infrastructure Adapters
```

## Consecuencias

### Positivas
- Dominio 100% testeable con fakes sin infra real
- Agregar o remover una fuente = un archivo nuevo, sin tocar el dominio
- Fácil migrar pytrends si Google lo rompe

### Negativas / Tradeoffs
- Más archivos y capas para un MVP
- DI manual requiere wiring explícito en `main.py`

## Alternativas descartadas
- **MVC plano**: descartado porque mezclaría lógica de negocio con detalles de infraestructura
- **Script procedural**: descartado porque no permite testing aislado ni extensión limpia
