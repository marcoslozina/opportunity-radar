# Skill: Accessibility (a11y)

## Principio base

Accesibilidad no es una feature opcional ni un checklist final. Es una propiedad del diseño que, si se ignora, excluye usuarios — y en muchos contextos es un requisito legal (ADA, WCAG 2.2, EN 301 549).

**Nivel mínimo aceptable: WCAG 2.2 nivel AA.**

---

## Los 4 principios (POUR)

| Principio | Qué significa |
|-----------|--------------|
| **Perceptible** | La información llega a los sentidos disponibles del usuario |
| **Operable** | El usuario puede navegar e interactuar con lo que tiene |
| **Comprensible** | El contenido y la UI son predecibles y entendibles |
| **Robusto** | Funciona con tecnología asistiva actual y futura |

---

## Estructura semántica — lo más importante

```html
<!-- ❌ Div soup: sin semántica -->
<div class="header">
  <div class="nav">
    <div onclick="go()">Inicio</div>
  </div>
</div>

<!-- ✅ HTML semántico -->
<header>
  <nav aria-label="Navegación principal">
    <a href="/">Inicio</a>
  </nav>
</header>
```

### Orden de encabezados
```html
<!-- ✅ Jerarquía correcta — no saltar niveles -->
<h1>Título de página</h1>
  <h2>Sección</h2>
    <h3>Subsección</h3>
```

### Landmarks obligatorios
```html
<header>     <!-- encabezado de sitio -->
<nav>        <!-- navegación (aria-label si hay varias) -->
<main>       <!-- contenido principal — solo uno por página -->
<aside>      <!-- contenido complementario -->
<footer>     <!-- pie de sitio -->
```

---

## Contraste — WCAG 2.2

| Tipo de texto | Ratio mínimo AA | Ratio AAA |
|---------------|----------------|-----------|
| Texto normal (<18px / <14px bold) | 4.5:1 | 7:1 |
| Texto grande (≥18px / ≥14px bold) | 3:1 | 4.5:1 |
| Componentes UI e íconos | 3:1 | — |

Herramientas: [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/), Figma Able plugin.

---

## Foco y teclado

```css
/* ✅ Nunca eliminar el outline sin reemplazarlo */
:focus-visible {
  outline: 2px solid var(--color-action-primary);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* ❌ Esto es un error de a11y */
:focus { outline: none; }
```

### Orden de tabulación
- El orden de `Tab` debe seguir el orden visual
- Los modales deben atrapar el foco (focus trap) mientras están abiertos
- Al cerrar un modal, el foco vuelve al elemento que lo abrió

### Teclas obligatorias
| Componente | Teclas requeridas |
|-----------|------------------|
| Botón | Enter, Space |
| Link | Enter |
| Checkbox | Space |
| Select/Listbox | ↑↓ para navegar, Enter para seleccionar |
| Modal | Esc para cerrar |
| Accordion | Enter/Space para expandir |

---

## ARIA — usar solo cuando el HTML nativo no alcanza

```html
<!-- ✅ Primero, HTML nativo -->
<button>Guardar</button>

<!-- ✅ ARIA cuando el elemento no es semánticamente correcto -->
<div role="button" tabindex="0" aria-pressed="false">
  Guardar
</div>

<!-- Atributos más usados -->
aria-label="descripción cuando no hay texto visible"
aria-labelledby="id-del-elemento-que-da-nombre"
aria-describedby="id-del-elemento-con-instrucciones"
aria-expanded="true|false"     <!-- acordeones, dropdowns -->
aria-haspopup="true"           <!-- botones que abren menús -->
aria-live="polite|assertive"   <!-- regiones con contenido dinámico -->
aria-hidden="true"             <!-- ocultar de lectores de pantalla -->
aria-disabled="true"           <!-- deshabilitado (no usar solo disabled) -->
aria-invalid="true"            <!-- campo con error -->
aria-required="true"           <!-- campo obligatorio -->
```

---

## Formularios

```html
<!-- ✅ Label explícito siempre -->
<label for="email">Email</label>
<input id="email" type="email" aria-describedby="email-hint email-error">
<p id="email-hint">Usá tu email corporativo.</p>
<p id="email-error" role="alert" aria-live="assertive">
  <!-- Aparece solo cuando hay error -->
  El email no tiene un formato válido.
</p>

<!-- ❌ Placeholder como único label -->
<input type="email" placeholder="Email">
```

### Mensajes de error
- Aparecer en tiempo real (no solo al submit)
- Describir QUÉ está mal y CÓMO corregirlo
- `role="alert"` o `aria-live="assertive"` para que los lectores los anuncien

---

## Imágenes y medios

```html
<!-- ✅ Imagen informativa -->
<img src="grafico.png" alt="Ventas subieron 40% en Q3 2025 respecto a Q2">

<!-- ✅ Imagen decorativa -->
<img src="decoracion.png" alt="">

<!-- ✅ Íconos sin texto visible -->
<button aria-label="Cerrar modal">
  <svg aria-hidden="true">...</svg>
</button>
```

### Videos
- Subtítulos para contenido hablado
- Audiodescripción si hay información solo visual
- No autoplay con sonido

---

## Reducción de movimiento

```css
/* Respetar preferencia del sistema */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Testing de accesibilidad

### Automatizado (detecta ~30% de problemas)
- **axe DevTools** (extensión Chrome) — corre en cada PR
- **Lighthouse** — accessibility score como gate de CI

### Manual obligatorio
```
1. Navegar toda la pantalla solo con Tab
2. Activar lector de pantalla: VoiceOver (Mac), NVDA (Win), TalkBack (Android)
3. Zoom al 200% — ¿el layout sigue funcionando?
4. Desactivar CSS — ¿el orden del contenido tiene sentido?
5. Probar con solo teclado + solo mouse + solo toque
```

### En CI (GitHub Actions)
```yaml
- name: Accessibility audit
  run: npx axe-cli http://localhost:3000 --exit
```
