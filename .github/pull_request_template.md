## ¿Qué hace este PR?

<!-- Una o dos oraciones. Qué cambia y por qué. -->

## Tipo de cambio

- [ ] `feat` — nueva funcionalidad
- [ ] `fix` — corrección de bug
- [ ] `arch` — decisión de arquitectura aplicada
- [ ] `refactor` — sin cambio de comportamiento
- [ ] `test` — tests
- [ ] `docs` — documentación / ADRs

## ADRs relacionados

<!-- Si este PR aplica una decisión de arquitectura, linkear el ADR -->
- docs/adr/ADR-XXX-...

## Checklist

### Código
- [ ] Los tests pasan (`make test`)
- [ ] Lint pasa (`make lint`)
- [ ] Sin `any` / tipos incorrectos
- [ ] Sin lógica de negocio fuera del dominio

### Arquitectura
- [ ] Las capas respetan la regla de dependencia
- [ ] Decisiones no obvias documentadas como ADR

### Seguridad
- [ ] Sin secrets en código o logs
- [ ] Input validado en el borde
- [ ] Autorización verificada donde corresponde

### Tests
- [ ] Tests nuevos para el comportamiento agregado
- [ ] Edge cases cubiertos
- [ ] Tests de integración si cambia infra

## Cómo probar

<!-- Pasos concretos para verificar que funciona -->
1.
2.
