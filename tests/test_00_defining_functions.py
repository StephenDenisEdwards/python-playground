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


# ---------------------------------------------------------------------------
# 9. Shared mutable object: same scenario, but it actually works
# ---------------------------------------------------------------------------
# Above, 'change_msg' tried to "change" a string via reassignment. It can't —
# strings are immutable, and reassigning a parameter only rebinds the LOCAL
# name. Below is the same idea, but with a LIST (mutable). Two functions:
#   * mutate_list   — MUTATES the shared object        -> caller sees it     ✓
#   * replace_list  — REBINDS the local name to a new list -> caller does NOT ✗
# Both functions take the same argument; only the *operation* differs.

def mutate_list(items: list[str]) -> None:
    items.append("STEVE")          # in-place mutation of the SHARED object

def replace_list(items: list[str]) -> None:
    items = ["STEVE"]              # local rebind only — caller unaffected
    assert items == ["STEVE"]      # proves the LOCAL name does point at the new list

def test_shared_mutable_object_visible_via_mutation() -> None:
    caller_list = ["hello"]
    mutate_list(caller_list)
    # Caller sees the change because both names pointed at the SAME list,
    # and .append() modified that object in place.
    assert caller_list == ["hello", "STEVE"]

    # Reset, then try the rebind version
    caller_list = ["hello"]
    replace_list(caller_list)
    # Caller's name still points at the original list. The function just
    # pointed its OWN local name at a new list and threw it away on return.
    assert caller_list == ["hello"]


# ---------------------------------------------------------------------------
# 10. The whole topic in plain English
# ---------------------------------------------------------------------------
# Two lists. That's it.
#
# CANNOT be changed by a function (you must return a new value):
#     int, float, bool, str, tuple, None, frozenset, bytes
#
# CAN be changed by a function (caller sees the change):
#     list, dict, set, bytearray, your own classes (unless frozen)
#
# What "changed by a function" means in code:
#
#     def f(thing):
#         thing.append(1)    # mutating the EXISTING object  -> caller SEES it
#         thing = something  # pointing 'thing' at a NEW object -> caller does NOT
#
# The first line only works if 'thing' is from the second list (mutable).
# The second line NEVER affects the caller, regardless of the type. Ever.
#
# Practical rule, one sentence:
#   If you pass in a list/dict/set/custom object and the function calls a
#   method on it (.append, .pop, d["x"] = ..., obj.attr = ...), the caller
#   sees it. For anything else, return the value.
#
# C# analogy:
#   Mutating a list/dict in Python == calling a method on a C# reference type
#     without 'ref' (e.g. xs.Add(1)). Caller sees the change.
#   Reassigning a parameter in Python has NO C# equivalent — there is no
#     'ref' in Python. To change the caller's variable, return the new value.

# ---- Example A: mutable type + method call -> caller sees it ----------------

def add_to_dict(d: dict[str, int]) -> None:
    d["new_key"] = 99          # mutation via subscript assignment

def test_dict_mutation_visible_to_caller() -> None:
    scores = {"alice": 10}
    add_to_dict(scores)
    assert scores == {"alice": 10, "new_key": 99}


# ---- Example B: mutable type + REBIND -> caller does NOT see it -------------

def replace_dict(d: dict[str, int]) -> None:
    d = {"new_key": 99}        # local rebind, NOT a mutation
    assert d == {"new_key": 99}  # the local name does point at the new dict

def test_dict_rebind_invisible_to_caller() -> None:
    scores = {"alice": 10}
    replace_dict(scores)
    # Caller's 'scores' name still bound to the original dict, untouched.
    assert scores == {"alice": 10}


# ---- Example C: custom class -> mutation works just like list/dict ----------

class Counter:
    def __init__(self) -> None:
        self.value = 0

def bump(c: Counter) -> None:
    c.value += 1              # mutating an ATTRIBUTE on the shared object

def test_custom_object_mutation_visible_to_caller() -> None:
    c = Counter()
    bump(c)
    bump(c)
    assert c.value == 2


# ---- Example D: immutable type -> caller NEVER sees a change ----------------

