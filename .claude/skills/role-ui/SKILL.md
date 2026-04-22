# Skill: UI Design

## Principio base

La UI es la traducción visual de la arquitectura de información. Si el UX está mal, la UI no lo puede salvar — pero una UI mala puede arruinar un buen UX. El objetivo es que el usuario no note el diseño porque simplemente funciona.

---

## Design tokens — la base de todo

Nunca valores mágicos en el código. Todo sale de tokens.

```css
/* ✅ Tokens semánticos (no atómicos) */
--color-action-primary: #0066CC;
--color-action-primary-hover: #0052A3;
--color-feedback-error: #D93025;
--color-feedback-success: #1E7E34;
--color-surface-default: #FFFFFF;
--color-surface-subtle: #F5F5F5;

--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 40px;

--radius-sm: 4px;
--radius-md: 8px;
--radius-full: 9999px;

--font-size-sm: 0.875rem;   /* 14px */
--font-size-base: 1rem;     /* 16px */
--font-size-lg: 1.125rem;   /* 18px */
--font-size-xl: 1.25rem;    /* 20px */
--font-size-2xl: 1.5rem;    /* 24px */

--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
--shadow-md: 0 4px 6px rgba(0,0,0,0.07);
--shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
```

---

## Tipografía

### Escala
- Una sola familia de fuente para UI (máximo dos: display + cuerpo)
- Escala modular: los tamaños tienen relación matemática entre sí
- Line-height: 1.5 para cuerpo, 1.2 para títulos

### Legibilidad
```
✅ Ancho de columna: 60–75 caracteres por línea (prose)
✅ Contraste mínimo: 4.5:1 para texto normal, 3:1 para texto grande
✅ No centrar párrafos largos
✅ Jerarquía: máximo 3 niveles visibles por pantalla
```

---

## Color

### Paleta semántica — no decorativa
```
Primary:    acción principal del usuario
Secondary:  acción secundaria / soporte
Success:    confirmación, completado
Warning:    precaución, requiere atención
Error:      fallo, bloqueante
Neutral:    texto, bordes, superficies
```

### Regla del color
- El color no es la única forma de comunicar estado (crítico para a11y)
- Si sacás el color y el significado se pierde → el diseño falla
- Acompañar siempre con ícono + texto

### Dark mode
```css
/* Tokens con modo */
@media (prefers-color-scheme: dark) {
  :root {
    --color-surface-default: #121212;
    --color-surface-subtle: #1E1E1E;
    --color-text-primary: #E8E8E8;
    /* El color de acción puede cambiar levemente */
  }
}
```

---

## Componentes — estados obligatorios

Todo componente interactivo debe tener estos estados diseñados:

```
Default → Hover → Focus → Active → Disabled → Loading → Error
```

```
Input:   Default | Focus | Filled | Error | Disabled
Button:  Default | Hover | Focus | Active | Loading | Disabled
Card:    Default | Hover (si es clickeable) | Selected
```

---

## Espaciado — sistema de 4pt

Todo margen, padding y gap debe ser múltiplo de 4.

```
4px  — separación mínima entre elementos relacionados
8px  — separación dentro de un componente
16px — separación entre componentes del mismo grupo
24px — separación entre secciones
40px — separación entre bloques mayores
```

---

## Responsive — mobile first

```css
/* Breakpoints recomendados */
--bp-sm: 640px;   /* teléfonos grandes */
--bp-md: 768px;   /* tablets */
--bp-lg: 1024px;  /* laptops */
--bp-xl: 1280px;  /* desktops */
```

### Reglas
- Diseñar primero en 375px (iPhone SE), luego escalar
- Touch target mínimo: 44×44px
- No depender de hover para funcionalidad crítica (touch no tiene hover)
- Stacks verticales en mobile, horizontales en desktop

---

## Íconos

```
✅ Sistema unificado (Lucide, Heroicons, Phosphor — uno solo)
✅ Tamaño consistente: 16px, 20px, 24px
✅ Siempre con label visible o aria-label
✅ No mezclar estilos (outline vs filled)
✅ Íconos de estado: siempre acompañados de color + texto
```

---

## Lo que NO hacer

```
❌ Más de 2 fuentes en el mismo producto
❌ Colores que no están en el sistema de tokens
❌ Padding inconsistente (ej: 13px, 17px, 22px)
❌ Animaciones de más de 300ms en interacciones frecuentes
❌ Modales que abren modales
❌ Scroll horizontal en mobile
❌ Texto blanco sobre imagen sin overlay
❌ Placeholder como única instrucción en un campo de formulario
```
