# Functional Idioms — for C# Developers

Companion notes to [test_04_functional_idioms.py](test_04_functional_idioms.py).

Coming from C#, your reflex for "transform a collection" is **LINQ**:

```csharp
var doubled = items.Where(x => x > 0).Select(x => x * 2).ToList();
```

Python expresses the same intent four different ways, in roughly decreasing order of idiomaticness:

1. **Comprehensions** — `[x * 2 for x in items if x > 0]` (preferred for simple cases)
2. **Generator expressions** — `(x * 2 for x in items if x > 0)` (lazy, like LINQ's `IEnumerable`)
3. **`map()` / `filter()`** — exist but less idiomatic
4. **`functools` / `itertools`** — for richer combinators

---

## 1. List comprehensions ≈ LINQ `Select` / `Where`

```
[ <expression> for <var> in <iterable> if <condition> ]
   |              |     |       |        |
   value to       |     |       |        optional filter
   produce        |     binding source
                  iteration
```

Side-by-side:

| LINQ | Comprehension |
|---|---|
| `numbers.Select(n => n * n).ToList()` | `[n * n for n in numbers]` |
| `numbers.Where(n => n % 2 == 0).Select(n => n * n).ToList()` | `[n * n for n in numbers if n % 2 == 0]` |
| `xs.SelectMany(x => x.Items)` | `[item for x in xs for item in x.items]` (nested) |

Read a comprehension left-to-right by **starting with the `for` clause** — that establishes what's being iterated, then the leading expression says what to produce from each item.

---

## 2. Dict and set comprehensions

Same shape, different brackets:

```python
{w: len(w) for w in words}      # dict — note the colon
{len(w) for w in words}         # set — no colon, just an expression
```

| LINQ | Python |
|---|---|
| `xs.ToDictionary(x => x.Key, x => x.Value)` | `{x.key: x.value for x in xs}` |
| `xs.Select(x => x.Tag).ToHashSet()` | `{x.tag for x in xs}` |

---

## 3. Generators — `IEnumerable<T>` + `yield return`

A generator function uses `yield` (not `yield return`) and produces values **lazily**, one at a time:

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b
```

Calling `fibonacci()` does **not** run the body — it returns a **generator object**. Each call to `next(gen)` runs the function up to the next `yield`, pauses, and returns the yielded value. Memory cost is O(1) regardless of how many values you draw.

This is identical in spirit to C#'s iterator methods:

```csharp
IEnumerable<int> Fibonacci() {
    int a = 0, b = 1;
    while (true) {
        yield return a;
        (a, b) = (b, a + b);
    }
}
```

### Generator expressions

A list comprehension in **parentheses** instead of brackets becomes a generator — same syntax, lazy execution:

```python
[n * n for n in range(1_000_000)]    # eagerly builds a million-item list
(n * n for n in range(1_000_000))    # builds a generator; computes on demand
```

Use generators when:
- the iterable is huge or infinite,
- you only need the first few items, or
- you're piping through `sum`, `any`, `max`, etc. which don't need a materialized list.

`itertools.islice(gen, n)` is the lazy `.Take(n)`.

---

## 4. Lambdas

| C# | Python |
|---|---|
| `Func<int, int> doubleIt = x => x * 2;` | `double_it = lambda x: x * 2` |
| `(x, y) => x + y` | `lambda x, y: x + y` |

**Key constraint:** a Python lambda must be a **single expression**. No statements, no multi-line bodies, no `return` keyword. If you need more, use `def`. (Linters and Ruff's `E731` warn against assigning a lambda to a name — they want you to write `def double_it(x): return x * 2` instead.)

The most common idiomatic use is as a `key=` argument to sorting/grouping:

```python
pairs.sort(key=lambda pair: pair[0])
```

---

## 5. `map`, `filter`, `reduce`

These exist but are **less idiomatic** than comprehensions:

```python
list(map(lambda x: x * 2, numbers))         # [n * 2 for n in numbers]
list(filter(lambda x: x > 2, numbers))      # [n for n in numbers if n > 2]
reduce(lambda acc, x: acc + x, numbers, 0)  # sum(numbers)
```

| LINQ | Functional builtin | Pythonic |
|---|---|---|
| `.Select(...)` | `map(fn, xs)` | `[fn(x) for x in xs]` |
| `.Where(...)` | `filter(pred, xs)` | `[x for x in xs if pred(x)]` |
| `.Aggregate(seed, ...)` | `functools.reduce(fn, xs, seed)` | (no comprehension form — use `sum`, `min`, `max`, `any`, `all`, or `reduce`) |

`reduce` was **moved out of builtins** in Python 3 — Guido considered it less readable than an explicit loop. Reach for it only when there's no better builtin.

---

## 6. Decorators — like C# attributes, but actually transformative

A decorator is a **function that takes a function and returns a (usually new) function**. The `@name` syntax is **sugar** for reassigning the decorated name:

```python
@log_calls
def add(a, b):
    return a + b

# is exactly equivalent to:
def add(a, b):
    return a + b
add = log_calls(add)
```

A simple decorator implementation:

```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        call_log.append(func.__name__)
        return func(*args, **kwargs)
    return wrapper
```

| C# Attributes | Python Decorators |
|---|---|
| `[Obsolete]`, `[HttpGet]` | `@deprecated`, `@app.route(...)` |
| **Metadata only** — frameworks read them via reflection | **Transform the function** at definition time |
| Don't change what the method does until something queries them | Can wrap, replace, register, memoize the function |

So while the syntax looks similar (`[Foo]` vs `@foo`), decorators are **active**: they run at definition time and the function they decorate is whatever they returned.

### `functools.lru_cache` — memoization in one line

```python
@lru_cache(maxsize=None)
def slow_square(n):
    return n * n
```

That `@lru_cache` wraps the function with a memoizing cache — repeated calls with the same args return the stored result. Useful for pure functions with expensive computations. No C# stdlib equivalent; in C# you'd write the cache yourself or use a library.

---

## 7. `*args` and `**kwargs` revisited

Already covered in [test_00_defining_functions.md](test_00_defining_functions.md#8-args-and-kwargs--variadic-parameters), so just a brief refresher of what's idiomatic when mixed:

```python
def describe(*items, sep: str = ", ", **labels) -> str:
    body = sep.join(str(i) for i in items)
    if labels:
        body += " | " + sep.join(f"{k}={v}" for k, v in labels.items())
    return body

describe(1, 2, 3)                          # "1, 2, 3"
describe("a", "b", sep="|")                # "a|b"
describe(1, 2, name="Ada", role="dev")     # "1, 2 | name=Ada, role=dev"
```

Notice `sep` is a **keyword-only parameter** because it appears *after* `*items` — once positional arg collection starts, no further positional args can land on `sep`. Forcing keyword-only arguments by placing them after `*args` (or a bare `*`) is a common Python idiom for "explicit-only" parameters.

---

## Quick reference

| Pattern | LINQ | Python |
|---|---|---|
| Project | `.Select(x => f(x))` | `[f(x) for x in xs]` or `map(f, xs)` |
| Filter | `.Where(p)` | `[x for x in xs if p(x)]` or `filter(p, xs)` |
| Sum | `.Sum()` | `sum(xs)` |
| To dict | `.ToDictionary(...)` | `{k: v for ...}` |
| To set | `.ToHashSet()` | `set(xs)` or `{... for ...}` |
| Aggregate | `.Aggregate(seed, fn)` | `reduce(fn, xs, seed)` |
| Lazy take | `.Take(n)` | `itertools.islice(gen, n)` |
| Flatten | `.SelectMany(...)` | `[y for x in xs for y in x]` |
| Memoization | (write your own) | `@functools.lru_cache` |
| Lambda | `x => x * 2` | `lambda x: x * 2` |
| Attributes | `[Foo]` (passive) | `@foo` (active — transforms) |
