# Contract: `/api/sources` — Source Registry Listing

**Feature**: [006-music-sources-expansion](../spec.md) | **Date**: 2026-09-30
**Status**: Modified — additive fields only, no breaking change

## Endpoint

```http
GET /api/sources
```

Returns JSON: an array of source objects. Unchanged in shape from today; this contract records the fields that are **added**.

## Response item

```json
{
  "id": "musicdel",
  "name": "Musicdel",
  "category": "music",
  "base_url": "https://musicdel.ir",
  "enabled": true,

  "kind": "full",
  "status": "active",
  "inactive_reason": null,
  "consecutive_failures": 0
}
```

### Fields

| Field | Type | Added | Description |
|---|---|---|---|
| `id` | string | existing | Stable source identifier |
| `name` | string | existing | Display name |
| `category` | string | existing | `movies` \| `games` \| `music` |
| `base_url` | string | existing | Primary reachable domain |
| `enabled` | boolean | existing | Whether the source is enabled in configuration |
| `kind` | string | **yes** | `full` \| `reference`. See [data-model.md](../data-model.md) |
| `status` | string | **yes** | `active` \| `degraded` \| `inactive`. Derived — see below |
| `inactive_reason` | string \| null | **yes** | Human-readable reason when `status != "active"`, else `null` |
| `consecutive_failures` | integer | **yes** | Failed searches since the last success |

### `status` derivation

| `status` | Condition |
|---|---|
| `inactive` | `enabled === false` in configuration |
| `degraded` | `enabled === true` and `consecutive_failures >= 3` |
| `active` | otherwise |

`inactive_reason` is required to be non-null and specific for `inactive` and `degraded` entries (FR-017, SC-007). A `degraded` source's reason states that it failed 3 consecutive searches and needs maintainer attention.

## Guarantees

- **G1** — Every one of the 20 named sites appears in this response, whether active or not (FR-017, SC-007).
- **G2** — Every entry carries a `kind`. No entry may omit it.
- **G3** — Every entry with `status != "active"` carries a non-empty `inactive_reason` naming the actual cause (dead domain, changed domain, requires account, licensed service, video platform, or access gated). A generic "error" string is non-conforming.
- **G4** — The response shape is unchanged for the existing 12 sources apart from the added fields. No field is removed or retyped (FR-028).
- **G5** — No credential, token, or account identifier appears anywhere in the response (FR-012).

## Consumer impact

`apps/web/src/types/media.ts` → `SourceStatus` gains the four new optional-with-default fields. `SourceStatusBar.tsx` renders a kind badge and the reason text. The Jinja `base.html` source list gains the same two pieces of information.

Because G4 holds, an older client that ignores the new fields continues to work unchanged.

## Errors

This endpoint does not perform network I/O and has no failure mode. It always returns `200` with an array, including when zero sources are configured.
