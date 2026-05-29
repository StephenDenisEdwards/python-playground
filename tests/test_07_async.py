"""
async / await — the same shape as C#'s TPL, but with a twist.

Mental map:
    C# Task<T>          ->  Python Awaitable / Coroutine
    Task.WhenAll(...)   ->  asyncio.gather(...)
    Task.Run(...)       ->  asyncio.create_task(...)
    await foo()         ->  await foo()          (same syntax!)

KEY DIFFERENCES from C#:
  - Async code runs on a single thread inside an *event loop*.
  - You can't 'await' inside a regular function — only inside `async def`.
  - Most stdlib I/O calls are SYNC; you need an async-aware library (aiohttp,
    asyncpg, etc.) or the asyncio.to_thread() escape hatch.
  - The Global Interpreter Lock (GIL) means async is for I/O concurrency, NOT
    for using multiple CPU cores. For CPU work, use multiprocessing.

pytest-asyncio (configured in pyproject.toml) detects `async def test_...` and
runs them inside an event loop automatically.
"""

import asyncio
import os
import time
from concurrent.futures import ProcessPoolExecutor


# ---------------------------------------------------------------------------
# 1. A basic async function
# ---------------------------------------------------------------------------

async def fetch_value(delay: float, value: int) -> int:
    """Simulates async I/O by sleeping (non-blocking sleep)."""
    await asyncio.sleep(delay)        # cooperative yield to the event loop
    return value


async def test_single_await() -> None:
    result = await fetch_value(0.01, 42)
    assert result == 42


# ---------------------------------------------------------------------------
# 2. asyncio.gather  ≈  Task.WhenAll
# ---------------------------------------------------------------------------
# Three "I/O" calls run *concurrently*. Total wall time ≈ slowest one,
# not the sum, because they share the event loop and each one yields during
# asyncio.sleep.

async def test_gather_runs_concurrently() -> None:
    started = time.perf_counter()
    a, b, c = await asyncio.gather(
        fetch_value(0.05, 1),
        fetch_value(0.05, 2),
        fetch_value(0.05, 3),
    )
    elapsed = time.perf_counter() - started
    assert (a, b, c) == (1, 2, 3)
    # If they ran sequentially this would be ~0.15s; gathered, ~0.05s.
    assert elapsed < 0.12


# ---------------------------------------------------------------------------
# 3. create_task — fire-and-track, like Task.Run
# ---------------------------------------------------------------------------

async def test_create_task() -> None:
    task = asyncio.create_task(fetch_value(0.01, 7))
    # ... do other work here while the task runs ...
    result = await task
    assert result == 7


# ---------------------------------------------------------------------------
# 4. Cancellation
# ---------------------------------------------------------------------------
# Tasks can be cancelled. The cancellation surfaces inside the coroutine as
# CancelledError, similar to C#'s CancellationToken throwing OperationCanceledException.

async def test_task_cancellation() -> None:
    task = asyncio.create_task(asyncio.sleep(10))
    task.cancel()
    import pytest
    with pytest.raises(asyncio.CancelledError):
        await task


# ---------------------------------------------------------------------------
# 5. Running blocking (sync) work without freezing the loop
# ---------------------------------------------------------------------------
# asyncio.to_thread() offloads a sync function to a worker thread, returning
# an awaitable. Use this when you must call a sync library from async code.

def blocking_compute(n: int) -> int:
    time.sleep(0.02)                # sync sleep — would block the loop
    return n * n

async def test_to_thread_offloads_blocking_calls() -> None:
    result = await asyncio.to_thread(blocking_compute, 6)
    assert result == 36


# ---------------------------------------------------------------------------
# 6. Coroutines are "cold"; C# Tasks are "hot"
# ---------------------------------------------------------------------------
# THE difference that bites C# devs first. In C#:
#
#     Task<int> t = FetchAsync();   // already RUNNING on the thread pool
#     int x = await t;              // await just collects the result
#
# In Python, calling an `async def` runs NONE of the body — it only builds a
# coroutine object that sits inert until you await it (or schedule it). Forget
# to await and you get a "coroutine was never awaited" warning and zero work.

async def test_calling_a_coroutine_does_not_run_it() -> None:
    log: list[str] = []

    async def record() -> None:
        log.append("ran")

    coro = record()              # in C#, the equivalent Task would already be running
    assert log == []             # ...but the body has NOT executed yet

    await coro                   # NOW the body runs
    assert log == ["ran"]


