# Personal Log (Chat-Style Journal)

Date: 2026-04-11
Status: Proposed

## Context

After login the application currently lands on a minimal home page with a pending-relations badge and a Profile button. The next feature is a **personal log**: a private, chat-style journal where the authenticated user writes timestamped text entries visible only to themselves. The interface is modelled on a messaging client (Telegram/WhatsApp): messages in chronological order oldest-at-top, newest-at-bottom, with an input bar fixed at the bottom.

Key product decisions:

- The log **is** the home page. On login the user lands directly in the chat interface.
- The pending-relations badge currently on `HomePage` must move; it will live on a navigation element that also reaches `ProfilePage` (details deferred to open question 1).
- Entries are private to the author; no sharing or cross-user visibility.
- Users can **edit** and **hard-delete** their own entries. Hard-delete is chosen for simplicity — no tombstone or soft-delete.
- **Optimistic UI**: a sent message appears immediately in a "pending" state; a delivered tick appears once the server confirms the write.
- **Lazy loading by time window**: the initial load covers the current week. Scrolling to the top of the chat loads the previous week's batch.
- Second-level timestamp precision is sufficient; a UUID4 suffix on the SK handles same-second collisions.
- Infrastructure constraint: near-zero AWS cost, Lambda Function URL, no API Gateway.

---

## Architecture

### Components

#### Backend

**`src/log/domain.py`** — pure domain types and entry-manipulation logic.
Defines `LogEntry` and `LogEntryPatch`. Provides pure factory and patch functions. No I/O.

**`src/log/repository.py`** — DynamoDB adapter for log entries (boundary, side-effectful).
Reads and writes items. Converts between raw DynamoDB attribute maps and `LogEntry` domain objects. Exposes a time-window query, a single-item fetch, a put, an update, and a delete.

**`src/log/handler.py`** — Lambda entry point for all `/log` routes (boundary).
Reads environment, verifies session token, delegates to repository and domain functions, returns HTTP responses. Handles four routes: `GET /log`, `POST /log`, `PUT /log/{entry_id}`, `DELETE /log/{entry_id}`.

**`src/app/dispatcher.py`** — updated to route `/log` and `/log/{entry_id}` paths to `log.handler`.

**`src/app/handler.py`** — `GET /` now returns only `pending_relations_count`. The home page no longer calls this endpoint for page content; the badge count is fetched separately during navigation setup (see open question 1).

#### Frontend

**`src/lib/ChatPage.svelte`** — replaces `HomePage.svelte` as the post-login landing page.
On mount, loads the current week's log entries via `log_service.listEntries`. Renders a scrollable message list (oldest-at-top) and a fixed bottom input bar. Provides navigation to `ProfilePage` via a header element that also shows the pending-relations badge. Manages local optimistic state for in-flight messages.

**`src/lib/ChatMessageList.svelte`** — renders the ordered sequence of `ChatMessage` view-model objects.
Handles scroll position; when the user scrolls to the top it emits an `onloadprevious` event to trigger loading of the prior week's batch.

**`src/lib/ChatMessageRow.svelte`** — renders a single message bubble.
Shows: text (or an inline edit field when in edit mode), ISO timestamp formatted to seconds, edit/delete hover actions, and a delivered-tick indicator (`pending` → spinner/clock glyph, `saved` → tick glyph).

**`src/lib/log_service.ts`** — API client for all `/log` endpoints.
Encapsulates `fetch` calls, maps responses to typed objects, reads base URL from `VITE_LOG_API_URL` (falls back to `http://localhost:8000` in dev).

---

### Interfaces

#### Domain types (Python pseudocode)

```python
@dataclass(frozen=True)
class LogEntry:
    entry_id: str          # UUID4
    owner_email: str
    raw_text: str
    logged_at: str         # ISO-8601 UTC, second precision, e.g. "2026-04-11T14:05:00Z"
    updated_at: str        # ISO-8601 UTC; equals logged_at on creation

@dataclass(frozen=True)
class LogEntryPatch:
    raw_text: str
    updated_at: str        # wall-clock time at which the edit was applied

def make_entry(
    entry_id: str,
    owner_email: str,
    raw_text: str,
    now: str,              # ISO-8601 UTC injected at boundary
) -> LogEntry: ...

def apply_patch(entry: LogEntry, patch: LogEntryPatch) -> LogEntry: ...
```

