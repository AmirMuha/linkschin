# UI Component & Interaction Contracts: Modern Web Interface

- **Feature**: `002-ui-ux-redesign`
- **Application**: `apps/web` (Next.js / React)
- **Design Tokens**: Tailwind CSS, Dark-First (`slate-950` canvas), Vazirmatn Persian typography

---

## 1. Component Hierarchy

```text
<AppShell dir="rtl">
  ├── <Header>
  │     ├── <BrandLogo />
  │     ├── <CategoryNav activeTab={category} onTabChange={setCategory} />
  │     ├── <SearchBar query={query} onSearch={handleSearch} />
  │     └── <SourceStatusBar sources={sources} warnings={warnings} />
  │
  ├── <MainContent>
  │     ├── <InViewFilterBar filters={filterState} onFilterChange={setFilterState} />
  │     │
  │     ├── {isLoading ? <SkeletonGrid count={8} /> : (
  │     │     <MediaGrid items={filteredItems}>
  │     │       ├── <MovieCard item={movie} onPlayStream={openVideoModal} />
  │     │       │     └── <MovieDownloadMatrix variants={movie.movie_variants} />
  │     │       │
  │     │       ├── <GameCard item={game} />
  │     │       │     ├── <PasswordPill password={release.archive_password} />
  │     │       │     └── <GamePartList parts={release.parts} onCopyAll={copyParts} />
  │     │       │
  │     │       └── <MusicCard item={music} onPlay={audioPlayer.play} />
  │     │             └── <MusicDownloadRow downloads={track.downloads} />
  │     │     </MediaGrid>
  │     │   )}
  │     └── <EmptyState / ErrorBanner />
  │
  ├── <GlobalAudioPlayer activeTrack={player.track} state={player.state} />
  ├── <VideoPlayerModal isOpen={modal.isOpen} streamUrl={modal.url} onClose={modal.close} />
  └── <ToastNotification toast={toastState} />
</AppShell>
```

---

## 2. Component Specifications

### 2.1 `<SearchBar />`
- **Props**:
  - `query: string`: Active query string.
  - `isLoading: boolean`: Disables input and displays inline spinner when active.
  - `onSearch: (q: string, refresh?: boolean) => void`: Callback on search submission.
- **Interactions**:
  - Global Shortcut: Pressing `/` or `Ctrl+K` / `Cmd+K` focuses the input element and selects existing text.
  - Pressing `Escape` blurs the input and clears focus.
  - Clear button (`X`) appears when input has text.
  - "تازه‌سازی" (Force Refresh) button allows re-scraping with cache bypass (`refresh=true`).
- **Accessibility**:
  - `role="search"`, `aria-label="جستجوی فیلم، بازی و موسیقی"`, high-contrast focus ring (`focus:ring-2 focus:ring-cyan-500`).

---

### 2.2 `<MovieCard />` & `<MovieDownloadMatrix />`
- **Props**:
  - `item: MediaItem`: Media item entity.
  - `onPlayStream: (streamUrl: string, title: string) => void`: Video modal trigger.
- **Visual Design**:
  - 2:3 vertical poster card with smooth hover scale (`scale-[1.02]`).
  - LTR isolation on release specs: Badges for resolution (`1080p`, `4K`), codecs (`x265`, `10bit`), and file size (`1.8 GB`) strictly carry `dir="ltr"` and `unicode-bidi: isolate`.
  - Audio specification rendered with localized Persian tag (`دوبله فارسی`, `زیرنویس چسبیده`, `زبان اصلی`).
- **Download Action**:
  - Direct CDN link rendered as `<a href={download_url} download rel="noopener noreferrer">`.
  - Copy link action button with icon toggle (`Copy` -> `Checkmark`) for 2 seconds.

---

### 2.3 `<GameCard />` & `<GamePartList />`
- **Props**:
  - `item: MediaItem`: Game release data.
  - `onCopyAll: (parts: GamePartLink[]) => void`: Batch clipboard exporter.
- **Archive Password Pill**:
  - Displayed in high-visibility pill (`bg-zinc-800 border-zinc-700 font-mono text-cyan-400 dir="ltr"`).
  - Single-click copy action with instant toast confirmation (`رمز کپی شد`).
- **Batch Export ("Copy All Links")**:
  - Copies all part URLs formatted as `URL1\nURL2\nURL3` for download managers (IDM, JDownloader, aria2).
  - Triggers non-intrusive toast notification: `"لینک تمام پارت‌ها کپی شد"`.
- **Missing Parts Alert**:
  - If `has_missing_parts == true`, renders an amber warning banner: `"توجه: پارت‌های شماره X یافت نشدند."`

---

### 2.4 `<MusicCard />`
- **Props**:
  - `item: MediaItem`: Discovered music track.
  - `isCurrentTrack: boolean`: True if this card's audio is currently loaded in the global player.
  - `isPlaying: boolean`: True if currently playing.
  - `onTogglePlay: (track: MusicTrack) => void`: Audition trigger.
- **Controls**:
  - Inline circular play/pause button overlaid on cover artwork or beside track title.
  - Download badges for `320kbps` and `128kbps` with file sizes.
  - If `stream_url == null`, play button renders disabled with tooltip: `"پیش‌نمایش آنلاین در دسترس نیست"`.

---

### 2.5 `<GlobalAudioPlayer />`
- **Props**:
  - Singleton component mounted at the root level.
- **State**:
  - `track: MusicTrack | null`
  - `isPlaying: boolean`
  - `currentTime: number`
  - `duration: number`
  - `volume: number` (persisted to `localStorage["player_volume"]`)
- **Behavior**:
  - Slides up as a fixed bottom bar when a track starts playing.
  - Single-instance guarantee: playing any track pauses and unloads any previously playing audio.
  - Scrubber bar allows seeking anywhere in the track buffer.

---

## 3. Keyboard Shortcuts Contract

| Key Combination | Scope | Action |
|-----------------|-------|--------|
| `/` or `Ctrl+K` / `Cmd+K` | Global | Focus and select search input |
| `Escape` | Global | Close modals, dismiss drawers, or blur search bar |
| `Space` / `K` | Audio Player focused | Toggle play / pause |
| `Tab` / `Shift+Tab` | Global | Standard sequential focus navigation across interactive controls |

---

## 4. Typography & Directionality Tokens

| Token | Class / CSS | Purpose |
|-------|-------------|---------|
| Persian Primary | `font-sans` (`Vazirmatn`) | Body text, Persian titles, descriptions, status messages |
| Technical Monospace | `font-mono` (`dir="ltr" unicode-bidi: isolate`) | Filenames, part labels, codecs, resolutions, passwords, URLs |
| Reading Direction | `dir="rtl"` (app root) | Right-to-Left document layout |
| Logical Spacing | `ms-*`, `me-*`, `ps-*`, `pe-*` | Symmetric padding and margins |
