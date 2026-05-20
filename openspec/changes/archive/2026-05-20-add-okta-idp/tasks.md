## 1. Dependencies and Config

- [x] 1.1 Add `httpx` to project dependencies (`pyproject.toml` / `requirements`)
- [x] 1.2 Add `OktaConfig` to `src/config.py` with `org_url` and `api_token` from env vars `OKTA_ORG_URL` / `OKTA_API_TOKEN`
- [x] 1.3 Add optional `okta: OktaConfig | None` field to the main app config; set to `None` when either env var is absent

## 2. OktaClient

- [x] 2.1 Create `src/integrations/__init__.py`
- [x] 2.2 Create `src/integrations/okta.py` with `OktaClient` class accepting `org_url` and `api_token`
- [x] 2.3 Implement `get_user(login: str) -> UserProfile | None` — calls `GET /api/v1/users/{login}` with SSWS auth header
- [x] 2.4 Implement manager resolution — calls `GET /api/v1/users/{id}/manager`; returns `"unknown"` on missing `displayName` or any error
- [x] 2.5 Implement field mapping from Okta response to `UserProfile` per spec (employment_status, start_date, tenure_days, all optional fields with fallbacks)
- [x] 2.6 Return `None` on HTTP 404 or any network/HTTP error (no exception propagation)

## 3. AnalystAgent Wiring

- [x] 3.1 Add `okta_client: OktaClient | None = None` parameter to `AnalystAgent.__init__`
- [x] 3.2 Update `lookup_user` to delegate to `self._okta_client.get_user(username)` when set; fall back to stub when `okta_client` is `None` or `get_user` returns `None`
- [x] 3.3 Remove the `# TODO: wire up to Okta IDP` comment from `lookup_user`

## 4. Orchestrator and App Wiring

- [x] 4.1 Update `Orchestrator.__init__` to accept `okta_client: OktaClient | None = None` and forward it to `AnalystAgent`
- [x] 4.2 Update `create_app()` lifespan in `src/api/app.py` to construct `OktaClient(org_url=..., api_token=...)` when `config.okta` is set, otherwise pass `None`

## 5. Tests

- [x] 5.1 Unit test `OktaClient.get_user` happy path — mock `httpx.Client`, assert correct `UserProfile` field mapping
- [x] 5.2 Unit test `OktaClient.get_user` with sparse profile — absent department, title, city, timezone, userType map to correct fallbacks
- [x] 5.3 Unit test `OktaClient.get_user` with non-ACTIVE statuses — `DEPROVISIONED` → `"terminated"`, `SUSPENDED` → `"on_leave"`
- [x] 5.4 Unit test `OktaClient.get_user` returns `None` on 404 and on network error
- [x] 5.5 Unit test `OktaClient.get_user` manager fallback — manager fetch fails → `manager` field is `"unknown"`
- [x] 5.6 Unit test `AnalystAgent.lookup_user` — with `okta_client` returning a profile, with `okta_client` returning `None`, and with no `okta_client`
- [x] 5.7 Update `OktaConfig` config tests — verify env var presence/absence produces correct `config.okta` value
