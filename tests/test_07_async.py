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

import pytest


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


# ---------------------------------------------------------------------------
# 10. Translating the rest of the C# async toolbox
# ---------------------------------------------------------------------------
# The idioms above cover WhenAll (gather), Task.Run (create_task / executors)
# and CancellationToken (task.cancel). Here are the remaining ones a C# dev
# reaches for, each mapped to its asyncio equivalent.


# --- 10a. Task.WhenAny --------------------------------------------------------
# C#:  Task winner = await Task.WhenAny(t1, t2);
# Python: asyncio.wait with return_when=FIRST_COMPLETED gives you the finished
# set and the still-pending set. Cancel the stragglers yourself.

async def test_when_any_first_completed() -> None:
    fast = asyncio.create_task(fetch_value(0.01, "fast"))
    slow = asyncio.create_task(fetch_value(1.00, "slow"))

    done, pending = await asyncio.wait(
        {fast, slow}, return_when=asyncio.FIRST_COMPLETED
    )

    assert fast in done and slow in pending
    assert fast.result() == "fast"

    for task in pending:                 # don't leak the loser — cancel it
        task.cancel()


# --- 10b. Streaming results as they finish -----------------------------------
# C# has no direct WhenEach until recent versions; asyncio.as_completed yields
# awaitables in *completion* order (not submission order), so you can process
# each result the moment it's ready.

async def test_as_completed_yields_in_finish_order() -> None:
    order: list[str] = []
    coros = [
        fetch_value(0.03, "c"),
        fetch_value(0.01, "a"),
        fetch_value(0.02, "b"),
    ]
    for finished in asyncio.as_completed(coros):
        order.append(await finished)

    # Sorted by delay, regardless of the order we submitted them.
    assert order == ["a", "b", "c"]


# --- 10c. TaskGroup ≈ a stricter Task.WhenAll --------------------------------
# C#:  await Task.WhenAll(t1, t2);
# asyncio.TaskGroup (3.11+) is structured concurrency: all tasks are awaited at
# block exit, AND if any one raises, the siblings are cancelled automatically.
# WhenAll lets the others keep running after the first fault; TaskGroup doesn't.

async def test_taskgroup_awaits_all_children() -> None:
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch_value(0.01, 1))
        t2 = tg.create_task(fetch_value(0.02, 2))
    # Outside the block both are guaranteed complete.
    assert (t1.result(), t2.result()) == (1, 2)


async def test_taskgroup_cancels_siblings_on_failure() -> None:
    sibling_cancelled = False

    async def faulty() -> None:
        raise ValueError("boom")

    async def long_sibling() -> None:
        nonlocal sibling_cancelled
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            sibling_cancelled = True       # the group cancelled us
            raise

    # A failure inside the group surfaces as an ExceptionGroup (3.11+), which is
    # the moral equivalent of C#'s AggregateException.
    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(long_sibling())
            tg.create_task(faulty())

    assert sibling_cancelled is True
    assert any(isinstance(e, ValueError) for e in excinfo.value.exceptions)


# --- 10d. TaskCompletionSource<T> → a Future ---------------------------------
# C#:  var tcs = new TaskCompletionSource<int>(); ... tcs.SetResult(42);
# Python: a Future is a settable awaitable you complete from elsewhere — handy
# for bridging callback-based APIs into async/await.

async def test_future_as_task_completion_source() -> None:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[int] = loop.create_future()

    # Simulate an external callback completing the future a bit later.
    def on_done() -> None:
        future.set_result(42)

    loop.call_later(0.01, on_done)         # like a timer firing the callback

    result = await future                  # suspends until set_result is called
    assert result == 42


# --- 10e. Bounded concurrency (Parallel.ForEachAsync MaxDegreeOfParallelism) --
# C#:  new ParallelOptions { MaxDegreeOfParallelism = 2 }
# Python: a Semaphore caps how many coroutines hold the resource at once.

async def test_semaphore_bounds_concurrency() -> None:
    in_flight = 0
    peak = 0
    sem = asyncio.Semaphore(2)             # at most 2 running at a time

    async def worker() -> None:
        nonlocal in_flight, peak
        async with sem:
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1

    await asyncio.gather(*(worker() for _ in range(6)))
    assert peak == 2                       # never more than the semaphore allows


# --- 10f. Timeouts (CancellationTokenSource.CancelAfter) ---------------------
# C#:  cts.CancelAfter(TimeSpan.FromMilliseconds(10));
# Python: asyncio.timeout (3.11+) cancels the block and raises TimeoutError.

async def test_timeout_cancels_a_slow_operation() -> None:
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.01):
            await fetch_value(1.0, "too slow")
