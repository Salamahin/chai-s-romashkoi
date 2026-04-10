# Add Relations Between Users

Date: 2026-04-10
Status: Accepted

## Context

Users can build a personal profile but currently have no way to connect with other users. The next requirement is a **relations** feature: one user can send a named relation request to another user by email address, the recipient confirms or rejects it, and both parties can view and delete their confirmed relations.

Key product decisions:

- The relation identifier for the target is the user's **email address** (present in `SessionClaims.email`).
- A relation has a **label** that is free-text with suggestions drawn from labels the user has used before, following the same UX pattern as profile tags.
- A relation exists in one of two states: **pending** (sent, awaiting confirmation) or **confirmed** (accepted by the recipient).
- **Rejection deletes the item** — no `rejected` status is stored.
- Users can delete both confirmed relations and pending-sent relations. A recipient cannot delete a pending-received relation (they can only confirm or reject it).
- The pending-received count is displayed as a notification badge on the **Profile** button on `HomePage.svelte`, since relations are managed from the Profile page.
- The `GET /` handler is repurposed to return a `pending_relations_count` field used by the home page badge.
- Infrastructure constraint remains: near-zero AWS cost, Lambda Function URLs, no API Gateway.

## Architecture

### Components

#### Backend

**`src/relations/domain.py`** — pure domain types and business logic for relations.
Defines `RelationRecord`, `RelationDirection`, and functions for computing label suggestions and validating send/confirm/delete operations.

**`src/relations/repository.py`** — DynamoDB adapter for relations (side-effectful).
Reads and writes relation items. Speaks only in domain types at its public boundary.

**`src/relations/label_suggestions.py`** — pure label-vocabulary function.
Derives the set of distinct normalised label strings from a collection of `RelationRecord` values. No I/O.

**`src/relations/handler.py`** — Lambda entry point (boundary) for all relation endpoints.
Reads environment variables, reads wall clock, verifies session, delegates to repository and domain functions, returns HTTP responses.

**`src/app/handler.py`** — updated to return `pending_relations_count` alongside the existing message.
At the boundary, calls `RelationRepository.count_pending_received(email)` and embeds the result in the `GET /` response.

#### Frontend

**`HomePage.svelte`** — top-level page shown after login.
Fetches home data (including `pending_relations_count`) from `GET /` on mount. Displays navigation buttons: Profile. The Profile button carries a badge showing the pending count when it is non-zero, since relations are managed from the Profile page. Clicking Profile navigates to `ProfilePage`.

**`ProfilePage.svelte`** — existing profile page, extended to include a relations section.
Accepts an `onback: () => void` prop to return to `HomePage`. On mount, loads both profile data (existing) and relations data (new: `listRelations`, `getKnownLabels`). Renders the existing profile entries section plus a new relations section below it.

**`RelationsPanel.svelte`** — sub-component rendered by `ProfilePage`.
Owns the relations load lifecycle and renders the full relations UI: pending-received list (with Confirm / Reject actions), pending-sent list (with Delete action), confirmed list (with Delete action), and the send-new-relation form.

**`RelationRow.svelte`** — single relation row, direction-aware.
Renders peer email, label, and appropriate action buttons based on direction and status.

**`LabelCombobox.svelte`** — label input with autocomplete, identical in structure to `TagCombobox.svelte`.
Accepts current value and known-labels list; normalises before emitting change.

**`relations_service.ts`** — API client for all relation endpoints.
Pure functions over `fetch`. No module-level state.

**`home_service.ts`** — API client for `GET /`.
Returns `HomeData` including `pending_relations_count`.

### Interfaces

#### Backend (typed pseudocode)

```
RelationStatus: Literal["pending", "confirmed"]
RelationDirection: Literal["sent", "received"]

RelationRecord:
  relation_id: str         # UUID, assigned when the relation is first sent
  owner_email: str         # email of the user who owns this copy of the record
  peer_email: str          # email of the other party
  label: str               # normalised (lowercase, trimmed)
  status: RelationStatus
  direction: RelationDirection
  created_at: str          # ISO-8601 UTC

HomeResponse:
  message: str
  pending_relations_count: int

def normalise_label(raw: str) -> str
def build_send_records(sender_email, recipient_email, label, relation_id, created_at) -> tuple[RelationRecord, RelationRecord]
def build_confirmed_records(sent_copy, received_copy) -> tuple[RelationRecord, RelationRecord]
def known_labels(records: tuple[RelationRecord, ...]) -> frozenset[str]

class RelationRepository:
  def list_for_owner(self, owner_email: str) -> tuple[RelationRecord, ...]
  def put_pair(self, sender_copy, recipient_copy) -> None
  def confirm_pair(self, confirmer_email, relation_id) -> RelationRecord
  def delete_pair(self, owner_email, relation_id) -> None
  def count_pending_received(self, owner_email: str) -> int
```

#### Frontend (TypeScript)

```typescript
type RelationStatus = "pending" | "confirmed"
type RelationDirection = "sent" | "received"

interface RelationRecord {
  relation_id: string
  peer_email: string
  label: string
  status: RelationStatus
  direction: RelationDirection
  created_at: string
}

interface RelationsSnapshot { relations: RelationRecord[] }
interface HomeData { message: string; pending_relations_count: number }

// home_service.ts
function getHomeData(sessionToken: string): Promise<HomeData>

// relations_service.ts
function listRelations(sessionToken: string): Promise<RelationsSnapshot>
function sendRelation(sessionToken: string, recipientEmail: string, label: string): Promise<RelationRecord>
function confirmRelation(sessionToken: string, relationId: string): Promise<RelationRecord>
function deleteRelation(sessionToken: string, relationId: string): Promise<void>
function getKnownLabels(sessionToken: string): Promise<string[]>
```

