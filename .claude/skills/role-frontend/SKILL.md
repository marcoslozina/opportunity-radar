# Skill: Frontend

## Stack base
React 18+ con TypeScript estricto. Sin `any`. Sin `// @ts-ignore`.

---

## Estructura de proyecto

```
src/
  components/
    ui/              # átomos: Button, Input, Badge (sin lógica de negocio)
    features/        # organismos por feature: UserCard, CheckoutForm
    layouts/         # shells de página: DashboardLayout, AuthLayout
  pages/             # entry points de rutas (mínima lógica)
  hooks/             # custom hooks reutilizables
  stores/            # estado global (Zustand / Redux Toolkit)
  services/          # llamadas a API (sin lógica de UI)
  types/             # tipos e interfaces compartidos
  utils/             # funciones puras sin side effects
```

---

## Principios de componentes

### Container / Presentational
```tsx
// ✅ Presentational: recibe datos, no los busca
const UserCard = ({ name, email, onEdit }: UserCardProps) => (
  <div>
    <h2>{name}</h2>
    <p>{email}</p>
    <button onClick={onEdit}>Editar</button>
  </div>
)

// ✅ Container: busca datos, delega render
const UserCardContainer = ({ userId }: { userId: string }) => {
  const { user, isLoading } = useUser(userId)
  if (isLoading) return <Skeleton />
  return <UserCard {...user} onEdit={() => navigate(`/users/${userId}/edit`)} />
}
```

### Regla de responsabilidad única
- Un componente hace una cosa
- Si el nombre tiene "And" → dividir (`UserFormAndValidation` → dos componentes)
- Props máximas: ~5-7. Más → extraer objeto o dividir componente

---

## Estado — cuándo usar qué

| Tipo de estado | Solución |
|---------------|---------|
| Local UI (toggle, form) | `useState` |
| Estado derivado | `useMemo` / computar en render |
| Side effects | `useEffect` (con dependencias explícitas) |
| Estado global de UI | Zustand |
| Estado del servidor | TanStack Query / SWR |
| Formularios complejos | React Hook Form |

**Regla:** el estado vive en el nivel más bajo posible que lo necesite.

---

## TypeScript en componentes

```tsx
// ✅ Props tipadas explícitamente
interface ButtonProps {
  label: string
  variant: 'primary' | 'secondary' | 'danger'
  isLoading?: boolean
  onClick: () => void
}

// ✅ Generics en hooks reutilizables
function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void]

// ✅ Discriminated unions para estados
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }
```

---

## Performance

```tsx
// Memorizar componentes costosos
const ExpensiveList = memo(({ items }: { items: Item[] }) => ...)

// Memorizar cálculos costosos
const sorted = useMemo(() => items.sort(compareFn), [items])

// Estabilizar callbacks
const handleClick = useCallback(() => doSomething(id), [id])

// Code splitting por ruta
const Dashboard = lazy(() => import('./pages/Dashboard'))
```

**Cuándo NO memorizar:** componentes simples, renders baratos. La memorización tiene costo.

---

## Accesibilidad (a11y) — no negociable

- Botones con `aria-label` si no tienen texto visible
- Imágenes con `alt` descriptivo (o `alt=""` si es decorativa)
- Formularios con `<label>` asociado a cada `<input>`
- Foco visible (no `outline: none` sin reemplazo)
- Color no como único diferenciador de información

---

## Decisiones de arquitectura comunes en Frontend

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Estado global:** Zustand vs Redux Toolkit vs Context API
- **Data fetching:** TanStack Query vs SWR vs fetch manual
- **Routing:** React Router vs TanStack Router
- **Estilos:** Tailwind vs CSS Modules vs styled-components
- **Forms:** React Hook Form vs Formik vs controlled manual
- **Testing:** React Testing Library vs Playwright vs Cypress
