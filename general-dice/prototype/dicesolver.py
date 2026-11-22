from enum import auto, Enum
from functools import cached_property

import gurobipy as gp

from diceset import DiceSet

TupleVarDict = gp.tupledict[tuple[int, ...], gp.Var]
IntVarDict = gp.tupledict[int, gp.Var]

class Objective(Enum):
    MAX_MIN_RATIO = auto()
    MAX_AVG_RATIO = auto()
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

class DiceSolver:
    def __init__(self, faces: int | list[int], dice: int | None = None, min_value: int = 0, max_value: int | None = None) -> None:
        if isinstance(faces, int):
            if dice is None:
                raise ValueError("The number of dice cannot be inferred")
            self.faces = [faces] * dice
        else:
            self.faces = list(faces)

        self.dice = len(self.faces)
        # self.min_value = min_value
        max_value = max_value if max_value is not None else sum(self.faces)
        self.values = list(range(min_value, max_value + 1))
        self.value_idxs = list(range(len(self.values)))
        
        self.model = gp.Model()
        self.objectives = []
        self.constraints = []
        self.used_vars = []

    def add_objective(self, objective: Objective, priority: int = 0, weight: float = 1) -> None:
        raise NotImplementedError


class GeneralDiceSolver(DiceSolver):
    @cached_property
    def _r(self) -> gp.Var:
        # r is the minimum win ratio of i against (i + 1) % n
        self.used_vars.append("r")
        r = self.model.addVar(0, 0.75)
        for i, j, fi, fj in enum_dice(self.faces):
            self.model.addConstr(
                gp.quicksum(
                    self._w[i, k, l]
                    for k in range(fi)
                    for l in range(fj)
                ) >= r * fi * fj
            )
        return r
    
    @cached_property
    def _m(self) -> gp.Var:
        self.used_vars.append("m")

        # m is the highest number used
        m = self.model.addVar(min(self.values), max(self.values), vtype=gp.GRB.INTEGER)
        for i in range(self.dice):
            for k in range(self.faces[i]):
                self.model.addConstr(self._x[i, k] <= m)
        return m

    @cached_property
    def _u(self) -> TupleVarDict:
        self.used_vars.append("u")

        # u = 1 if the kth face of the ith dice is the vi'th value
        u = gp.tupledict()
        for i in range(self.dice):
            for k in range(self.faces[i]):
                for vi in self.value_idxs:
                    u[i, k, vi] = self.model.addVar(vtype=gp.GRB.BINARY)
                self.model.addConstr(
                    gp.quicksum(u[i, k, vi] for vi in self.value_idxs) == 1
                )
                self.model.addConstr(
                    gp.quicksum(u[i, k, vi] * v for vi, v in enumerate(self.values)) == self._x[i, k]
                )
        return u
    
    @cached_property
    def _q(self) -> TupleVarDict:
        self.used_vars.append("q")

        q = gp.tupledict()
        # q[i, k1, k2] = 1 if x[i, k1] == x[i, k2]
        for i in range(self.dice):
            for k in range(self.faces[i] - 1):
                M = max(self.values) - min(self.values)
                q[i, k] = self.model.addVar(vtype=gp.GRB.BINARY)
                self.model.addConstr(
                    1 - q[i, k] <= self._x[i, k + 1] - self._x[i, k]
                )
                self.model.addConstr(
                    M * (1 - q[i, k]) >= self._x[i, k + 1] - self._x[i, k]
                )
                #self.model.addGenConstrIndicator(
                #    q[i, k], True,
                #    self._x[i, k] - self._x[i, k + 1],
                #    gp.GRB.EQUAL, 0
                #)
        return q
    
    @cached_property
    def _s(self) -> TupleVarDict:
        self.used_vars.append("s")

        s = gp.tupledict()
        for i in range(self.dice):
            fi = self.faces[i]
            for k in range(fi - 1):
                s[i, k] = self.model.addVar(vtype=gp.GRB.BINARY)
                self.model.addConstr(s[i, k] <= fi * self._q[i, k])
                self.model.addConstr(s[i, k] >= self._q[i, k])
            
            for k in range(fi - 2):
                self.model.addConstr(
                    s[i, k + 1] <= s[i, k] + 1 + fi * (1 - self._q[i, k + 1])
                )
                self.model.addConstr(
                    s[i, k + 1] >= s[i, k] + 1 - fi * (1 - self._q[i, k + 1])
                )
        return s

    @cached_property
    def _w(self) -> TupleVarDict:
        self.used_vars.append("w")

        # w = 1 if x[i, k] > x[j, l]
        w = gp.tupledict()
        for i, j, fi, fj in enum_dice(self.faces):
            for k in range(fi):
                for l in range(fj):
                    w[i, k, l] = self.model.addVar(vtype=gp.GRB.BINARY, name="w")
                    self.model.addGenConstrIndicator(
                        w[i, k, l], True,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                for l in range(fj - 1):
                    self.model.addConstr(w[i, k, l + 1] <= w[i, k, l])
                    
            for k in range(fi - 1):
                for l in range(fj):
                    self.model.addConstr(w[i, k, l] <= w[i, k + 1, l])
                    
        return w
    
    @cached_property
    def _x(self) -> TupleVarDict:
        self.used_vars.append("x")

        # x[i, k] is the kth number on the ith dice
        x = gp.tupledict()
        for i in range(self.dice):
            for k in range(self.faces[i]):
                x[i, k] = self.model.addVar(min(self.values), max(self.values), vtype=gp.GRB.INTEGER)
            for k in range(self.faces[i] - 1):
                self.model.addConstr(x[i, k] <= x[i, k + 1])
        return x

    @cached_property
    def _y2(self) -> IntVarDict:
        self.used_vars.append("y2")

        # y2 = 1 if v is used in general
        y = self.model.addVars(len(self.values), vtype=gp.GRB.BINARY)
        for vi in self.value_idxs:
            s = gp.quicksum(
                self._u[i, k, vi]
                for i in range(self.dice)
                for k in range(self.faces[i])
            )
            self.model.addConstr(s >= y[vi])
            # self.model.addConstr(y[vi] * sum(self.faces) >= s)
        return y
    
    @cached_property
    def _z1(self) -> IntVarDict:
        self.used_vars.append("z1")

        # z1 is the maximum amount of times a value is repeated on dice i,
        z = self.model.addVars(self.dice, lb=0, ub=max(self.faces), vtype=gp.GRB.INTEGER)

        #for i in range(self.dice):
        #    for vi in self.value_idxs:
        #        self.model.addConstr(
        #            z[i] >= gp.quicksum(self._u[i, k, vi] for k in range(self.faces[i]))
        #        )
        #    self.model.addConstr(z[i] <= self.faces[i])
        for i in range(self.dice):
            self.model.addGenConstrMax(z[i], [self._s[i, k] for k in range(self.faces[i] - 1)])
        return z

    @cached_property
    def _z2(self) -> gp.Var:
        self.used_vars.append("z2")

        # z2 is the max of z1
        z = self.model.addVar(0, max(self.faces), vtype=gp.GRB.INTEGER)

        for i in range(self.dice):
            for vi in self.value_idxs:
                self.model.addConstr(
                    z >= gp.quicksum(self._u[i, k, vi] for k in range(self.faces[i]))
                )
        # self.model.addGenConstrMax(z, self._s)

        return z
    
    def _set_objective(self, objective: Objective, index: int, priority: int, weight: float = 1) -> gp.LinExpr | gp.Var:
        if objective == Objective.MAX_MIN_RATIO:
            expr = -self._r
        elif objective == Objective.MAX_AVG_RATIO:
            expr = -gp.quicksum(self._w)
        elif objective == Objective.MIN_MAX_VALUE:
            expr = self._m
        elif objective == Objective.MIN_MAX_REPEATS:
            expr = self._z2
        elif objective == Objective.MIN_AVG_REPEATS:
            expr = -gp.quicksum(self._y2)
        else:
            raise ValueError(f"Objective {objective} not known")
        
        self.model.setObjectiveN(expr, index, priority, weight)
        return expr
    
    def _set_constraint(self, constraint: Constraint, *args) -> None:
        if constraint == Constraint.NO_SKIP_VALUES:
            for vi, v in enumerate(self.values):
                self.model.addConstr(
                    self._m - v <= max(self.values) * self._y2[vi]
                )
  
        elif constraint == Constraint.EQUAL_MEAN:
            for i, j, fi, fj in enum_dice(self.faces):
                self.model.addConstr(
                    gp.quicksum(self._x[i, k] for k in range(fi)) * fj ==
                    gp.quicksum(self._x[j, l] for l in range(fj)) * fi
                )
        elif constraint == Constraint.IS_NONTRANSITIVE:
            eps = args[0] if args else 1e-3
            self.model.addConstr(self._r >= 0.5 + eps)
        elif constraint == Constraint.MAX_REPEAT:
            repeat = [args[0]] * self.dice if isinstance(args[0], int) else args[0]
            for i in range(self.dice):
                self.model.addConstr(self._z1[i] <= repeat[i])
        else:
            raise ValueError(f"Constraint {constraint} not known")

    def set_values(self, values: list[int]) -> None:
        self.values = values
        self.value_idxs = list(range(len(values)))

    def add_objective(self, objective: Objective, priority: int | None = None, weight: float = 1) -> None:
        self.objectives.append((objective, priority, weight))

    def add_constraint(self, constraint: Constraint, *args) -> None:
        self.constraints.append((constraint,) + args)

    def build(self) -> None:
        last_priority = len(self.objectives)
        for i, (obj, p, w) in enumerate(self.objectives):
            if p is None:
                p = last_priority - 1
            last_priority = p
            self._set_objective(obj, i, p, w)

        for c, *args in self.constraints:
            self._set_constraint(c, *args)
    
    def solve(self) -> DiceSet:
        self.model.optimize()
        dice = [
            [round(self._x[i, k].X) for k in range(self.faces[i])]
            for i in range(self.dice)
        ]
        return DiceSet(dice)


def prime_list(n: int) -> list[int]:
    primes = []
    for i in range(2, n + 1):
        for p in primes:
            if i % p == 0:
                break
        else:
            primes.append(i)
    return primes


def main():
    solver = GeneralDiceSolver(faces=[12, 12, 12])

    solver.add_objective(Objective.MAX_MIN_RATIO)
    solver.add_objective(Objective.MAX_AVG_RATIO)
    #solver.add_objective(Objective.MIN_MAX_REPEATS)
    #solver.add_objective(Objective.MIN_AVG_REPEATS)
    solver.add_objective(Objective.MIN_MAX_VALUE)
    primes = prime_list(100)
    solver.set_values(primes)
    #nums = list(range(-50, 50))
    #solver.set_values(nums)

    solver.add_constraint(Constraint.MAX_REPEAT, 0)
    # solver.add_constraint(Constraint.NO_SKIP_VALUES)
    solver.add_constraint(Constraint.EQUAL_MEAN)
    solver.build()
    solver._u
    #solver.model.addConstr(solver._r >= 0.675)
    #solver.model.addConstr(gp.quicksum(solver._w) == 421)
    #start = [[7, 7, 7, 59, 59, 59], [3, 3, 5, 47, 47, 53, 53, 53], [2, 2, 37, 41, 41, 41, 41, 41, 41, 43], [23, 29, 29, 29, 29, 29, 31, 31, 31, 31, 31, 73], [11, 11, 13, 13, 17, 19, 19, 19, 19, 19, 19, 19, 19, 61, 61, 61, 61, 61, 67, 71]]
    #for i, d in enumerate(start):
    #    for k, v in enumerate(d):
    #        solver._x[i, k].Start = v
    solver.model.Params.MIPFocus = 3
    solver.model.Params.NoRelHeurTime = 10
    solver.model.Params
    dice = solver.solve()
    #print([[solver._q[i, k].X for k in range(solver.faces[i] - 1)] for i in range(solver.dice)])
    print(solver.used_vars)
    #print([[solver._s[i, k].X for k in range(solver.faces[i] - 1)] for i in range(solver.dice)])
    print(dice)
    print(dice.count_win_ratios())

if __name__ == '__main__':
    main()
