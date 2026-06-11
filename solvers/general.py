import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_constraint, lazy_objective, Var, VarDict, VarDict2D, VarDict3D, iter_dice
from diceset import DiceSet

class GeneralDiceSolver(DiceSolver):
    @lazy_var("r", dependencies=["w"])
    def _r(self) -> Var:
        # r is the minimum win ratio of i against (i + 1) % n
        r = self.model.addVar(0, 0.75, name="r")
        for i, j, fi, fj in iter_dice(self.faces):
            self.model.addConstr(
                gp.quicksum(
                    self._w[i, k, l]
                    for k in range(fi)
                    for l in range(fj)
                ) >= r * fi * fj
            )
        return r
    
    @lazy_var("q", dependencies=["w", "w2"])
    def _q(self) -> gp.Var:
        q = self.model.addVar(0, 1, name="q")
        for i, j, fi, fj in iter_dice(self.faces):
            self.model.addConstr(
                # gp.quicksum(
                #     self._w2[i, k, l]
                #     for k in range(fi)
                #     for l in range(fj)
                # ) <= q * gp.quicksum(
                #     self._w[i, k, l]
                #     for k in range(fi)
                #     for l in range(fj)
                # )
                gp.quicksum(
                    self._w[i, k, l] - self._w2[i, k, l]
                    for k in range(fi)
                    for l in range(fj)
                ) >= q * fi * fj
            )
            self.model.addConstr(
                gp.quicksum(
                    self._w[i, k, l]
                    for k in range(fi)
                    for l in range(fj)
                ) >= 1
            )
        return q

    @lazy_var("m", dependencies=["x"])
    def _m(self) -> gp.Var:
        # m is the highest number used
        m = self.model.addVar(min(self.values), max(self.values), vtype=gp.GRB.INTEGER, name="m")
        for i in range(self.dice):
            for k in range(self.faces[i]):
                self.model.addConstr(self._x[i, k] <= m)
        return m

    @lazy_var("u", dependencies=["x"])
    def _u(self) -> VarDict3D:
        # u = 1 if the kth face of the ith dice is the vi'th value
        u = gp.tupledict()
        for i in range(self.dice):
            for k in range(self.faces[i]):
                for vi in self.value_idxs:
                    u[i, k, vi] = self.model.addVar(vtype=gp.GRB.BINARY, name=f"u[{i},{k},{vi}]")
                self.model.addConstr(
                    gp.quicksum(u[i, k, vi] for vi in self.value_idxs) == 1
                )
                self.model.addConstr(
                    gp.quicksum(u[i, k, vi] * v for vi, v in enumerate(self.values)) == self._x[i, k]
                )
        return u
    
    @lazy_var("w", dependencies=["x"])
    def _w(self) -> VarDict3D:
        # w = 1 if x[i, k] > x[j, l]
        w = gp.tupledict()
        for i, j, fi, fj in iter_dice(self.faces):
            for k in range(fi):
                for l in range(fj):
                    w[i, k, l] = self.model.addVar(vtype=gp.GRB.BINARY, name=f"w[{i},{k},{l}]")
                    self.model.addGenConstrIndicator(
                        w[i, k, l], True,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    self.model.addGenConstrIndicator(
                        w[i, k, l], False,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.LESS_EQUAL, 0
                    )
                    
                for l in range(fj - 1):
                    self.model.addConstr(w[i, k, l + 1] <= w[i, k, l])
                    
            for k in range(fi - 1):
                for l in range(fj):
                    self.model.addConstr(w[i, k, l] <= w[i, k + 1, l])
                    
        return w
    
    @lazy_var("w2", dependencies=["x"])
    def _w2(self) -> VarDict3D:
        # w = 1 if x[i, k] > x[j, l]
        w = gp.tupledict()
        for i, j, fi, fj in iter_dice(self.faces):
            for k in range(fi):
                for l in range(fj):
                    w[i, k, l] = self.model.addVar(vtype=gp.GRB.BINARY, name=f"w2[{i},{k},{l}]")
                    self.model.addGenConstrIndicator(
                        w[i, k, l], True,
                        self._x[j, l] - self._x[i, k],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    self.model.addGenConstrIndicator(
                        w[i, k, l], False,
                        self._x[j, l] - self._x[i, k],
                        gp.GRB.LESS_EQUAL, 0
                    )
                    
                for l in range(fj - 1):
                    self.model.addConstr(w[i, k, l + 1] >= w[i, k, l])
                    
            for k in range(fi - 1):
                for l in range(fj):
                    self.model.addConstr(w[i, k, l] >= w[i, k + 1, l])
                    
        return w

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

    @lazy_var("y", dependencies=["u"])
    def _y(self) -> VarDict:
        # y = 1 if v is used in general
        y = self.model.addVars(len(self.values), vtype=gp.GRB.BINARY, name="y")
        for vi in self.value_idxs:
            s = gp.quicksum(
                self._u[i, k, vi]
                for i in range(self.dice)
                for k in range(self.faces[i])
            )
            self.model.addConstr(s >= y[vi])
            # self.model.addConstr(y[vi] * sum(self.faces) >= s)
        return y
    
    @lazy_var("z", dependencies=["u"])
    def _z(self) -> VarDict:
        # z is the maximum amount of times a value is repeated on dice i,
        z = self.model.addVars(self.dice, lb=0, ub=max(self.faces), vtype=gp.GRB.INTEGER, name="z")

        for i in range(self.dice):
            for vi in self.value_idxs:
                self.model.addConstr(
                    z[i] >= gp.quicksum(self._u[i, k, vi] for k in range(self.faces[i]))
                )
            self.model.addConstr(z[i] <= self.faces[i])
        return z

    @lazy_var("z2", dependencies=["z"])
    def _z2(self) -> gp.Var:
        # z2 is the max of z1
        z = self.model.addVar(0, max(self.faces), vtype=gp.GRB.INTEGER, name="z2")

        self.model.addGenConstrMax(z, self._z)

        return z
    
    @lazy_objective("max_min_ratio", dependencies=["r"])
    def _max_min_ratio(self):
        return -self._r
    
    @lazy_objective("max_avg_ratio", dependencies=["w"])
    def _max_avg_ratio(self):
        return -gp.quicksum(self._w)
    
    @lazy_objective("min_max_value", dependencies=["m"])
    def _min_max_value(self):
        return self._m

    @lazy_objective("min_max_repeats", dependencies=["z2"])
    def _min_max_repeats(self):
        return self._z2

    @lazy_objective("min_avg_repeats", dependencies=["z2"])
    def _min_avg_repeats(self):
        return -gp.quicksum(self._y)

    @lazy_objective("max_winloss", dependencies=["z2"])
    def _max_winloss(self):
        return -self._q

    @lazy_constraint("no_skip_values", dependencies=["m", "y"])
    def _no_skip_values(self):
        for vi, v in enumerate(self.values):
            self.model.addConstr(
                self._m - v <= max(self.values) * self._y[vi]
            )
    
    @lazy_constraint("equal_mean", dependencies=["x"])
    def _equal_mean(self):
        for i, j, fi, fj in iter_dice(self.faces):
            self.model.addConstr(
                gp.quicksum(self._x[i, k] for k in range(fi)) * fj ==
                gp.quicksum(self._x[j, l] for l in range(fj)) * fi
            )
  
    @lazy_constraint("is_nontransitive", dependencies=["r"])
    def _is_nontransitive(self, eps: float = 1e-3):
        self.model.addConstr(self._r >= 0.5 + eps)

    @lazy_constraint("max_repeat", dependencies=["x"])
    def _max_repeat(self, repeat: int | list[int]):
        repeat = [repeat] * self.dice if isinstance(repeat, int) else repeat
        for i in range(self.dice):
            for k in range(self.faces[i] - repeat[i]):
                self.model.addConstr(self._x[i, k] + 1 <= self._x[i, k + repeat[i]])

    def set_values(self, values: list[int]):
        self.values = values
        self.value_idxs = list(range(len(values)))

    @lazy_constraint("set_start", dependencies=["x"])
    def set_start(self, dice: DiceSet) -> None:
        for i, d in enumerate(dice.dice):
            for k, v in enumerate(d):
                self._x[i, k].Start = v

    def _get_result(self) -> DiceSet:
        return DiceSet([
            [round(self._x[i, k].X) for k in range(self.faces[i])]
            for i in range(self.dice)
        ])
