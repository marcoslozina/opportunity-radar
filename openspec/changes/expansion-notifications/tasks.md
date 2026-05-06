# Tasks: Expansion - Email Notifications

## Phase 1: Domain & Config
- [ ] 1.1 Create `src/domain/ports/notification_port.py`.
- [ ] 1.2 Update `src/config.py` to include `resend_api_key` and `notification_email`.

## Phase 2: Infrastructure (Adapter)
- [ ] 2.1 Implement `ResendEmailAdapter` in `src/infrastructure/adapters/resend_email.py`.
- [ ] 2.2 Add basic HTML template generator logic.

## Phase 3: Application Integration
- [ ] 3.1 Update `RunPipelineUseCase` constructor to accept `notification_port`.
- [ ] 3.2 Update `execute` method to trigger notification.
- [ ] 3.3 Update `src/api/routes/pipeline.py` (or dependency injection setup) to provide the adapter.

## Phase 4: UI & Polish
- [ ] 4.1 Improve HTML template styling (vibrant colors, responsive).
- [ ] 4.2 Include niche-specific formatting (PropFlow branding vs ESG branding).

## Phase 5: Verification
- [ ] 5.1 Unit tests for `ResendEmailAdapter` (mocking httpx).
- [ ] 5.2 Manual verification of email delivery (using valid API key).
