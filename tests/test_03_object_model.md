# Python's Object Model — for C# Developers

Companion notes to [test_03_object_model.py](test_03_object_model.py).

Python is fully object-oriented — *everything* is an object, including functions and classes themselves. But the surface differs from C# in several places that matter when you start writing classes.

Headline differences:
- **No `new` keyword.** `Foo()` constructs an instance.
- **`self` is explicit** — the first parameter of every instance method, equivalent to C#'s implicit `this`.
- **Dunder methods** (`__init__`, `__eq__`, `__len__`, ...) implement language protocols. Implementing them is how you "operator overload."
- **`@dataclass`** is Python's nearest equivalent to a C# `record`.
- **Multiple inheritance** is allowed; the C3 linearization algorithm defines lookup order.

---

## 1. A plain class

C#:
```csharp
public class Point {
    public double X { get; }
    public double Y { get; }
    public Point(double x, double y) { X = x; Y = y; }
    public double DistanceFromOrigin() => Math.Sqrt(X*X + Y*Y);
}
```

Python:
```python
class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

p = Point(3, 4)            # no 'new'
p.distance_from_origin()   # 5.0
```

Key things to notice:
- `__init__` is the **initializer**, not strictly a constructor. The object is created by Python *before* `__init__` runs (in `__new__`); `__init__` just fills it in. You rarely override `__new__`.
- **`self` is explicit.** You must write `self.x = x` to attach state to the instance. Forgetting `self.` makes `x` a local variable that vanishes at return time.
- There's no field-declaration syntax — attributes "exist" once `self.x = ...` runs.

---

## 2. Dunder methods drive the language

"Dunder" = **d**ouble **under**score. These methods hook into Python's built-in operations:

| You implement... | ...and now this works | C# parallel |
|---|---|---|
| `__init__` | construction | constructor |
| `__eq__` | `a == b` | override `Equals` / `==` |
| `__hash__` | hashing into `set`/`dict` | override `GetHashCode` |
| `__repr__` | `repr(a)` and debugger display | `override ToString()` (developer-facing) |
| `__str__` | `str(a)` and `print(a)` | `override ToString()` (user-facing) |
| `__len__` | `len(a)` | `ICollection.Count` |
| `__iter__` | `for x in a:` | `IEnumerable.GetEnumerator` |
| `__add__` | `a + b` | `operator +` overload |
| `__lt__`, `__le__`, etc. | `<`, `<=`, ... | `IComparable<T>` |

**Important pairing:** if you override `__eq__`, also override `__hash__`. Otherwise, Python sets `__hash__ = None`, making your object unhashable (can't put it in a `set` or use as a `dict` key). This is the language version of C#'s warning about overriding `Equals` without `GetHashCode`.

Returning `NotImplemented` from `__eq__` when the type doesn't match lets Python try the reflected operation on the other operand — the canonical "we don't know how to compare these" signal.

The `!r` in `f"Money({self.amount}, {self.currency!r})"` means "use `repr()` for this value" — useful in `__repr__` so strings appear with quotes around them.

---

## 3. `@dataclass` — Python's closest thing to a C# record

For value-object-like classes, the boilerplate of writing `__init__`, `__eq__`, `__repr__` by hand is tedious. `@dataclass` generates them from your declared fields:

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    tags: list[str] = field(default_factory=list)
```

| `@dataclass` option | C# parallel |
|---|---|
| (default) | mutable POCO with auto-generated `Equals`/`ToString` |
| `frozen=True` | `record` — immutable, structural equality |
| `slots=True` | no field-bag dict (smaller memory footprint) |
| `order=True` | auto-generates `<`, `<=`, etc. |

**Critical gotcha:** **`field(default_factory=list)` for mutable defaults.** Writing `tags: list[str] = []` would re-trigger the [mutable-default trap from test_00](test_00_defining_functions.md#7-the-mutable-default-argument-trap). The dataclass decorator actually raises an error if you try, but the *reason* is the same.

Modern alternatives:
- **`pydantic.BaseModel`** — like dataclasses but with runtime validation/coercion.
- **`attrs`** — the older third-party library that inspired dataclasses; still richer.

---

## 4. Properties — `@property` when you need `get`/`set`

In C#, every public field is conventionally a property (`public int X { get; set; }`). In Python, the convention is the **opposite**: just expose `self.x` directly. Only wrap with `@property` when you need:
- validation,
- computed values, or
- a read-only attribute.

The call site is **unchanged** between a plain attribute and a `@property` (no parens) — so promoting one to the other is a non-breaking refactor:

```python
class Temperature:
    def __init__(self, celsius: float) -> None:
        self._celsius = celsius        # _ = "internal" convention

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:     # no setter -> read-only
        return self._celsius * 9 / 5 + 32

t = Temperature(100)
t.celsius                 # 100  (no parens — looks like a field)
t.fahrenheit              # 212
t.celsius = 0             # invokes the setter
```

Compare to C#'s `public double Celsius { get => ...; set { validate; ... } }` — same idea, different keyword sugar.

---

## 5. Inheritance and `super()`

```python
class Animal:
    def __init__(self, name: str) -> None:
        self.name = name
    def speak(self) -> str:
        return "(silence)"

class Dog(Animal):                       # base class in parentheses
    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name)           # parameterless super()
        self.breed = breed
    def speak(self) -> str:              # no 'override' keyword
        return "Woof!"
