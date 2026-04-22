# Skill: Machine Learning Engineering

## Rol
Integrar ML en sistemas productivos. No solo entrenar modelos — deployarlos, monitorizarlos y mantenerlos.

---

## Tipos de problema → enfoque

| Problema | Enfoque recomendado | Cuándo escalar |
|----------|--------------------|--------------:|
| Clasificación de texto | Fine-tuning LLM o embeddings + classifier | > 10k ejemplos |
| Extracción de entidades | LLM con structured outputs | Siempre |
| Recomendación | Collaborative filtering + embeddings | > 100k usuarios |
| Anomaly detection | Isolation Forest / Autoencoder | Depende del dominio |
| Forecasting | ARIMA / Prophet / LSTM | Según estacionalidad |
| Similarity search | Embeddings + vector DB | > 1k documentos |

**Regla:** antes de entrenar un modelo, probá si un LLM + buen prompt resuelve el problema. Es más rápido y mantenible.

---

## Pipeline ML (producción)

```
Raw Data → Preprocessing → Feature Engineering → Training → Evaluation → Serving
    ↓             ↓                ↓                ↓            ↓           ↓
  S3/DB       Validación       Feature Store     MLflow      Métricas    FastAPI/Lambda
```

### Estructura de proyecto

```
ml/
  data/
    raw/               # datos originales, inmutables
    processed/         # datos transformados
    features/          # features computadas
  notebooks/           # exploración (no producción)
  src/
    data/              # loaders, preprocessors
    features/          # feature engineering
    models/            # training, evaluation
    serving/           # inference API
  tests/
  configs/             # hyperparámetros, rutas
```

---

## Validación de datos (antes de entrenar)

```python
import pandera as pa
from pandera import Column, DataFrameSchema

schema = DataFrameSchema({
    "user_id": Column(str, nullable=False),
    "label": Column(int, pa.Check.isin([0, 1])),
    "text": Column(str, pa.Check(lambda x: x.str.len() > 0)),
    "created_at": Column("datetime64[ns]"),
})

def validate_training_data(df):
    try:
        schema.validate(df)
    except pa.errors.SchemaError as e:
        raise ValueError(f"Datos inválidos para entrenamiento: {e}")
```

---

## Embeddings para ML con Claude API

```python
import voyageai

voyage = voyageai.Client()

def embed_texts(texts: list[str], batch_size: int = 128) -> list[list[float]]:
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = voyage.embed(texts[i:i+batch_size], model="voyage-3").embeddings
        embeddings.extend(batch)
    return embeddings

# Para clasificación downstream
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

X = embed_texts(texts)
clf = LogisticRegression(max_iter=1000)
scores = cross_val_score(clf, X, labels, cv=5, scoring='f1_weighted')
print(f"F1: {scores.mean():.3f} ± {scores.std():.3f}")
```

---

## Evaluación — métricas por tipo de problema

```python
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    mean_absolute_error,
    ndcg_score
)

# Clasificación
print(classification_report(y_true, y_pred))
print(f"AUC-ROC: {roc_auc_score(y_true, y_prob):.3f}")

# Regresión
print(f"MAE: {mean_absolute_error(y_true, y_pred):.3f}")

# Ranking / Recomendación
print(f"NDCG@10: {ndcg_score(y_true, y_scores, k=10):.3f}")
```

**No reportes solo accuracy.** Para datos desbalanceados, F1 o AUC-ROC.

---

## Serving de modelos

### FastAPI + modelo en memoria

```python
from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI()
model = joblib.load("model.pkl")
embedder = VoyageEmbedder()

class PredictRequest(BaseModel):
    text: str

class PredictResponse(BaseModel):
    label: int
    confidence: float

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    embedding = embedder.embed([req.text])[0]
    proba = model.predict_proba([embedding])[0]
    return PredictResponse(
        label=int(proba.argmax()),
        confidence=float(proba.max())
    )
```

### Cuándo usar qué serving

| Escala | Latencia | Solución |
|--------|---------|----------|
| < 100 req/s | < 200ms | FastAPI en ECS/Lambda |
| > 100 req/s | < 100ms | FastAPI + uvicorn workers |
| Batch async | No crítica | Lambda + SQS + S3 |
| Modelos grandes | Variable | SageMaker Endpoints |

---

## Monitoreo en producción

```python
# Log de predicciones para detectar drift
import logging

logger = logging.getLogger("ml.inference")

def predict_with_logging(text: str, model_version: str) -> dict:
    result = model.predict(text)
    logger.info({
        "input_length": len(text),
        "prediction": result["label"],
        "confidence": result["confidence"],
        "model_version": model_version,
        "latency_ms": result["latency"]
    })
    return result
```

**Métricas a monitorear:**
- Distribution drift de features (PSI, KL divergence)
- Degradación de métricas en producción vs holdout
- Latencia de inferencia (p50, p95, p99)
- Tasa de predicciones de baja confianza

---

## Decisiones comunes en ML Engineering

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Build vs Buy:** entrenar modelo propio vs LLM + prompting vs API de terceros
- **Feature store:** Feast vs Tecton vs custom en Redis
- **Experiment tracking:** MLflow vs W&B vs Comet
- **Serving:** FastAPI custom vs SageMaker vs BentoML vs Ray Serve
- **Vector DB:** pgvector vs Pinecone vs Weaviate vs Chroma
- **Reentrenamiento:** scheduled vs triggered por drift vs online learning
