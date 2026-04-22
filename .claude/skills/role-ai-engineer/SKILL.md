# Skill: AI Engineer (Claude API — Oficial Anthropic)

> Basado exclusivamente en documentación oficial: https://docs.anthropic.com

## SDK Setup

```python
# Python
import anthropic
client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del env
```

```typescript
// TypeScript
import Anthropic from '@anthropic-ai/sdk'
const client = new Anthropic() // lee ANTHROPIC_API_KEY del env
```

**Nunca hardcodear la API key. Siempre env var.**

---

## Modelos disponibles (Abril 2026)

| Modelo | ID | Cuándo usar |
|--------|----|-------------|
| Claude Opus 4.7 | `claude-opus-4-7` | Razonamiento complejo, agentes, tareas difíciles |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Balance costo/capacidad, uso general |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Tareas simples, latencia baja, costo mínimo |

**Regla:** empezá con Sonnet. Subí a Opus si la calidad no es suficiente. Bajá a Haiku si el costo importa.

---

## Llamada básica

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="Sos un asistente técnico especializado en Python.",
    messages=[
        {"role": "user", "content": "¿Cómo implemento un singleton thread-safe?"}
    ]
)
print(response.content[0].text)
```

---

## Prompt Caching (reducir costos hasta 90%)

Fuente: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

```python
# Cache explícito en contenido largo (docs, contexto grande)
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "Sos un experto en este codebase.",
        },
        {
            "type": "text",
            "text": "<codebase>" + full_codebase_content + "</codebase>",
            "cache_control": {"type": "ephemeral"}  # TTL: 5 min
        }
    ],
    messages=[{"role": "user", "content": user_question}]
)
```

**Mínimo para cachear:** 4096 tokens (Opus/Sonnet), 2048 (Haiku)
**TTL:** 5 minutos (default) o 1 hora (doble costo de write, útil para sesiones largas)
**Precios cache hit:** ~90% más barato que input normal

---

## Tool Use (function calling)

Fuente: https://docs.anthropic.com/en/docs/build-with-claude/tool-use

```python
tools = [
    {
        "name": "search_database",
        "description": "Busca registros en la base de datos por criterios",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Criterio de búsqueda"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    }
]

messages = [{"role": "user", "content": "Encontrá todos los usuarios de Argentina"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    if response.stop_reason == "end_turn":
        print(response.content[0].text)
        break

    # Procesar tool use
    for block in response.content:
        if block.type == "tool_use":
            result = execute_tool(block.name, block.input)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                }]
            })
```

---

## Structured Outputs

```python
from pydantic import BaseModel

class ExtractedData(BaseModel):
    name: str
    email: str
    intent: str
    priority: int

response = client.messages.parse(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{"role": "user", "content": raw_text}],
    output_format=ExtractedData,
)
data = response.parsed_output  # tipo ExtractedData garantizado
```

**Limitaciones:**
- Sin schemas recursivos ni `$ref` externos
- Sin constraints numéricos (`minimum`/`maximum`)
- Incompatible con citations y message prefilling

---

## Streaming

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[{"role": "user", "content": prompt}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

# O para procesar el mensaje final completo:
final = stream.get_final_message()
```

**Usar streaming cuando:** max_tokens > 1000, necesitás UX responsiva, tasks largas.

---

## Batch API (50% de descuento)

```python
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

# Crear batch (hasta 100k requests o 256MB)
batch = client.messages.batches.create(
    requests=[
        Request(
            custom_id=f"item-{i}",
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": text}]
            )
        )
        for i, text in enumerate(texts)
    ]
)

# Polling (completa en < 1h, máximo 24h)
import time
while True:
    batch = client.messages.batches.retrieve(batch.id)
    if batch.processing_status == "ended":
        break
    time.sleep(60)

# Procesar resultados (streaming para no cargar todo en memoria)
for result in client.messages.batches.results(batch.id):
    if result.result.type == "succeeded":
        handle(result.custom_id, result.result.message.content[0].text)
```

**Cuándo usar batch:** procesamiento masivo sin urgencia, clasificación, análisis de datasets.

---

## Multi-turn conversation

```python
messages = []

def chat(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=messages
    )

    assistant_reply = response.content[0].text
    messages.append({"role": "assistant", "content": assistant_reply})
    return assistant_reply
```

**Atención:** el historial crece. Para conversaciones largas: summarizar periódicamente.

---

## Manejo de errores

```python
import anthropic

try:
    response = client.messages.create(...)
except anthropic.RateLimitError:
    # Esperar y reintentar con backoff exponencial
    time.sleep(60)
except anthropic.APIConnectionError:
    # Problema de red, reintentar
    pass
except anthropic.APIStatusError as e:
    print(f"API error {e.status_code}: {e.message}")
```

---

## Estimación de costos antes de ejecutar

```python
token_count = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": prompt}]
)
print(f"Tokens estimados: {token_count.input_tokens}")
```

---

## Decisiones comunes en AI Engineering

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Modelo:** Opus vs Sonnet vs Haiku según complejidad y costo
- **Caching:** automático vs breakpoints explícitos
- **Tool use:** cuántas tools por llamada, granularidad
- **Streaming vs sync:** según latencia requerida
- **Batch vs real-time:** según urgencia del procesamiento
