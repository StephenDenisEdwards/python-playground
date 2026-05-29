# Async / Await — for C# Developers

Companion notes to [test_07_async.py](test_07_async.py).

The syntax looks identical to C#. The **execution model is not**. This is the single most important thing to internalize before writing async Python:

> Python's `asyncio` runs your coroutines on **a single thread**, inside an **event loop**.

Compare:

| | C# `async`/`await` | Python `asyncio` |
|---|---|---|
| Underlying scheduler | Thread-pool (`TaskScheduler`) | Single-threaded **event loop** |
| Default parallelism | Real multi-core via threads | None — one thread only |
| CPU-bound work benefits? | Yes (when offloaded to thread pool) | **No** — use `multiprocessing` or `to_thread` |
| Continuations after `await` | Typically resume on a thread-pool thread | Always resume on the event-loop thread |
| Library compatibility | Sync and async work together fine | Calling a blocking sync function **freezes the whole loop** |

Why? **The GIL** (Global Interpreter Lock). CPython only runs one Python bytecode at a time per process. `asyncio` doesn't fight the GIL — it gives up trying to use multiple threads for Python code, and instead uses one thread plus cooperative yields to interleave I/O.

The upshot: **async in Python is for I/O concurrency, not CPU parallelism.** For CPU work, reach for `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`.

---

## The mental map

| C# | Python |
|---|---|
| `Task<T>` | `Awaitable[T]` / `Coroutine[..., T]` |
| `Task.WhenAll(...)` | `asyncio.gather(...)` |
| `Task.Run(...)` | `asyncio.create_task(...)` |
| `Task.Delay(ms)` | `asyncio.sleep(seconds)` |
| `CancellationToken` | `asyncio.Task.cancel()` raises `CancelledError` |
| `Task.WhenAny` | `asyncio.wait(..., return_when=FIRST_COMPLETED)` |
| `Task.WhenAll` (strict) | `asyncio.TaskGroup()` (3.11+) |
| `TaskCompletionSource<T>` | `loop.create_future()` |
| `Parallel.ForEachAsync` (MaxDOP) | `asyncio.Semaphore(n)` |
| `cts.CancelAfter(...)` | `asyncio.timeout(...)` (3.11+) / `wait_for` |
| `AggregateException` | `ExceptionGroup` (3.11+) |
| `await foo()` | `await foo()` ✓ same |

---

## 1. A basic async function

```python
async def fetch_value(delay: float, value: int) -> int:
    await asyncio.sleep(delay)
    return value
```

The `async def` keyword makes this a **coroutine function**. Calling it does **not** run the body — it returns a **coroutine object** that you must `await` (or schedule with `create_task` / `gather` / `asyncio.run`):

```python
fetch_value(0.01, 42)         # returns a coroutine, doesn't run!
await fetch_value(0.01, 42)   # this actually runs it
```

`await` can only appear inside an `async def`. The top-level entry point is usually `asyncio.run(main())`.

`pytest-asyncio` detects `async def test_...` and runs each inside an event loop, which is why the tests work without any explicit `asyncio.run`.

---

## 2. `asyncio.gather` ≈ `Task.WhenAll`

The most common concurrent pattern: run several awaitables together and wait for all of them.

```python
a, b, c = await asyncio.gather(
    fetch_value(0.05, 1),
    fetch_value(0.05, 2),
    fetch_value(0.05, 3),
)
```

If each `fetch_value` is "sleeping" (i.e., waiting on I/O), all three sleeps overlap on the single thread — total wall time ≈ slowest one, not the sum. **This only works because `asyncio.sleep` is async.** A plain `time.sleep` would block the event loop and force them to run serially.

`gather` returns results in argument order, regardless of completion order.

### Error handling

By default, the first exception cancels the others and propagates. To collect *all* results (including exceptions), use `return_exceptions=True`:

```python
results = await asyncio.gather(a(), b(), c(), return_exceptions=True)
# results may include exception objects instead of raising
```

---

## 3. `create_task` — fire-and-track

`asyncio.create_task(coro)` schedules the coroutine on the loop *immediately* and returns a `Task` object you can `await` later (or cancel, or check status):

```python
task = asyncio.create_task(fetch_value(0.01, 7))
# ... do other work here while the task runs ...
result = await task
```

C# parallel: `Task.Run(...)` returning a `Task<T>`. The semantic difference: in C# the work is on a different thread; in Python it's on the same thread, just interleaved.

---

## 4. Cancellation

`task.cancel()` schedules a `CancelledError` to be raised inside the coroutine the next time it suspends. The coroutine can either let it propagate (the default) or catch it to clean up:

```python
task = asyncio.create_task(asyncio.sleep(10))
task.cancel()
with pytest.raises(asyncio.CancelledError):
    await task
```

C# parallel: `CancellationToken` — except in Python it's **pushed** from outside (`task.cancel()`) rather than **polled** from inside. Cleanup happens by catching `CancelledError` in a `try/finally`.

**Don't swallow `CancelledError`** — re-raise after cleanup, otherwise the cancellation effectively fails.

---

## 5. Running blocking work without freezing the loop

If you must call a sync function from async code (no async version exists, e.g., a sync database driver), use `asyncio.to_thread`:

```python
def blocking_compute(n):
    time.sleep(0.02)
    return n * n

result = await asyncio.to_thread(blocking_compute, 6)
```

`to_thread` offloads the call to the default thread pool executor and returns an awaitable. The event loop stays responsive.

**For CPU-bound work**, threads are gated by the GIL — `to_thread` doesn't help. Use `loop.run_in_executor(ProcessPoolExecutor(), ...)` or `multiprocessing` instead.

---

## 6. Coroutines are "cold"; C# Tasks are "hot"

The first thing that bites a C# dev. In C#, calling an async method **starts** it:

```csharp
Task<int> t = FetchAsync();   // already running on the thread pool
int x = await t;              // await just collects the result
```

In Python, calling an `async def` runs **none** of the body — it builds an inert coroutine object that does nothing until you `await` it (or schedule it):

```python
coro = record()      # body has NOT run
await coro           # NOW it runs
```

Forget to `await` and you get a `RuntimeWarning: coroutine was never awaited` and zero work done.

---

## 7. `create_task` is "hot" — but cooperative

`asyncio.create_task(coro)` is the closest thing to a C# hot `Task`: it *schedules* the coroutine. But on a single thread it still doesn't run on the calling line — it runs only when the current coroutine next yields control:

```python
task = asyncio.create_task(record())
# body has NOT run yet — we haven't yielded
await asyncio.sleep(0)        # yield once; the loop now runs the task
# body has run
```

Nothing else runs until *you* step aside at an `await`.

---

## 8. Single-threaded + cooperative: interleaving only at `await`

In C# the runtime can resume continuations on thread-pool threads, so work interleaves "for free". In Python everything is on one thread, and a coroutine runs uninterrupted until it hits an `await` — the only point another coroutine can step in.

```python
async def worker(name):
    log.append(f"{name}-start")
    await asyncio.sleep(0.01)     # yields; the other worker gets a turn
    log.append(f"{name}-end")

await asyncio.gather(worker("A"), worker("B"))
# -> A-start, B-start, A-end, B-end   (interleaved)
```

Swap `asyncio.sleep` for a synchronous `time.sleep` and the order becomes `A-start, A-end, B-start, B-end` — `time.sleep` never yields, so A monopolises the single thread. **This is the #1 async Python footgun:** one stray blocking call silently serializes everything. In C# the same blocking call only ties up one thread-pool thread.

---

## 9. Real CPU parallelism: processes, not threads

