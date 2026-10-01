# Linkschin — Iranian Multi-Media Direct Link Aggregator (Monorepo)

A fast, server-rendered multi-media fetcher and aggregator targeting Iranian sources for **Movies, Games, and Music**.
Extracts direct download links, split game archives with extraction passwords, and audio previews without server-side media proxying.

## Repository Structure

Managed with [Turborepo](https://turbo.build/) and `pnpm` workspaces:

```
├── apps/
│   ├── api/          # Python aggregator service, CLI, and FastAPI web routes
│   └── (web/)        # Reserved for upcoming standalone web interface
├── packages/         # Shared libraries (future)
├── package.json      # Monorepo root scripts & dev dependencies
├── pnpm-workspace.yaml
└── turbo.json        # Turborepo task pipeline
```

## Quick Start

### Prerequisites
- Node.js >= 18 and `pnpm` (>= 9)
- Python >= 3.11 (standard `venv` module) and [`poethepoet`](https://poethepoet.org/) for `poe` tasks

### Installation
```bash
# Install Turborepo and workspace dependencies
pnpm install

# Create the API virtualenv and install dependencies
cd apps/api
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

The virtualenv lives at `apps/api/.venv`. Activate it with `source apps/api/.venv/bin/activate`, or call the interpreter directly as `.venv/bin/python`.

### Running Tasks via Turborepo
From the repository root:

```bash
# Run API in development mode with reload
pnpm dev

# Run full test suite across the monorepo
pnpm test

# Run linter / compile check
pnpm lint

# Run CLI smoke check
pnpm check
```

### Running Tasks via poe
With the virtualenv active, run the same tasks from `apps/api`:

```bash
poe dev         # API with reload on 127.0.0.1:8000
poe test        # pytest suite
poe test-offline  # standalone offline runner
poe lint        # byte-compile check
poe check       # CLI smoke check
```

List every available task with `poe --help`.
