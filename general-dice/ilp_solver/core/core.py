from functools import cached_property, cache, wraps
from typing import Callable, TypeVar
from contextlib import contextmanager

import gurobipy as gp

from diceset import DiceSet


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
    # TODO -- add objective sense
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


class SolverBase:
    def __init__(self) -> None:
        self.model = gp.Model()
        self.objectives = []
        self.constraints = []
        self.variables = []

        self._build_started = False

    def __init_subclass__(cls) -> None:
        # TODO -- recurse through these and detect circular dependencies
        cls._dependencies: dict[str, list[str]] = {}
        cls._constraint_fns: dict[str, str] = {}
        cls._objective_fns: dict[str, str] = {}
        for name, attr in vars(cls).items():
            if not hasattr(attr, "_type"):
                continue

            if attr._type == "constraint":
                cls._constraint_fns[attr._name] = name
            elif attr._type == "objective":
                cls._objective_fns[attr._name] = name

            cls._dependencies[attr._name] = attr._dependencies
    
    def add_objective(self, objective: str, priority: int | None = None, weight: float = 1) -> None:
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

        if len(self.objectives) == 1:
            obj = self.objectives[0][0]
            expr = getattr(self, self._objective_fns[obj])
            self.model.setObjective(expr)
        else:
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

    def solve(self) -> DiceSet | None:
        if not self._build_started:
            self._build()

        self.model.optimize()
        try:
            return self._get_result()
        except AttributeError:
            return None