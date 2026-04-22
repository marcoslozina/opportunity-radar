# Skill: TypeScript

## Aplica a
Frontend (React) y Backend (Node.js / Bun). Las convenciones son las mismas.

## Configuración base

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "target": "ES2022",
    "moduleResolution": "bundler"
  }
}
```

Sin `any`. Sin `// @ts-ignore`. Sin `as` a ciegas.

---

## Convenciones de tipos

```typescript
// ✅ Tipos explícitos en funciones públicas
function findUser(id: UserId): Promise<User | null>

// ✅ Discriminated unions para estados
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E }

// ✅ Branded types para IDs
type UserId = string & { readonly _brand: 'UserId' }
function UserId(raw: string): UserId { return raw as UserId }

// ✅ Readonly para objetos de dominio
type User = Readonly<{
  id: UserId
  name: string
  email: string
}>

// ❌ Nunca
const user: any = getUser()
function process(data: object): any
```

---

## Backend Node.js (Clean Architecture)

```
src/
  domain/
    entities/        # tipos e interfaces de negocio
    ports/           # interfaces de repositorios y servicios
  application/
    use-cases/       # lógica de aplicación
  infrastructure/
    adapters/        # implementaciones concretas
    db/              # Prisma / Drizzle
    http/            # clientes externos
  api/
    routes/          # Fastify / Express routers
    schemas/         # Zod para validación de entrada
tests/
```

### Port (interfaz)
```typescript
// domain/ports/user-repository.ts
export interface UserRepository {
  findById(id: UserId): Promise<User | null>
  save(user: User): Promise<void>
}
```

### Use Case
```typescript
// application/use-cases/create-user.ts
export class CreateUserUseCase {
  constructor(private readonly repo: UserRepository) {}

  async execute(input: CreateUserInput): Promise<UserId> {
    const user = User.create(input.name, input.email)
    await this.repo.save(user)
    return user.id
  }
}
```

### Validación con Zod
```typescript
import { z } from 'zod'

const CreateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
})

type CreateUserInput = z.infer<typeof CreateUserSchema>
```

---

## Frontend React

### Componente tipado
```tsx
interface ButtonProps {
  label: string
  variant: 'primary' | 'secondary' | 'danger'
  isLoading?: boolean
  onClick: () => void
}

export const Button = ({ label, variant, isLoading = false, onClick }: ButtonProps) => (
  <button
    className={variants[variant]}
    disabled={isLoading}
    onClick={onClick}
  >
    {isLoading ? <Spinner /> : label}
  </button>
)
```

### Custom hook tipado
```typescript
function useAsync<T>(fn: () => Promise<T>): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' })

  const run = useCallback(async () => {
    setState({ status: 'loading' })
    try {
      const value = await fn()
      setState({ status: 'success', value })
    } catch (error) {
      setState({ status: 'error', error: error as Error })
    }
  }, [fn])

  return { ...state, run }
}
```

---

## Testing

```typescript
// Vitest (frontend) / Jest (backend)
// Naming: describe qué hace, not cómo
describe('CreateUserUseCase', () => {
  it('returns user id when input is valid', async () => {
    const repo = new FakeUserRepository()
    const useCase = new CreateUserUseCase(repo)
    const id = await useCase.execute({ name: 'Ana', email: 'ana@test.com' })
    expect(repo.findById(id)).resolves.not.toBeNull()
  })

  it('throws DuplicateEmailError when email already exists', async () => {
    const repo = new FakeUserRepository({ existingEmail: 'ana@test.com' })
    const useCase = new CreateUserUseCase(repo)
    await expect(
      useCase.execute({ name: 'Ana', email: 'ana@test.com' })
    ).rejects.toThrow(DuplicateEmailError)
  })
})
```

---

## Decisiones de arquitectura comunes en TypeScript

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Runtime:** Node.js vs Bun vs Deno
- **Framework HTTP:** Fastify vs Express vs Hono
- **ORM/Query:** Prisma vs Drizzle vs Kysely vs raw SQL
- **Validación:** Zod vs Valibot vs TypeBox
- **Bundler:** Vite vs esbuild vs tsup
- **Test:** Vitest vs Jest
