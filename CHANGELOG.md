# Changelog

## [Unreleased] - 2026-05-06
### Added
- CircuitBreaker for Redis to avoid timeout cascade.
- MONITORING.md for uptime, Sentry, billing alerts, and log commands.
- IP-based brute force lockout for API key authentication.
- X-Request-ID middleware for observability.
- Resend welcome email on subscription creation.
- Audit log for billing events on subscription creation.
- TrustedHostMiddleware with TRUSTED_HOSTS configuration.

### Fixed
- Read real client IP from CF-Connecting-IP for brute force lockout.
- Replace deprecated utcnow() with timezone-aware now(timezone.utc).
- Replace utcnow() with timezone-aware datetime.now(timezone.utc).

## [Unreleased] - 2026-05-06
### Added
- IP-based brute force lockout for API key auth
- X-Request-ID middleware
- Block SQLite in production environment
- Resend welcome email on subscription_created
- Audit log billing events for subscription_created
- TrustedHostMiddleware with TRUSTED_HOSTS config
- CORS middleware — allow app.marcoslozina.com and radar.marcoslozina.com

### Fixed
- Read real client IP from CF-Connecting-IP for brute force lockout
- Replace deprecated utcnow() with timezone-aware now(timezone.utc)
- Replace utcnow() with timezone-aware datetime.now(timezone.utc)

## [Unreleased] - 2026-05-06
### Added
- Add Resend welcome email on subscription_created
- Audit log billing events for subscription_created
- Add TrustedHostMiddleware with TRUSTED_HOSTS config
- Add CORS middleware — allow app.marcoslozina.com and radar.marcoslozina.com
- Dual-write to shared Supabase portal on subscription create
- Billing layer, tiers, quota, rate limits, domain rename
- Add threshold-based alert system with webhook and email delivery
- Add opportunity DNA archetype fingerprint

### Fixed
- Replace utcnow() with timezone-aware datetime.now(timezone.utc)
- Update LS_SUCCESS_URL to portal central with product=opportunity-radar
- Add src to pytest pythonpath

### Changed
- Make client injectable in provision_to_portal
- Make _key_cache injectable via _make_get_api_key factory
- Move niche keywords from Settings to niche_keywords.json

## [Unreleased] - 2026-05-06
### Added
- Audit log for billing events on subscription creation.
- TrustedHostMiddleware with TRUSTED_HOSTS configuration.
- CORS middleware to allow specified domains.
- Dual-write functionality to Supabase portal on subscription creation.
- Billing layer enhancements including tiers, quota, rate limits, and domain rename.
- Threshold-based alert system with webhook and email delivery.
- Opportunity DNA archetype fingerprint.
- Trend trajectory feature in opportunity briefings.
- Evidence panel to show scoring justification per opportunity.
- API keys authentication layer for external vertical consumers.

### Fixed
- Updated LS_SUCCESS_URL to portal central with product=opportunity-radar.
- Replaced `utcnow()` with timezone-aware `datetime.now(timezone.utc)` for tests.
- Added src to pytest pythonpath.

## [Unreleased] - 2026-05-06
### Added
- add TrustedHostMiddleware with TRUSTED_HOSTS config
- add CORS middleware — allow app.marcoslozina.com and radar.marcoslozina.com
- dual-write to shared Supabase portal on subscription create
- billing layer, tiers, quota, rate limits, domain rename
- add threshold-based alert system with webhook and email delivery
- add opportunity DNA archetype fingerprint
- add trend trajectory to opportunity briefings
- add evidence panel to surface scoring justification per opportunity
- add API keys authentication layer for external vertical consumers
- rebrand to PropFlow and implement real estate niche expansion

### Fixed
- replace utcnow() with timezone-aware datetime.now(timezone.utc)
- update LS_SUCCESS_URL to portal central with product=opportunity-radar
- add src to pytest pythonpath

### Changed
- make client injectable in provision_to_portal
- make _key_cache injectable via _make_get_api_key factory
- move niche keywords from Settings to niche_keywords.json
- rename propflow discovery_mode to real_estate

## [Unreleased] - 2026-05-06
### Added
- Add CORS middleware — allow app.marcoslozina.com and radar.marcoslozina.com
- Dual-write to shared Supabase portal on subscription create
- Billing layer, tiers, quota, rate limits, domain rename
- Add threshold-based alert system with webhook and email delivery
- Add opportunity DNA archetype fingerprint
- Add trend trajectory to opportunity briefings
- Add evidence panel to surface scoring justification per opportunity
- Add API keys authentication layer for external vertical consumers
- Rebrand to PropFlow and implement real estate niche expansion
- Add Streamlit dashboard with category-based niche discovery

