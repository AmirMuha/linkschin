# Iranian Multi-Media Direct Link Aggregator (Monorepo)

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
- Python >= 3.11 with [`uv`](https://docs.astral.sh/uv/)

### Installation
```bash
# Install Turborepo and workspace dependencies
pnpm install

# Setup Python virtualenv for the API service
cd apps/api && uv sync
```

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
