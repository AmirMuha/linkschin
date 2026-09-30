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
import tests.test_movies_scrapers as tmov
import tests.test_music_scrapers as tmu
import tests.test_reference_sources as tref
import tests.test_source_kind as tsk
import tests.test_sources_config as ts
import tests.test_streaming as tst
import tests.test_worker as tw

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class MonkeyPatch:
    def __init__(self):
        self.old_env = {}
        self.old_attrs = []

    def setenv(self, key, val):
        import os
        self.old_env[key] = os.environ.get(key)
        os.environ[key] = val

    def setattr(self, target, name, value):
        self.old_attrs.append((target, name, getattr(target, name)))
        setattr(target, name, value)

    def undo(self):
        import os
        for obj, name, old in self.old_attrs:
            setattr(obj, name, old)
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    print("=" * 60)
    print("Running Iranian Media Aggregator Test Suite (Offline)")
    print("=" * 60)

    # Load every fixture generically: <name>.html -> kwarg <name>.
    # ponytail: glob instead of a hand-kept list; forgot-one is now impossible.
    fix_map = {
        f.stem: f.read_text(encoding="utf-8")
        for f in sorted(FIXTURES_DIR.glob("*.html"))
    }

    modules = [tm, tc, tdb, tg, tmov, tmu, tref, tsk, ts, tst, tw]

    total = 0
    passed = 0
    failed = 0
    skipped = 0

    for mod in modules:
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
                elif p == "tmp_path":
                    import tempfile
                    kwargs[p] = Path(tempfile.mkdtemp())
                elif p == "db_path":
                    import tempfile
                    kwargs[p] = str(Path(tempfile.mkdtemp()) / "t.db")
                elif p.endswith("_html") and p[:-5] in fix_map:
                    kwargs[p] = fix_map[p[:-5]]

            # pytest-parametrized tests can't run in this zero-dep runner;
            # pytest executes them (and the whole suite) normally.
            missing = [p for p in sig.parameters
                       if p not in kwargs and sig.parameters[p].default is inspect.Parameter.empty]
            if missing:
                skipped += 1
                print(f"  ~ {name} (pytest-only: {', '.join(missing)})")
                continue

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
