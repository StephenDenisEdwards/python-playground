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

## 11. Handling a CPU-bound worker

§9 proved that processes give real parallelism. This is the shape of an actual worker, plus the practical rules that decide whether it performs well.

**Step 1 — never run it inline.** A CPU-bound call in a coroutine freezes the whole event loop (the §8 footgun):

```python
async def handler(data):
    result = heavy_compute(data)   # ❌ blocks every other task until it returns
```

**Step 2 — don't use threads either.** `to_thread` / `ThreadPoolExecutor` give *no* CPU speedup for pure-Python work — the GIL serializes them (see the full explanation below):

```python
result = await asyncio.to_thread(heavy_compute, data)   # ❌ no parallelism for CPU work
```

**Step 3 — offload to a process pool, awaited from async code:**

```python
from concurrent.futures import ProcessPoolExecutor

# Create the pool ONCE (app startup), not per request — spawning is expensive.
pool = ProcessPoolExecutor(max_workers=os.cpu_count())

async def handler(data):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, heavy_compute, data)  # ✓ loop stays free
```

If you're **not** in async code at all, use the pool directly — the `Parallel.ForEach` equivalent:

```python
with ProcessPoolExecutor() as pool:
    results = list(pool.map(heavy_compute, items))
```

### The rules that make a worker actually perform

- **Create the pool once and reuse it.** Building a pool per request is a common performance bug — each process is a fresh interpreter.
- **Batch the work.** Arguments and results cross the process boundary via `pickle`, so make each unit of work big enough that the compute dwarfs the transfer. `pool.map(fn, items, chunksize=N)` helps; or split the data into batches yourself (see the test `test_cpu_bound_worker_batches_across_processes`).
- **Picklable in, picklable out.** The worker must be a **module-level** function (no lambdas/nested defs) and the data must be picklable — this is the same Windows `spawn` caveat from §9.
- **Bounded by cores, not threads.** `max_workers=os.cpu_count()` is the usual ceiling; more processes than cores just adds context-switching.

### The escape hatch: native libraries that release the GIL

If the heavy work is inside a C/Fortran library — **NumPy, Pandas, SciPy, Polars, image/crypto/compression libs** — those release the GIL during their inner loops. Then **threads parallelize that work**, and `to_thread` / `ThreadPoolExecutor` become viable again with none of the pickling or process-startup cost:

```python
# numpy releases the GIL inside the matmul, so threads run truly in parallel:
await asyncio.to_thread(numpy_heavy_matrix_op, big_array)
```

So the rule is: **pure-Python CPU loop → processes; CPU loop inside a GIL-releasing native lib → threads are fine.** See the runnable `test_numpy_releases_gil_so_threads_parallelize`.

> **Why that test asserts correctness, not speed:** a wall-clock assertion would be flaky, because numpy's BLAS backend is often *already* multi-threaded internally — the serial run may saturate every core too, so fanning out across Python threads adds little (or oversubscribes). The parallelism is real; proving it by the clock is environment-dependent.

### Decision table

| Situation | Use |
|---|---|
| I/O-bound (network, disk, DB) | `asyncio` / `to_thread` / `ThreadPoolExecutor` |
| CPU-bound, pure Python | `ProcessPoolExecutor` + `run_in_executor` |
| CPU-bound inside NumPy/Pandas/native | threads / `to_thread` (GIL is released) |
| CPU-bound, no async app at all | `ProcessPoolExecutor.map` or `multiprocessing` |

---

## 12. Writing your own CPU-heavy C function (how numpy does it)

The numpy escape hatch in §11 works because numpy's heavy loops are written in C and **release the GIL**. You can do the same with your own code. `native/native_demo.c` is a real CPython C extension whose hot loop is wrapped in the GIL-releasing macros:

```c
static PyObject *sum_squares(PyObject *self, PyObject *args) {
    long long n, total = 0;
    if (!PyArg_ParseTuple(args, "L", &n)) return NULL;

    Py_BEGIN_ALLOW_THREADS          /* drop the GIL — other threads may run */
    for (long long i = 0; i < n; i++) total += i * i;
    Py_END_ALLOW_THREADS            /* re-acquire before touching Python objects */

    return PyLong_FromLongLong(total);
}
```

Build it with MSVC (setuptools finds the compiler via `vswhere` — no Developer Command Prompt needed):

```
cd native
../.venv/Scripts/python.exe setup.py build_ext --inplace
```

