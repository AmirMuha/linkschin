"""Standalone test runner requiring zero third-party dependencies."""

import asyncio
import inspect
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tests.test_models as tm
import tests.test_cache as tc
import tests.test_db as tdb
import tests.test_games_scrapers as tg
import tests.test_music_scrapers as tmu
import tests.test_sources_config as ts
import tests.test_streaming as tst
import tests.test_worker as tw

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class MonkeyPatch:
    def __init__(self):
        self.old_env = {}

    def setenv(self, key, val):
        import os
        self.old_env[key] = os.environ.get(key)
        os.environ[key] = val

    def undo(self):
        import os
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    print("=" * 60)
    print("Running Iranian Media Aggregator Test Suite (Offline)")
    print("=" * 60)

    # Load fixtures
    dlha_search = (FIXTURES_DIR / "downloadha_search.html").read_text(encoding="utf-8")
    dlha_item = (FIXTURES_DIR / "downloadha_item.html").read_text(encoding="utf-8")
    pop_search = (FIXTURES_DIR / "popmusic_search.html").read_text(encoding="utf-8")
    pop_item = (FIXTURES_DIR / "popmusic_item.html").read_text(encoding="utf-8")
    nex1_search = (FIXTURES_DIR / "nex1music_search.html").read_text(encoding="utf-8")
    nex1_item = (FIXTURES_DIR / "nex1music_item.html").read_text(encoding="utf-8")

    modules = [
        (tm, {}),
        (tc, {}),
        (tdb, {}),
        (tg, {"downloadha_search_html": dlha_search, "downloadha_item_html": dlha_item}),
        (tmu, {
            "popmusic_search_html": pop_search,
            "popmusic_item_html": pop_item,
            "nex1music_search_html": nex1_search,
            "nex1music_item_html": nex1_item,
        }),
        (ts, {}),
        (tst, {}),
        (tw, {}),
    ]

    total = 0
    passed = 0
    failed = 0

    for mod, fix_map in modules:
        mod_name = mod.__name__.split(".")[-1]
        print(f"\n[{mod_name}]")
        for name, func in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            total += 1
            # Build kwargs based on signature
            sig = inspect.signature(func)
            kwargs = {}
            mp = None
            for p in sig.parameters:
                if p == "monkeypatch":
                    mp = MonkeyPatch()
                    kwargs[p] = mp
                elif p in fix_map:
                    kwargs[p] = fix_map[p]

            try:
                if inspect.iscoroutinefunction(func):
                    asyncio.run(func(**kwargs))
                else:
                    func(**kwargs)
                if mp:
                    mp.undo()
                print(f"  ✓ {name}")
                passed += 1
            except Exception as e:
                if mp:
                    mp.undo()
                print(f"  ✗ {name}: {e}")
                failed += 1

    print("\n" + "=" * 60)
    print(f"SUMMARY: Total={total} | Passed={passed} | Failed={failed}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
