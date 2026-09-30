"""Declarative source profile configuration loader and validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import yaml

from models import Category, SourceConfig

DEFAULT_PROFILES_PATH = Path(__file__).resolve().parent / "profiles.yaml"

# Registry of known parser names and classes
PARSER_REGISTRY: dict[str, Any] = {}

KNOWN_PARSER_NAMES: set[str] = {
    "uptvs",
    "doostihaa",
    "downloadha",
    "yasdl",
    "popmusic",
    "nex1music",
    "html_wordpress_list",
    "html_search_card",
    "filimo",
    "namava",
    "filmnet",
    "gapfilm",
    "telewebion",
    "aparat",
    "imvbox",
    "danfilo",
    "filmchiin",
    "filmtarin",
    "babakfilm",
    "ndamedia",
    "sarvnema",
    "salamcinema",
    "tiwall",
    "namasha",
    "rubika",
    "digitoon",
    "fam",
}


def register_parser(name: str, parser_cls: Any) -> None:
    """Register a parser implementation by name."""
    PARSER_REGISTRY[name] = parser_cls
    KNOWN_PARSER_NAMES.add(name)


def get_parser(name: str) -> Any:
    """Retrieve a parser class by name."""
    return PARSER_REGISTRY.get(name)


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
        if not parser_name or (parser_name not in KNOWN_PARSER_NAMES and parser_name not in PARSER_REGISTRY):
            raise ValueError(f"Unknown parser '{parser_name}' for source '{source_id}'")

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
