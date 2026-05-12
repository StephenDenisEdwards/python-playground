"""
Python's object model from a C# perspective.

Key differences:
  - No 'new' keyword: Foo() constructs.
  - 'self' is the explicit first parameter of every instance method (== 'this').
  - Dunder methods (__init__, __eq__, __len__, ...) implement language protocols.
  - @dataclass auto-generates ctor/Equals/ToString — the closest thing to C# records.
  - Multiple inheritance is allowed; C3 MRO defines lookup order.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 1. A plain class
# ---------------------------------------------------------------------------
# Compare to C#:
#   public class Point {
#       public double X { get; }
#       public double Y { get; }
#       public Point(double x, double y) { X = x; Y = y; }
#       public double DistanceFromOrigin() => Math.Sqrt(X*X + Y*Y);
#   }

class Point:
    """A simple immutable-by-convention 2D point."""

    def __init__(self, x: float, y: float) -> None:
        # __init__ is the *initializer* (not strictly a ctor).
        # 'self' is explicit; you must use 'self.x = x' to store state.
        self.x = x
        self.y = y

    def distance_from_origin(self) -> float:
        # Every instance method takes 'self' as first parameter.
        return (self.x ** 2 + self.y ** 2) ** 0.5

def test_plain_class() -> None:
    p = Point(3, 4)            # no 'new' keyword
    assert p.distance_from_origin() == 5.0


# ---------------------------------------------------------------------------
# 2. Dunder methods drive language protocols
# ---------------------------------------------------------------------------
# Implementing __eq__ enables ==.    (In C# you override Equals + ==)
# Implementing __len__ enables len(). (In C# you implement ICollection.Count)
# Implementing __repr__ enables a developer-friendly string.

class Money:
    def __init__(self, amount: int, currency: str) -> None:
        self.amount = amount
        self.currency = currency

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        # Required if you override __eq__ AND want to use the object in sets/dicts.
        return hash((self.amount, self.currency))

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency!r})"   # !r = use repr()

def test_dunders_drive_protocols() -> None:
    a = Money(100, "GBP")
    b = Money(100, "GBP")
    c = Money(100, "USD")
    assert a == b                          # __eq__
    assert a != c
    assert {a, b, c} == {a, c}             # __hash__ allows set membership
    assert repr(a) == "Money(100, 'GBP')"  # __repr__


# ---------------------------------------------------------------------------
# 3. @dataclass — Python's nearest equivalent to a C# record
# ---------------------------------------------------------------------------
# Auto-generates __init__, __repr__, __eq__ from the declared fields.
# Add frozen=True for record-like immutability.

@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    tags: list[str] = field(default_factory=list)  # MUST use default_factory
                                                    # for mutable defaults!

def test_dataclass_is_like_a_record() -> None:
    a = Customer(1, "Alice", ["vip"])
    b = Customer(1, "Alice", ["vip"])
    assert a == b                              # structural equality, no boilerplate
    assert repr(a) == "Customer(id=1, name='Alice', tags=['vip'])"


# ---------------------------------------------------------------------------
# 4. Properties — when you DO need C#-style 'get'/'set'
# ---------------------------------------------------------------------------
# Most of the time you just expose attributes directly. Wrap with @property only
# when you need validation or computed values — the call site is unchanged
# (no parentheses), so refactoring is cheap.

class Temperature:
    def __init__(self, celsius: float) -> None:
        self._celsius = celsius            # leading underscore = "internal"

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        # Computed property — no setter, so it's read-only.
        return self._celsius * 9 / 5 + 32

def test_properties() -> None:
    t = Temperature(100)
    assert t.celsius == 100              # attribute access, NOT t.celsius()
    assert t.fahrenheit == 212
    t.celsius = 0
    assert t.fahrenheit == 32

    import pytest
    with pytest.raises(ValueError):
        t.celsius = -300                 # validator runs


# ---------------------------------------------------------------------------
# 5. Inheritance and super()
# ---------------------------------------------------------------------------

class Animal:
    def __init__(self, name: str) -> None:
        self.name = name
    def speak(self) -> str:
        return "(silence)"

class Dog(Animal):                          # parens contain the base classes
    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name)              # super() is parameterless here
        self.breed = breed
    def speak(self) -> str:                 # no 'override' keyword
        return "Woof!"

def test_inheritance() -> None:
    d = Dog("Rex", "Lab")
    assert d.speak() == "Woof!"
    assert isinstance(d, Animal)


# ---------------------------------------------------------------------------
# 6. Multiple inheritance and the Method Resolution Order (MRO)
# ---------------------------------------------------------------------------
# C# disallows multiple class inheritance. Python allows it; method lookup uses
# the C3 linearization algorithm, exposed via ClassName.__mro__.
# Common pattern: small "mixin" classes that add capabilities.

class JSONSerializableMixin:
    def to_json(self) -> str:
        import json
        return json.dumps(self.__dict__)

class TimestampedMixin:
    def stamp(self) -> str:
        return f"@stamp {self.name}"        # relies on a sibling having .name

class User(JSONSerializableMixin, TimestampedMixin):
    def __init__(self, name: str) -> None:
        self.name = name

def test_multiple_inheritance_and_mro() -> None:
    u = User("Alice")
    assert u.to_json() == '{"name": "Alice"}'
    assert u.stamp() == "@stamp Alice"
    # MRO controls which base provides a method when multiple do.
    mro_names = [c.__name__ for c in User.__mro__]
    assert mro_names == ["User", "JSONSerializableMixin", "TimestampedMixin", "object"]


# ---------------------------------------------------------------------------
# 7. Class methods and static methods
# ---------------------------------------------------------------------------
# @staticmethod          -> like C# 'static'  (no implicit first arg)
# @classmethod           -> like C# 'static', but receives the *class* as 'cls'
#                            (useful for alternative constructors).

class Date:
    def __init__(self, y: int, m: int, d: int) -> None:
        self.y, self.m, self.d = y, m, d

    @classmethod
    def today(cls) -> "Date":               # cls allows subclasses to get their own type
        import datetime
        t = datetime.date.today()
        return cls(t.year, t.month, t.day)

    @staticmethod
    def is_leap(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def test_class_and_static_methods() -> None:
    assert Date.is_leap(2024)
    assert not Date.is_leap(2023)
    today = Date.today()
    assert isinstance(today, Date)