### Changed
- Make client injectable in provision_to_portal
- Make _key_cache injectable via _make_get_api_key factory
- Move niche keywords from Settings to niche_keywords.json
- Rename propflow discovery_mode to real_estate

### Fixed
- Replace utcnow() with timezone-aware datetime.now(timezone.utc)
- Update LS_SUCCESS_URL to portal central with product=opportunity-radar
- Add src to pytest pythonpath

## [Unreleased] - 2026-05-05
### Added
- **PropFlow Expansion**: Rebranded to PropFlow and implemented specialized Real Estate niche for Argentina.
- **Sustainability & ESG LATAM**: Implementation of a specialized scoring engine and insights for the ESG domain.
- **Scoring Engine v2**: Generalization of weights and factory for domain-specific scoring (PropFlow vs ESG).
- **Dashboard Awareness**: Dynamic labels (Aplicabilidad vs Implicación) and improved layout for niche-specific results.
- **Technical Saneamiento**: Fixed technical debt in repositories and unit/integration tests after domain refactoring.

## [Unreleased] - 2026-04-22

## [Unreleased] - 2026-04-22
### Added
- Product discovery domain for monetization opportunities
- Opportunity radar scoring engine

## [Unreleased] - 2026-04-22
### Added
- Implement opportunity radar scoring engine

## [Unreleased] - 2026-04-22
### Added
- Initial commit

## [Unreleased] - 2026-04-21
### Added
- Add requirements engineering and DDD skills
- Add SOLID, app-performance, concurrency skills and /gc command
- Add UX/UI and responsible design skills
- Add pre-commit hooks, conventional commits, CODEOWNERS, and issue templates
- Add format check, link check, and real build gates
- Add 5 AI-powered GitHub Actions workflows
- Add orchestrator skill and parallel agent commands (parallel-phases, parallel-apply)
- Add observability, environments, performance skills — complete enterprise template
- Add privacy skill, harden settings (deny git push), secret detection rules in CLAUDE.md and code-review
- Add README, expand .gitignore to cover all supported languages
- Add AGENTS.md, lang-go, infra-docker, new-adr command, dependabot config
- Complete template — backend, security, testing skills + ADR template, Makefile, CI workflow, custom commands

### Fixed
- Add models: read permission for GitHub Models access
- Install anthropic before python scripts and fix gitleaks false positive
- Make docker build conditional on Dockerfile existence

## [Unreleased] - 2026-04-20
### Added
- Add SOLID, app-performance, concurrency skills and /gc command
- Add UX/UI and responsible design skills
- Add pre-commit hooks, conventional commits, CODEOWNERS, and issue templates
- Add format check, link check, and real build gates
- Add 5 AI-powered GitHub Actions workflows
- Add orchestrator skill and parallel agent commands (parallel-phases, parallel-apply)
- Add observability, environments, performance skills — complete enterprise template
- Add privacy skill, harden settings (deny git push), secret detection rules in CLAUDE.md and code-review
- Add AGENTS.md, lang-go, infra-docker, new-adr command, dependabot config
- Complete template — backend, security, testing skills + ADR template, Makefile, CI workflow, custom commands
- Add full team skills — architect, frontend, code-review, cicd, aws, ai-engineer, rag, ml, typescript
- Make template language-agnostic with python + java skill subsets

### Fixed
- Add models: read permission for GitHub Models access
- Install anthropic before python scripts and fix gitleaks false positive
- Make docker build conditional on Dockerfile existence

All notable changes to this project will be documented here.

## [Unreleased] - 2026-04-20
### Added
- Add UX/UI and responsible design skills.
- Add pre-commit hooks, conventional commits, CODEOWNERS, and issue templates.
- Add format check, link check, and real build gates.
- Add 5 AI-powered GitHub Actions workflows.
- Add orchestrator skill and parallel agent commands (parallel-phases, parallel-apply).
- Add observability, environments, performance skills — complete enterprise template.
- Add privacy skill, harden settings (deny git push), secret detection rules in CLAUDE.md and code-review.
- Add AGENTS.md, lang-go, infra-docker, new-adr command, dependabot config.
- Complete template — backend, security, testing skills + ADR template, Makefile, CI workflow, custom commands.
- Add full team skills — architect, frontend, code-review, cicd, aws, ai-engineer, rag, ml, typescript.
- Make template language-agnostic with python + java skill subsets.
- Initial live coding setup with SDD + Python architecture skills.

### Fixed
- Add models: read permission for GitHub Models access.
- Install anthropic before python scripts and fix gitleaks false positive.
- Make docker build conditional on Dockerfile existence. 

### Security
- Add privacy skill, harden settings (deny git push), secret detection rules in CLAUDE.md and code-review.
