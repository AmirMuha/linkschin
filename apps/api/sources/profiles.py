"""Declarative source profile configuration loader and validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import yaml

from models import Category, SourceConfig

DEFAULT_PROFILES_PATH = Path(__file__).resolve().parent / "profiles.yaml"

# parser name -> plugin class. Populated by sources/__init__.py registering each
# plugin it owns, so a profile can only name a parser that genuinely exists. A
# hand-kept list of names could drift from reality and let a profile resolve to a
# name with no implementation behind it -- the "registers but returns nothing" bug
# FR-023 forbids.
PARSER_REGISTRY: dict[str, Any] = {}

# Shapes handled by the shared BaseMoviePlugin parser rather than a dedicated module.
# Several profiles may share one parser (FR-022): a site whose shape is already
# supported is registered by configuration alone, with no new code.
SHARED_PARSER_NAMES: frozenset[str] = frozenset({
    "html_wordpress_list",
    "html_search_card",
})


def register_parser(name: str, parser_cls: Any) -> None:
    """Register a parser implementation by name."""
    PARSER_REGISTRY[name] = parser_cls


def get_parser(name: str) -> Any:
    """Retrieve a parser class by name, or None when nothing is registered under it."""
    return PARSER_REGISTRY.get(name)


def known_parser_names() -> set[str]:
    """Every name a profile may legally reference."""
    return set(PARSER_REGISTRY) | SHARED_PARSER_NAMES


@dataclass(slots=True)
class SourceProfile:
    """Declarative source definition from profiles.yaml."""
    id: str
    name: str
    category: Category
    addresses: list[str]
    provides_downloads: bool = True
    parser: str = ""
    enabled: bool = True

    def to_source_config(self) -> SourceConfig:
        return SourceConfig(
            id=self.id,
            name=self.name,
            category=self.category,
            base_urls=list(self.addresses),
            enabled=self.enabled,
            provides_downloads=self.provides_downloads,
        )


def _validate_address(source_id: str, address: str) -> str:
    if not isinstance(address, str) or not address.strip():
        raise ValueError(f"Invalid empty address for source '{source_id}'")
    parsed = urlparse(address.strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid address '{address}' for source '{source_id}': must be absolute http/https URL with host")
    return address.strip()


def load_profiles(path: Path | str | None = None) -> list[SourceProfile]:
    """
    Load and validate source profiles from YAML file.
    Rejects malformed addresses and unknown parsers with descriptive errors.
    """
    p = Path(path) if path else DEFAULT_PROFILES_PATH
    if not p.exists():
        return []

    content = p.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if not data or not isinstance(data, dict):
        return []

    raw_sources = data.get("sources", [])
    if not isinstance(raw_sources, list):
        return []

    profiles: list[SourceProfile] = []
    for raw in raw_sources:
        if not isinstance(raw, dict):
            continue

        source_id = str(raw.get("id", "")).strip()
        if not source_id:
            raise ValueError("Source definition missing required 'id'")

        name = str(raw.get("name", "")).strip() or source_id

        cat_raw = raw.get("category", "movies")
        try:
            category = Category(cat_raw)
        except ValueError:
            raise ValueError(f"Invalid category '{cat_raw}' for source '{source_id}'")

        addresses_raw = raw.get("addresses")
        if not addresses_raw or not isinstance(addresses_raw, list):
            raise ValueError(f"Source '{source_id}' must have a non-empty 'addresses' list")

        validated_addresses = [_validate_address(source_id, addr) for addr in addresses_raw]

        parser_name = str(raw.get("parser", "")).strip()
        if not parser_name or parser_name not in known_parser_names():
            raise ValueError(
                f"Unknown parser '{parser_name}' for source '{source_id}': "
                f"no implementation is registered under that name"
            )

        provides_downloads = bool(raw.get("provides_downloads", True))
        enabled = bool(raw.get("enabled", True))

        profiles.append(
            SourceProfile(
                id=source_id,
                name=name,
                category=category,
                addresses=validated_addresses,
                provides_downloads=provides_downloads,
                parser=parser_name,
                enabled=enabled,
            )
        )

    return profiles
