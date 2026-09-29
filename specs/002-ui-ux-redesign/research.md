# Technical Research & Decisions: Modern Web Interface and UI/UX Redesign

- **Feature**: `002-ui-ux-redesign`
- **Date**: 2026-09-29
- **Status**: Complete (All technical unknowns resolved)

---

## Decision 1: Frontend Architecture & Monorepo Integration

### Decision
Create `apps/web` as a **Next.js (App Router, TypeScript, React)** application within the existing Turborepo and pnpm workspace, coexisting with `apps/api`.

### Rationale
- **User Mandate & Modern UX**: The feature input explicitly requested a Next.js platform web interface. Rich client-side features (inline audio player with time scrubber, instantaneous client-side quality filtering, clipboard batch export, and animated skeleton loaders) are significantly cleaner and more maintainable in React than vanilla JavaScript embedded in Jinja2 templates.
- **Turborepo Integration**: The repository was already migrated to a Turborepo monorepo (`package.json`, `turbo.json`, `pnpm-workspace.yaml`). Adding `apps/web` completes the workspace architecture cleanly alongside `apps/api`.
- **Fast Development & Production Builds**: Turborepo manages parallel builds and pipeline caching across `apps/api` and `apps/web`.

### Alternatives Considered
- *Jinja2 + Vanilla JS / HTMX*: Preserves the original MVP setup without Node build steps, but falls short of delivering a top-tier cinematic experience with persistent audio playback across category switches, complex stateful download matrices, and interactive format filters.
- *Standalone Vite SPA*: Lightweight, but lacks Next.js routing, metadata optimization, and standard React server component capabilities if SSR or edge caching is leveraged later.

---

## Decision 2: Styling, Design Tokens & Component System

### Decision
**Tailwind CSS** paired with headless accessibility primitives (**Radix UI** or native accessible dialog/popover) and **Lucide React** icons.

### Rationale
- **Dark-First Entertainment Theme**: A high-contrast dark aesthetic (`slate-950`/`zinc-950` canvas, `zinc-900` cards, emerald/cyan/violet accents for category cues) provides an immersive, cinema-grade interface.
- **Micro-Interactions**: Hover scales (`scale-[1.02]`), subtle glassmorphism borders (`border-white/10`), and non-blocking skeleton loaders can be composed utility-first without massive runtime overhead.
- **Accessible Primitives**: Radix UI unstyled components guarantee full keyboard navigation (focus rings, `Escape` dismissals, ARIA tab roles, modal focus traps) without custom accessibility boilerplate.

### Alternatives Considered
- *Full UI Kits (MUI, Ant Design)*: Heavy bundle size, difficult to customize into a bespoke media aggregator aesthetic, poor default RTL support.
- *Pure Vanilla CSS*: Higher maintenance burden, harder to maintain consistent spacing and color tokens across cards, badges, and drawers.

---

## Decision 3: Bilingual RTL/LTR Layout & Persian Typography

### Decision
Root `dir="rtl"` with **Vazirmatn** variable font for Persian text, combined with strict `dir="ltr"` and `unicode-bidi: isolate` wrappers for technical identifiers (filenames, release hashes, codecs, resolutions, URLs).

### Rationale
- **The Bidirectional Inversion Problem**: In Persian right-to-left interfaces, mixed technical strings like `1080p.BluRay.x265-PSA` or `Part 01.rar` often invert brackets, punctuation, and periods (e.g. `.rar` rendering at the start of the string instead of the end). Wrapping technical badges, links, and filenames with explicit `dir="ltr"` and `unicode-bidi: isolate` / monospace styling completely eliminates bidirectional layout bugs.
- **Vazirmatn Font**: The gold-standard open-source Persian font with extensive weight support, clean Latin character matching, and crisp legibility on high-DPI and mobile screens.
- **CSS Logical Properties**: Using `ms-` (margin-inline-start), `me-` (margin-inline-end), `ps-`, and `pe-` in Tailwind ensures symmetric padding and margins across RTL and LTR viewports.

