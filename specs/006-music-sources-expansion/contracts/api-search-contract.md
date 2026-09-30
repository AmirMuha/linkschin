# Contract: `/api/search` — Music Search

**Feature**: [006-music-sources-expansion](../spec.md) | **Date**: 2026-09-30
**Status**: Modified — additive query parameter, additive item fields, behavioural change to ordering

## Endpoint

```http
GET /api/search?q=<term>&category=music&refresh=<bool>&sources=<id>&sources=<id>
```

The HTML equivalent `/search` takes the same parameters.

## Query parameters

| Parameter | Type | Default | Status | Description |
|---|---|---|---|---|
| `q` | string | required | existing | Search term; NFKC-normalized before use |
| `category` | string | `movies` | existing | `movies` \| `games` \| `music` |
| `refresh` | boolean | `false` | existing | Bypass cache and re-scrape |
| `sources` | string, repeatable | *(none)* | **new** | Source ids to **exclude** from this search |

`sources` is a list of ids the user has chosen to hide (FR-029). It is a hint from the client, not a trust boundary: unknown ids are ignored, and it can only ever *remove* sources, never add one.

The equivalent Next.js path `/search` accepts the same parameter, so the browser client can persist a hidden set and re-attach it to every request without a round trip of its own.

## Response

Unchanged envelope. `items` gains fields; ordering is specified below.

```json
{
  "query": "محسن چاوشی",
  "category": "music",
  "is_cached": false,
  "warnings": [],
  "items": [
    {
      "id": "mus_del_8123",
      "title": "حنایی",
      "category": "music",
      "source_id": "musicdel",
      "page_url": "https://musicdel.ir/track/8123",
      "poster_url": "https://musicdel.ir/cover/8123.jpg",
      "stream_url": "https://dl.musicdel.ir/8123-128.mp3",
      "music_tracks": [
        {
          "id": "mus_del_8123_track",
          "title": "حنایی",
          "artist": "محسن چاوشی",
          "stream_url": "https://dl.musicdel.ir/8123-128.mp3",
          "downloads": [
            {"bitrate": "128kbps", "download_url": "https://dl.musicdel.ir/8123-128.mp3"},
            {"bitrate": "320kbps", "download_url": "https://dl.musicdel.ir/8123-320.mp3"}
          ]
        }
      ],
      "source_kind": "full"
    },
    {
      "id": "spo_track_xyz",
      "title": "حنایی",
      "category": "music",
      "source_id": "spotify",
      "page_url": "https://open.spotify.com/track/xyz",
      "poster_url": "https://i.scdn.co/image/xyz",
      "stream_url": null,
      "music_tracks": [],
      "source_kind": "reference"
    }
  ]
}
```

### New item fields

| Field | Type | Description |
|---|---|---|
| `source_kind` | string | `full` \| `reference`, copied from the source's configuration |

### Reference-source result shape (normative)

A result from a reference source MUST have **all** of:

| Field | Required value |
|---|---|
| `source_kind` | `"reference"` |
| `page_url` | the track's page on the originating site, `http(s)` |
| `stream_url` | `null` |
| `music_tracks` | `[]` |

This is the wire-level expression of FR-011 and is what SC-003 is verified against: a client can tell it must not render a player purely by inspecting the item.

## Ordering

Items are ordered so that **every** `full` item precedes **every** `reference` item (FR-005a). Within each group, the pre-existing relevance order is preserved exactly.

Consequences a client may rely on:

- The first item is always a full-source item whenever any full-source result exists.
- Adding reference sources to the registry does not change the relative order of existing full-source results.
- A cached response and a freshly scraped response have identical ordering.

## Guarantees

- **G1** — A result from a reference source never carries a stream URL, a download variant, or a non-empty `music_tracks` (FR-011, FR-012).
- **G2** — No response field or behaviour introduces credential handling; a reference source is never asked to authenticate (FR-012).
- **G3** — `sources` only ever removes sources from the query set. It cannot cause a disabled or degraded source to be queried (FR-031).
- **G4** — A user's `sources` selection never affects another user's response. The filtered set is not written to the shared cache, so a cache hit always reflects the unfiltered set (FR-030).
- **G5** — A failing or slow source never prevents results from the other sources. Existing behaviour: the source contributes a `warnings` entry and an empty result list.
- **G6** — Media URLs, where present, are upstream URLs served directly to the client. The response never contains a URL that routes media through this service (FR-013, SC-008).
- **G7** — For movies and games, the response is byte-for-byte unchanged apart from the additive `source_kind` field (FR-028).

## Errors

Unchanged from today. A bad `category` falls back to `movies`; a missing `q` is a `422`. No new failure mode is introduced by the `sources` parameter — unknown or malformed values are ignored rather than rejected, so a stale client-side saved set can never break a search.

## Client obligations

A client MUST:

1. Not render a player or download control when `source_kind` is `"reference"` (SC-003).
2. Not assume `music_tracks` is non-empty.
3. Treat `source_kind` as absent-or-`"full"` for backward compatibility with a pre-feature server.

A client MUST NOT attempt to fetch, proxy, or cache media through this service for any item, full or reference (FR-013).
