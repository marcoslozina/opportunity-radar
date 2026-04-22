# Skill: RAG (Retrieval-Augmented Generation)

> Basado en documentación oficial Anthropic: https://docs.anthropic.com/en/docs/build-with-claude/rag

## Qué es RAG y por qué existe

Los LLMs tienen dos limitaciones: conocimiento cortado en fecha de entrenamiento
y sin acceso a información privada/actualizada. RAG resuelve ambos:

```
Sin RAG: "¿Estado del ticket PROJ-4521?" → adivina o no sabe

Con RAG:
  1. Buscar ticket en Jira
  2. Pasar contenido + pregunta al modelo
  → Responde con información real
```

---

## Pipeline RAG — 3 componentes

### 1. Ingesta y chunking

```python
def chunk_document(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks
```

**Tamaños recomendados por tipo de contenido:**
| Contenido | Chunk size | Overlap |
|-----------|-----------|---------|
| Documentación técnica | 200-400 tokens | 50 tokens |
| Código fuente | Por función/clase | Mínimo |
| Conversaciones | Por turno | Sin overlap |
| Artículos | Por párrafo | 1-2 oraciones |

**Regla:** chunks chicos pierden contexto, chunks grandes desperdician ventana. Testear con tu data.

---

### 2. Embeddings y búsqueda semántica

```python
import voyageai
import numpy as np

class VectorDB:
    def __init__(self):
        self.client = voyageai.Client()
        self.embeddings: list = []
        self.metadata: list = []
        self.query_cache: dict = {}

    def index(self, chunks: list[dict]) -> None:
        texts = [f"{c['heading']}\n{c['text']}" for c in chunks]
        # Batch de 128 para eficiencia
        all_embeddings = []
        for i in range(0, len(texts), 128):
            batch = self.client.embed(texts[i:i+128], model="voyage-3").embeddings
            all_embeddings.extend(batch)
        self.embeddings = all_embeddings
        self.metadata = chunks

    def search(self, query: str, k: int = 5, threshold: float = 0.75) -> list[dict]:
        # Cache de queries repetidas
        if query not in self.query_cache:
            self.query_cache[query] = self.client.embed([query], model="voyage-3").embeddings[0]

        q_emb = self.query_cache[query]
        similarities = np.dot(self.embeddings, q_emb)
        top_indices = np.argsort(similarities)[::-1]

        return [
            {"text": self.metadata[i]["text"], "score": similarities[i]}
            for i in top_indices
            if similarities[i] >= threshold
        ][:k]
```

**Embedding models recomendados:**
- General: `voyage-3` (Voyage AI, recomendado por Anthropic)
- Código: `voyage-code-3`
- Multilingüe: `voyage-multilingual-2`

---

### 3. Generación con contexto

```python
import anthropic

client = anthropic.Anthropic()
db = VectorDB()

def answer(question: str) -> str:
    # Recuperar contexto relevante
    results = db.search(question, k=3)
    context = "\n\n---\n\n".join([r["text"] for r in results])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""Respondés preguntas SOLO con el contexto provisto.
Si la información no está en el contexto, decí explícitamente que no tenés esa información.
No inventes respuestas ni uses conocimiento externo.""",
        messages=[{
            "role": "user",
            "content": f"<context>\n{context}\n</context>\n\nPregunta: {question}"
        }]
    )
    return response.content[0].text
```

---

## Técnicas avanzadas (mejoran precisión)

### Summary Indexing
Indexar resúmenes + chunks completos por separado.
Buscar por resumen, devolver chunk completo.
**Mejora MRR hasta +17.6% según benchmarks oficiales Anthropic.**

### Contextual Embeddings
Usar Claude para generar contexto situacional antes de embeddear cada chunk:

```python
def add_context_to_chunk(chunk: str, doc_summary: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # barato para este paso
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""Documento: {doc_summary}
Chunk: {chunk}
Generá una oración que contextualice este chunk dentro del documento."""
        }]
    )
    return f"{response.content[0].text}\n\n{chunk}"
```

### Re-ranking con Claude
Recuperar top-10, reordenar por relevancia real antes de pasar al modelo:

```python
def rerank(query: str, candidates: list[str], top_k: int = 3) -> list[str]:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""Query: {query}
Candidatos: {json.dumps(list(enumerate(candidates)))}
Devolvé los índices de los {top_k} más relevantes en orden, como JSON array."""
        }]
    )
    indices = json.loads(response.content[0].text)
    return [candidates[i] for i in indices]
```

---

## Métricas de evaluación

```python
# Precision: de lo que recuperé, ¿cuánto era correcto?
# Recall: de lo correcto, ¿cuánto recuperé?
# MRR: ¿qué tan arriba aparece el primer resultado correcto?

def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, item in enumerate(retrieved, 1):
        if item in relevant:
            return 1 / i
    return 0.0

def precision_recall(retrieved: list[str], relevant: set[str]) -> tuple[float, float]:
    hits = len(set(retrieved) & relevant)
    return hits / len(retrieved), hits / len(relevant)
```

**Baseline → optimizado (benchmarks oficiales Anthropic):**
- Precision: 0.43 → 0.44 (+2.3%)
- Recall: 0.66 → 0.69 (+4.5%)
- MRR: 0.74 → 0.87 (+17.6%)
- Accuracy end-to-end: 71% → 81% (+10%)

---

## Cuándo RAG no es la solución

RAG funciona bien para búsqueda de información.
Funciona mal cuando:
- La pregunta requiere razonamiento sobre información que no existe en los docs
- La base de conocimiento tiene información contradictoria (problema de gobernanza)
- La pregunta requiere datos en tiempo real (usar tool use + API en su lugar)

---

## Integración con Prompt Caching

Para RAG con contexto repetido (misma base de docs):

```python
system = [
    {"type": "text", "text": "Respondés basándote solo en el contexto provisto."},
    {
        "type": "text",
        "text": f"<knowledge_base>{static_docs}</knowledge_base>",
        "cache_control": {"type": "ephemeral"}  # cachea los docs estáticos
    }
]
```

**Ahorra hasta 90% en tokens de entrada para docs que se repiten entre requests.**

---

## Decisiones comunes en RAG

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Vector DB:** Pinecone vs Weaviate vs Chroma vs pgvector
- **Embedding model:** Voyage AI vs OpenAI Ada vs Cohere
- **Chunk strategy:** fijo vs semántico vs por estructura del doc
- **Reranking:** cross-encoder vs Claude vs BM25 híbrido
- **Gobernanza de docs:** versionado, actualización, deduplicación
