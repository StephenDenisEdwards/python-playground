"""
The gotchas that bite C# developers.

Each test demonstrates a trap and then shows the idiomatic fix.
"""

import pytest


# ---------------------------------------------------------------------------
# 1. Mutable default arguments are evaluated ONCE, at function-def time
# ---------------------------------------------------------------------------
# This is the single most-cited Python gotcha. The default value object
# is created when the function is defined, and the SAME object is reused
# on every call where the caller omits the argument.

def append_buggy(item, target=[]):     # noqa: B006 — deliberately buggy
    target.append(item)
    return target

def test_mutable_default_argument_bug() -> None:
    a = append_buggy(1)
    b = append_buggy(2)
    # Surprise! Both calls shared the SAME default list.
    assert a == [1, 2]
    assert b == [1, 2]
    assert a is b              # same list object


def append_fixed(item, target=None):
    if target is None:
        target = []            # build a fresh list per call
    target.append(item)
    return target

def test_mutable_default_argument_fix() -> None:
    a = append_fixed(1)
    b = append_fixed(2)
    assert a == [1]
    assert b == [2]
    assert a is not b


# ---------------------------------------------------------------------------
# 2. Late binding in closures (the for-loop lambda trap)
# ---------------------------------------------------------------------------
# Closures capture the VARIABLE, not the value. By the time you call the
# lambdas, the loop variable has its final value. (C# fixed this for
# 'foreach' in C# 5, but it's still true for the classic 'for' loop.)

def test_closure_captures_variable_not_value() -> None:
    funcs = [lambda: i for i in range(3)]
    # Every closure sees the same 'i', which ended at 2.
    assert [f() for f in funcs] == [2, 2, 2]


def test_closure_capture_fix_via_default_arg() -> None:
    # The default-argument trick FREEZES the value at definition time.
    funcs = [lambda i=i: i for i in range(3)]
    assert [f() for f in funcs] == [0, 1, 2]


# ---------------------------------------------------------------------------
# 3. == vs is
# ---------------------------------------------------------------------------
# ==  : value equality        (calls __eq__,  like C# Equals)
# is  : reference identity    (compares object identity,  like C# ReferenceEquals)
# Use 'is' only for None, True, False, and other true singletons.

def test_equality_vs_identity() -> None:
    a = [1, 2, 3]
    b = [1, 2, 3]
    c = a
    assert a == b                  # same value
    assert a is not b              # different objects
    assert a is c                  # same object

    # SMALL int cache: CPython caches -5..256, so 'is' may *appear* to work
    # for small ints. Don't rely on this — it's an implementation detail.
    x = 256
    y = 256
    assert x is y                  # true today, not guaranteed by the language


# ---------------------------------------------------------------------------
# 4. No method overloading by signature
# ---------------------------------------------------------------------------
# In C# you can have:
#   int Foo(int a)         { ... }
#   int Foo(int a, int b)  { ... }
# In Python the second definition simply replaces the first.

class Calculator:
    def add(self, a):                  # this definition is overwritten...
        return a
    def add(self, a, b=0, c=0):        # ...by this one. The earlier 'add' is gone.  # noqa: F811
        return a + b + c

def test_no_overloading_use_defaults_or_args() -> None:
    calc = Calculator()
    assert calc.add(1) == 1
    assert calc.add(1, 2) == 3
    assert calc.add(1, 2, 3) == 6
    with pytest.raises(TypeError):
        calc.add()                     # original zero-arg version is GONE


# functools.singledispatch is the closest thing to type-based overloading.
from functools import singledispatch

@singledispatch
def describe(value) -> str:
    return f"unknown: {value!r}"

@describe.register
def _(value: int) -> str:
    return f"int: {value}"

@describe.register
def _(value: str) -> str:
    return f"str: {value!r}"

def test_singledispatch_emulates_overloading() -> None:
    assert describe(42) == "int: 42"
    assert describe("hi") == "str: 'hi'"
    assert describe([1, 2]) == "unknown: [1, 2]"


# ---------------------------------------------------------------------------
# 5. Integer division
# ---------------------------------------------------------------------------
# /  always returns a float (since Python 3).
# // is floor division, returning the same type as its operands.

def test_division_operators() -> None:
    assert 7 / 2 == 3.5            # NOT 3, unlike int / int in C#
    assert 7 // 2 == 3
    assert 7 % 2 == 1


# ---------------------------------------------------------------------------
# 6. Mutable vs immutable arguments
# ---------------------------------------------------------------------------
# Python passes references by value (like C#: 'object' parameters).
# Reassigning the parameter inside a function doesn't affect the caller,
# but MUTATING the object does.

def reassign(lst):
    lst = [99]                     # rebinds local name only

def mutate(lst):
    lst.append(99)                 # mutates the caller's object

def test_reassignment_vs_mutation() -> None:
    a = [1, 2, 3]
    reassign(a)
    assert a == [1, 2, 3]          # unchanged

    mutate(a)
    assert a == [1, 2, 3, 99]      # mutated in place
