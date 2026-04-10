# Style Guide

Rules are guidelines, not laws. Violate any of them if doing so produces meaningfully clearer or more readable code. Use judgment.

## Side effects and business logic
Business functions receive data as arguments. I/O (network, clock, files, entropy) happens at the boundary and results are passed in.

## Immutability
`@dataclass(frozen=True)` for value objects. Return new values instead of mutating arguments. No mutable default arguments.

## Nullability
Business functions take concrete types, not `X | None`. Normalize nulls at system boundaries before passing to logic.

## Error handling
Let exceptions propagate. Catch only what you can genuinely handle: retry transients, translate low-level exceptions into domain ones. Never catch-and-return-None. Be specific — no bare `except Exception` in business logic.

## Naming
No `utils`, `helpers`, `common`, `shared`, `misc` module names. Name by responsibility.

## Paradigm
Prefer functional → OO → imperative. Use classes for behavior injection or stateful accumulators. Don't wrap stateless logic in a class.

## Types
Annotate everything. Named dataclasses over bare tuples for multi-value returns. Avoid `X | Y` unions inside the system — they signal a function doing too much. No `isinstance`/`hasattr`/`getattr` for type dispatch.

## Complexity
Functions ≤ ~20 lines. Extract named helpers when they grow. No defensive checks for cases that can't happen. Validate only at system boundaries.

## Documentation
Docstrings for public APIs only. Comments only where logic is genuinely non-obvious. Never restate what the code does.

## Logging
Log at system boundaries only (handlers, consumers, entry points). Never inside business logic. Never log-and-swallow.

## Testing
Business logic is pure — test it by calling functions with inputs and asserting outputs, no mocks needed. Minimize `MagicMock`/`patch`. Heavy mocking signals leaked side effects.
