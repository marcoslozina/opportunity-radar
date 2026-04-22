# Skill: Responsible Design

## Principio base

El diseño es un acto con consecuencias. Cada decisión — qué mostrar, qué ocultar, qué hacer fácil, qué hacer difícil — afecta el comportamiento del usuario. Diseño responsable significa tomar esas decisiones con conciencia de su impacto.

Referencia central: [Anthropic Model Spec — Avoiding Manipulation](https://www.anthropic.com/research/model-spec) y [Nielsen Norman Group — Dark Patterns](https://www.nngroup.com/articles/dark-patterns/).

---

## Dark patterns — nunca

Los dark patterns explotan sesgos cognitivos para que el usuario haga algo que no haría si entendiera completamente. Son un fallo de diseño y ético.

| Dark pattern | Descripción | Ejemplo concreto |
|---|---|---|
| **Confirmshaming** | Vergüenza por no aceptar | "No, prefiero pagar más" como opción de rechazo |
| **Roach motel** | Fácil entrar, difícil salir | Suscribirse en 1 click, cancelar en 7 pasos |
| **Misdirection** | Dirigir atención lejos de la opción real | Botón "Continuar" lleva a suscripción no pedida |
| **Hidden costs** | Costos que aparecen tarde en el flujo | Precio final ≠ precio mostrado al inicio |
| **Trick questions** | Checkboxes confusos o dobles negaciones | "No quiero no recibir emails de socios" |
| **Urgency falsa** | Timers o stock que no son reales | "¡Solo quedan 2! Oferta termina en 10:00" (siempre) |
| **Bait and switch** | Prometer X, entregar Y | Botón de descarga instala algo distinto |
| **Privacy zuckering** | Default permisivo en privacidad | "Compartir con todos" preseleccionado |
| **Disguised ads** | Publicidad que parece contenido | "Resultado recomendado" que es paid |

---

## Diseño de interfaces con IA — principios

Cuando el producto expone IA al usuario (chatbots, sugerencias, generación de contenido):

### Transparencia obligatoria
```
✅ El usuario sabe cuándo habla con IA vs humano
✅ El usuario sabe cuándo el contenido fue generado por IA
✅ El nivel de confianza/certeza se comunica claramente
✅ Las limitaciones del sistema son visibles y honestas
```

```
❌ Hacer pasar IA por humano sin disclosure
❌ Ocultar que una respuesta fue generada automáticamente
❌ Presentar salidas de IA como hechos sin indicar incertidumbre
❌ Crear ilusión de comprensión emocional profunda
```

### No manipulación
El sistema no debe:
- Crear urgencia artificial para que el usuario tome decisiones apresuradas
- Usar personalización para explotar vulnerabilidades emocionales
- Diseñar para maximizar engagement a costa del bienestar del usuario
- Hacer que sea difícil terminar una sesión o desactivar una función

### Autonomía del usuario
```
✅ El usuario puede rechazar sugerencias de IA sin penalización
✅ El usuario puede desactivar personalización
✅ El usuario puede ver y borrar su historial
✅ El usuario puede salir del flujo en cualquier momento
✅ El usuario controla cuándo y cómo la IA actúa en su nombre
```

---

## Privacidad en UX (Privacy by Design)

La privacidad se diseña desde el inicio, no se agrega al final.

### Consent real
```
❌ Pre-checked "Acepto recibir comunicaciones de socios"
❌ "Aceptar cookies" vs "Configurar" con colores distintos
❌ Scroll y leer 30 páginas para rechazar

✅ Opciones de igual prominencia visual
✅ Rechazar es tan fácil como aceptar
✅ El consentimiento es específico, informado y revocable
```

### Data minimization en formularios
```
❌ Pedir fecha de nacimiento completa cuando solo necesitás saber si es mayor de edad
❌ Pedir teléfono como campo obligatorio para algo que se puede hacer sin él
❌ Dirección completa para envíos que solo necesitan ciudad

✅ Solo pedir lo que se usa
✅ Explicar por qué se pide cada dato sensible
✅ Campos opcionales claramente marcados
```

### Transparencia de datos
- El usuario puede ver qué datos tiene el sistema sobre él
- El usuario puede pedir borrado
- Los cambios de política se comunican con anticipación suficiente

---

## Inclusividad — más allá de accesibilidad técnica

### Lenguaje inclusivo en UI copy
```
❌ "Hola chicos" / "Señor/Señora" / binario forzado
✅ "Hola" / "Estimado/a cliente" / opciones no binarias cuando aplica

❌ Jerga técnica o corporativa que excluye
✅ Vocabulario del usuario, no del sistema

❌ Ejemplos solo con nombres anglosajones, ciudades de EE.UU.
✅ Ejemplos que reflejan diversidad cultural
```

### Formularios de identidad
```
✅ Nombre de preferencia separado del nombre legal (cuando aplica)
✅ Pronombres opcionales
✅ Género como campo abierto o con opción "Prefiero no decir"
✅ Fecha de nacimiento no obligatoria si no es necesaria
```

---

## Bienestar digital — diseñar contra la adicción

No todo engagement es valioso. El diseño responsable no maximiza tiempo en pantalla a cualquier costo.

### Señales de diseño adictivo a evitar
```
❌ Scroll infinito sin punto de parada natural
❌ Autoplay sin consentimiento
❌ Notificaciones diseñadas para crear ansiedad si no se revisan
❌ Variable reward schedules (casino mechanics) en contextos no-gaming
❌ Streaks que crean miedo a perder, no motivación positiva
```

### Alternativas
```
✅ Mostrar "Viste todo el contenido nuevo" en lugar de scroll infinito
✅ Pausas sugeridas después de X tiempo de uso
✅ Notificaciones agrupadas en lugar de constantes
✅ Progreso honesto, no inflatado
```

---

## Checklist de diseño responsable

Antes de entregar cualquier pantalla:

```
□ ¿El usuario entiende qué va a pasar antes de hacer click?
□ ¿Rechazar es tan fácil como aceptar?
□ ¿El estado de error explica qué salió mal y cómo corregirlo?
□ ¿Los defaults favorecen al usuario o al negocio?
□ ¿Si el usuario fuera mi familiar, estaría cómodo mostrándole esto?
□ ¿La IA en este flujo está claramente identificada como IA?
□ ¿El usuario puede deshacer o salir en cualquier punto?
□ ¿Se piden solo los datos que realmente se usan?
□ ¿El lenguaje excluye a algún grupo por cómo está escrito?
```
