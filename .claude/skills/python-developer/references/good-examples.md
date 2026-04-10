# Good Examples

## Side effects injected at boundary

```python
# Business logic operates only on data
def calc_statistics(data: list[dict]) -> float:
    return average(row["value"] for row in data)

# Boundary: I/O happens outside
def calc_statistics_from_file(filename: str) -> float:
    with open(filename, "r") as file:
        data = json.load(file)
    return calc_statistics(data)
```

```python
# Entropy captured outside and injected explicitly
@dataclass(frozen=True)
class DiscountEntropy:
    current_second: int
    draw: float

def pick_discount(entropy: DiscountEntropy) -> int:
    if entropy.current_second % 2 == 0 and entropy.draw > 0.5:
        return 20
    if entropy.draw > 0.2:
        return 10
    return 0
```

## Immutability

```python
# Return a new value instead of mutating
def add_tag(tags: list[str], tag: str) -> list[str]:
    return [*tags, tag]
```

```python
# Immutable default
def collect(item: str, result: tuple[str, ...] = ()) -> tuple[str, ...]:
    return (*result, item)
```

## Boundary normalization for nulls

```python
def foo(args: list[str]):
    for item in args:
        yield item

def foo_from_payload(args: list[str] | None):
    return foo(args or [])
```

## Error handling

```python
# Propagate — let the caller decide
def load_config(path: str) -> Config:
    with open(path) as f:
        return Config(**json.load(f))

# Boundary: translate low-level exception into domain one
def load_config(path: str) -> Config:
    try:
        with open(path) as f:
            return Config(**json.load(f))
    except FileNotFoundError as e:
        raise ConfigNotFoundError(path) from e
```

```python
# Catch only what you expect and can handle
try:
    result = process(data)
except ValueError as e:
    raise InvalidDataError(data) from e
```

## Functional style

```python
def active_emails(users: list[User]) -> list[str]:
    return [u.email for u in users if u.is_active]
```

## Class for behavior injection

```python
class OrderProcessor:
    def __init__(self, repo: OrderRepository, notifier: Notifier):
        self._repo = repo
        self._notifier = notifier

    def process(self, order: Order) -> None:
        data = self._repo.fetch(order.id)
        result = compute(data)
        self._repo.save(result)
        self._notifier.notify(result)
```

## Named types over bare tuples

```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float

def get_coordinates() -> Point:
    return Point(x=51.5, y=0.1)
```

## Focused functions, no defensive checks

```python
# Trust the caller — no impossible-case guards
def apply_discount(price: float, rate: float) -> float:
    return price * (1 - rate)
```

```python
# Extract focused helpers instead of one large function
def process_order(order: Order) -> Receipt:
    total = apply_coupon(subtotal(order.items), order.coupon)
    return build_receipt(order.items, with_tax(total))
```

## Self-explanatory code over comments

```python
raw_config = path.read_text()

def is_transient(error: HttpError) -> bool:
    return error.code in (429, 503)

if is_transient(error):
    retry()
```

## Logging at boundaries only

```python
# Business logic — no logging
def get_user(user_id: str) -> User:
    return db.fetch_user(user_id)

# Boundary (HTTP handler) — log once
try:
    user = get_user(user_id)
except UserNotFoundError:
    logger.warning("User not found: %s", user_id)
    return Response(status=404)
```

## Pure business logic needs no mocks

```python
def test_discount():
    entropy = DiscountEntropy(current_second=4, draw=0.9)
    assert pick_discount(entropy) == 20
```

---

## Pragmatic rule-bending

Rules exist to improve clarity. If following a rule produces more complexity than it removes, break it.

**Example — JWKS caching with `cachetools`:**

```python
@cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=6 * 3600))
def fetch_jwks(url: str) -> JwksPayload:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())
```

This has a mutable module-level `TTLCache` (violates immutability) and side effects inside the function (violates boundary separation). The "correct" alternative — a `JwksCache` dataclass threaded through every call site — adds indirection and boilerplate with no real benefit. The `cachetools` version is simpler, well-understood, and the trade-off is obvious at a glance. Prefer it.

When bending a rule, the test is: *would a reader immediately understand the intent and accept the trade-off?* If yes, the violation is fine.