#### Repository interface (Python pseudocode)

```python
class LogRepository:
    def put(self, entry: LogEntry) -> None: ...

    def update_text(self, owner_email: str, entry_id: str, patch: LogEntryPatch) -> LogEntry: ...
    # Raises ValueError if entry does not exist or belongs to a different owner.

    def delete(self, owner_email: str, entry_id: str) -> None: ...
    # Raises ValueError if entry does not exist or belongs to a different owner.

    def list_window(
        self,
        owner_email: str,
        week_start: str,   # ISO-8601 UTC, inclusive lower bound
        week_end: str,     # ISO-8601 UTC, exclusive upper bound
    ) -> tuple[LogEntry, ...]: ...
    # Returns entries ordered by logged_at ascending.
```

#### HTTP handler routes

```
GET    /log?week_start=<ISO>&week_end=<ISO>
    -> 200 { entries: LogEntryResponse[] }

POST   /log
    body: { text: string }
    -> 201 LogEntryResponse

PUT    /log/{entry_id}
    body: { text: string }
    -> 200 LogEntryResponse

DELETE /log/{entry_id}
    -> 204 (no body)
```

```python
@dataclass(frozen=True)
class LogEntryResponse:
    entry_id: str
    raw_text: str
    logged_at: str
    updated_at: str
```

#### Frontend service module (`log_service.ts`)

```typescript
interface LogEntry {
  entry_id: string
  raw_text: string
  logged_at: string    // ISO-8601
  updated_at: string   // ISO-8601
}

interface LogWindow {
  entries: LogEntry[]
}

function listEntries(
  sessionToken: string,
  weekStart: string,
  weekEnd: string,
): Promise<LogWindow>

function createEntry(
  sessionToken: string,
  text: string,
): Promise<LogEntry>

function editEntry(
  sessionToken: string,
  entryId: string,
  text: string,
): Promise<LogEntry>

function deleteEntry(
  sessionToken: string,
  entryId: string,
): Promise<void>
```

#### Frontend view-model types

```typescript
type DeliveryState = 'pending' | 'saved' | 'failed'

interface ChatMessage {
  localId: string         // client-generated UUID, used as Svelte key before entry_id is known
  entry_id: string | null // null while optimistic (not yet confirmed by server)
  raw_text: string
  logged_at: string
  updated_at: string
  delivery: DeliveryState
  isEditing: boolean
}
```

#### `ChatPage.svelte` props

```typescript
interface Props {
  onclearauth: () => void
}
```

#### `ChatMessageList.svelte` props

```typescript
interface Props {
  messages: ChatMessage[]
  onloadprevious: () => void
  onedit: (localId: string, newText: string) => void
  ondelete: (localId: string) => void
}
```

#### `ChatMessageRow.svelte` props

```typescript
interface Props {
  message: ChatMessage
  onedit: (newText: string) => void
  ondelete: () => void
}
```

---

### Data flow

**Initial load (current week)**

```
ChatPage.onMount
  -> log_service.listEntries(token, weekStart, weekEnd)
  -> GET /log?week_start=...&week_end=...
  -> LogRepository.list_window(email, week_start, week_end)
  -> DynamoDB Query (SK BETWEEN "LOG#{week_start}" AND "LOG#{week_end}")
  -> [LogEntry, ...] -> [LogEntryResponse, ...] -> [ChatMessage(delivery=saved), ...]
  -> ChatMessageList renders messages oldest-at-top
```

**Lazy load previous week (scroll to top)**

```
ChatMessageList emits onloadprevious
  -> ChatPage decrements week window by 7 days
  -> log_service.listEntries(token, prevWeekStart, prevWeekEnd)
  -> prepends returned messages to local list (preserving scroll position)
```

