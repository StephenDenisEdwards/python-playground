/* A CPU-heavy CPython C extension — the same technique numpy uses.
 *
 * sum_squares(n) computes  sum(i*i for i in range(n))  in a tight C loop.
 * The interesting part is Py_BEGIN_ALLOW_THREADS / Py_END_ALLOW_THREADS: they
 * RELEASE the GIL around the loop, so while this runs, other Python threads can
 * execute. That is exactly why numpy-heavy work parallelizes across threads
 * (numpy wraps its inner loops in the same macros). Without these macros the
 * function would hold the GIL the whole time and behave like pure-Python CPU
 * code — no parallelism (see test_07_async.py §9).
 *
 * For C# devs: this is the rough equivalent of writing a native component and
 * P/Invoking it, except the C is compiled against CPython's own C API and the
 * GIL is the lock you explicitly drop to let other "threads" proceed.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *sum_squares(PyObject *self, PyObject *args) {
    long long n;
    if (!PyArg_ParseTuple(args, "L", &n)) {
        return NULL;
    }

    long long total = 0;
    Py_BEGIN_ALLOW_THREADS          /* drop the GIL: other threads may run now */
    for (long long i = 0; i < n; i++) {
        total += i * i;
    }
    Py_END_ALLOW_THREADS            /* re-acquire the GIL before touching Python objects */

    return PyLong_FromLongLong(total);
}

static PyMethodDef methods[] = {
    {"sum_squares", sum_squares, METH_VARARGS,
     "sum_squares(n) -> sum of i*i for i in range(n); releases the GIL during the loop."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "native_demo",
    "CPU-heavy C extension that releases the GIL (numpy-style).",
    -1,
    methods,
};

PyMODINIT_FUNC PyInit_native_demo(void) {
    return PyModule_Create(&module);
}
