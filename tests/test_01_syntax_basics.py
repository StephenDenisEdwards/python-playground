"""
Syntax basics for a C# developer.

Run just this file:
    pytest tests/test_01_syntax_basics.py
"""

# ---------------------------------------------------------------------------
# 1. Indentation as syntax
# ---------------------------------------------------------------------------
# In C# a code block is delimited by braces { }.
# In Python the block is the indented region — no braces, no semicolons.
# Use 4 spaces (NOT tabs); mixing the two will raise IndentationError.

def test_indentation_defines_blocks() -> None:
    total = 0
    for i in range(5):          # 'for i in range(5):' == 'for (int i=0; i<5; i++)'
        total += i              # this line is inside the loop because it's indented
    # this line is OUTSIDE the loop again because the indent dropped
    assert total == 0 + 1 + 2 + 3 + 4


# ---------------------------------------------------------------------------
# 2. Variables: no type declarations, no 'var'
# ---------------------------------------------------------------------------

def test_variables_have_no_declared_type() -> None:
    x = 5                  # int — like 'var x = 5;'
    x = "now I'm a string" # legal! variables are just names bound to objects
    assert isinstance(x, str)


# ---------------------------------------------------------------------------
# 3. Naming conventions
# ---------------------------------------------------------------------------
# C#:        Python:
# PascalCase classes              -> PascalCase classes      (same)
# camelCase  methods / locals     -> snake_case              (different!)
# UPPER_CASE constants            -> UPPER_CASE constants    (same)
# IFoo       interface prefix     -> no 'I' prefix; use Protocol classes

MAX_RETRIES = 3                  # module-level constant (convention only)

def add_numbers(first: int, second: int) -> int:    # snake_case
    return first + second

def test_naming_conventions() -> None:
    assert add_numbers(2, 3) == 5
    assert MAX_RETRIES == 3


# ---------------------------------------------------------------------------
# 4. f-strings ≈ C# interpolated strings  $"hello {name}"
# ---------------------------------------------------------------------------

def test_f_strings() -> None:
    name = "World"
    n = 42
    # f"..."  ≡  $"..."
    greeting = f"Hello, {name}! n+1 = {n + 1}"
    assert greeting == "Hello, World! n+1 = 43"

    # Format specifiers come after a colon, like C#: $"{value:F2}"
    pi = 3.14159
    assert f"{pi:.2f}" == "3.14"


# ---------------------------------------------------------------------------
# 5. None ≈ null
# ---------------------------------------------------------------------------
# Use 'is None' / 'is not None' — NOT '== None'.
# 'is' compares object identity; there is exactly ONE None object, so identity
# is the correct check (and faster, and idiomatic).

def test_none_is_pythons_null() -> None:
    value = None
    assert value is None
    assert value is not 0       # None is NOT the same as 0   (noqa: F632 demo)


# ---------------------------------------------------------------------------
# 6. Truthiness
# ---------------------------------------------------------------------------
# Empty collections, empty strings, 0, 0.0, and None are all 'falsy'.
# Everything else is 'truthy'. Idiomatic Python uses this directly:
#       if my_list:                  (instead of  if (myList.Count > 0))
#       if name:                     (instead of  if (!string.IsNullOrEmpty(name)))

def test_truthiness() -> None:
    assert not []          # empty list  -> falsy
    assert not ""          # empty str   -> falsy
    assert not 0           # zero        -> falsy
    assert not None        # None        -> falsy
    assert [0]             # non-empty list -> truthy (even though it contains 0)
    assert "hello"         # non-empty string -> truthy


# ---------------------------------------------------------------------------
# 7. Tuple unpacking / multiple return values
# ---------------------------------------------------------------------------
# C# uses ValueTuple and deconstruction: (int a, string b) = GetThing();
# Python returns a tuple and assigns positionally.

def min_and_max(values: list[int]) -> tuple[int, int]:
    return min(values), max(values)        # implicit tuple — parens optional

def test_tuple_unpacking() -> None:
    lo, hi = min_and_max([3, 1, 4, 1, 5, 9, 2, 6])
    assert (lo, hi) == (1, 9)

    # Swap without a temp variable
    a, b = 1, 2
    a, b = b, a
    assert (a, b) == (2, 1)

    # Star-unpacking grabs the "rest"
    first, *middle, last = [10, 20, 30, 40, 50]
    assert first == 10
    assert middle == [20, 30, 40]
    assert last == 50


# ---------------------------------------------------------------------------
# 8. Comments and docstrings
# ---------------------------------------------------------------------------
# Single-line:    # like C# //
# Multi-line:     triple-quoted strings, usually used as docstrings (below).
# There is no /* */; multi-line "comments" are just unused string literals.

def greet(name: str) -> str:
    """Return a friendly greeting.

    This triple-quoted string at the top of a function is the *docstring*.
    It's the C# /// <summary> equivalent and is accessible at runtime via
    greet.__doc__ — tools like Sphinx and IDEs render it as help text.
    """
    return f"Hi, {name}"

def test_docstring_is_accessible_at_runtime() -> None:
    assert greet("Stephen") == "Hi, Stephen"
    assert "friendly greeting" in greet.__doc__
