"""
Standard library highlights — "batteries included".

These modules are part of CPython itself, no pip install required.
They cover most everyday data structures and utilities.
"""

from collections import defaultdict, Counter, deque
from itertools import chain, groupby, islice, accumulate
from functools import partial
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. defaultdict ≈ Dictionary<TKey, TValue> with a default factory
# ---------------------------------------------------------------------------
# Saves you the "if key not in dict: dict[key] = []" boilerplate.

def test_defaultdict_groups_items() -> None:
    words = ["apple", "ant", "banana", "berry", "cherry"]
    by_letter: dict[str, list[str]] = defaultdict(list)   # default factory = list
    for w in words:
        by_letter[w[0]].append(w)                         # no KeyError, no setup
    assert by_letter["a"] == ["apple", "ant"]
    assert by_letter["b"] == ["banana", "berry"]


# ---------------------------------------------------------------------------
# 2. Counter ≈ ToFrequencyDictionary / GroupBy().Count()
# ---------------------------------------------------------------------------

def test_counter_counts_things() -> None:
    text = "to be or not to be"
    counts = Counter(text.split())
    assert counts["to"] == 2
    assert counts.most_common(2) == [("to", 2), ("be", 2)]


# ---------------------------------------------------------------------------
# 3. deque ≈ LinkedList<T>: O(1) push/pop at both ends
# ---------------------------------------------------------------------------

def test_deque_for_queue_and_stack() -> None:
    q = deque(["a", "b", "c"])
    q.append("d")            # right side
    q.appendleft("z")        # left side
    assert list(q) == ["z", "a", "b", "c", "d"]
    assert q.pop() == "d"
    assert q.popleft() == "z"


# ---------------------------------------------------------------------------
# 4. itertools — composable lazy iterators
# ---------------------------------------------------------------------------

def test_itertools_chain_flattens_iterables() -> None:
    # Like SelectMany / Concat
    flat = list(chain([1, 2], (3, 4), {5, 6}))
    assert sorted(flat) == [1, 2, 3, 4, 5, 6]


def test_itertools_islice_takes_first_n() -> None:
    # islice is the lazy 'Take(n)' from LINQ
    big = (n for n in range(10_000_000))    # generator, no allocation
    assert list(islice(big, 5)) == [0, 1, 2, 3, 4]


def test_itertools_groupby_consecutive_runs() -> None:
    # NOTE: groupby groups *consecutive* equal items — sort first if you want
    # SQL-style grouping.
    data = sorted([("a", 1), ("b", 2), ("a", 3)], key=lambda p: p[0])
    grouped = {key: [pair[1] for pair in group]
               for key, group in groupby(data, key=lambda p: p[0])}
    assert grouped == {"a": [1, 3], "b": [2]}


def test_itertools_accumulate_is_a_running_total() -> None:
    assert list(accumulate([1, 2, 3, 4])) == [1, 3, 6, 10]


# ---------------------------------------------------------------------------
# 5. functools.partial — pre-bind arguments (≈ closures or Curry)
# ---------------------------------------------------------------------------

def test_partial_pre_binds_arguments() -> None:
    def power(base: int, exponent: int) -> int:
        return base ** exponent
    square = partial(power, exponent=2)
    cube = partial(power, exponent=3)
    assert square(5) == 25
    assert cube(3) == 27


# ---------------------------------------------------------------------------
# 6. pathlib — the modern, OO replacement for os.path / System.IO.Path
# ---------------------------------------------------------------------------
# Operators like '/' are overloaded for path joining — much cleaner than
# Path.Combine().

def test_pathlib_basics(tmp_path: Path) -> None:
    # pytest's 'tmp_path' fixture is a Path to a per-test temp directory
    file = tmp_path / "sub" / "hello.txt"        # '/' joins path segments
    file.parent.mkdir(parents=True)              # mkdir -p
    file.write_text("hello, pathlib")
    assert file.exists()
    assert file.suffix == ".txt"
    assert file.read_text() == "hello, pathlib"
