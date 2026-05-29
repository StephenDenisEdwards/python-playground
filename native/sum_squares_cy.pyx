# cython: language_level=3
"""A CPU-heavy hot loop written in Cython.

Cython compiles this Python-ish source to C, then to a native extension. The
`with nogil:` block RELEASES the GIL exactly like the hand-written C extension's
Py_BEGIN_ALLOW_THREADS (native_demo.c) — so this parallelizes across plain
threads too. The win over raw C is ergonomics: no PyArg_ParseTuple, no manual
refcounting, no module boilerplate — just typed Python.

The `cdef` type declarations are what make it fast: with `n`, `i`, and `total`
typed as C `long long`, the loop compiles to a pure C loop touching no Python
objects, which is also what makes it legal inside `nogil`.
"""


def sum_squares(long long n):
    cdef long long total = 0
    cdef long long i
    with nogil:                       # drop the GIL for the duration of the loop
        for i in range(n):            # compiles to a C for-loop (no Python objects)
            total += i * i
    return total                      # GIL re-held here; safe to build a Python int