### Alternatives Considered
- *System Persian Fonts*: Inconsistent across platforms (macOS/iOS have Persian system fonts, older Windows versions fall back to poorly spaced Arial/Tahoma). Bundling Vazirmatn via `@fontsource/vazirmatn` or Next.js `next/font` guarantees typography consistency.

---

## Decision 4: Backend API Contract & Communication Layer

### Decision
Expose typed JSON endpoints on FastAPI in `apps/api`:
- `GET /api/search?q={query}&category={category}&refresh={bool}`
- `GET /api/sources`
- `GET /api/health`
Enable FastAPI `CORSMiddleware` for localhost origins during development, and share TypeScript types mirroring Python dataclass models.

### Rationale
- **Clean Separation**: Decouples presentation (`apps/web`) from scraping and link extraction (`apps/api`).
- **Graceful Error Surfacing**: Scraper timeouts (7s per source, 10s global) return partial results along with a `warnings` array in the JSON response, enabling the frontend to display non-blocking status badges for temporarily degraded sources.
- **Direct Link Extraction**: The API continues to extract direct CDN download links and streaming URLs, fulfilling the metadata-only requirement.

### Alternatives Considered
- *BFF (Backend for Frontend) in Next.js API Routes*: Redundant server layer that adds latency and duplicate proxying logic. Calling FastAPI directly from client or Next.js fetch avoids an extra hop.

---

## Decision 5: Client-Side Audio & Video Playback Architecture

### Decision
A single global **Audio Player Context/Store** managing an in-memory HTML5 `Audio` instance for music previews, alongside an opportunistic lightweight modal/inline `<video>` player for movie results with direct stream URLs.

### Rationale
- **Single-Track Exclusivity**: When a user clicks play on Track B while Track A is playing, the global audio manager immediately halts Track A, loads Track B, and preserves user volume settings in `localStorage`.
- **Zero-Relay Direct Streaming**: Stream URLs from Iranian CDNs (MP3/MP4) load directly in native browser audio/video elements. No media bytes touch the application server, strictly adhering to Constitution Principle III.
- **Unobtrusive UX**: The audio player sits as a sticky bottom bar or inline card control, allowing the user to continue browsing other results without audio interruption.

### Alternatives Considered
- *Third-Party Audio Player Libraries (Howler.js, React-Player)*: Unnecessary dependency baggage (violates ponytail simplicity). Native HTML5 `Audio` and `<video>` cover 100% of the requirements with zero external dependencies.

---

## Decision 6: Clipboard Integration & Batch Link Exporter

### Decision
A unified clipboard utility utilizing `navigator.clipboard.writeText()` with a graceful fallback to a temporary hidden textarea for non-secure or restricted contexts.

### Rationale
- **Download Manager Compatibility**: Multi-part game archives export direct URLs formatted as newline-separated text (`url1\nurl2\nurl3`), which is automatically parsed by Internet Download Manager (IDM), JDownloader, aria2, and wget.
- **Instant Visual Feedback**: Every copy trigger (part link, movie link, password, batch list) triggers a temporary checkmark icon and non-intrusive toast notification confirming the action.
- **Password Pill**: Game archive extraction passwords (e.g. `www.yasdl.com`) have a dedicated one-tap copy button right next to the password text.

---

## Decision 7: Search Experience, Keyboard Shortcuts & Race Condition Handling

### Decision
Client-side search bar with `AbortController` request cancellation, `/` and `Ctrl+K` / `Cmd+K` global focus shortcuts, and search history saved in `localStorage`.

### Rationale
- **Race Condition Prevention**: If a user switches rapidly between "Movies" and "Games", or types a revised query before the 10-second scraper budget resolves, any in-flight request is aborted via `AbortController.abort()` to prevent obsolete results from overwriting newer queries.
- **Power-User Navigation**: Pressing `/` or `Ctrl+K` immediately focuses and selects the search input, while `Escape` clears or dismisses open drawers.
- **Instant Local Filtering**: Once results load, users can filter by quality (1080p, 720p, 480p) or audio type (Dubbed vs Subtitled) instantly in the client without re-querying the backend.
