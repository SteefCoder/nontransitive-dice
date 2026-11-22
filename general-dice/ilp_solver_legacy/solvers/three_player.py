import math

import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_constraint, lazy_objective, Var, VarDict, VarDict2D, VarDict3D, VarDictND
from diceset import DiceSet


def iter_distinct_dice(faces: list[int]):
    for i, fi in enumerate(faces):
        for j, fj in enumerate(faces):
            if i != j:
                yield i, j, fi, fj


class ThreePlayerSolver(DiceSolver):
    def __init__(self, faces: int | list[int], dice: int | None = None, min_value: int = 1, max_value: int | None = None) -> None:
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
        self.Q = {i ** 2 % self.dice for i in range(1, self.dice)}

        super().__init__()

    def _get_result(self) -> DiceSet:
        return DiceSet([
            [round(self._x[i, k].X) for k in range(self.faces[i])]
            for i in range(self.dice)
        ])
                
    @lazy_var("x")
    def _x(self) -> VarDict2D:
        # x[i, k] is the kth number on the ith dice
        x = gp.tupledict()
        for i in range(self.dice):
            for k in range(self.faces[i]):
                x[i, k] = self.model.addVar(min(self.values), max(self.values), vtype=gp.GRB.INTEGER, name=f"x[{i},{k}]")
            for k in range(self.faces[i] - 1):
                self.model.addConstr(x[i, k] <= x[i, k + 1])
        return x

    @lazy_var("w", dependencies=["x"])
    def _w(self) -> VarDictND:
        # w = 1 if x[i, k] > x[j, l]
        w = gp.tupledict()
        for i, j, fi, fj in iter_distinct_dice(self.faces):
            if (j - i) % self.dice in self.Q:
                continue
            print(i, j)
            for k in range(fi):
                for l in range(fj):
                    wi = self.model.addVar(vtype=gp.GRB.BINARY, name=f"w[{i},{j},{k},{l}]")
                    w[i, j, k, l] = wi
                    w[j, i, l, k] = 1 - wi
                    self.model.addGenConstrIndicator(
                        wi, True,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    self.model.addGenConstrIndicator(
                        wi, False,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.LESS_EQUAL, 0
                    )

                for l in range(fj - 1):
                    self.model.addConstr(w[i, j, k, l + 1] <= w[i, j, k, l])

            for k in range(fi - 1):
                for l in range(fj):
                    self.model.addConstr(w[i, j, k, l] <= w[i, j, k + 1, l])

        # for i, j, fi, fj in iter_distinct_dice(self.faces):

        #     for k in range(fi):
        #         for l in range(fj):
        #             w[i, j, k, l] = 1 - w[j, i, l, k]
        #             #self.model.addConstr(w[i, j, k, l] + w[j, i, l, k] <= 1)

        return w
    
    @lazy_var("tr", dependencies=["w"])
    def _tr(self) -> VarDict2D:
        r = gp.tupledict()
        for i, j, fi, fj in iter_distinct_dice(self.faces):
            # if j - i not in self.Q:
            #     continue
            r[i, j] = self.model.addVar(vtype=gp.GRB.INTEGER)

            self.model.addConstr(gp.quicksum(
                self._w[i, j, k, l]
                for k in range(fi)
                for l in range(fj)
            ) == r[i, j])

        return r
    
    @lazy_var("t", dependencies=["w"])
    def _t(self) -> VarDict2D:
        t = gp.tupledict()
        _t = gp.tupledict()

        for i in range(self.dice):
            _t[i] = self.model.addVar(vtype=gp.GRB.BINARY)

        for i, j, fi, fj in iter_distinct_dice(self.faces):
            # if abs(j - i) not in self.Q:
            #     continue
            t[i, j] = _t[(i - j) % self.dice]
            t[j, i] = 1 - t[i, j]

            self.model.addGenConstrIndicator(
                t[i, j], True,
                self._tr[i, j], gp.GRB.GREATER_EQUAL, 1 + fi * fj // 2
            )
            self.model.addGenConstrIndicator(
                t[i, j], False,
                self._tr[i, j], gp.GRB.LESS_EQUAL, fi * fj // 2
            )

        # for i in range(self.dice):
        #     for j in range(i):
        #         self.model.addConstr(t[i, j] + t[j, i] <= 1)
        return t
    
    @lazy_var("p4", dependencies=["t"])
    def _p4(self) -> VarDictND:
        p = gp.tupledict()
        for i in range(self.dice):
            for j in range(i):
                for k in range(j):
                    for l in range(self.dice):
                        if l in (i, j, k):
                            continue

                        p[i, j, k, l] = self.model.addVar(vtype=gp.GRB.BINARY)
                        self.model.addGenConstrAnd(p[i, j, k, l], [self._t[l, i], self._t[l, j], self._t[l, k]])

        return p
    
    @lazy_var("p3", dependencies=["t"])
    def _p3(self) -> VarDict3D:
        p = gp.tupledict()
        for i in range(self.dice):
            for j in range(i):
                for k in range(self.dice):
                    if k in (i, j):
                        continue

                    p[i, j, k] = self.model.addVar(vtype=gp.GRB.BINARY)
                    self.model.addGenConstrAnd(p[i, j, k], [self._t[k, i], self._t[k, j]])

        return p

    @lazy_constraint("full_four_player", dependencies=["p4"])
    def _full_four_player(self):
        for i in range(self.dice):
            for j in range(i):
                for k in range(j):
                    self.model.addConstr(gp.quicksum(
                        self._p4[i, j, k, l]
                        for l in range(self.dice)
                        if l not in (i, j, k)
                    ) >= 1)

    @lazy_constraint("full_three_player", dependencies=["t"])
    def _full_three_player(self):

        for i in self.Q:
            self.model.addConstr(self._t[i, 0] == 1)

        for i in range(self.dice):
            # for j in range(i):
            #     self.model.addConstr(gp.quicksum(
            #         self._p3[i, j, k]
            #         for k in range(self.dice)
            #         if k not in (i, j)
            #     ) >= 1)
            break
            self.model.addConstr(self._t[i, (i + 1) % self.dice] == 1)
            self.model.addConstr(
                gp.quicksum(self._t[i, j] for j in range(self.dice) if i != j) == 
                gp.quicksum(self._t[0, j] for j in range(1, self.dice))
            )

    @lazy_constraint("nontransitive", dependencies=["t"])
    def _nontransitive(self):
        for i in range(self.dice):
            j = (i + 1) % self.dice
            self.model.addConstr(self._t[i, j] == 1)

    @lazy_constraint("three_player", dependencies=["t"])
    def _three_player(self):
        for i in range(self.dice):
            j = (i + 1) % self.dice
            k = (i + 2) % self.dice
            self.model.addConstr(self._t[i, j] == 1)
            self.model.addConstr(self._t[i, k] == 1)

    @lazy_objective("max_full", dependencies=["t", "tr"])
    def _max_full(self):
        r = self.model.addVar(0, 0.75)

        for i, j, fi, fj in iter_distinct_dice(self.faces):
            self.model.addConstr(r <= self._tr[i, j] / (fi * fj) + (1 - self._t[i, j]))
        
        return -r
    
    @lazy_objective("max_full_int", dependencies=["t", "tr"])
    def _max_full_int(self):
        r = self.model.addVar(0, 0.75 * self.faces[0] ** 2)

        for i, j, fi, fj in iter_distinct_dice(self.faces):
            self.model.addConstr(r <= self._tr[i, j] + fi * fj * (1 - self._t[i, j]))
        
        return -r
    
    @lazy_constraint("equal_mean", dependencies=["x"])
    def _equal_mean(self):
        for i in range(self.dice):
            fi, f0 = self.faces[i], self.faces[0]
            self.model.addConstr(
                gp.quicksum(self._x[i, k] for k in range(fi)) * f0 ==
                gp.quicksum(self._x[0, l] for l in range(f0)) * fi
            )