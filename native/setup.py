"""Build the native_demo C extension in place.

Run from this directory:

    ../.venv/Scripts/python.exe setup.py build_ext --inplace

setuptools locates MSVC automatically (via vswhere), so no Developer Command
Prompt is needed. The resulting native_demo.*.pyd lands next to this file; the
async tests add this directory to sys.path and import it (skipping if absent).
"""
from setuptools import Extension, setup

setup(
    name="native_demo",
    version="0.0.0",
    ext_modules=[Extension("native_demo", ["native_demo.c"])],
)
