# Python Gotchas — for C# Developers

Companion notes to [test_08_gotchas.py](test_08_gotchas.py).

A collection of footguns that bite people coming from C#. Each one has a corresponding test in the file: first showing the trap, then the idiomatic fix.

---

## 1. Mutable default arguments — the most famous Python gotcha

```python
def append_buggy(item, target=[]):
    target.append(item)
    return target

append_buggy(1)   # [1]
append_buggy(2)   # [1, 2]   <- surprise!
append_buggy(3)   # [1, 2, 3]
```

**The mechanic:** the `[]` default is created **once**, when the `def` statement runs — not on every call. Every call that omits `target` reuses **the same list object**. So accumulations from one call leak into the next.

**The fix:** use `None` as a sentinel and create the mutable inside the body:

```python
def append_fixed(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

**Why C# devs don't have this trap:** in C#, default parameter values must be compile-time constants — you can't even *write* `void Foo(List<int> xs = new List<int>())`. The runtime evaluates defaults per-call. Python's defaults are objects evaluated at definition time.

This is covered with more depth in [test_00_defining_functions.md](test_00_defining_functions.md#7-the-mutable-default-argument-trap). Ruff/Pylint detect it (`B006`).

---

## 2. Closures capture the variable, not the value

```python
funcs = [lambda: i for i in range(3)]
[f() for f in funcs]            # [2, 2, 2]   — not [0, 1, 2]!
```

By the time the lambdas are called, the loop is done and `i` has its final value (2). All three closures share the same `i`.

**Two fixes:**

```python
# Fix 1: bind at definition via default arg
funcs = [lambda i=i: i for i in range(3)]
[f() for f in funcs]            # [0, 1, 2]

# Fix 2: extract a factory function
def make_fn(value):
    return lambda: value
funcs = [make_fn(i) for i in range(3)]
```

**C# trivia:** C# had the **same** bug for `for` loops, and fixed it for `foreach` in C# 5 (2012). The classic `for (int i = 0; i < 3; i++) lambdas.Add(() => i);` *still* exhibits the late-binding behavior in modern C#. Python never patched it, but the default-argument idiom is the workaround.

---

## 3. `==` vs `is`

```python
a = [1, 2, 3]
b = [1, 2, 3]
c = a
a == b          # True — same value
a is b          # False — different objects
a is c          # True — same object
```

| Operator | What it does | C# parallel |
|---|---|---|
| `==` | value equality — calls `__eq__` | `Equals` / `==` overload |
| `is` | object identity | `ReferenceEquals` |

**Use `is` for:**
- `None` (always, always `is None`)
- `True` and `False` (singletons)
- explicit identity checks (cache invalidation, sentinel objects)

**Never use `is`** for numeric or string equality — even if it "happens to work":

### The small-int cache trap

```python
x = 256
y = 256
x is y            # True — but only by accident!
x = 257
y = 257
x is y            # False on most CPython versions
```

CPython pre-allocates `int` objects in the range `[-5, 256]` and reuses them. So small ints look identity-equal. This is a **CPython implementation detail**, not a language guarantee. Don't rely on it. The linter rule `F632` (use of `is` with a literal) catches this.

---

## 4. No method overloading by signature

```python
class Calculator:
    def add(self, a):                # overwritten...
        return a
    def add(self, a, b=0, c=0):      # ...by this. The first 'add' is gone.
        return a + b + c
```

A `class` body is just a sequence of statements; the second `def add` rebinds the name `add` to the new function, exactly the same as `x = 1; x = 2` rebinds `x`.

**Three idiomatic alternatives:**

### a) Default values

```python
def add(self, a, b=0, c=0):
    return a + b + c
```

Covers most "I want different arities" cases.

### b) `*args` for varargs

```python
def add(self, *values):
    return sum(values)
```

### c) `functools.singledispatch` — for type-based dispatch

```python
@singledispatch
def describe(value) -> str:
    return f"unknown: {value!r}"

@describe.register
def _(value: int) -> str:
    return f"int: {value}"

