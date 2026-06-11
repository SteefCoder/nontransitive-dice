from functools import cached_property, cache, wraps
from typing import Callable, TypeVar
from contextlib import contextmanager

import gurobipy as gp

from diceset import DiceSet

Var = gp.Var
VarDict = gp.tupledict[int, gp.Var]
VarDict2D = gp.tupledict[tuple[int, int], gp.Var]
VarDict3D = gp.tupledict[tuple[int, int, int], gp.Var]


def iter_dice(faces: list[int]):
    for i, fi in enumerate(faces):
        j = (i + 1) % len(faces)
        yield i, j, fi, faces[j]


T = TypeVar("T")
V = TypeVar("V")

def lazy_var(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func: Callable[..., T]) -> cached_property[T]:
        @cached_property
        def wrapper(self):
            if not self._build_started:
                raise Exception("Accessing lazy variable before build start")
            self.variables.append(name)
            return func(self)

        wrapper._type = "var"  # type: ignore[attr-defined]
        wrapper._name = name  # type: ignore[attr-defined]
        wrapper._dependencies = dependencies  # type: ignore[attr-defined]
        return wrapper

    return decorator

def lazy_constraint(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func):
        @wraps(func)
        @cache
        def wrapper(self, *args, **kwargs):
            if not self._build_started:
                raise Exception("Accessing lazy constraint before build start")
            return func(self, *args, **kwargs)
            
        wrapper._type = "constraint"  # type: ignore[attr-defined]
        wrapper._name = name  # type: ignore[attr-defined]
        wrapper._dependencies = dependencies  # type: ignore[attr-defined]

        return wrapper

    return decorator

def lazy_objective(name: str, dependencies: list[str] | None = None):
    dependencies = dependencies or []

    def decorator(func: Callable[..., T]) -> cached_property[T]:
        @cached_property
        def wrapper(self):
            if not self._build_started:
                raise Exception("Accessing lazy objective before build start")
            return func(self)
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

        self._build_started = False

        # TODO -- recurse through these and detect circular dependencies
        self._dependencies = {}
        self._constraint_fns = {}
        self._objective_fns = {}
        for name in dir(self):
            if not hasattr(self.__class__, name):
                continue

            attr = getattr(self.__class__, name)
            if not hasattr(attr, "_type"):
                continue

            if attr._type == "constraint":
                self._constraint_fns[attr._name] = name
            elif attr._type == "objective":
                self._objective_fns[attr._name] = name

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
    
    def _build(self) -> None:
        self._build_started = True

        for constraint, *args in self.constraints:
            fn = getattr(self, self._constraint_fns[constraint])
            fn(*args)
        
        last_priority = len(self.objectives)
        for i, (obj, p, w) in enumerate(self.objectives):
            if p is None:
                p = last_priority - 1
            last_priority = p
            expr = getattr(self, self._objective_fns[obj])
            self.model.setObjectiveN(expr, i, p, w)

    def _get_result(self) -> DiceSet:
        raise NotImplementedError
    
    @contextmanager
    def build(self):
        if not self._build_started:
            self._build()

        try:
            yield self
        finally:
            self.model.close()

    def solve(self) -> DiceSet:
        if not self._build_started:
            self._build()

        self.model.optimize()
        return self._get_result()
