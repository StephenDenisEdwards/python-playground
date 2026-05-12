"""
Python's type system from a C# perspective.

Key shifts:
  - Types attach to *values*, not *variables*.
  - Type hints exist but are NOT enforced at runtime.
  - Interfaces are replaced by *duck typing* and (structurally) by Protocols.
"""

from typing import Protocol


# ---------------------------------------------------------------------------
# 1. Dynamic typing
# ---------------------------------------------------------------------------
# In C#:    int x = 5;          // x is permanently int
# In Python: a name can rebind to any type.

def test_dynamic_typing() -> None:
    x: object = 5
    assert isinstance(x, int)
    x = "five"
    assert isinstance(x, str)
    x = [5]
    assert isinstance(x, list)


# ---------------------------------------------------------------------------
# 2. Type hints — PEP 484
# ---------------------------------------------------------------------------
# Type hints look enforced but the CPython runtime IGNORES them.
# They are checked by external tools: mypy, pyright (used by Pylance/VS Code).
# They show up to readers and IDEs the same way C#'s static types do.

def add(a: int, b: int) -> int:
    return a + b

def test_type_hints_are_not_runtime_enforced() -> None:
    # Calling with strings WORKS at runtime — the hints are just metadata.
    # mypy/pyright would flag this as a static error.
    assert add("foo", "bar") == "foobar"   # type: ignore[arg-type]
    assert add(2, 3) == 5


# ---------------------------------------------------------------------------
# 3. Modern hint syntax (Python 3.10+)
# ---------------------------------------------------------------------------
# Use built-in generic containers and `|` for union types.
#   list[int]            (was: typing.List[int])
#   dict[str, int]
#   int | None           (was: Optional[int] or Union[int, None])

def first_or_none(items: list[int]) -> int | None:
    return items[0] if items else None        # ternary: 'X if cond else Y'

def test_modern_hint_syntax() -> None:
    assert first_or_none([10, 20]) == 10
    assert first_or_none([]) is None


# ---------------------------------------------------------------------------
# 4. Duck typing
# ---------------------------------------------------------------------------
# "If it walks like a duck and quacks like a duck, it's a duck."
# A function doesn't care about the declared type of its argument — only that
# the argument supports the operations it uses.

def total_length(things) -> int:
    # We only require that `things` is iterable and each item has __len__.
    return sum(len(t) for t in things)

def test_duck_typing_accepts_anything_iterable() -> None:
    # All of these work because their elements support len(), and the containers
    # are iterable. There is no IEnumerable<T> / ICollection<T> hierarchy.
    assert total_length(["ab", "cde"]) == 5
    assert total_length(("ab", "cde")) == 5                  # tuple
    assert total_length({"ab", "cde"}) == 5                  # set
    assert total_length(iter(["ab", "cde"])) == 5            # iterator


# ---------------------------------------------------------------------------
# 5. Protocols  ≈ structural interfaces
# ---------------------------------------------------------------------------
# A `Protocol` describes a SHAPE (methods/attributes) that satisfying classes
# must have — but classes do NOT need to declare they implement it. This is
# closest to Go's interfaces or C#'s `dynamic` + reflection, not to C#'s
# nominal `interface`s.

class SupportsArea(Protocol):
    """Anything that has an `area()` method returning a float."""
    def area(self) -> float: ...

class Square:
    # Notice: no 'class Square(SupportsArea):' — duck/structural typing.
    def __init__(self, side: float) -> None:
        self.side = side
    def area(self) -> float:
        return self.side * self.side

class Circle:
    def __init__(self, radius: float) -> None:
        self.radius = radius
    def area(self) -> float:
        return 3.14159 * self.radius ** 2

def total_area(shapes: list[SupportsArea]) -> float:
    return sum(s.area() for s in shapes)

def test_protocol_structural_typing() -> None:
    shapes = [Square(2), Circle(1)]   # Square and Circle have NO common base
    assert round(total_area(shapes), 2) == 7.14


# ---------------------------------------------------------------------------
# 6. isinstance() and the EAFP idiom
# ---------------------------------------------------------------------------
# C# style: check first, then act ("Look Before You Leap").
# Python often prefers EAFP — "Easier to Ask Forgiveness than Permission":
# just try the operation, catch the exception if it fails.

def safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def test_eafp_pattern() -> None:
    assert safe_int("42") == 42
    assert safe_int("not a number") is None
    assert safe_int(None) is None
