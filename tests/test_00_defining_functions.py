"""
Defining functions with 'def' — for a C# developer.

Run just this file:
    pytest tests/test_00_defining_functions.py
"""

# ---------------------------------------------------------------------------
# 1. Basic 'def' syntax
# ---------------------------------------------------------------------------
# 'def' introduces a function, the way 'public void' / 'public int' / etc.
# would in C#. There's no return-type keyword in the signature — instead the
# optional '-> Type' annotation goes at the end, and the colon ends the line.
#
#   def name(param1: Type, param2: Type = default) -> ReturnType:
#       <indented body>
#
# Notes for a C# eye:
#   * Type annotations are *hints* — not enforced at runtime.
#   * No access modifiers. A leading underscore ('_helper') is the only
#     convention to mark "internal".
#   * No method overloading by signature. One name == one function.
#     Use default values or *args / **kwargs instead.

def add(a: int, b: int) -> int:
    """A plain function: params, return type, and a returned value."""
    return a + b

def test_def_basic_function_with_return() -> None:
    # Calling it looks just like C#
    assert add(2, 3) == 5


# ---------------------------------------------------------------------------
# 2. Default parameter values
# ---------------------------------------------------------------------------

def shout(message: str, times: int = 1) -> str:
    """'times: int = 1' gives a *default value*, like C#'s optional params."""
    return (message + "!") * times

def test_def_default_parameter_values() -> None:
    assert shout("hi") == "hi!"            # uses default times=1
    assert shout("hi", 3) == "hi!hi!hi!"   # positional override


# ---------------------------------------------------------------------------
# 3. Keyword arguments
# ---------------------------------------------------------------------------

def describe(name: str, age: int, city: str) -> str:
    return f"{name}, {age}, from {city}"

def test_def_keyword_arguments() -> None:
    # In C# this is 'named arguments': Describe(name: "Ada", age: 36, city: "London")
    # In Python they're called 'keyword arguments'. Order doesn't matter when named.
    assert describe(age=36, city="London", name="Ada") == "Ada, 36, from London"


# ---------------------------------------------------------------------------
# 4. No 'return' -> implicit None
# ---------------------------------------------------------------------------

def log_silently(message: str) -> None:
    """No 'return' statement -> the function implicitly returns None."""
    _ = message  # pretend to do something

def test_def_no_return_yields_none() -> None:
    # Unlike C# 'void', the absence of return doesn't mean "no value":
    # it means "the value None". You can capture it; it's just usually useless.
    result = log_silently("hello")
    assert result is None


# ---------------------------------------------------------------------------
# 5. Functions are first-class objects
# ---------------------------------------------------------------------------

def test_def_functions_are_first_class_objects() -> None:
    # A function name is just a variable bound to a callable object —
    # similar to a C# delegate or Func<int,int,int>, but without the type ceremony.
    operation = add               # 'operation' now refers to the same function
    assert operation(4, 5) == 9
    assert callable(operation)    # built-in test for "can this be called?"


# ---------------------------------------------------------------------------
# 6. Parameter passing: "pass by object reference"
# ---------------------------------------------------------------------------
# Python has neither 'ref' nor 'out'. Arguments are passed by *object
# reference*: the parameter inside the function becomes a new local name
# bound to the same object the caller passed in.
#
#   MUTATE the object     -> caller sees it    (like passing a C# ref type)
#   REASSIGN the name     -> caller does NOT   (no equivalent of C# 'ref')

def append_item(items: list[int], value: int) -> None:
    items.append(value)           # mutates the list the caller still holds

def try_to_replace(items: list[int]) -> list[int]:
    items = [99, 99, 99]          # rebinds local name only — caller unaffected
    return items                  # proves the local 'items' is the new list

def test_def_pass_by_object_reference_mutate_vs_reassign() -> None:
    original = [1, 2, 3]

    append_item(original, 4)      # caller's list IS mutated
    assert original == [1, 2, 3, 4]

    inside = try_to_replace(original)   # caller's list is NOT replaced
    assert inside == [99, 99, 99]       # inside the function the name was rebound
    assert original == [1, 2, 3, 4]     # but the caller's variable is unchanged

    # Immutable types (int, str, tuple) appear "pass by value" only because
    # you cannot mutate them — there is no in-place operation to observe.
    def try_to_increment(n: int) -> None:
        n += 1                    # rebinds local 'n' to a new int object
    x = 10
    try_to_increment(x)
    assert x == 10                # caller's int is untouched


# ---------------------------------------------------------------------------
# 7. The mutable default argument trap
# ---------------------------------------------------------------------------
# Default values are evaluated ONCE, when the 'def' statement runs — NOT on
# every call. If the default is a mutable object (list, dict, set), every
# call that uses the default shares the SAME object. This is Python's most
# famous foot-gun and has no C# equivalent.

def buggy_append(value: int, bucket: list[int] = []) -> list[int]:
    """DO NOT WRITE THIS. The default list is created once and reused."""
    bucket.append(value)
    return bucket

def safe_append(value: int, bucket: list[int] | None = None) -> list[int]:
    """The idiomatic fix: use None as the sentinel and build a fresh list."""
    if bucket is None:
        bucket = []
    bucket.append(value)
    return bucket

def test_def_mutable_default_argument_trap() -> None:
    # The buggy version "remembers" values across calls — almost never what you want.
    assert buggy_append(1) == [1]
    assert buggy_append(2) == [1, 2]      # surprise! the default list persisted
    assert buggy_append(3) == [1, 2, 3]

    # The safe pattern starts fresh each call.
    assert safe_append(1) == [1]
    assert safe_append(2) == [2]
    assert safe_append(3) == [3]


# ---------------------------------------------------------------------------
# 8. *args and **kwargs: variadic parameters
# ---------------------------------------------------------------------------
# '*args'   collects extra POSITIONAL args into a tuple   (C#: params T[])
# '**kwargs' collects extra KEYWORD args into a dict      (no C# equivalent)

def sum_all(*args: int) -> int:
    """'*args' is a tuple of whatever positional args the caller passed."""
    total = 0
    for n in args:
        total += n
    return total

def make_record(**kwargs: object) -> dict[str, object]:
    """'**kwargs' is a dict mapping keyword-arg name -> value."""
    return dict(kwargs)

def test_def_args_and_kwargs() -> None:
    # *args: variable number of positional arguments
    assert sum_all() == 0
    assert sum_all(1, 2, 3) == 6
    # You can also "spread" an existing iterable into a call with *:
    nums = [10, 20, 30]
    assert sum_all(*nums) == 60

    # **kwargs: variable number of keyword arguments
    record = make_record(name="Ada", age=36)
    assert record == {"name": "Ada", "age": 36}

    # And spread a dict into keyword args with **:
    payload = {"city": "London", "country": "UK"}
    assert make_record(**payload) == {"city": "London", "country": "UK"}
