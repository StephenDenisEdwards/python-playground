# Python Playground — for C# developers

A set of unit tests that demonstrate Python's key features. Each test is small,
self-contained, and documented with comments that draw analogies to C#.

## Why tests?
Tests are the easiest way to "run a code snippet" in Python: every assertion
acts as a live demonstration that the feature behaves as described. You can
execute them all at once or pick a single one to step through in a debugger.

## Setup (one time)

From `C:\Users\steph\source\repos\python-playground`:

```powershell
# 1. Create an isolated virtual environment (like a per-project NuGet cache)
python -m venv .venv

# 2. Activate it (PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies (pytest, pytest-asyncio, numpy, setuptools)
pip install -r requirements.txt
```

## Optional: build the native C extension (§12)

`test_07_async.py` §12 demonstrates a hand-written CPython C extension that
releases the GIL (the same technique numpy uses). It must be **compiled** before
that test will run — it requires a C compiler (on Windows, the **MSVC "Desktop
development with C++"** workload; `setuptools` locates it automatically, so no
Developer Command Prompt is needed):

```powershell
cd native
..\.venv\Scripts\python.exe setup.py build_ext --inplace
cd ..
```

If you skip this step, that single test is **skipped** (not failed) — every other
test runs normally. The compiled binary is git-ignored, so each clone builds its
own.

## Running the tests

```powershell
# Run everything
pytest

# Run a single file
pytest tests/test_01_syntax_basics.py

# Run a single test by name
pytest tests/test_03_object_model.py::test_dataclass_is_like_a_record

# Run tests matching a keyword
pytest -k "duck"

# Show print() output (pytest captures it by default)
pytest -s
```

## Layout

| File | Topic | C# analogue |
|------|-------|-------------|
| `test_01_syntax_basics.py` | Indentation, naming, f-strings, truthiness, `None`, unpacking | `null`, `$"..."` |
| `test_02_type_system.py`   | Dynamic typing, type hints, duck typing, `Protocol`         | `dynamic`, structural typing |
| `test_03_object_model.py`  | Classes, `self`, dunders, `@dataclass`, properties, MRO     | `record`, `IDisposable` |
| `test_04_functional_idioms.py` | Comprehensions, generators, lambdas, decorators         | LINQ, `IEnumerable`, attributes |
| `test_05_context_managers.py`  | `with`, `__enter__`/`__exit__`, `contextlib`             | `using` |
| `test_06_collections_stdlib.py` | `defaultdict`, `Counter`, `deque`, `itertools`, `pathlib` | `Dictionary`, `Path` |
| `test_07_async.py`         | `async`/`await`, `asyncio.gather`                            | `Task.WhenAll` |
| `test_08_gotchas.py`       | Mutable defaults, closure binding, `==` vs `is`, no overloads | various traps |
