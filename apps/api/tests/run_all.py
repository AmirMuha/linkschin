"""Standalone test runner requiring zero third-party dependencies."""

import asyncio
import inspect
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TESTS_DIR = Path(__file__).resolve().parent


def _discover_modules() -> list:
    """Import every tests/test_*.py, sorted for a stable run order.

    Was a hand-kept import list, which is how a new test file ships as dead code
    the way the 19 005 parsers did: pytest ran them, the offline runner silently
    did not, and neither failure looked like a failure. Same reason the fixture map
    below globs instead of listing.
    """
    import importlib

    found = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        found.append(importlib.import_module(f"tests.{path.stem}"))
    return found

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

    modules = _discover_modules()

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
