---
name: lambda-developer
description: Architecture conventions for Lambda + shared layer + CloudFront in this project
---

Reference material for Lambda-based backend development.

- `references/architecture.md` — overall layout: shared layer, per-domain Lambdas, CloudFront routing table
- `references/adding-a-lambda.md` — checklist for introducing a new Lambda (backend + terraform + dev server)
- `references/handler-conventions.md` — handler structure, CORS, session guard, response shape
