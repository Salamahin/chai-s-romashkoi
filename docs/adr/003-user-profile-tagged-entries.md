# User Profile with Tagged Free-Text Entries

Date: 2026-04-10
Status: Proposed

## Context

The application currently authenticates users via Google OAuth and shows a placeholder "hello" message. There is no way for a user to store any personal data. The next requirement is a **user profile** consisting of an ordered list of free-text entries, each associated with a single tag chosen from a growing vocabulary of tags the user has used before.

Key product decisions already made:

- Each entry has exactly one tag and one free-text body.
- Tag names are normalised (lowercase, whitespace-trimmed) in the domain before storage.
- Entries are ordered by creation time (ULID insertion order). No drag-to-reorder. New entries are appended to the bottom.
- Save is a **patch** operation: only changed, added, and removed entries are written per save. This keeps individual DynamoDB writes small regardless of how many total entries a profile contains, and avoids any single-transaction item limit concern.
- There is no hard cap on the number of entries per profile.
- `GET /profile/tags` requires a valid session, consistent with all other profile endpoints.

Infrastructure constraints remain unchanged: near-zero AWS cost, Lambda Function URL (no API Gateway), S3 + CloudFront frontend.

## Architecture

### Components

#### Backend

**`src/profile/domain.py`** — pure domain types and business logic.
Defines `ProfileEntry` and `Profile` as frozen dataclasses. Contains functions for computing a patch diff between two profiles and for normalising tag names.

**`src/profile/repository.py`** — DynamoDB adapter (side-effectful).
Responsible for reading and writing profile entries. Speaks only in domain types at its public boundary. Executes `Query`, `PutItem`, and `DeleteItem` against the profiles table.

**`src/profile/tags.py`** — pure tag-vocabulary function.
Derives the set of distinct normalised tag names from a `Profile`. No I/O.

**`src/profile/handler.py`** — Lambda entry point (boundary).
Reads environment variables, reads wall clock, verifies session, delegates to repository and domain functions, returns HTTP responses.

#### Frontend

**`ProfilePage.svelte`** — top-level profile route component.
Owns load/save lifecycle. Fetches the profile on mount, passes data into `ProfileEditor`, collects the edited state, and calls `profile_service.saveProfile`.

**`ProfileEditor.svelte`** — stateful editor shell.
Receives the current `ProfileSnapshot` as a prop. Renders the ordered list of `ProfileEntryRow` components and an "Add entry" affordance. Emits the updated snapshot upward on change.

**`ProfileEntryRow.svelte`** — single editable row.
Renders one `ProfileEntry` with a `TagCombobox` and a plain text input for the body. Emits change and delete events.

**`TagCombobox.svelte`** — tag input with autocomplete.
Accepts the current tag value and the list of known tags as props. Normalises input (lowercase + trim) before emitting a change event.

**`profile_service.ts`** — API client for profile endpoints.
Pure functions over `fetch`. No module-level state.

### Interfaces

#### Backend (typed pseudocode)

```
# --- domain types ---

ProfileEntry:
  entry_id: str          # ULID, assigned at creation
  tag: str               # normalised (lowercase, trimmed)
  text: str
  updated_at: str        # ISO-8601 UTC string

Profile:
  user_sub: str
  entries: tuple[ProfileEntry, ...]   # ordered by entry_id (ULID ≈ creation time)

ProfilePatch:
  upserted: tuple[ProfileEntry, ...]  # entries to PutItem
  deleted_ids: tuple[str, ...]        # entry_ids to DeleteItem

# --- domain functions ---

def normalise_tag(raw: str) -> str
# Returns lowercase, whitespace-stripped version of raw.

def normalise_entry(entry: ProfileEntry) -> ProfileEntry
# Returns a new ProfileEntry with tag replaced by normalise_tag(entry.tag).

def compute_patch(old: Profile, new: Profile) -> ProfilePatch
# Pure diff: entries present/changed in new → upserted; entry_ids in old but
# absent from new → deleted_ids.

def apply_patch(base: Profile, patch: ProfilePatch) -> Profile
# Returns a new Profile with patch applied, entries re-sorted by entry_id.

# --- repository interface ---

class ProfileRepository:
  def get(self, user_sub: str) -> Profile
  def apply(self, user_sub: str, patch: ProfilePatch) -> None

# --- tags function ---

def known_tags(profile: Profile) -> frozenset[str]
# Returns the set of distinct normalised tag names across all entries.

# --- handler config ---

ProfileConfig:
  session_secret: str
  profiles_table_name: str

# --- handler (Lambda entry point) ---

def handler(event: dict[str, object], context: object) -> dict[str, object]
# Routes on (method, rawPath):
#   GET  /profile        → load profile for authenticated user
#   PUT  /profile        → receive ProfileSnapshot, compute patch against stored
#                          profile, persist, return updated ProfileSnapshot
#   GET  /profile/tags   → return list of known tag strings for authenticated user
```

