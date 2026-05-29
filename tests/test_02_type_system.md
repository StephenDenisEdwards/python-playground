# Python's Type System — for C# Developers

Companion notes to [test_02_type_system.py](test_02_type_system.py).

The single biggest mental shift coming from C#:

> **Types belong to *values*, not to *variables*.**

In C#, `int x = 5;` means the *slot* `x` is permanently typed `int`. In Python, `x` is just a name pointing at an object; the object has a type, the name does not. Reassigning `x = "five"` is fine — you're just re-pointing the name at a new object of a different type.

---

## 1. Dynamic typing

| C# | Python |
|---|---|
| `int x = 5;` (slot is `int` forever) | `x = 5` (name points at an `int`) |
| `x = "five";` — compile error | `x = "five"` — fine, name now points at a `str` |
| `var` — inferred but still static | no equivalent; names are never typed |

`isinstance(value, SomeType)` is the runtime equivalent of `value is SomeType` in C#.

---

## 2. Type hints (PEP 484) are *not* enforced

```python
def add(a: int, b: int) -> int:
    return a + b

add("foo", "bar")   # returns "foobar" at runtime — no error
```

Coming from C#, this is the most surprising part. **Hints are metadata.** The CPython interpreter ignores them entirely. They're enforced by **external static analyzers**:

- **mypy** — the original, command-line
- **pyright** — Microsoft's; powers Pylance / VS Code's Python tooling

Think of hints as roughly equivalent to XML doc comments in C# that an analyzer happens to read — except IDEs and modern Python culture treat them as load-bearing, and most non-trivial codebases run a type-checker in CI.

The `# type: ignore[arg-type]` comment on line 41 of the test file is how you silence a static-checker warning on a specific line, similar to `#pragma warning disable` in C#.

---

## 3. Modern hint syntax (Python 3.10+)

Older Python required importing generic types from `typing`. Modern syntax uses the built-in containers directly and `|` for unions:

| Old (still works) | Modern (3.10+) | C# equivalent |
|---|---|---|
| `List[int]` | `list[int]` | `List<int>` |
| `Dict[str, int]` | `dict[str, int]` | `Dictionary<string, int>` |
| `Optional[int]` | `int \| None` | `int?` (nullable) |
| `Union[int, str]` | `int \| str` | no direct equivalent |

The ternary `items[0] if items else None` reads left-to-right as "the value, *if* the condition, *else* the alternative." It's the same as C#'s `items.Any() ? items[0] : null` — just with the operands reordered.

---

## 4. Duck typing

> *"If it walks like a duck and quacks like a duck, it's a duck."*

A function doesn't care what *type* its argument is — only that it supports the operations the function uses. No `IEnumerable<T>` / `ICollection<T>` / `IList<T>` hierarchy required.

```python
def total_length(things) -> int:
    return sum(len(t) for t in things)
```

This works on `list`, `tuple`, `set`, a generator, anything that:
1. Is iterable (`for t in things` works), and
2. Whose elements support `len()`.

In C# you'd need every input to implement a common interface, or you'd write overloads. In Python, the *contract is implicit* — if it works, it works.

---

## 5. Protocols ≈ structural interfaces

A `Protocol` describes a **shape** (methods/attributes) that a class must have. Crucially, the class does **not** declare that it implements the protocol:

```python
class SupportsArea(Protocol):
    def area(self) -> float: ...

class Square:                 # No ': SupportsArea' — yet it satisfies it
    def area(self) -> float: ...
```

Comparison:

| Style | C# | Python |
|---|---|---|
| **Nominal** ("declared") | `class Square : IHasArea` — explicit | `class Square(SupportsArea):` — possible but rarely needed |
| **Structural** ("shape-based") | none in C# | `Protocol` — the idiomatic choice |

The closest C# analogue is **Go interfaces** — any type with the right methods automatically satisfies the interface. The benefit: you can write functions against `SupportsArea` and pass them objects from libraries that have never heard of your protocol, as long as the shape matches.

Type-checkers (mypy/pyright) verify protocol conformance statically; at runtime, Python just calls `.area()` and trusts it works (duck typing again).

---

## 6. EAFP vs LBYL — the Pythonic exception style

Two idioms for handling possible failure:

- **LBYL** — *Look Before You Leap* (typical C#): check conditions, then act.
- **EAFP** — *Easier to Ask Forgiveness than Permission* (Pythonic): just do it, catch the exception if it fails.

```python
# LBYL (less Pythonic)
if isinstance(value, str) and value.isdigit():
    return int(value)
return None

# EAFP (Pythonic)
try:
    return int(value)
except (TypeError, ValueError):
    return None
```

Why Python leans EAFP:
- Exceptions in Python are cheap — they aren't the expensive `Exception` objects C# constructs with full stack traces eagerly serialized.
- LBYL has race conditions on shared state (file exists check → file deleted → open fails anyway).
- The "happy path" reads more linearly.

`int("42")` returns `42`. `int("foo")` raises `ValueError`. `int(None)` raises `TypeError`. The `except (TypeError, ValueError):` tuple catches both — equivalent to a C# `catch` block with an `is` pattern matching multiple exception types.

---

## Quick reference

| Concept | C# | Python |
|---|---|---|
| Variable typing | Static — slot has a type | Dynamic — value has a type |
| Type enforcement | Compiler | External tool (mypy/pyright) |
| Interfaces | Nominal (`: IFoo`) | Structural (`Protocol`), or duck typing |
| Generic collections | `List<int>`, `Dictionary<K,V>` | `list[int]`, `dict[K, V]` |
| Nullable | `int?`, `string?` | `int \| None`, `str \| None` |
| Failure handling | Mostly LBYL | Mostly EAFP |
| Runtime type check | `value is SomeType` | `isinstance(value, SomeType)` |
