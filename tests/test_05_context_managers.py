"""
Context managers ≡ C#'s 'using' statement.

In C#:
    using (var stream = File.OpenRead(path)) { ... }    // calls Dispose() on exit

In Python:
    with open(path) as stream:                          # calls __exit__ on exit
        ...

A context manager is any object that defines __enter__ and __exit__.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. The built-in case: opening a file
# ---------------------------------------------------------------------------
# 'open' returns a file object that closes itself on __exit__ — even if the
# block raises an exception.

def test_with_open_closes_the_file() -> None:
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("hello")
        path = f.name

    # Re-open and read it.
    with open(path, "r") as f:
        content = f.read()
    assert content == "hello"

    Path(path).unlink()       # cleanup


# ---------------------------------------------------------------------------
# 2. Writing your own context manager (class form)
# ---------------------------------------------------------------------------
# Implement __enter__ and __exit__. Compare to C#'s IDisposable.Dispose().

class Timer:
    """Records elapsed time across a `with` block."""

    def __enter__(self) -> "Timer":
        import time
        self.start = time.perf_counter()
        return self                              # the `as t:` value comes from here

    def __exit__(self, exc_type, exc, tb) -> None:
        import time
        self.elapsed = time.perf_counter() - self.start
        # Returning False (or None) lets exceptions propagate (the usual case).
        # Returning True would *suppress* an exception — be careful.

def test_class_based_context_manager() -> None:
    with Timer() as t:
        sum(range(1000))
    assert t.elapsed >= 0


# ---------------------------------------------------------------------------
# 3. Writing your own context manager (generator form)
# ---------------------------------------------------------------------------
# contextlib.contextmanager turns a generator function into a context manager.
# Code BEFORE `yield` runs on entry; code AFTER `yield` runs on exit.

@contextmanager
def temporary_attribute(obj, name: str, value):
    """Temporarily set obj.name = value, restoring the old value on exit."""
    sentinel = object()
    previous = getattr(obj, name, sentinel)
    setattr(obj, name, value)
    try:
        yield value
    finally:
        # Always restore, even if the body raised.
        if previous is sentinel:
            delattr(obj, name)
        else:
            setattr(obj, name, previous)

class Config:
    pass

def test_generator_based_context_manager() -> None:
    cfg = Config()
    cfg.debug = False
    with temporary_attribute(cfg, "debug", True) as v:
        assert v is True
        assert cfg.debug is True
    assert cfg.debug is False           # restored


# ---------------------------------------------------------------------------
# 4. Exception safety
# ---------------------------------------------------------------------------
# __exit__ runs even if the body raises. Use this for cleanup that must happen
# (closing connections, releasing locks).

class TrackedResource:
    def __init__(self) -> None:
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True

def test_context_manager_runs_on_exception() -> None:
    import pytest
    resource = TrackedResource()
    with pytest.raises(RuntimeError):
        with resource:
            raise RuntimeError("boom")
    assert resource.closed is True       # __exit__ still ran
