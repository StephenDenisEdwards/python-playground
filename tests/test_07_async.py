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
import time


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
