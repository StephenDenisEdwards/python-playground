# Collections & Standard Library — for C# Developers

Companion notes to [test_06_collections_stdlib.py](test_06_collections_stdlib.py).

Python's marketing slogan is **"batteries included"**: the standard library ships with most of what you need. No NuGet equivalent for these — they're in CPython itself.

This file tours the modules a C# developer reaches for daily: `collections`, `itertools`, `functools`, `pathlib`.

---

## 1. `defaultdict` — `Dictionary<K, V>` with a default factory

The classic "group items by some key" pattern in C#:

```csharp
var byLetter = new Dictionary<char, List<string>>();
foreach (var w in words) {
    if (!byLetter.ContainsKey(w[0]))
        byLetter[w[0]] = new List<string>();
    byLetter[w[0]].Add(w);
}
```

Python with `defaultdict`:

```python
from collections import defaultdict

by_letter = defaultdict(list)        # 'list' is the default *factory*
for w in words:
    by_letter[w[0]].append(w)        # no key check, no setup
```

When you access a missing key, the factory (`list` here) is called to create a default value, which is inserted **then** returned. Common factories: `list`, `set`, `int` (for counters), `dict` (for nested maps).

C# parallel: `Dictionary<K, V>.TryGetValue` patterns or extension methods like `GetOrAdd` on `ConcurrentDictionary`. `defaultdict` makes it built-in syntax.

---

## 2. `Counter` — frequency dictionaries

```python
from collections import Counter

counts = Counter("to be or not to be".split())
counts["to"]                # 2
counts.most_common(2)       # [("to", 2), ("be", 2)]
```

`Counter` is a `dict` subclass specialized for counting hashable items. It supports arithmetic on counts: `c1 + c2` (sum), `c1 - c2` (subtract, clamping at 0), `c1 & c2` (min/intersection), `c1 | c2` (max/union).

LINQ parallel: `xs.GroupBy(x => x).ToDictionary(g => g.Key, g => g.Count())`. Counter is shorter and faster.

---

## 3. `deque` — `LinkedList<T>` with O(1) at both ends

```python
from collections import deque

q = deque(["a", "b", "c"])
q.append("d")        # right
q.appendleft("z")    # left
q.pop()              # "d" — right
q.popleft()          # "z" — left
```

A `list` has O(1) append/pop at the **right** end, but O(n) at the left (because everything shifts). `deque` is a doubly-linked block structure with O(1) at **both** ends. Use it when you need a queue, sliding window, or "last N items" buffer (it accepts `maxlen=N` to act as a ring buffer).

C# parallel: `LinkedList<T>` for general doubly-linked, or `Queue<T>` for FIFO-only.

---

## 4. `itertools` — composable lazy iterators

`itertools` is the LINQ of Python. Every function takes an iterable, returns a (lazy) iterator. Combine them like Lego.

| Function | Effect | LINQ parallel |
|---|---|---|
| `chain(a, b, c)` | concatenate iterables | `.Concat(...)` / `.SelectMany` |
| `islice(it, n)` | take first n (lazy) | `.Take(n)` |
| `islice(it, start, stop, step)` | slice an iterator | `.Skip(...).Take(...)` |
| `groupby(it, key=...)` | group **consecutive** equal items | (NOT the same as LINQ `.GroupBy`!) |
| `accumulate(it)` | running totals | `.Aggregate` (but yielding each step) |
| `count(start, step)` | infinite counter | `Enumerable.Range` (but unbounded) |
| `cycle(it)` | repeat forever | (no parallel) |
| `repeat(x, n)` | repeat `x` n times | `Enumerable.Repeat(x, n)` |
| `product(*iters)` | Cartesian product | nested `from`-clauses |
| `combinations(it, r)` | r-combinations | (no stdlib parallel) |
| `permutations(it, r)` | r-permutations | (no stdlib parallel) |
| `tee(it, n)` | split iterator into n copies | (no parallel; iterators are consumable) |

### Watch out: `groupby` groups **consecutive** equal items

This is the most surprising difference from LINQ's `.GroupBy`. LINQ collects all items with the same key globally; `itertools.groupby` only groups runs of equal-keyed items. **Sort first** if you want SQL-style grouping:

```python
data = sorted(data, key=lambda p: p[0])
grouped = {key: [p[1] for p in group]
           for key, group in groupby(data, key=lambda p: p[0])}
```

### `islice` and generators are made for each other

```python
big = (n for n in range(10_000_000))     # generator — no list allocated
list(islice(big, 5))                     # [0, 1, 2, 3, 4]
```

The generator only produces what `islice` actually pulls. This is the prototype for lazy data pipelines in Python.

---

## 5. `functools.partial` — pre-bind arguments

`partial(fn, *args, **kwargs)` returns a new callable with some arguments already filled in. Similar to "currying":

```python
from functools import partial

def power(base, exponent):
    return base ** exponent

square = partial(power, exponent=2)
cube   = partial(power, exponent=3)

square(5)   # 25
cube(3)     # 27
```

C# parallel: write a closure — `Func<int, int> square = b => power(b, 2);`. `partial` is more concise when you're just pre-binding, and integrates cleanly with `map`, `sorted`, callbacks, etc.

Other `functools` highlights:
- `@lru_cache` / `@cache` — memoization (covered in [test_04_functional_idioms.md](test_04_functional_idioms.md#functoolslru_cache--memoization-in-one-line))
- `@singledispatch` — type-based function overloading (covered in [test_08_gotchas.md](test_08_gotchas.md))
- `reduce` — left-fold (covered in test_04)

---

## 6. `pathlib` — the modern path API

`pathlib.Path` is the OO replacement for the older `os.path` string-juggling. It's roughly Python's `System.IO.Path` + `FileInfo` + `DirectoryInfo` combined into one type.

The killer feature is operator overloading for path joining:

```python
from pathlib import Path

file = tmp_path / "sub" / "hello.txt"        # '/' is path-join
file.parent.mkdir(parents=True)              # mkdir -p
file.write_text("hello")
file.read_text()
file.exists()
file.suffix                                   # ".txt"
file.stem                                     # "hello"
file.with_suffix(".bak")
file.glob("*.txt")
```

Compare to C#'s `Path.Combine(tmp, "sub", "hello.txt")` plus separate `File.WriteAllText`/`File.ReadAllText` calls — `pathlib` is more cohesive.

The `tmp_path` pytest fixture seen in the tests is a `Path` to a per-test temp directory automatically cleaned up afterward. **Always prefer fixtures or `tempfile.TemporaryDirectory()` over hardcoded paths in tests.**

---

## Other batteries worth knowing

| Module | Use case | C# parallel |
|---|---|---|
| `json` | JSON read/write | `System.Text.Json` |
| `csv` | CSV read/write | `CsvHelper` (third-party in .NET) |
| `re` | regular expressions | `System.Text.RegularExpressions` |
| `datetime` | dates and times | `DateTime`, `DateOnly`, `TimeSpan` |
| `dataclasses` | record-like classes | C# `record` (covered in test_03) |
| `enum` | enumerations | `enum` keyword |
| `typing` | type hints | (built into C#) |
| `logging` | structured logging | `ILogger` / `Microsoft.Extensions.Logging` |
| `argparse` | CLI argument parsing | `System.CommandLine` |
| `subprocess` | run external commands | `System.Diagnostics.Process` |
| `unittest` | testing | `MSTest` / `xUnit` |
| `concurrent.futures` | thread/process pools | `Task.Run`, `Parallel.ForEach` |
| `sqlite3` | embedded SQL database | `Microsoft.Data.Sqlite` |
| `urllib.request` | HTTP client | `HttpClient` (but most people use `httpx` or `requests`) |

---

## Quick reference

| Need | Reach for |
|---|---|
| Dict with auto-created default values | `collections.defaultdict(factory)` |
| Frequency counts | `collections.Counter(iterable)` |
| Fast queue / double-ended buffer | `collections.deque` |
| Lazy concat | `itertools.chain(...)` |
| Lazy take-N | `itertools.islice(it, n)` |
| Running totals | `itertools.accumulate(it)` |
| Cartesian product / combinations | `itertools.product` / `combinations` |
| Pre-bind arguments | `functools.partial(fn, x)` |
| Memoize | `@functools.cache` |
| Cross-platform paths | `pathlib.Path` |
| Path concatenation | `path / "subdir" / "file.txt"` |