Then `test_c_extension_releases_gil_so_threads_parallelize` imports it and runs four calls across threads via `asyncio.to_thread` — they parallelize, because the GIL is dropped inside the loop. (The test skips if the module hasn't been built.) Drop the `Py_BEGIN/END_ALLOW_THREADS` macros and it would hold the GIL and behave like a pure-Python CPU loop — no parallelism.

### How numpy is implemented, and the modern alternatives

numpy's core is exactly this: a **hand-written CPython C extension** (`numpy._core._multiarray_umath`) that wraps its ufunc inner loops in `NPY_BEGIN_ALLOW_THREADS`. Linear algebra (`@`, `dot`, `solve`) delegates to an external **BLAS/LAPACK** library (OpenBLAS, MKL, Accelerate) that is often multithreaded internally. It's built and shipped as **precompiled wheels** (via `meson-python`), so `pip install numpy` never compiles on the user's machine.

Hand-writing the raw C API is the most control but the most boilerplate. For **new** code, the commonly recommended tools are:

| Tool | What it is | GIL release | C# analogy |
|---|---|---|---|
| **Cython** | Python-ish source → generated C | `with nogil:` | — |
| **pybind11 / nanobind** | Bind existing **C++** | `py::gil_scoped_release` | C++/CLI wrapper |
| **PyO3 + maturin** | Extension in **Rust** (polars, pydantic-core) | `Python::allow_threads` | — |
| **ctypes / cffi** | Call an already-compiled shared library | auto-released during the call | **P/Invoke (`DllImport`)** |
| **Numba** | JIT-compiles numeric Python at runtime | `@njit(nogil=True)` | RyuJIT, for numeric Python |
| **raw CPython C API** | What numpy/CPython themselves use (`native_demo.c`) | manual `Py_BEGIN_ALLOW_THREADS` | a native CLR-aware component |

Rule of thumb: wrapping an existing C lib → `ctypes`/`cffi`; new hot-loop code → **Cython** (or **Numba** for numeric, no build step); a new C++/Rust module → **pybind11/nanobind** or **PyO3**; plain array math → just use numpy/scipy.

---

## The GIL (Global Interpreter Lock) — in full

The **GIL** is a single mutex inside the CPython interpreter that allows **only one thread to execute Python bytecode at a time**, per process. Even on a 16-core machine, your Python threads take turns holding that one lock; only the holder runs Python code.

### The C# contrast

There's nothing like it in .NET. In C#, 16 threads can genuinely run C# code on 16 cores at once — the runtime just makes you responsible for protecting shared state with `lock`. Python flips that: the interpreter holds one big lock *for* you, so two threads simply can't run Python simultaneously in the first place.

```
C# threads:     [core0: T1] [core1: T2] [core2: T3]   ← all running at once
Python threads: [core0: T1] ... T2 waits ... T3 waits  ← one at a time, taking turns
```

### Why it exists

CPython manages memory with **reference counting**, which isn't thread-safe — every object's refcount is incremented/decremented constantly, and making each of those operations individually thread-safe would be slow and complex. The GIL is the cheap shortcut: protect the *entire* interpreter with one lock instead. It also makes writing C extensions far simpler. It's a **CPython implementation detail**, not part of the language spec — Jython and IronPython have no GIL.

### When the GIL is released (why it's not as bad as it sounds)

1. **During blocking I/O.** A thread waiting on a socket, disk, or `time.sleep` drops the GIL so another thread can run. → **I/O-bound threading works fine.**
2. **Inside many C extensions.** NumPy, Pandas, hashing/compression libraries, etc. release the GIL during their heavy C loops. → threads parallelize *that* work.

It only hurts **CPU-bound pure-Python code**, where threads are stuck taking turns on one core:

| Workload | Threads help? |
|---|---|
| I/O-bound (network, disk, DB) | ✅ yes — GIL released while blocked |
| CPU-bound in a native lib (NumPy) | ✅ yes — GIL released in C |
| CPU-bound pure Python | ❌ no — serialized by the GIL |

### How it connects to everything here

- It's *why* `asyncio` is single-threaded and cooperative — no point fighting for multiple threads when only one can run Python at once (§8).
- It's *why* `to_thread` / `ThreadPoolExecutor` give no CPU speedup, and you reach for **processes** (§9, §11) — each process has its own interpreter and therefore its own GIL, so they truly run in parallel.

**Forward-looking note:** Python 3.13+ ships an experimental **free-threaded ("no-GIL") build** (PEP 703), where threads can run Python in parallel like C#'s. It's opt-in and not yet the default, so everything above still applies to the interpreter you're running.

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
