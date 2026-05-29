# Python Syntax Basics — for C# Developers

Companion notes to [test_01_syntax_basics.py](test_01_syntax_basics.py).

This file covers the surface-level syntax differences that hit you in the first ten minutes of writing Python: blocks, naming, strings, null, truthiness, tuples, and comments.

---

## 1. Indentation **is** the syntax

C# uses `{ }` to delimit blocks; the indentation is purely cosmetic. Python is the opposite:

- A code block is defined by its **indentation level**.
- Statements that start a block end with a colon (`if x:`, `for i in range(5):`, `def foo():`).
- The block continues until the indent drops back.

```python
for i in range(5):       # 'for (int i = 0; i < 5; i++)'
    total += i           # inside the loop — indented
# back to outer scope    — indent dropped
```

**Rules of the road:**
- **4 spaces** per level. PEP 8 standard. Almost every Python project enforces this.
- **Never mix tabs and spaces.** CPython raises `IndentationError` or `TabError` rather than guessing. Configure your editor: "insert spaces, not tabs."

`range(n)` is the Python equivalent of a `for (int i = 0; i < n; i++)` loop. It yields `0, 1, ..., n-1` lazily — no list is allocated.

---

## 2. Variables have no declared type

There is **no `var`, no `int`, no type keyword** in front of an assignment:

```python
x = 5                   # like 'var x = 5;'
x = "now I'm a string"  # legal — names are just bindings
```

A variable is a **name pointing at an object**. Reassigning it just re-points the name; the old object is garbage-collected if nothing else holds it.

You may see type *annotations* on local variables (`x: int = 5`) — those are **hints for static checkers**, not declarations. Section 2 of [test_02_type_system.md](test_02_type_system.md) covers this in detail.

---

## 3. Naming conventions

| Element | C# | Python (PEP 8) |
|---|---|---|
| Classes | `PascalCase` | `PascalCase` ✓ same |
| Methods / functions | `camelCase` (or `PascalCase` for public) | `snake_case` |
| Local variables | `camelCase` | `snake_case` |
| Constants | `UPPER_CASE` | `UPPER_CASE` ✓ same |
| Interfaces | `IFoo` prefix | no `I` prefix — use `Protocol` |
| "Internal" / "private" | `private` / `internal` keywords | `_leading_underscore` convention |

Python has no `const` keyword — `MAX_RETRIES = 3` is a regular assignment, and the all-caps name is **convention only**. Nothing stops you from rebinding it. Tools and humans honor the convention.

---

## 4. f-strings = C# interpolated strings

The shape is almost identical:

```csharp
// C#
$"Hello, {name}! n+1 = {n + 1}"
$"{value:F2}"
```

```python
# Python
f"Hello, {name}! n+1 = {n + 1}"
f"{value:.2f}"
```

The format-spec mini-language after the colon is similar but not identical to C#'s (`:.2f` is "2 decimal float," `:>10` is "right-align in 10 chars," `:,` adds thousands separators).

Older code may use `"...".format(...)` or `%` formatting; in modern Python (3.6+), prefer f-strings.

---

## 5. `None` is Python's `null`

```python
value = None
assert value is None
```

**Use `is None` / `is not None`, not `== None`.**

| Operator | What it does | C# parallel |
|---|---|---|
| `==` | calls `__eq__` (value equality) | `Equals` / `==` overload |
| `is` | object identity | `ReferenceEquals` |

There is exactly **one** `None` object in any Python process (a singleton), so identity comparison is correct, faster, and idiomatic. The same goes for `True` and `False`. Linters will flag `== None`.

---

## 6. Truthiness

Python treats many values as `True`/`False` in boolean context. The "falsy" set is small and worth memorizing:

| Falsy | Truthy (everything else) |
|---|---|
| `False`, `None` | objects with content |
| `0`, `0.0`, `0j` | any non-zero number |
| `""`, `[]`, `()`, `{}`, `set()` | any non-empty collection |

This enables some very compact, idiomatic checks:

```python
if my_list:        # Python idiom
if name:           # checks "non-empty string"
```

```csharp
// C# equivalents
if (myList.Count > 0) ...
if (!string.IsNullOrEmpty(name)) ...
```

**Gotcha:** `[0]` is truthy — it contains an element (even if that element is `0`). The check is on the *container*, not its contents.

---

## 7. Tuple unpacking — beats C# `ValueTuple`

C# has `ValueTuple` and deconstruction:
```csharp
(int a, string b) = GetThing();
```

Python is simpler: any function can return multiple values as a **tuple**, and any tuple (or list) can be unpacked positionally:

```python
def min_and_max(values):
    return min(values), max(values)     # parens optional; this IS a tuple

lo, hi = min_and_max([3, 1, 4, 1, 5])
```

### Swap without a temp

```python
a, b = b, a       # idiomatic
```

The right-hand side is evaluated to a tuple `(b, a)` first, then unpacked.

### Star-unpacking

The `*` operator on the left-hand side absorbs "the rest":

```python
first, *middle, last = [10, 20, 30, 40, 50]
# first = 10, middle = [20, 30, 40], last = 50
```

C# has no direct equivalent — you'd reach for `Skip`/`Take` LINQ chains.

---

## 8. Comments and docstrings

| Style | Python | C# |
|---|---|---|
| Single-line | `# comment` | `// comment` |
| Block | (no syntax) — just `#` per line, or an unused string literal | `/* ... */` |
| Documentation | triple-quoted **docstring** at top of function/class/module | `/// <summary>...</summary>` |

The docstring is a real string object — it's stored as `func.__doc__` and is available at runtime, in `help(func)`, and in IDE tooltips:

```python
def greet(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hi, {name}"

greet.__doc__   # 'Return a friendly greeting.'
```

Conventions for docstring formatting (Google style, NumPy style, reStructuredText) vary by project. Sphinx and most IDEs render them as help text.

---

## Quick reference

| Concept | C# | Python |
|---|---|---|
| Block delimiter | `{ }` | indentation (4 spaces) |
| Variable declaration | `var x = 5;` / `int x = 5;` | `x = 5` |
| Null | `null` | `None` (compare with `is`) |
| Empty-check idiom | `string.IsNullOrEmpty(s)` | `if not s:` |
| Interpolated string | `$"value = {x:F2}"` | `f"value = {x:.2f}"` |
| Multiple return | `(int, int)` ValueTuple | tuple — `return a, b` |
| Swap two vars | needs a temp | `a, b = b, a` |
| Method case | `PascalCase` | `snake_case` |
| Doc comment | `/// <summary>` | `"""docstring"""` |
| Range loop | `for (int i=0; i<n; i++)` | `for i in range(n):` |
