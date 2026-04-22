# Skill: Java

## Setup de proyecto

**Gradle (preferido):**
```bash
gradle init --type java-application --dsl kotlin
```

**Maven:**
```bash
mvn archetype:generate -DgroupId=com.ejemplo -DartifactId=nombre
```

Java 21+ con records, sealed classes y pattern matching disponibles.

## Convenciones obligatorias

- Java 21+
- Records para value objects y DTOs inmutables
- `Optional<T>` solo en returns, nunca como parámetro
- Excepciones de dominio unchecked (`extends RuntimeException`)
- Paquetes por capa, no por tipo (`domain.user`, no `entities.User`)

## Estructura de capas

```
src/main/java/com/ejemplo/
  domain/
    model/           # entidades, value objects, aggregates
    port/            # interfaces (inbound y outbound)
    exception/       # excepciones de dominio
  application/
    usecase/         # casos de uso (implementan ports inbound)
    service/         # servicios de aplicación
  infrastructure/
    adapter/
      in/            # REST controllers, consumers
      out/           # repos, clients HTTP, etc.
    config/          # beans de Spring, configuración
src/test/java/
  unit/
  integration/
```

## Patrones clave

### Port de salida (outbound)
```java
// domain/port/UserRepository.java
public interface UserRepository {
    Optional<User> findById(UserId id);
    void save(User user);
}
```

### Entidad de dominio
```java
// domain/model/User.java
public class User {
    private final UserId id;
    private String name;
    private Email email;

    private User(UserId id, String name, Email email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public static User create(String name, String email) {
        return new User(UserId.generate(), name, new Email(email));
    }
}
```

### Value Object con record
```java
// domain/model/UserId.java
public record UserId(UUID value) {
    public static UserId generate() {
        return new UserId(UUID.randomUUID());
    }
}
```

### Use Case
```java
// application/usecase/CreateUserUseCase.java
public class CreateUserUseCase {
    private final UserRepository repository;

    public CreateUserUseCase(UserRepository repository) {
        this.repository = repository;
    }

    public UserId execute(String name, String email) {
        var user = User.create(name, email);
        repository.save(user);
        return user.getId();
    }
}
```

### Con Spring Boot (DI automático)
```java
@Service
public class CreateUserUseCase { ... }

@Repository
public class JpaUserRepository implements UserRepository { ... }
```

## Testing

```bash
./gradlew test              # todos
./gradlew test --tests "*CreateUser*"
```

Stack: JUnit 5 + Mockito + AssertJ

Naming: `should_<resultado>_when_<condición>`

```java
@Test
void should_throw_duplicate_error_when_email_already_exists() {
    // given
    when(repository.findByEmail(any())).thenReturn(Optional.of(existingUser));
    // when / then
    assertThatThrownBy(() -> useCase.execute("Juan", "a@b.com"))
        .isInstanceOf(DuplicateEmailException.class);
}
```

- Unit: Mockito para ports, testear use cases aislados
- Integration: `@SpringBootTest` + Testcontainers para repos

## Decisiones de arquitectura comunes en Java

Ante estas elecciones, aplicar el protocolo de decisión del CLAUDE.md:
- **Framework:** Spring Boot vs Quarkus vs Micronaut vs plain Java
- **Build:** Gradle (Kotlin DSL) vs Maven
- **Persistencia:** JPA/Hibernate vs JOOQ vs JDBC puro
- **REST:** Spring MVC vs Spring WebFlux (reactivo)
- **Mensajería:** Kafka vs RabbitMQ vs SQS
- **Tests de integración:** Testcontainers vs H2 en memoria

## Cuándo usar qué

| Caso | Usar |
|------|------|
| Value object inmutable | `record` |
| Entidad con estado mutable | `class` con constructor privado |
| Resultado que puede fallar | `Optional<T>` o excepción de dominio |
| Config tipada | `@ConfigurationProperties` |
| DTO de API | `record` con anotaciones Jackson |