def try_to_increment(n: int) -> None:
    n += 1                    # rebind in disguise — ints are immutable
    n = 999                   # explicit rebind
    assert n == 999           # local 'n' is 999...

def test_int_cannot_be_changed_by_caller() -> None:
    x = 10
    try_to_increment(x)
    assert x == 10            # ...but caller's x is still 10. Return it instead.


# ---- Example E: the only way to "change" an immutable -> return it ----------

def increment(n: int) -> int:
    return n + 1              # new int, caller does the rebind

def test_immutables_change_by_returning() -> None:
    x = 10
    x = increment(x)          # caller reassigns its own name
    assert x == 11


# ---------------------------------------------------------------------------
# 11. Joining strings: '+', f-strings, and str.join
# ---------------------------------------------------------------------------
# str.join has a famously unintuitive shape:
#     SEPARATOR.join(ITERABLE_OF_STRINGS)
# i.e. the string you call it on is the SEPARATOR, and the argument is the
# iterable to glue together. C# is the other way around:
#     string.Join(separator, items)
#
# Rule of thumb:
#   * Fixed, small number of pieces known at write-time -> use '+' or f-string.
#   * Variable / unknown / large number of pieces       -> use str.join.
#
# The performance reason for join:
#   Strings are immutable. 'result += x' in a loop allocates a NEW string and
#   copies the accumulated content each time — O(n^2) overall. 'sep.join(seq)'
#   does it in a single pass with one allocation. (C# answer: StringBuilder.)

# ---- Example A: '+' and f-strings for simple concatenation ------------------

def test_simple_concatenation_with_plus_and_fstrings() -> None:
    a = "hello"
    b = "STEVE"
    assert a + b == "helloSTEVE"            # '+' just sticks them together
    assert f"{a}{b}" == "helloSTEVE"        # f-string, no separator
    assert f"{a} {b}" == "hello STEVE"      # f-string with a literal space


# ---- Example B: join shines when the count is variable ----------------------

def format_tags(tags: list[str]) -> str:
    return ", ".join(tags)                  # handles empty and single-item lists for free

def test_join_handles_variable_counts() -> None:
    assert format_tags(["python", "testing", "csharp"]) == "python, testing, csharp"
    assert format_tags(["solo"]) == "solo"          # no trailing separator
    assert format_tags([]) == ""                    # empty -> empty string


# ---- Example C: building a CSV row (the canonical join use case) ------------

def test_join_builds_csv_row() -> None:
    fields = ["Ada", "36", "London"]
    assert ",".join(fields) == "Ada,36,London"


# ---- Example D: joining non-strings requires converting first ---------------

def test_join_requires_string_elements() -> None:
    ids = [101, 202, 303]

    # Direct join of ints raises TypeError — unlike C#'s string.Join which
    # would call .ToString() for you.
    import pytest
    with pytest.raises(TypeError):
        ",".join(ids)                       # type: ignore[arg-type]

    # Two idiomatic conversions:
    assert ",".join(str(i) for i in ids) == "101,202,303"   # generator expression
    assert ",".join(map(str, ids)) == "101,202,303"         # map(str, ...)


# ---- Example E: join with '\n' to build multi-line text ---------------------

def test_join_builds_multiline_text() -> None:
    lines = ["def foo():", "    return 42"]
    assert "\n".join(lines) == "def foo():\n    return 42"


# ---- Example F: why join beats += in a loop (the StringBuilder reason) ------

def concat_with_plus(words: list[str]) -> str:
    """O(n^2). Each += allocates a fresh string and copies the accumulator."""
    result = ""
    for w in words:
        result += w
    return result

def concat_with_join(words: list[str]) -> str:
    """O(n). One allocation, one pass. Idiomatic."""
    return "".join(words)

def test_join_and_plus_produce_the_same_result() -> None:
    # Same RESULT — the difference is performance, not correctness.
    # For tiny inputs you'd never notice; for 100k+ pieces it's the difference
    # between instant and unusable.
    words = ["word"] * 1000
    assert concat_with_plus(words) == concat_with_join(words)