`asyncio.to_thread` is useless for CPU-bound work — the GIL lets only one thread run Python bytecode at a time. For genuine multi-core parallelism (what C#'s `Task.Run` gives you on the thread pool) you spawn separate *processes*, each with its own interpreter and GIL:

```python
loop = asyncio.get_running_loop()
with ProcessPoolExecutor(max_workers=2) as pool:
    a, b = await asyncio.gather(
        loop.run_in_executor(pool, cpu_bound, 50_000),
        loop.run_in_executor(pool, cpu_bound, 50_000),
    )
```

The test proves it by checking each worker's `os.getpid()` differs from the main process. **Windows caveat:** `multiprocessing` uses `spawn`, which re-imports the module and pickles the worker by name — so the worker must be a module-level function, never a nested function or lambda.

---

## 10. Translating the rest of the C# async toolbox

The sections above cover `WhenAll` (`gather`), `Task.Run` (`create_task` / executors) and `CancellationToken` (`task.cancel()`). Here are the remaining idioms.

### `Task.WhenAny` — first to finish wins

```python
done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
winner = done.pop().result()
for t in pending:
    t.cancel()              # don't leak the losers
```

### Process results as they complete

`asyncio.as_completed` yields awaitables in **completion** order, not submission order:

```python
for finished in asyncio.as_completed(coros):
    result = await finished     # whichever finished first
```

### `TaskGroup` ≈ a stricter `WhenAll`

`asyncio.TaskGroup` (3.11+) is structured concurrency: all children are awaited at block exit, **and if one raises, the siblings are cancelled automatically**. `WhenAll` lets the others keep running after the first fault; `TaskGroup` doesn't.

```python
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(fetch(1))
    t2 = tg.create_task(fetch(2))
# both guaranteed complete here; t1.result(), t2.result()
```

A failure surfaces as an `ExceptionGroup` (the moral equivalent of C#'s `AggregateException`), caught with `except*` or asserted via `BaseExceptionGroup`.

### `TaskCompletionSource<T>` → a `Future`

A settable awaitable you complete from elsewhere — handy for bridging callback APIs into async/await:

```python
future = asyncio.get_running_loop().create_future()
# later, from a callback:
future.set_result(42)
value = await future            # suspends until set_result
```

### Bounded concurrency (`MaxDegreeOfParallelism`)

A `Semaphore` caps how many coroutines run at once:

```python
sem = asyncio.Semaphore(2)      # at most 2 in flight
async def worker(x):
    async with sem:
        return await do_work(x)
await asyncio.gather(*(worker(x) for x in items))
```

### Timeouts (`CancellationTokenSource.CancelAfter`)

```python
async with asyncio.timeout(0.01):   # 3.11+; raises TimeoutError
    await slow_op()
# pre-3.11 / single awaitable: await asyncio.wait_for(slow_op(), 0.01)
```

### The non-equivalents

- **`ConfigureAwait(false)`** — irrelevant in Python. There's no captured `SynchronizationContext`; continuations always resume on the loop thread.
- **Hot-by-default `Task`** — Python coroutines are cold (§6); `create_task` is the opt-in.

---

## Common pitfalls

### Forgetting to `await`

```python
fetch_value(0.01, 42)        # RuntimeWarning: coroutine was never awaited
```

The coroutine object is created and immediately discarded; the body never runs. Linters and Python itself will warn you about this. If you really mean "kick it off and ignore the result," use `asyncio.create_task(...)` so it has somewhere to run.

### Blocking the loop

```python
async def bad():
    time.sleep(5)         # blocks the WHOLE event loop for 5 seconds
```

`time.sleep` is synchronous and CPU-blocking. So is most of the stdlib I/O (`requests`, `socket.recv`, `open(...).read()`, etc.). Use `asyncio.sleep`, an async-aware library, or `to_thread`.

### Mixing async and sync libraries

You can't just `await` a sync HTTP call. Either:
- use an async-aware library (`aiohttp`, `httpx` in async mode, `asyncpg`, `aiofiles`); or
- wrap the sync call with `asyncio.to_thread(sync_fn, args)`.

### Top-level entry point

In an `async def main():` script, you can't just call `main()` — you need to drive the event loop:

```python
if __name__ == "__main__":
    asyncio.run(main())
```

`asyncio.run` creates a loop, runs the coroutine, and closes the loop. Don't create your own loop manually unless you know why.

---

## Quick reference

| Need | C# | Python |
|---|---|---|
| Mark function async | `async Task Foo() {}` | `async def foo():` |
| Suspend on a result | `await task` | `await coro` |
| Wait for all | `await Task.WhenAll(...)` | `await asyncio.gather(...)` |
| Wait for first | `await Task.WhenAny(...)` | `asyncio.wait(..., return_when=FIRST_COMPLETED)` |
| Schedule without awaiting | `Task.Run(...)` | `asyncio.create_task(...)` |
| Wait for all (strict, cancel-on-fault) | — | `async with asyncio.TaskGroup()` |
| Results in finish order | `Task.WhenEach(...)` | `asyncio.as_completed(...)` |
| Settable awaitable | `TaskCompletionSource<T>` | `loop.create_future()` |
| Cap concurrency | `MaxDegreeOfParallelism` | `asyncio.Semaphore(n)` |
| Timeout | `cts.CancelAfter(ms)` | `async with asyncio.timeout(s)` |
| Aggregated failures | `AggregateException` | `ExceptionGroup` |
| Async delay | `Task.Delay(ms)` | `asyncio.sleep(seconds)` |
| Cancel | `cts.Cancel()` | `task.cancel()` |
| Run sync work asynchronously | `Task.Run(() => Sync())` | `await asyncio.to_thread(sync, args)` |
| Real CPU parallelism | `Task.Run(cpuWork)` | `run_in_executor(ProcessPoolExecutor(), ...)` |
| Entry point | `static async Task Main()` | `asyncio.run(main())` |
| Use case | I/O **and** CPU parallelism | I/O concurrency **only** |