```

Notes for a C# reader:
- The base class goes in **parentheses after the class name**, not after a colon.
- **No `override` keyword.** Any method with the same name in a subclass overrides. There is no virtual/non-virtual distinction — all methods are effectively virtual.
- `super()` (parameterless since Python 3) returns a proxy that calls the next class in the MRO. Equivalent to C#'s `base.Method(...)`.
- `isinstance(d, Animal)` works exactly like C#'s `d is Animal`.

---

## 6. Multiple inheritance and the MRO

C# forbids inheriting from multiple classes (only interfaces). Python allows it:

```python
class User(JSONSerializableMixin, TimestampedMixin):
    ...
```

The order in `User.__mro__` ("Method Resolution Order") determines which base provides a method when multiple bases define it. Python uses the **C3 linearization** algorithm — a deterministic, predictable order that respects subclass-before-base and left-to-right declaration order.

**The mixin pattern**: small classes that add one capability each (`SerializableMixin`, `TimestampedMixin`, ...). Combine them by listing all parents in the class declaration. This is the practical use case — full diamond-inheritance hierarchies are rare and discouraged.

In C# you'd use interfaces with default methods (C# 8+) or composition for the same effect.

---

## 7. `@classmethod` and `@staticmethod`

| Decorator | First parameter | C# parallel |
|---|---|---|
| (none) | `self` (instance) | regular instance method |
| `@classmethod` | `cls` (the class itself) | static factory method that knows its own type |
| `@staticmethod` | (none — no implicit first arg) | plain `static` method |

```python
class Date:
    def __init__(self, y, m, d): ...

    @classmethod
    def today(cls) -> "Date":              # 'cls' is Date (or a subclass)
        t = datetime.date.today()
        return cls(t.year, t.month, t.day)

    @staticmethod
    def is_leap(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
```

The classic use of `@classmethod` is **alternative constructors** — `dict.fromkeys(...)`, `datetime.now()` style. Because `cls` reflects the actual class at call time, a subclass calling `Subclass.today()` gets a `Subclass` instance back, automatically.

`@staticmethod` is essentially "a free function that happens to live in this namespace" — useful for organization.

---

## Quick reference

| Concept | C# | Python |
|---|---|---|
| Construct | `new Foo()` | `Foo()` |
| `this` | implicit | `self` (explicit first parameter) |
| Constructor | `public Foo(...)` | `def __init__(self, ...)` |
| Override | `override` keyword | just redefine the method |
| Call base | `base.Method()` | `super().method()` |
| Equality | `override Equals` + `==` | `def __eq__(self, other)` |
| Hash | `override GetHashCode` | `def __hash__(self)` |
| Property | `public T X { get; set; }` | `@property` + `@x.setter` |
| Computed/readonly | `=> ...` getter | `@property` with no setter |
| Record-like | `record Customer(int Id, string Name)` | `@dataclass(frozen=True)` |
| Static method | `static` | `@staticmethod` |
| Factory | `static Foo Create(...)` | `@classmethod def create(cls, ...)` |
| Multiple inheritance | no (interfaces only) | yes — listed in parens, C3 MRO |
| "Internal" | `internal` / `private` | `_leading_underscore` convention |