#### Frontend (TypeScript)

```typescript
// --- value types ---

interface ProfileEntry {
  entry_id: string        // ULID
  tag: string
  text: string
  updated_at: string      // ISO-8601
}

interface ProfileSnapshot {
  entries: ProfileEntry[]
}

// --- profile_service.ts ---

function getProfile(sessionToken: string): Promise<ProfileSnapshot>
// GET /profile, Authorization: Bearer <sessionToken>

function saveProfile(
  sessionToken: string,
  snapshot: ProfileSnapshot,
): Promise<ProfileSnapshot>
// PUT /profile with body ProfileSnapshot.
// Backend computes patch against its stored state; returns updated snapshot.

function getKnownTags(sessionToken: string): Promise<string[]>
// GET /profile/tags, Authorization: Bearer <sessionToken>

// --- ProfilePage.svelte props ---
// none (reads session from auth_service)

// --- ProfileEditor.svelte props ---
interface ProfileEditorProps {
  snapshot: ProfileSnapshot
  onchange: (updated: ProfileSnapshot) => void
}

// --- ProfileEntryRow.svelte props ---
interface ProfileEntryRowProps {
  entry: ProfileEntry
  knownTags: string[]
  onchange: (updated: ProfileEntry) => void
  ondelete: () => void
}

// --- TagCombobox.svelte props ---
interface TagComboboxProps {
  value: string
  options: string[]
  onchange: (normalised: string) => void
}
```

### Data flow

```
Browser                          Lambda handler              DynamoDB
  |                                   |                          |
  | GET /profile                      |                          |
  |---------------------------------->|                          |
  |                                   | verify_session_token     |
  |                                   | ProfileRepository.get()  |
  |                                   |------------------------->|
  |                                   |<-- items (Query result) -|
  |                                   | build Profile            |
  |<-- 200 ProfileSnapshot -----------|                          |
  |                                   |                          |
  | [user edits entries]              |                          |
  |                                   |                          |
  | PUT /profile { entries: [...] }   |                          |
  |---------------------------------->|                          |
  |                                   | verify_session_token     |
  |                                   | ProfileRepository.get()  |
  |                                   |------------------------->|
  |                                   |<-- stored Profile -------|
  |                                   | normalise_entry (each)   |
  |                                   | compute_patch(old, new)  |
  |                                   | repository.apply(patch)  |
  |                                   |  PutItem × upserted      |
  |                                   |  DeleteItem × deleted    |
  |                                   |------------------------->|
  |                                   |<-- OK ------------------|
  |                                   | apply_patch(old, patch)  |
  |<-- 200 ProfileSnapshot -----------|                          |
  |                                   |                          |
  | GET /profile/tags                 |                          |
  |---------------------------------->|                          |
  |                                   | verify_session_token     |
  |                                   | ProfileRepository.get()  |
  |                                   |------------------------->|
  |                                   |<-- stored Profile -------|
  |                                   | known_tags(profile)      |
  |<-- 200 { tags: [...] } -----------|                          |
```

**Frontend internal flow:**

`ProfilePage` mounts → calls `getProfile` and `getKnownTags` in parallel → passes `ProfileSnapshot` and `knownTags` to `ProfileEditor` → user edits rows via `ProfileEntryRow` / `TagCombobox` → `ProfileEditor` emits updated snapshot → `ProfilePage` calls `saveProfile` on explicit save → renders returned snapshot.

New entries are created client-side with a ULID assigned in the browser at the moment the row is added. This means entry ordering is determined by the ULID embedded in the `entry_id`, which encodes creation time with sufficient resolution to be monotonically ordered in practice.

### Boundary map

| Location | Side effect | Enters domain as |
|---|---|---|
| `profile/handler.py` | Read env vars | `ProfileConfig` |
| `profile/handler.py` | Read wall clock | `now_utc: int` passed to `verify_session_token` |
| `profile/handler.py` | Parse HTTP event body | `ProfileSnapshot` dict, validated before domain call |
| `profile/repository.py` | DynamoDB `Query` | `Profile` (pure value) |
| `profile/repository.py` | DynamoDB `PutItem` / `DeleteItem` | — |
| `profile/handler.py` | Write HTTP response | — |
| `ProfilePage.svelte` | `fetch` calls via `profile_service` | `ProfileSnapshot`, `string[]` |
| `TagCombobox.svelte` | DOM input event | normalised `string` emitted via `onchange` |
| `ProfilePage.svelte` | ULID generation for new entries | `entry_id: string` on new `ProfileEntry` |

