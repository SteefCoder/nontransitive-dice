from __future__ import annotations

from enum import auto, Enum
from functools import cached_property, cache
from typing import Callable, TypeVar

import gurobipy as gp

from diceset import DiceSet

Var = gp.Var
VarDict = gp.tupledict[int, gp.Var]
VarDict2D = gp.tupledict[tuple[int, int], gp.Var]
VarDict3D = gp.tupledict[tuple[int, int], gp.Var]


class Objective(Enum):
    MAX_MIN_RATIO = auto()
    MAX_AVG_RATIO = auto()
    MAX_WINLOSS = auto()
    MIN_MAX_VALUE = auto()
    MIN_MAX_REPEATS = auto()
    MIN_AVG_REPEATS = auto()


class Constraint(Enum):
    NO_SKIP_VALUES = auto()
    EQUAL_MEAN = auto()
    IS_NONTRANSITIVE = auto()
    MAX_REPEAT = auto()


def enum_dice(faces: list[int]):
    for i in range(len(faces)):
        j = (i + 1) % len(faces)
        yield i, j, faces[i], faces[j]


T = TypeVar("T")

def lazy_var(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func: Callable[..., T]) -> cached_property[T]:
        wrapper = cached_property(func)
        wrapper._type = "var"  # type: ignore[attr-defined]
        wrapper._name = name  # type: ignore[attr-defined]
        wrapper._dependencies = dependencies  # type: ignore[attr-defined]
        return wrapper

    return decorator

def constraint(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func: Callable[..., T]):
        wrapper = cache(func)
        wrapper._type = "constraint"  # type: ignore[attr-defined]
        wrapper._name = name  # type: ignore[attr-defined]
        wrapper._dependencies = dependencies  # type: ignore[attr-defined]
        return wrapper

    return decorator

def objective(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func: Callable[..., T]):
        wrapper = cached_property(func)
        wrapper._type = "objective"  # type: ignore[attr-defined]
        wrapper._name = name  # type: ignore[attr-defined]
        wrapper._dependencies = dependencies  # type: ignore[attr-defined]
        return wrapper

    return decorator


class DiceSolver:
    def __init__(self, faces: int | list[int], dice: int | None = None, min_value: int = 0, max_value: int | None = None) -> None:
        if isinstance(faces, int):
            if dice is None:
                raise ValueError("The number of dice cannot be inferred")
            self.faces = [faces] * dice
        else:
            self.faces = list(faces)

        self.dice = len(self.faces)
        max_value = max_value if max_value is not None else sum(self.faces)
        self.values = list(range(min_value, max_value + 1))
        self.value_idxs = list(range(len(self.values)))
        
        self.model = gp.Model()
        self.objectives = []
        self.constraints = []
        self.variables = []

        # TODO -- recurse through these and detect circular dependencies
        self._dependencies = {}
        self._constraint_fns = {}
        self._objective_fns = {}
        for attr in self.__dict__.values():
            if not hasattr(attr, "_type"):
                continue

            if attr._type == "constraint":
                self._constraint_fns[attr._name] = attr
            elif attr._type == "objective":
                self._objective_fns[attr._name] = attr

            self._dependencies[attr._name] = attr._dependencies
        
    def add_objective(self, objective: str, priority: int = 0, weight: float = 1) -> None:
        if objective not in self._dependencies:
            raise ValueError(f"Objective {objective} not known")

        self.objectives.append((objective, priority, weight))

    def add_constraint(self, constraint: str, *args) -> None:
        # TODO -- add valid arg checking for constraints
        if constraint not in self._dependencies:
            raise ValueError(f"Constraint {constraint} not known")

        self.constraints.append((constraint,) + args)
    
    def build(self) -> None:
        for constraint, *args in self.constraints:
            self._constraint_fns[constraint](self, *args)
        
        last_priority = len(self.objectives)
        for i, (obj, p, w) in enumerate(self.objectives):
            if p is None:
                p = last_priority - 1
            last_priority = p
            expr = self._objective_fns[obj](self)
            self.model.setObjectiveN(expr, i, p, w)

    def solve(self) -> DiceSet:
        raise NotImplementedError
