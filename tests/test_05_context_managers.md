# Context Managers — for C# Developers

Companion notes to [test_05_context_managers.py](test_05_context_managers.py).

Context managers are Python's answer to C#'s `using` statement. The whole purpose: **guarantee cleanup**, even if the code inside throws.

```csharp
// C#
using (var stream = File.OpenRead(path)) {
    // ... use stream ...
}   // Dispose() called here, even on exception
```

```python
# Python
with open(path) as stream:
    # ... use stream ...
# __exit__ called here, even on exception
```

A **context manager** is any object that implements two methods: `__enter__` and `__exit__`. The `with` statement is the syntax that invokes them.

---

## 1. The built-in case: `open`

```python
with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
    f.write("hello")
    path = f.name

with open(path, "r") as f:
    content = f.read()
```

The `as f` part receives whatever `__enter__` returned. On exit (normal or via exception), `__exit__` is called and the file is closed. **Always use `with` for file I/O** — leaving files open is a portability hazard (especially on Windows, which locks open files).

This is the analogue of `using var stream = File.OpenRead(path);` in C# 8+ (or the bracketed `using (...)` form before that).

---

## 2. Writing your own — class form

Implement `__enter__` and `__exit__`. This is the direct analogue of implementing `IDisposable.Dispose()`, except you also get an *entry* hook:

```python
class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self                           # this is what 'as t:' receives

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self.start
```

Usage:

```python
with Timer() as t:
    sum(range(1000))
print(t.elapsed)
```

### The three exception parameters

`__exit__(exc_type, exc, tb)` is called with three arguments describing whether the `with` block exited normally or via an exception:

| Exit reason | `exc_type` | `exc` | `tb` |
|---|---|---|---|
| Normal exit | `None` | `None` | `None` |
| Exception raised | the exception **class** | the exception **instance** | the traceback object |

### Return value of `__exit__`

| Return | Behavior | C# parallel |
|---|---|---|
| `None` / `False` | Exception (if any) propagates normally | normal `finally` behavior |
| `True` | **Suppresses** the exception | (no parallel — C#'s `using` cannot swallow exceptions) |

Returning `True` to swallow exceptions is rare and dangerous — almost always return `None`.

---

## 3. Writing your own — generator form (preferred for one-offs)

For small context managers, writing a class is overkill. `contextlib.contextmanager` lets you write one as a generator function. **Everything before `yield`** is the entry; **everything after** is the exit:

```python
from contextlib import contextmanager

@contextmanager
def temporary_attribute(obj, name, value):
    sentinel = object()
    previous = getattr(obj, name, sentinel)
    setattr(obj, name, value)
    try:
        yield value                            # the 'as ...' value
    finally:
        if previous is sentinel:
            delattr(obj, name)
        else:
            setattr(obj, name, previous)
```

Usage:

```python
with temporary_attribute(cfg, "debug", True) as v:
    # cfg.debug is True for this block
    ...
# cfg.debug is restored, even if the block raised
```

**Always use `try`/`finally`** inside a `@contextmanager` generator. The cleanup code in the `finally` clause is what runs on exception — without it, an exception inside the `with` block would skip your cleanup entirely.

Why `sentinel = object()` instead of `None`? Because the attribute might genuinely have been `None` before — using a unique sentinel object lets you distinguish "attribute didn't exist" from "attribute was `None`."

---

## 4. Exception safety

The headline guarantee: **`__exit__` runs even if the body raises.**

```python
class TrackedResource:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self.closed = True

resource = TrackedResource()
with pytest.raises(RuntimeError):
    with resource:
        raise RuntimeError("boom")
assert resource.closed is True       # cleanup ran
```

This is the entire point of context managers — like C#'s `using`, you can write the cleanup once at the top of a block and trust it'll run.

---

## Common context managers in the wild

| Use case | Context manager |
|---|---|
| File I/O | `open(path, mode)` |
| Locks | `with lock:` (re-entrant lock acquire/release) |
| Database transactions | `with conn:` / `with conn.cursor() as cur:` |
| Temporary directories | `tempfile.TemporaryDirectory()` |
| Suppressing exceptions | `contextlib.suppress(FileNotFoundError)` |
| Redirecting stdout/stderr | `contextlib.redirect_stdout(stream)` |
| Changing the working dir | `contextlib.chdir(path)` (Python 3.11+) |
| Combining several at once | `contextlib.ExitStack` |

`ExitStack` deserves a callout: when the number of context managers is dynamic (you don't know how many files you'll open until runtime), you'd otherwise have arbitrarily nested `with` blocks. `ExitStack` lets you push them onto a stack and exits them all in reverse order:

```python
with contextlib.ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
    # all `files` are closed when the with block exits
```

---

## Quick reference

| C# | Python |
|---|---|
| `IDisposable.Dispose()` | `__exit__(self, exc_type, exc, tb)` |
| (no entry hook) | `__enter__(self)` (returns the `as` value) |
| `using (var x = Foo()) { ... }` | `with Foo() as x:` |
| `using var x = Foo();` (C# 8+) | `with Foo() as x:` |
| Multiple `using`s | `with a() as A, b() as B:` |
| (no equivalent) | `@contextmanager` generator form |
| (no equivalent) | dynamic stack: `contextlib.ExitStack` |
| `try/finally` for cleanup | put cleanup in `__exit__` or `finally:` block of `@contextmanager` |