All diff, patch, and tag-normalisation logic is pure (no I/O, no mutation of external state).

## Implementation plan

### `dynamodb_architect`

Design a single-table schema for profile entries with the following requirements:

- **Access patterns to support:**
  1. Fetch all entries for a given user (used on load, on save, and on tags fetch).
  2. Upsert a single entry for a given user.
  3. Delete a single entry for a given user.
- **Suggested key design:**
  - `PK = USER#<sub>` (user's Google `sub` claim)
  - `SK = ENTRY#<ulid>` (ULID provides lexicographic creation-time ordering)
- **Attributes per item:** `tag` (String), `text` (String), `updated_at` (String, ISO-8601).
- **Billing mode:** PAY_PER_REQUEST (on-demand). No provisioned capacity — consistent with near-zero cost constraint.
- No GSIs are needed; all access patterns are served by the primary key.
- Confirm whether a TTL attribute is wanted (not currently required; entries are permanent until explicitly deleted by the user).

### `infrastructure_engineer`

Introduce the following Terraform changes inside `deploy/`:

1. **New DynamoDB table resource** (in a new module or directly in `deploy/modules/lambda/` if collocated with Lambda):
   - Table name: `<project_name>-profiles` (or parameterised via variable).
   - Billing mode: `PAY_PER_REQUEST`.
   - Hash key: `PK` (String). Range key: `SK` (String).
   - No GSIs.

2. **IAM policy** — attach an inline policy to `aws_iam_role.this` (the existing Lambda role) granting:
   - `dynamodb:Query` on the table ARN.
   - `dynamodb:PutItem` on the table ARN.
   - `dynamodb:DeleteItem` on the table ARN.

3. **Lambda environment variable** — add `PROFILES_TABLE_NAME` to the `environment.variables` block in `aws_lambda_function.this`. Its value should be the table name output from the DynamoDB resource.

4. **CORS** — add `"PUT"` to the `allow_methods` list on `aws_lambda_function_url.this`. (`GET` and `POST` are already present from the auth ADR.)

5. **Output** — expose the table name as a Terraform output if useful for debugging.

No new AWS services with fixed hourly cost are introduced. DynamoDB on-demand billing charges only for actual read/write capacity units consumed, which is consistent with the near-zero cost constraint.

### `python_developer`

Create the following modules under `backend/src/profile/`:

**`domain.py`** — pure, no imports outside stdlib.
- Define frozen dataclasses `ProfileEntry` and `Profile` as described in the interfaces section.
- Define `ProfilePatch` as a frozen dataclass.
- Implement `normalise_tag(raw: str) -> str`.
- Implement `normalise_entry(entry: ProfileEntry) -> ProfileEntry`.
- Implement `compute_patch(old: Profile, new: Profile) -> ProfilePatch`. Keyed by `entry_id`. An entry is "upserted" if it is new or if its `tag`, `text`, or `updated_at` differs from the stored version.
- Implement `apply_patch(base: Profile, patch: ProfilePatch) -> Profile`. Result entries are sorted by `entry_id` string (ULID lexicographic order equals creation-time order).

**`tags.py`** — pure.
- Implement `known_tags(profile: Profile) -> frozenset[str]`. Returns the set of distinct `entry.tag` values.

**`repository.py`** — side-effectful DynamoDB adapter.
- Accept a `boto3` DynamoDB table resource injected at construction time (enables testing with a fake).
- `get(user_sub: str) -> Profile` — issues a `Query` with `KeyConditionExpression PK = USER#<sub>`, maps each item to a `ProfileEntry`, returns a `Profile` sorted by SK.
- `apply(user_sub: str, patch: ProfilePatch) -> None` — calls `table.put_item` for each upserted entry and `table.delete_item` for each deleted entry. These are individual calls (not a transaction), consistent with the patch-semantics decision. If atomicity within a single save is later required, this can be upgraded to a `transact_write_items` call.

**`handler.py`** — Lambda entry point and routing.
- Read `SESSION_SECRET` and `PROFILES_TABLE_NAME` from environment at module level (warm reuse).
- Construct `ProfileRepository` with a module-level boto3 table resource (warm reuse).
- Route dispatch on `(method, rawPath)`:
  - `GET /profile` → call `repository.get(sub)`, serialise to dict, return 200.
  - `PUT /profile` → deserialise body to list of entry dicts, build incoming `Profile`, call `repository.get(sub)` for old state, call `normalise_entry` on each incoming entry, call `compute_patch(old, normalised_new)`, call `repository.apply(sub, patch)`, call `apply_patch(old, patch)`, return 200 with updated snapshot.
  - `GET /profile/tags` → call `repository.get(sub)`, call `known_tags(profile)`, return 200 with sorted list.
  - Any other path → return 404.
- All routes require a valid session (call `require_session` from `src/app/handler.py` or extract it to a shared location accessible from both handlers).
- CORS headers must be included on all responses, including error responses, consistent with the existing `CORS_HEADERS` pattern.

The existing `src/app/handler.py` dispatcher should be updated to forward `/profile` and `/profile/tags` requests to the profile handler. The `require_session` helper should be moved to a shared module (e.g., `src/session_guard.py`) so both the app handler and the profile handler can import it without circular dependency.

### `frontend_developer`

Create the following files under `frontend/src/`:

**`lib/profile_service.ts`**
- Implement `getProfile`, `saveProfile`, `getKnownTags` as described in the interfaces section.
- All functions accept `sessionToken: string` as first argument. No module-level auth state.
- `saveProfile` sends `PUT /profile` with `Content-Type: application/json` and `Authorization: Bearer <token>`. Body is `ProfileSnapshot`.
- On non-2xx response, throw an `Error` with the HTTP status code in the message.

**`lib/ProfilePage.svelte`**
- On mount: call `getSessionToken()` from `auth_service`, then call `getProfile` and `getKnownTags` in parallel (`Promise.all`).
- Manages `snapshot: ProfileSnapshot` and `knownTags: string[]` as local state.
- Renders a loading state while fetching, an error message on failure, and `ProfileEditor` when data is ready.
- Provides a Save button. On click, calls `saveProfile` with the current snapshot; on success, replaces local snapshot with the returned one; on 401, calls `clearSession()` and redirects to login.

**`lib/ProfileEditor.svelte`**
- Accepts `snapshot: ProfileSnapshot`, `knownTags: string[]`, and `onchange: (updated: ProfileSnapshot) => void` as props.
- Renders one `ProfileEntryRow` per entry in `snapshot.entries` order (do not sort client-side; server order is canonical).
- Renders an "Add entry" button. On click, generates a new ULID for `entry_id`, creates a `ProfileEntry` with empty `tag` and `text` and current ISO timestamp as `updated_at`, appends it to the list, emits `onchange`.
- On row change or delete, rebuilds the entries array (immutably) and emits `onchange`.

**`lib/ProfileEntryRow.svelte`**
- Accepts `entry: ProfileEntry`, `knownTags: string[]`, `onchange`, `ondelete` as props.
- Renders `TagCombobox` bound to `entry.tag` and a `<textarea>` or `<input>` for `entry.text`.
- On any field change, emits `onchange` with a new `ProfileEntry` object (do not mutate the prop), with `updated_at` set to the current ISO timestamp.

**`lib/TagCombobox.svelte`**
- Accepts `value: string`, `options: string[]`, `onchange: (normalised: string) => void` as props.
- Renders a text input with a datalist (or custom dropdown) showing `options`.
- Before emitting `onchange`, normalises the input: `value.toLowerCase().trim()`.

**`App.svelte`** — update routing to render `ProfilePage` as the main authenticated view (replacing or wrapping the current `AppPage` placeholder).

For the dev environment, `profile_service.ts` does not need a dev alias — it makes real HTTP calls to the local FastAPI server, which will serve the profile endpoints once the backend is implemented.

## Open questions

1. Should `repository.apply` use individual `PutItem`/`DeleteItem` calls or a `transact_write_items` batch? Individual calls are simpler and avoid the 100-action transaction limit, but they are not atomic. If a Lambda invocation is interrupted mid-patch, the stored profile could be partially updated. For a personal-scale app this is likely acceptable; the implementer should decide whether to add a retry/recovery mechanism.

2. ULID generation on the frontend: which library should be used (`ulid` npm package, `ulidx`, or a hand-rolled implementation)? The choice affects bundle size. Alternatively, the server could assign ULIDs on `PUT /profile` for new entries, with the client using a temporary client-side ID to track new rows before the first save.

3. Should `ProfilePage` auto-save on every change (debounced) or only on explicit Save button press? Explicit save is specified in the design; confirm whether a debounced auto-save is wanted as an enhancement.

4. Should deleted entries be soft-deleted (kept in DynamoDB with a `deleted: true` flag and a TTL) or hard-deleted immediately? The current design specifies hard deletion via `DeleteItem`. Soft-deletion would allow undo; confirm whether that is in scope.

5. The `require_session` helper is currently defined inside `src/app/handler.py`. Moving it to a shared module (`src/session_guard.py`) is necessary to avoid importing the app handler from the profile handler. Confirm that this refactor is in scope for the implementing developer, or whether the profile handler should duplicate the guard logic temporarily.
