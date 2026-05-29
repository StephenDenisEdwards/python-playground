"""Build the Cython sum_squares_cy extension in place.

Run from this directory:

    ../.venv/Scripts/python.exe setup_cython.py build_ext --inplace

Needs `pip install Cython` plus a C compiler (MSVC on Windows; setuptools finds
it via vswhere). cythonize() generates sum_squares_cy.c from the .pyx, then
setuptools compiles it to sum_squares_cy.*.pyd next to this file. The async
tests add this directory to sys.path and import it (skipping if absent).
"""
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="sum_squares_cy",
    ext_modules=cythonize("sum_squares_cy.pyx", language_level=3),
)
