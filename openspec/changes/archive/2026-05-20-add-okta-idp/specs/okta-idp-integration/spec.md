## ADDED Requirements

### Requirement: OktaClient fetches and maps real user identity
`OktaClient` SHALL fetch user identity from Okta's Users API (`GET /api/v1/users/{login}`) and map the response to a `UserProfile`. A second call to `GET /api/v1/users/{id}/manager` SHALL be made to resolve the manager name.

Field mapping SHALL follow these rules:
- `name` ← `profile.firstName + " " + profile.lastName`
- `email` ← `profile.email`
- `team` ← `profile.department`, empty string or absent → `"unknown"`
- `role` ← `profile.title`, empty string or absent → `"unknown"`
- `manager` ← `profile.displayName` from manager response, absent or error → `"unknown"`
- `employment_status` ← `status`: `ACTIVE` → `"active"`, `DEPROVISIONED` → `"terminated"`, all others → `"on_leave"`
- `start_date` ← `activated` (ISO 8601 date), absent → `date(2000, 1, 1)`
- `tenure_days` ← `(today - start_date).days`
- `work_location` ← `profile.city`, absent → `"remote"`
- `timezone` ← `profile.timezone`, absent → `"UTC"`
- `access_level` ← `profile.userType`, absent → `"unknown"`
- `on_call` ← `False` (not available in Okta)
- `out_of_office` ← `False` (not available in Okta)
- `termination_date` ← `None` (not reliably available in Okta)

#### Scenario: Active user with full profile
- **WHEN** Okta returns a user with `status: ACTIVE`, populated `profile.department`, `profile.title`, `profile.city`, and a resolvable manager
- **THEN** `OktaClient.get_user()` returns a `UserProfile` with all fields populated from Okta data, `employment_status` set to `"active"`, `on_call` and `out_of_office` set to `False`

#### Scenario: Deprovisioned user
- **WHEN** Okta returns a user with `status: DEPROVISIONED`
- **THEN** `employment_status` is `"terminated"`

#### Scenario: Suspended or staged user
- **WHEN** Okta returns a user with `status` other than `ACTIVE` or `DEPROVISIONED` (e.g. `SUSPENDED`, `STAGED`, `LOCKED_OUT`)
- **THEN** `employment_status` is `"on_leave"`

#### Scenario: Sparse profile fields
- **WHEN** Okta returns a user with `profile.department`, `profile.title`, `profile.city`, `profile.timezone`, `profile.userType` absent or empty string
- **THEN** the corresponding `UserProfile` fields are set to `"unknown"` or `"remote"` (for location) or `"UTC"` (for timezone) as specified in the field mapping

#### Scenario: Manager fetch fails or manager has no display name
- **WHEN** the manager API call returns a non-2xx status or the manager profile lacks `displayName`
- **THEN** `manager` is set to `"unknown"` and `get_user()` still returns a valid `UserProfile`

#### Scenario: activated field absent
- **WHEN** the Okta user record does not include an `activated` timestamp
- **THEN** `start_date` defaults to `date(2000, 1, 1)` and `tenure_days` is calculated from that date

---

### Requirement: OktaClient returns None on user-not-found or HTTP error
`OktaClient.get_user()` SHALL return `None` when Okta responds with 404 (user not found) or when any HTTP or network error occurs. It SHALL NOT raise an exception to the caller.

#### Scenario: User not found in Okta
- **WHEN** Okta responds with `404` for the user lookup
- **THEN** `get_user()` returns `None`

#### Scenario: Network or HTTP error
- **WHEN** a network timeout, connection error, or non-404 HTTP error occurs during the user or manager fetch
- **THEN** `get_user()` returns `None`

---

### Requirement: OktaClient uses synchronous httpx
`OktaClient` SHALL use `httpx.Client` (synchronous) for all HTTP calls. It SHALL authenticate using the SSWS token format: `Authorization: SSWS {token}`. It SHALL NOT cache responses or share state between calls.

#### Scenario: SSWS token is sent on every request
- **WHEN** `get_user()` makes any HTTP call to the Okta API
- **THEN** the request includes an `Authorization: SSWS {token}` header

#### Scenario: Each call is independent
- **WHEN** `get_user()` is called twice for different users
- **THEN** no state from the first call affects the second call

---

### Requirement: AnalystAgent.lookup_user delegates to OktaClient when configured
`AnalystAgent` SHALL accept an optional `okta_client: OktaClient | None = None` parameter in its constructor. When `okta_client` is set and `OktaClient.get_user()` returns a `UserProfile`, `lookup_user` SHALL return that profile. When `okta_client` is `None` or `get_user()` returns `None`, `lookup_user` SHALL return the existing stub profile.

#### Scenario: Okta configured and user found
- **WHEN** `AnalystAgent` is constructed with a non-None `okta_client` and `okta_client.get_user(username)` returns a `UserProfile`
- **THEN** `lookup_user(username)` returns the Okta-sourced `UserProfile`

#### Scenario: Okta configured but user not found
- **WHEN** `AnalystAgent` is constructed with a non-None `okta_client` and `okta_client.get_user(username)` returns `None`
- **THEN** `lookup_user(username)` returns the stub `UserProfile`

#### Scenario: Okta not configured
- **WHEN** `AnalystAgent` is constructed without an `okta_client` (default `None`)
- **THEN** `lookup_user(username)` returns the stub `UserProfile` unchanged

---

### Requirement: OktaConfig holds Okta credentials
`src/config.py` SHALL define an `OktaConfig` model with `org_url: str` (from `OKTA_ORG_URL`) and `api_token: str` (from `OKTA_API_TOKEN`). The application config SHALL include an optional `okta: OktaConfig | None` field that is `None` when either environment variable is absent.

#### Scenario: Both env vars present
- **WHEN** `OKTA_ORG_URL` and `OKTA_API_TOKEN` are both set
- **THEN** `config.okta` is a populated `OktaConfig` instance

#### Scenario: One or both env vars absent
- **WHEN** `OKTA_ORG_URL` or `OKTA_API_TOKEN` is absent or empty
- **THEN** `config.okta` is `None`

---

### Requirement: Orchestrator constructs and injects OktaClient
The `Orchestrator` SHALL construct an `OktaClient` from config when `config.okta` is not `None` and pass it to `AnalystAgent` as `okta_client`. When `config.okta` is `None`, the `Orchestrator` SHALL pass `okta_client=None`.

#### Scenario: Okta configured at startup
- **WHEN** the application starts with `OKTA_ORG_URL` and `OKTA_API_TOKEN` set
- **THEN** `Orchestrator` constructs an `OktaClient` and injects it into `AnalystAgent`

#### Scenario: Okta not configured at startup
- **WHEN** the application starts without Okta environment variables
- **THEN** `Orchestrator` passes `okta_client=None` to `AnalystAgent` and the existing stub behavior is preserved