@describe.register
def _(value: str) -> str:
    return f"str: {value!r}"

describe(42)        # "int: 42"
describe("hi")      # "str: 'hi'"
describe([1, 2])    # "unknown: [1, 2]"
```

The function is chosen at runtime based on the **type of the first argument**. The underscore for the function name is convention — the dispatcher uses the type annotation, not the name. For dispatching on `self` too, see `functools.singledispatchmethod`.

---

## 5. Integer division

```python
7 / 2           # 3.5     ← always float in Python 3
7 // 2          # 3       ← floor division (integer division)
7 % 2           # 1
-7 // 2         # -4      ← floor, not truncate!
```

In **C#**, `int / int` is integer division, and you must cast for float: `(double)7 / 2 == 3.5`.
In **Python 3**, `/` always returns a float. Use `//` when you want integer division. This is one of the most common surprises in a Python 2 → Python 3 conversion.

**Watch the floor:** `//` floors toward negative infinity, not toward zero. `-7 // 2 == -4`, not `-3`. C#'s `/` truncates toward zero. If you need C# semantics, use `int(a / b)` or `math.trunc(a / b)`.

---

## 6. Reassignment vs mutation

```python
def reassign(lst):
    lst = [99]                # local rebind only

def mutate(lst):
    lst.append(99)            # mutates the caller's object

a = [1, 2, 3]
reassign(a);  a    # [1, 2, 3]    — unchanged
mutate(a);    a    # [1, 2, 3, 99] — modified
```

This is fully covered in [test_00_defining_functions.md](test_00_defining_functions.md#56-the-big-one-how-arguments-are-passed). The headline: Python has no `ref` keyword. Mutate the object if you want the caller to see changes; otherwise **return the new value** and let the caller reassign.

---

## A few more traps not in the test file (but worth knowing)

### `is` with string literals

```python
"hello" is "hello"   # True (today, due to interning) — but DO NOT rely on this
```

CPython interns short identifier-like strings. Compare strings with `==`.

### `bool` is a subclass of `int`

```python
True == 1           # True
True + True         # 2
isinstance(True, int)   # True
```

This is occasionally useful (summing `True`/`False` to count), occasionally surprising (a `dict` keyed on `True` and `1` collides).

### Late-bound name lookup in methods

A method calling another method on `self` does the lookup at call time, not at class-definition time. Reassigning `self.method = something_else` works, and subclasses' overrides win. No "virtual" / "non-virtual" distinction.

### Iterating a generator twice

```python
gen = (x * x for x in range(3))
list(gen)           # [0, 1, 4]
list(gen)           # []    <- generator is exhausted!
```

Generators are one-shot. To iterate twice, materialize to a list, or rebuild the generator.

### `range`, `dict.keys()`, `map()` are not lists

In Python 3, many "collection-shaped" things are lazy iterators. `range(5)` is a `range` object; `dict.keys()` is a view; `map(fn, xs)` is a map iterator. Wrap with `list(...)` if you need a concrete list (e.g., to index or to compare with `==` to a list literal).

### Floating point

```python
0.1 + 0.2 == 0.3    # False
```

Same as every other language using IEEE 754. Use `math.isclose(a, b)` for fuzzy comparison, or `decimal.Decimal` for exact decimal arithmetic.

---

## Quick reference

| Gotcha | Fix |
|---|---|
| `def f(x=[]):` | Use `def f(x=None): if x is None: x = []` |
| `[lambda: i for i in range(n)]` returns all same | `[lambda i=i: i for i in range(n)]` |
| `x is y` for value equality | use `==` (reserve `is` for `None`, `True`, `False`) |
| Method overloading | default args, `*args`, or `@singledispatch` |
| `int / int` returning float | use `//` for integer division |
| Mutating vs reassigning a parameter | mutate to share, return to update |
| Generator consumed after first pass | rebuild it, or materialize to `list` |
| `0.1 + 0.2 != 0.3` | `math.isclose` or `decimal.Decimal` |
| `True == 1` and `True + True == 2` | mostly fine — but don't key dicts on `True` and `1` |
