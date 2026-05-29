# Defining Functions — for C# Developers

Companion notes to [test_00_defining_functions.py](test_00_defining_functions.py).

In C# every method lives inside a class and starts with access modifiers and a return type. Python functions are **standalone, top-level objects** introduced by a single keyword: `def`. The signature carries the parameter names; the body is the indented block underneath.

```python
def name(param1: Type, param2: Type = default) -> ReturnType:
    <indented body>
```

C# eye-opener checklist:
- **No access modifiers.** Convention only: a leading underscore (`_helper`) signals "internal — don't touch."
- **No method overloading by signature.** A second `def add(...)` simply replaces the first. Use default values, `*args`, or `functools.singledispatch` instead.
- **Type annotations are hints**, enforced by external tools (mypy/pyright), not by the runtime.

---

## 1–3. Defaults, keyword arguments, and the missing `return`

| Concept | C# | Python |
|---|---|---|
| Optional parameters | `void Shout(string msg, int times = 1)` | `def shout(message: str, times: int = 1) -> str:` |
| Named arguments at call site | `Describe(name: "Ada", age: 36)` | `describe(name="Ada", age=36)` |
| Method with no return | `void Log(...)` | `def log(...) -> None:` |

The last row is subtle: in C#, `void` means *no value*. In Python, a function with no `return` still returns a value — it's just `None`. You can assign it; the assignment is just useless.

```python
result = log_silently("hello")
assert result is None
```

---

## 4. Functions are first-class objects

A function name in Python is just a variable bound to a callable object. You can pass it around, store it, reassign it:

```python
operation = add          # 'add' is the function itself, not a call
operation(4, 5)          # works — same as add(4, 5)
callable(operation)      # True
```

C# equivalent: `Func<int, int, int> op = Add;` — but **without the type ceremony** of declaring a delegate or `Func<...>` shape. Any function fits any slot, as long as the arity and behavior match at call time.

---

## 5–6. The big one: how arguments are passed

This is where C# instincts mislead. Python has **no `ref` and no `out`**. Every argument is passed by what the docs call *"object reference"*. Concretely:

- The parameter inside the function is a **new local name** bound to **the same object** the caller passed in.
- **Mutating** that object (`.append(...)`, `obj.attr = ...`) is visible to the caller.
- **Reassigning** the local name (`items = [...]`, `n += 1` on an int) is **never** visible to the caller.

This explains both halves of the test file's central demonstration:

```python
def mutate_list(items):   items.append("STEVE")    # caller SEES it
def replace_list(items):  items = ["STEVE"]        # caller does NOT see it
```

### The two-lists rule (test file's section 10)

The mental model that makes all of this click:

| Immutable (cannot be changed in-place) | Mutable (can be) |
|---|---|
| `int`, `float`, `bool`, `str`, `tuple`, `None`, `frozenset`, `bytes` | `list`, `dict`, `set`, `bytearray`, your own classes (unless frozen) |

**One-sentence rule:**
> If you pass a `list`/`dict`/`set`/custom object and the function calls a method on it (`.append`, `d["x"] = ...`, `obj.attr = ...`), the caller sees the change. For anything else, **return the new value**.

C# analogy:
- **Mutating a list/dict in Python** ≈ calling a method on a reference type without `ref` (`xs.Add(1)`). Caller sees it.
- **Reassigning a parameter in Python** has **no C# equivalent**. There is no `ref`. Want to update the caller's variable? Return a value.

```python
def increment(n: int) -> int:
    return n + 1       # caller does: x = increment(x)
```

---

## 7. The mutable default argument trap

The most famous Python foot-gun and **the one with no C# parallel**.

```python
def buggy_append(value, bucket=[]):   # default list created ONCE
    bucket.append(value)
    return bucket

buggy_append(1)   # [1]
buggy_append(2)   # [1, 2]   <- the default "remembered"!
buggy_append(3)   # [1, 2, 3]
```

**Why:** the `[]` is evaluated **once**, when the `def` statement runs — not on each call. Every call that omits `bucket` reuses the same list object.

**The idiomatic fix** — use `None` as a sentinel and build a fresh container inside the body:

```python
def safe_append(value, bucket: list[int] | None = None) -> list[int]:
    if bucket is None:
        bucket = []
    bucket.append(value)
    return bucket
```

Modern linters (Ruff's `B006`, Pylint's `dangerous-default-value`) flag this automatically.

---

## 8. `*args` and `**kwargs` — variadic parameters

| Python | What it collects | C# parallel |
|---|---|---|
| `*args` | extra **positional** args → `tuple` | `params T[] args` |
| `**kwargs` | extra **keyword** args → `dict[str, ...]` | no direct equivalent |

The `*` and `**` operators are also used at the **call site** to *spread* a collection into a call:

```python
nums = [10, 20, 30]
sum_all(*nums)              # same as sum_all(10, 20, 30)

payload = {"city": "London", "country": "UK"}
make_record(**payload)      # same as make_record(city="London", country="UK")
```

C# parallel for `*nums`: roughly `nums.ToArray()` passed to a `params` parameter. No parallel exists for `**payload`.

---

## 11. Joining strings: the StringBuilder lesson

Strings are **immutable** in Python (same as C#). That makes `result += word` in a loop O(n²) — every iteration allocates a brand-new string and copies the running total. C#'s answer is `StringBuilder`; Python's answer is `str.join`:

```python
"".join(words)              # one allocation, one pass — O(n)
", ".join(tags)             # CSV-style joining
"\n".join(lines)            # multi-line text
```

**The shape is famously backwards from C#:**

| | Call site |
|---|---|
| C# | `string.Join(separator, items)` |
| Python | `separator.join(items)` |

The separator is the receiver; the iterable is the argument. Read it as: *"this is the glue — apply it to those pieces."*

### When to use what

| Situation | Use |
|---|---|
| Small, fixed number of pieces | `+` or an f-string |
| Variable / unknown / large count | `sep.join(iterable)` |
| Joining non-strings | `",".join(str(i) for i in ids)` or `",".join(map(str, ids))` |

Note that final case: `",".join([1, 2, 3])` raises `TypeError`. Unlike C#'s `string.Join`, Python does **not** auto-call `.ToString()` — you must convert first.

---

## Quick reference

| Concept | C# | Python |
|---|---|---|
| Declare a function | `public int Add(int a, int b) { ... }` | `def add(a: int, b: int) -> int:` |
| Optional parameter | `int times = 1` | `times: int = 1` |
| Named argument at call | `Foo(name: "Ada")` | `foo(name="Ada")` |
| No return value | `void` | `-> None` (function returns `None`) |
| Variadic positional | `params int[] xs` | `*xs` (tuple) |
| Variadic keyword | (none) | `**opts` (dict) |
| Pass-by-ref | `ref` / `out` | (none — return the value) |
| Method overloading | yes, by signature | no — use defaults, `*args`, or `singledispatch` |
| Mutable default trap | (none) | always use `None` sentinel |
| Build long string | `StringBuilder` | `sep.join(iterable)` |