**Send message (optimistic)**

```
User submits input bar
  -> ChatPage creates ChatMessage { localId, entry_id: null, delivery: 'pending' }
  -> appends to local list immediately (UI updates)
  -> log_service.createEntry(token, text)  [async]
  -> POST /log -> LogRepository.put(entry) -> DynamoDB PutItem
  -> server returns LogEntryResponse
  -> ChatPage finds message by localId, sets entry_id + delivery='saved'
  -> ChatMessageRow tick glyph updates
```

**Edit message**

```
User clicks edit on a row
  -> ChatMessageRow enters isEditing=true (inline editable field)
  -> User submits edit
  -> ChatPage calls log_service.editEntry(token, entry_id, newText)
  -> PUT /log/{entry_id} -> LogRepository.update_text -> DynamoDB UpdateItem
  -> server returns updated LogEntryResponse
  -> ChatPage replaces ChatMessage in local list (immutable replace by localId)
```

**Delete message**

```
User clicks delete
  -> ChatPage calls log_service.deleteEntry(token, entry_id)
  -> DELETE /log/{entry_id} -> LogRepository.delete -> DynamoDB DeleteItem
  -> ChatPage removes message from local list by localId
```

---

### Boundary map

| Side effect | Location |
|---|---|
| Wall-clock time (`now`) | `log/handler.py` — injected as ISO-8601 string into `make_entry` and `LogEntryPatch` |
| UUID generation (`entry_id`) | `log/handler.py` — `uuid.uuid4()` called once per POST, passed into `make_entry` |
| DynamoDB reads/writes | `log/repository.py` — all methods |
| Session verification | `log/handler.py` — `require_session(headers, secret, now_utc)` at request entry |
| `fetch` / network I/O | `log_service.ts` — all functions |
| Optimistic local state mutation | `ChatPage.svelte` — append, replace, remove from `messages` array |

Business logic in `log/domain.py` (`make_entry`, `apply_patch`) is purely functional: no I/O, no timestamps sourced internally, no UUID generation.

---

## Implementation plan

### `dynamodb_architect`

Design the access patterns for the log feature on the existing profiles table (single-table design, same table used by relations and profiles).

**Entity: LogEntry**

Attributes:
- `PK`: `USER#<owner_email>`
- `SK`: `LOG#<logged_at>#<entry_id>` where `logged_at` is ISO-8601 UTC to second precision (e.g. `2026-04-11T14:05:00Z`) and `entry_id` is a UUID4. The composite SK gives chronological sort within a user partition and collision-safety within the same second.
- `owner_email`: string (denormalised for filter/guard use)
- `entry_id`: string (UUID4; stored separately to support lookup by id without re-parsing the SK)
- `raw_text`: string
- `logged_at`: string (ISO-8601 UTC)
- `updated_at`: string (ISO-8601 UTC)

**Access patterns to support:**

1. Query entries by time window for one user: `PK = USER#<email>` AND `SK BETWEEN LOG#<week_start> AND LOG#<week_end>`. No GSI needed; covered by the base table.
2. Update text + `updated_at` by user + entry_id: requires knowing the full SK. The handler must either store `logged_at` in a secondary location or reconstruct the SK from a separate lookup. Recommended: store a GSI or keep `logged_at` in a separate attribute and use a GSI `PK=USER#<email>, SK=entry_id` for point lookups. Alternatively, the client sends `logged_at` with edit/delete requests so the handler can reconstruct the SK directly — this avoids a GSI. Decide which approach fits cost constraints.
3. Delete by user + entry_id: same reconstruction need as update (see above).

The `dynamodb_architect` must decide: point-lookup strategy (GSI vs. client-supplied `logged_at` in request body/path). Document the chosen approach and specify any new GSI on the profiles table.

### `infrastructure_engineer`

