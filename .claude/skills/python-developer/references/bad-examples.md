# Bad Examples (Anti-Patterns)

## Reinventing the wheel instead of using a library

Before writing parsing, retry, caching, or formatting logic by hand, check if a well-maintained library already does it. Hand-rolled versions are harder to maintain and miss edge cases.

```python
# Bad: manual .env parser — mishandles quotes, comments, multiline values
def _load_dotenv() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_dotenv()

# Good: use python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

## Side effects hidden in business logic

```python
# I/O mixed into logic
def calc_statistics(filename: str) -> float:
    with open(filename, "r") as file:
        data = json.load(file)
    return average(row["value"] for row in data)
```

```python
# Hidden entropy
def pick_discount() -> int:
    current_second = datetime.now(UTC).second
    draw = Random().random()
    if current_second % 2 == 0 and draw > 0.5:
        return 20
    if draw > 0.2:
        return 10
    return 0
```

## Mutating arguments / mutable defaults

```python
def add_tag(tags: list[str], tag: str) -> None:
    tags.append(tag)  # mutates caller's list

def collect(item: str, result: list[str] = []) -> list[str]:
    result.append(item)  # shared across all calls
    return result
```

## Nullable inputs in business logic

```python
def foo(args: list[str] | None):
    if args is None:
        return
    for item in args:
        yield item
```

## Catch-and-swallow

```python
def load_config(path: str) -> Config | None:
    try:
        with open(path) as f:
            return Config(**json.load(f))
    except Exception:
        return None  # silently converts failure into plausible-looking result
```

```python
# Too broad — masks real bugs
try:
    result = process(data)
except Exception:
    return default_result
```

## Logging and swallowing

```python
def get_user(user_id: str) -> User | None:
    try:
        return db.fetch_user(user_id)
    except UserNotFoundError as e:
        logger.error("Failed to fetch user: %s", e)
        return None  # error disappears
```

## Imperative accumulation

```python
def active_emails(users: list[User]) -> list[str]:
    result = []
    for user in users:
        if user.is_active:
            result.append(user.email)
    return result
```

## Passing multiple functions instead of a class

```python
def process_order(order: Order, fetch: Callable, save: Callable, notify: Callable):
    data = fetch(order.id)
    result = compute(data)
    save(result)
    notify(result)
```

## Class wrapping stateless logic

```python
class DiscountCalculator:
    def __init__(self, rate: float):
        self.rate = rate

    def apply(self, price: float) -> float:
        return price * (1 - self.rate)
```

## Anonymous tuple for multi-value return

```python
def get_coordinates() -> tuple[float, float]:
    return 51.5, 0.1
```

## Union type inside system

```python
def render(value: dict | list | str) -> str:
    ...
```

## Helper wrapping a cast (unnecessary indirection at boundaries)

When extracting a typed value from an untyped boundary dict (`dict[str, object]`), use `cast` directly. Don't introduce a named helper just to paper over a type — that hides the intent and adds a function that does nothing meaningful.

```python
# Bad: helper exists only to satisfy the type checker
def _coerce_body(raw: object) -> str:
    if isinstance(raw, bytes):
        return raw.decode()
    return str(raw)

body_str = _coerce_body(event.get("body") or "")

# Good: cast at the boundary, inline
body_str = cast(str, event.get("body") or "")
```

## Defensive checks for impossible cases

```python
def apply_discount(price: float, rate: float) -> float:
    if price is None:
        raise ValueError("price must not be None")
    if rate is None:
        raise ValueError("rate must not be None")
    if rate < 0 or rate > 1:
        raise ValueError("rate must be between 0 and 1")
    return price * (1 - rate)
```

## One large function doing too much

```python
def process_order(order: Order) -> Receipt:
    # validate
    if not order.items:
        raise ValueError("empty order")
    # apply discounts
    total = sum(item.price for item in order.items)
    if order.coupon:
        total *= (1 - order.coupon.rate)
    # compute tax
    tax = total * 0.2
    total_with_tax = total + tax
    # build receipt
    lines = [f"{item.name}: {item.price}" for item in order.items]
    return Receipt(lines=lines, total=total_with_tax)
```

## Comments that restate the code

```python
# Read the file
with open(path) as f:
    data = f.read()

# Retry only on transient errors
if error.code in (429, 503):
    retry()
```

## Mocking internals to test business logic

```python
def test_discount():
    with patch("myapp.discount.datetime") as mock_dt:
        mock_dt.now.return_value.second = 4
        with patch("myapp.discount.Random") as mock_rng:
            mock_rng.return_value.random.return_value = 0.9
            assert pick_discount() == 20
```