# ---------------------------------------------------------------------------
# 7. create_task is "hot" — but only runs when the loop next gets control
# ---------------------------------------------------------------------------
# create_task is the closest thing to a C# hot Task: it SCHEDULES the coroutine
# on the loop. But note the subtlety — even then the body doesn't run on the
# calling line. It runs the next time the current coroutine yields control
# (here, `await asyncio.sleep(0)`). On a single thread, nothing else can run
# until *you* step aside.

async def test_create_task_runs_only_after_you_yield() -> None:
    log: list[str] = []

    async def record() -> None:
        log.append("ran")

    task = asyncio.create_task(record())   # scheduled — but the loop hasn't run it
    assert log == []                       # we haven't yielded, so it can't have run
    await asyncio.sleep(0)                  # yield once; the loop now runs the task
    assert log == ["ran"]
    await task                              # already done; just collects the result


# ---------------------------------------------------------------------------
# 8. Single-threaded + cooperative: interleaving happens ONLY at await
# ---------------------------------------------------------------------------
# In C# the runtime can resume continuations on thread-pool threads, so work
# interleaves "for free". In Python everything is on ONE thread, and a coroutine
# runs uninterrupted until it hits an `await`. That await is the only point
# another coroutine can step in.

async def test_await_lets_others_interleave() -> None:
    log: list[str] = []

    async def worker(name: str) -> None:
        log.append(f"{name}-start")
        await asyncio.sleep(0.01)     # yields here; the other worker gets a turn
        log.append(f"{name}-end")

    await asyncio.gather(worker("A"), worker("B"))
    # Both STARTED before either finished — proof they interleaved on one thread.
    assert log == ["A-start", "B-start", "A-end", "B-end"]


async def test_blocking_call_starves_the_loop() -> None:
    log: list[str] = []

    async def blocking_worker(name: str) -> None:
        log.append(f"{name}-start")
        time.sleep(0.01)              # SYNC sleep: never yields, freezes the loop
        log.append(f"{name}-end")

    await asyncio.gather(blocking_worker("A"), blocking_worker("B"))
    # A ran start->end with NO chance for B to interleave: time.sleep holds the
    # single thread the whole time. This is the #1 async Python footgun — a sync
    # call in async code silently serializes everything. In C# the equivalent
    # blocking call would only tie up one thread-pool thread, not the world.
    assert log == ["A-start", "A-end", "B-start", "B-end"]


# ---------------------------------------------------------------------------
# 9. Real CPU parallelism: processes, not threads
# ---------------------------------------------------------------------------
# In C#, Task.Run on the thread pool gives genuine multi-core CPU parallelism.
# In Python it does NOT: the GIL lets only one thread execute Python bytecode at
# a time, so asyncio.to_thread is useless for CPU-bound work — it just shuffles
# the same single-core work between threads.
#
# To actually use multiple cores you spawn separate *processes*, each with its
# own interpreter and its own GIL. ProcessPoolExecutor does this, and
# loop.run_in_executor lets you await the result from async code.
#
# NOTE: the worker must be a module-level function. On Windows, multiprocessing
# uses "spawn", which re-imports this module in each child and pickles the
# function by name — a nested or lambda function can't be pickled.

def cpu_bound(n: int) -> tuple[int, int]:
    """A CPU-bound task. Returns (the worker's process id, the result)."""
    total = sum(i * i for i in range(n))
    return os.getpid(), total


async def test_processpool_gives_real_parallelism() -> None:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=2) as pool:
        (pid_a, result_a), (pid_b, result_b) = await asyncio.gather(
            loop.run_in_executor(pool, cpu_bound, 50_000),
            loop.run_in_executor(pool, cpu_bound, 50_000),
        )

    expected = sum(i * i for i in range(50_000))
    assert result_a == result_b == expected

    # The decisive proof: the work ran in CHILD processes, not this interpreter.
    # Different PID == a separate interpreter == a separate GIL == real
    # multi-core parallelism. asyncio.to_thread (see §5) would have run all of
    # this in THIS process, bottlenecked on the one GIL.
    assert pid_a != os.getpid()
    assert pid_b != os.getpid()