- Add a new Lambda function (or reuse the dispatcher pattern) for `/log` routes: `GET /log`, `POST /log`, `PUT /log/{entry_id}`, `DELETE /log/{entry_id}`.
- Add the four routes to the Lambda Function URL allowed paths / CloudFront distribution behaviours, following the existing pattern from relations (`/relations*`). The new path pattern is `/log` and `/log/*`.
- Expose environment variable `LOG_API_URL` (or reuse the dispatcher's base URL) to the frontend via the Vite build. If the dispatcher Lambda already handles all routes, no new Lambda is needed — just route the new paths to the same dispatcher.
- No new DynamoDB tables; the feature reuses `PROFILES_TABLE_NAME`.
- Expose `VITE_LOG_API_URL` to the frontend build.

### `python_developer`

Create the following modules:

**`src/log/domain.py`**
- `LogEntry` frozen dataclass with fields: `entry_id`, `owner_email`, `raw_text`, `logged_at`, `updated_at`.
- `LogEntryPatch` frozen dataclass with fields: `raw_text`, `updated_at`.
- `make_entry(entry_id: str, owner_email: str, raw_text: str, now: str) -> LogEntry` — pure factory; sets both `logged_at` and `updated_at` to `now`.
- `apply_patch(entry: LogEntry, patch: LogEntryPatch) -> LogEntry` — returns new `LogEntry` with updated `raw_text` and `updated_at`; preserves all other fields.

**`src/log/repository.py`**
- `LogRepository.__init__(self, table: Any) -> None`
- `put(self, entry: LogEntry) -> None` — DynamoDB `PutItem`.
- `update_text(self, owner_email: str, entry_id: str, patch: LogEntryPatch) -> LogEntry` — DynamoDB `UpdateItem`; raises `ValueError` if item not found or owner mismatch.
- `delete(self, owner_email: str, entry_id: str) -> None` — DynamoDB `DeleteItem`; raises `ValueError` if item not found or owner mismatch.
- `list_window(self, owner_email: str, week_start: str, week_end: str) -> tuple[LogEntry, ...]` — DynamoDB Query with `SK BETWEEN "LOG#{week_start}" AND "LOG#{week_end}"`, returns ascending order.
- SK reconstruction strategy: follow the decision made by `dynamodb_architect`. If the GSI approach is chosen, implement a `_get_by_entry_id(owner_email, entry_id)` private method that queries the GSI to fetch the full item (including `logged_at`) before updating or deleting.

**`src/log/handler.py`**
Entry point for all four routes. At the boundary:
- Read `SESSION_SECRET` and `PROFILES_TABLE_NAME` from environment.
- Instantiate `LogRepository`.
- For each request: call `require_session`, extract `claims.email`, dispatch by method+path.
- `POST /log`: generate `entry_id = str(uuid.uuid4())`, `now = datetime.now(UTC).isoformat()`, call `make_entry`, then `repo.put`, return 201 with `LogEntryResponse`.
- `GET /log`: parse `week_start` and `week_end` from query string, call `repo.list_window`, return 200.
- `PUT /log/{entry_id}`: parse body `text`, build `LogEntryPatch(raw_text=text, updated_at=now)`, call `repo.update_text`, return 200.
- `DELETE /log/{entry_id}`: call `repo.delete`, return 204.

**`src/app/dispatcher.py`**
Add routing: if `raw_path == "/log"` or `raw_path.startswith("/log/")` → `log_handler.handler(event, context)`.

**Tests** (`tests/test_log_*.py`):
- Unit tests for `domain.py`: `make_entry` and `apply_patch` are pure functions, test without moto.
- Integration tests for `repository.py`: use `mock_aws` / `moto`, create the profiles table with appropriate key schema, exercise all four repository methods.
- Handler tests: use the same mock-table pattern as existing handler tests.

### `frontend_developer`

**Replace `HomePage.svelte` with `ChatPage.svelte`** (or rename in-place; check with team). The existing `HomePage.svelte` displays a minimal badge+button UI; the chat replaces this entirely. The pending-relations badge moves to a navigation header within `ChatPage` (see open question 1).

**`src/lib/ChatPage.svelte`**
- Props: `{ onclearauth: () => void }`
- State: `messages: ChatMessage[]`, `loadedWeeks: string[]` (week-start ISO strings already fetched), `isLoadingMore: boolean`, `currentPage: 'chat' | 'profile'`
- On mount: compute current week window, call `log_service.listEntries`, map to `ChatMessage[]` with `delivery='saved'`, also call `home_service.getHomeData` for badge count.
- Render: header bar (app name + Profile button with badge), `ChatMessageList` (flex-grow, scrollable), fixed bottom input bar.
- Send: create optimistic `ChatMessage { localId: crypto.randomUUID(), entry_id: null, delivery: 'pending', ... }`, push to `messages`, then await `log_service.createEntry`, on success find by `localId` and update `entry_id` + `delivery='saved'`.
- Edit: find `ChatMessage` by `localId`, call `log_service.editEntry`, on success replace the message in `messages` (immutable replace: `messages = messages.map(m => m.localId === localId ? updated : m)`).
- Delete: call `log_service.deleteEntry`, on success filter message out of `messages`.
- Load previous: decrement week window, call `log_service.listEntries`, prepend results to `messages`.

**`src/lib/ChatMessageList.svelte`**
- Props: `{ messages: ChatMessage[], onloadprevious: () => void, onedit: (localId: string, newText: string) => void, ondelete: (localId: string) => void }`
- Renders `ChatMessageRow` for each message, keyed by `localId`.
- Attaches a scroll listener: when `scrollTop === 0` emits `onloadprevious`.
- On new message appended (length increases), auto-scrolls to bottom.

**`src/lib/ChatMessageRow.svelte`**
- Props: `{ message: ChatMessage, onedit: (newText: string) => void, ondelete: () => void }`
- Normal state: bubble with `raw_text`, formatted `logged_at` (local time, second precision), hover-reveal edit/delete icon buttons, delivery indicator (spinner if `pending`, tick glyph if `saved`). If `updated_at !== logged_at`, show a small "edited" label.
- Edit state (`isEditing`): replace text with `<textarea>` pre-filled with `raw_text`; Save and Cancel buttons. Save calls `onedit(newText)` and exits edit state.

**`src/lib/log_service.ts`**
Implement all four functions from the interface section. Base URL from `import.meta.env.VITE_LOG_API_URL ?? 'http://localhost:8000'`. Use `assertOk` from `http_utils.ts`.

**`src/lib/home_service.ts`** — no change to API shape; `ChatPage` continues calling `getHomeData` to obtain the badge count on mount and after navigation back from `ProfilePage`.

**`vite.config.ts`** — no alias changes required for the log feature.

---

## Decisions

1. **Badge placement after home-page replacement.** The badge count is fetched independently via `GET /` on `ChatPage` mount — no change to `src/app/handler.py`. The badge appears in the chat header's Profile navigation button. `ChatPage` performs two parallel requests on mount: `GET /log` for the current week and `GET /` for the badge count.

2. **Point-lookup strategy for edit and delete.** Use a GSI. Rather than leaking the internal SK structure (`logged_at`) to the API, add a GSI to support point lookups by `entry_id` alone. The `dynamodb_architect` must specify the GSI definition. The handler receives only `entry_id` in the path (`PUT /log/{entry_id}`, `DELETE /log/{entry_id}`).

3. **Week boundary definition.** Use UTC timestamps. "Current week" is a rolling 7-day window: `week_end = now (UTC)`, `week_start = now − 7 days (UTC)`. Each "load previous" call shifts the window back by 7 days. Document this convention in `log_service.ts`.

4. **Error handling for failed optimistic sends.** If `POST /log` returns an error, mark the message `delivery='failed'` and show a **Retry** button on the bubble. Tapping Retry re-sends via `createEntry`; on success the message transitions to `delivery='saved'` and receives its server `entry_id`. `DeliveryState` must be `'pending' | 'saved' | 'failed'`.
