# Skill: Go

## Setup de proyecto

```bash
go mod init github.com/{usuario}/{proyecto}
go get {dependencia}
```

Go 1.22+. Sin frameworks innecesarios — la stdlib alcanza para mucho.

---

## Convenciones obligatorias

- Errores siempre manejados: sin `_` para ignorar un `error`
- Sin `panic` en código de producción — solo en `init()` o condiciones imposibles
- Interfaces pequeñas: 1-3 métodos (io.Reader, io.Writer como modelo)
- Packages nombrados por lo que proveen, no por lo que contienen (`user` no `models`)
- `context.Context` como primer parámetro en toda función que hace I/O

---

## Estructura de proyecto

```
cmd/
  api/
    main.go            # entry point — solo wiring
internal/
  domain/
    user.go            # entidad + lógica de negocio
    repository.go      # interface (port)
  application/
    create_user.go     # use case
  infrastructure/
    postgres/
      user_repo.go     # implementación del port
    http/
      user_handler.go  # handler HTTP
pkg/                   # código exportable y reutilizable
config/
  config.go
```

`internal/` hace que los paquetes no sean importables desde fuera del módulo. Úsalo para todo excepto lo que explícitamente querés que sea una librería pública.

---

## Patrones clave

### Interface (Port)
```go
// internal/domain/repository.go
type UserRepository interface {
    FindByID(ctx context.Context, id UserID) (*User, error)
    Save(ctx context.Context, user *User) error
}
```

### Entidad de dominio
```go
// internal/domain/user.go
type UserID string

type User struct {
    ID    UserID
    Name  string
    Email string
}

func NewUser(name, email string) (*User, error) {
    if name == "" {
        return nil, errors.New("name is required")
    }
    return &User{
        ID:    UserID(uuid.New().String()),
        Name:  name,
        Email: email,
    }, nil
}
```

### Use Case
```go
// internal/application/create_user.go
type CreateUserUseCase struct {
    repo domain.UserRepository
}

func NewCreateUserUseCase(repo domain.UserRepository) *CreateUserUseCase {
    return &CreateUserUseCase{repo: repo}
}

func (uc *CreateUserUseCase) Execute(ctx context.Context, name, email string) (domain.UserID, error) {
    user, err := domain.NewUser(name, email)
    if err != nil {
        return "", fmt.Errorf("creating user: %w", err)
    }
    if err := uc.repo.Save(ctx, user); err != nil {
        return "", fmt.Errorf("saving user: %w", err)
    }
    return user.ID, nil
}
```

### Manejo de errores — convenciones
```go
// ✅ Wrappear con contexto
if err := repo.Save(ctx, user); err != nil {
    return fmt.Errorf("CreateUser: saving to db: %w", err)
}

// ✅ Errores de dominio centinela
var ErrUserNotFound = errors.New("user not found")
var ErrDuplicateEmail = errors.New("email already exists")

// ✅ Chequear tipo de error
if errors.Is(err, ErrUserNotFound) {
    // manejar 404
}
```

---

## HTTP con stdlib (sin framework)

```go
// internal/infrastructure/http/user_handler.go
func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    var input struct {
        Name  string `json:"name"`
        Email string `json:"email"`
    }
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        http.Error(w, "invalid input", http.StatusUnprocessableEntity)
        return
    }

    id, err := h.useCase.Execute(r.Context(), input.Name, input.Email)
    if err != nil {
        if errors.Is(err, domain.ErrDuplicateEmail) {
            http.Error(w, "email already exists", http.StatusConflict)
            return
        }
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(map[string]string{"id": string(id)})
}
```

Para APIs más complejas: **Chi** (router ligero, compatible con stdlib) o **Gin**.

---

## Testing

```bash
go test ./...                     # todos
go test ./internal/application/   # por paquete
go test -run TestCreateUser -v    # por nombre
go test -race ./...               # detectar race conditions
```

```go
// Fake repository
type fakeUserRepo struct {
    users  map[domain.UserID]*domain.User
    emails map[string]bool
}

func (r *fakeUserRepo) Save(ctx context.Context, user *domain.User) error {
    if r.emails[user.Email] {
        return domain.ErrDuplicateEmail
    }
    r.users[user.ID] = user
    r.emails[user.Email] = true
    return nil
}

func TestCreateUser_WhenEmailExists_ReturnsError(t *testing.T) {
    repo := &fakeUserRepo{
        emails: map[string]bool{"ana@test.com": true},
    }
    uc := application.NewCreateUserUseCase(repo)

    _, err := uc.Execute(context.Background(), "Ana", "ana@test.com")

    if !errors.Is(err, domain.ErrDuplicateEmail) {
        t.Errorf("expected ErrDuplicateEmail, got %v", err)
    }
}
```

---

## Concurrencia — reglas

```go
// ✅ Compartir datos con channels, no con memoria compartida
// ✅ Si usás mutex, documentar qué protege
// ✅ Siempre pasar context para cancelación
// ✅ go test -race para detectar races en CI

// ❌ Nunca
go func() {
    sharedMap[key] = value  // race condition sin mutex
}()
```

---

## Decisiones comunes en Go

Aplicar protocolo de decisión del CLAUDE.md ante:
- **HTTP framework:** stdlib + Chi vs Gin vs Echo vs Fiber
- **ORM:** GORM vs sqlc vs pgx raw
- **DI:** manual (preferido) vs Wire
- **Config:** env vars directas vs Viper vs godotenv
- **Testing:** testify vs stdlib testing