### Data flow

```
Browser                        Lambda handler              DynamoDB
  |                                 |                          |
  | GET /  (home page mount)        |                          |
  |-------------------------------->| count_pending_received() |
  |                                 |------------------------->| Query GSI: owner=email, status_direction=pending#received
  |<-- 200 HomeData { count } ------|                          |
  |                                 |                          |
  | GET /relations  (profile mount) |                          |
  |-------------------------------->| list_for_owner(email)    |
  |                                 |------------------------->| Query PK=USER#email, SK begins_with RELATION#
  |<-- 200 RelationsSnapshot -------|                          |
  |                                 |                          |
  | POST /relations                 |                          |
  |-------------------------------->| build_send_records()     |
  |                                 | put_pair() → transact    |
  |                                 |------------------------->| Put sender copy + Put recipient copy
  |<-- 201 RelationRecord (sender) -|                          |
  |                                 |                          |
  | POST /relations/{id}/confirm    |                          |
  |-------------------------------->| confirm_pair()           |
  |                                 |  GetItem confirmer       |
  |                                 |  GetItem peer            |
  |                                 |  transact Put both       |
  |                                 |------------------------->|
  |<-- 200 RelationRecord (updated)-|                          |
  |                                 |                          |
  | DELETE /relations/{id}          |                          |
  |-------------------------------->| delete_pair()            |
  |                                 |  GetItem owner           |
  |                                 |  transact Delete both    |
  |                                 |------------------------->|
  |<-- 204 ----------------------   |                          |
```

## DynamoDB Schema

Relations coexist in the existing `<project_name>-profiles` single-table alongside profile entries.

### Key Design

| Entity          | PK                    | SK                        | Attributes |
|-----------------|-----------------------|---------------------------|------------|
| Profile entry   | `USER#<sub>`          | `ENTRY#<ulid>`            | `tag`, `text`, `updated_at` |
| Relation record | `USER#<owner_email>`  | `RELATION#<relation_id>`  | see below |

**Note on PK namespace:** profile entries use `USER#<sub>` (opaque Google numeric ID); relation records use `USER#<owner_email>`. Collision is empirically impossible (Google `sub` values are purely numeric). The implementer must never interchange the two namespaces. A future migration to `USERSUB#` / `USEREMAIL#` prefixes would eliminate any ambiguity but is out of scope.

### Full Item Attributes

| Attribute          | Type   | Example                     | Purpose |
|--------------------|--------|-----------------------------|---------|
| `PK`               | String | `USER#alice@example.com`    | Partition key |
| `SK`               | String | `RELATION#<uuid>`           | Sort key |
| `owner_email`      | String | `alice@example.com`         | Top-level projection for GSI partition key |
| `peer_email`       | String | `bob@example.com`           | Needed to look up peer's record during confirm/delete |
| `label`            | String | `"colleague"`               | Normalised (lowercase, trimmed) |
| `status`           | String | `"pending"` / `"confirmed"` | Lifecycle state |
| `direction`        | String | `"sent"` / `"received"`     | Owner's perspective |
| `created_at`       | String | `"2026-04-10T14:00:00Z"`    | ISO-8601 UTC; sort order for `list_for_owner` |
| `status_direction` | String | `"pending#received"`        | Composite denormalised attribute; GSI sort key |

### GSI: PendingReceivedIndex

| Property        | Value |
|-----------------|-------|
| Partition key   | `owner_email` (String) |
| Sort key        | `status_direction` (String) |
| Projection      | `KEYS_ONLY` |
| Serves          | `count_pending_received` — `GET /` home badge |

**Why `status_direction` and not `status` alone:** a GSI on `status` alone would require a filter expression on `direction`, causing DynamoDB to read all pending relations (sent + received) and discard the sent ones — wasting RCUs. The composite attribute makes access pattern 2 a pure key condition that reads only matching items.

**`status_direction` values:**

| status      | direction  | status_direction       |
|-------------|------------|------------------------|
| `pending`   | `sent`     | `pending#sent`         |
| `pending`   | `received` | `pending#received`     |
| `confirmed` | `sent`     | `confirmed#sent`       |
| `confirmed` | `received` | `confirmed#received`   |

### Condition Expressions

| Operation | Condition | On failure |
|-----------|-----------|------------|
| Send — Put each copy | `attribute_not_exists(PK)` | `409 Conflict` (duplicate send) |
| Confirm — Put confirmer's copy | `#status = :pending AND #direction = :received` | `409 Conflict` |
| Confirm — Put peer's copy | none (unconditional) | `409 Conflict` if peer's record missing |
| Delete / Reject | none — fall back to single `DeleteItem` if peer's copy missing | idempotent |

### Terraform additions (reference)

```hcl
# Add to aws_dynamodb_table.profiles:

attribute { name = "owner_email";    type = "S" }
attribute { name = "status_direction"; type = "S" }

global_secondary_index {
  name            = "PendingReceivedIndex"
  hash_key        = "owner_email"
  range_key       = "status_direction"
  projection_type = "KEYS_ONLY"
}

# Add to IAM policy actions: "dynamodb:TransactWriteItems"
# Add to IAM policy resources: "${aws_dynamodb_table.profiles.arn}/index/PendingReceivedIndex"
```
