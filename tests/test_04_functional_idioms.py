"""
Functional / LINQ-style idioms.

In C# you'd reach for LINQ:
    var doubled = items.Where(x => x > 0).Select(x => x * 2).ToList();

In Python the same intent is expressed with:
    1. Comprehensions       (preferred for simple cases)
    2. Generator expressions (lazy, like LINQ's IEnumerable)
    3. map() / filter()      (less idiomatic; comprehensions are preferred)
    4. functools / itertools (for more advanced operations)
"""

from functools import reduce, lru_cache


# ---------------------------------------------------------------------------
# 1. List comprehensions   ≈ LINQ Select / Where
# ---------------------------------------------------------------------------
# Syntax:   [ <expression> for <var> in <iterable> if <condition> ]

def test_list_comprehension_basic() -> None:
    numbers = [1, 2, 3, 4, 5]
    # LINQ: numbers.Select(n => n * n).ToList()
    squares = [n * n for n in numbers]
    assert squares == [1, 4, 9, 16, 25]

    # LINQ: numbers.Where(n => n % 2 == 0).Select(n => n * n).ToList()
    even_squares = [n * n for n in numbers if n % 2 == 0]
    assert even_squares == [4, 16]


# ---------------------------------------------------------------------------
# 2. Dict and set comprehensions
# ---------------------------------------------------------------------------

def test_dict_and_set_comprehensions() -> None:
    words = ["apple", "banana", "cherry"]

    # dict comp:  { key_expr: value_expr for ... }
    lengths = {w: len(w) for w in words}
    assert lengths == {"apple": 5, "banana": 6, "cherry": 6}

    # set comp:  { expr for ... }  — note braces with no colon
    distinct_lengths = {len(w) for w in words}
    assert distinct_lengths == {5, 6}


# ---------------------------------------------------------------------------
# 3. Generators — lazy iteration, ≈ IEnumerable<T> + yield return
# ---------------------------------------------------------------------------

def fibonacci():                                # no 'yield return' — just 'yield'
    """Yields Fibonacci numbers forever. Memory cost: O(1)."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

def test_generator_function() -> None:
    gen = fibonacci()                           # function returns a generator
    first10 = [next(gen) for _ in range(10)]    # `_` is a throwaway name, like 'discard'
    assert first10 == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_generator_expression() -> None:
    # Parentheses instead of brackets create a generator — same syntax otherwise.
    # This is the lazy form of a list comprehension.
    gen = (n * n for n in range(1_000_000))
    # Nothing has been computed yet. Now consume the first 3:
    from itertools import islice
    assert list(islice(gen, 3)) == [0, 1, 4]


# ---------------------------------------------------------------------------
# 4. Lambdas
# ---------------------------------------------------------------------------
# C#:    Func<int, int> doubleIt = x => x * 2;
# Python: doubleIt = lambda x: x * 2

def test_lambda() -> None:
    double_it = lambda x: x * 2          # noqa: E731 — pedagogical; normally use 'def'
    assert double_it(21) == 42

    # Lambdas are limited to one expression; use 'def' for anything longer.
    pairs = [("b", 2), ("a", 1), ("c", 3)]
    pairs.sort(key=lambda pair: pair[0])
    assert pairs == [("a", 1), ("b", 2), ("c", 3)]


# ---------------------------------------------------------------------------
# 5. Higher-order functions: map / filter / reduce
# ---------------------------------------------------------------------------
# These exist but Pythonistas prefer comprehensions for readability.
# reduce() is in functools (it was moved out of builtins for that reason).

def test_map_filter_reduce() -> None:
    numbers = [1, 2, 3, 4, 5]
    assert list(map(lambda x: x * 2, numbers)) == [2, 4, 6, 8, 10]
    assert list(filter(lambda x: x > 2, numbers)) == [3, 4, 5]
    assert reduce(lambda acc, x: acc + x, numbers, 0) == 15   # like Aggregate(0, (a,b)=>a+b)


# ---------------------------------------------------------------------------
# 6. Decorators — like C# attributes, but they actually transform the function
# ---------------------------------------------------------------------------
# A decorator is a function that takes a function and returns a (usually new)
# function. The @name syntax is sugar for:
#     greet = log_calls(greet)

call_log: list[str] = []

def log_calls(func):
    """A simple decorator that records each invocation."""
    def wrapper(*args, **kwargs):           # *args/**kwargs forward anything
        call_log.append(func.__name__)
        return func(*args, **kwargs)
    return wrapper

@log_calls
def add(a: int, b: int) -> int:
    return a + b

def test_decorator() -> None:
    call_log.clear()
    assert add(2, 3) == 5
    assert add(10, 20) == 30
    assert call_log == ["add", "add"]


# functools.lru_cache is a built-in decorator — memoisation in one line.
@lru_cache(maxsize=None)
def slow_square(n: int) -> int:
    return n * n

def test_lru_cache_decorator() -> None:
    assert slow_square(5) == 25
    assert slow_square(5) == 25          # second call served from cache
    info = slow_square.cache_info()
    assert info.hits >= 1


# ---------------------------------------------------------------------------
# 7. *args and **kwargs — varargs and named-vararg dictionaries
# ---------------------------------------------------------------------------
# C# 'params': void Foo(params int[] xs)
# Python:    def foo(*xs):           # tuple of positional args
#            def foo(**opts):        # dict of keyword args

def describe(*items, sep: str = ", ", **labels) -> str:
    body = sep.join(str(i) for i in items)
    if labels:
        body += " | " + sep.join(f"{k}={v}" for k, v in labels.items())
    return body

def test_args_and_kwargs() -> None:
    assert describe(1, 2, 3) == "1, 2, 3"
    assert describe("a", "b", sep="|") == "a|b"
    assert describe(1, 2, name="Stephen", role="dev") == "1, 2 | name=Stephen, role=dev"
