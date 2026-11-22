import math

import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_constraint, lazy_objective, Var, VarDict, VarDict2D, VarDict3D, iter_dice
from diceset import DiceSet

class GeneralDiceSolver(DiceSolver):
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
        super().__init__()
        
    @lazy_var("r", dependencies=["w"])
    def _r(self) -> Var:
        # r is the minimum win ratio of i against (i + 1) % n
        r_upper = 1 - 1 / (4 * math.cos(math.pi / (self.dice + 2)))

        r = self.model.addVar(0, r_upper, name="r")
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

    @lazy_objective("min_avg_repeats", dependencies=["y"])
    def _min_avg_repeats(self):
        return -gp.quicksum(self._y)

    @lazy_objective("max_winloss", dependencies=["q"])
    def _max_winloss(self):
        return -self._q
    
    @lazy_constraint("use_all_n_times", dependencies=["u"])
    def _use_all_n_times(self, n: int):
        for vi in self.value_idxs:
            self.model.addConstr(gp.quicksum(
                self._u[i, k, vi]
                for i in range(self.dice)
                for k in range(self.faces[i])
            ) == n)
    
    @lazy_constraint("use_n_times", dependencies=["u", "y"])
    def _use_n_times(self, n: int):
        for vi in self.value_idxs:
            self.model.addConstr(gp.quicksum(
                self._u[i, k, vi]
                for i in range(self.dice)
                for k in range(self.faces[i])
            ) == n * self._y[vi])
    
    @lazy_constraint("no_skip_values", dependencies=["m", "y"])
    def _no_skip_values(self):
        s = gp.tupledict()
        f = self.faces[0]
        for vi, v in enumerate(self.values[:-1]):
            s[vi] = self.model.addVar(vtype=gp.GRB.BINARY)
            self.model.addConstr(s[vi] >= self._y[vi + 1] - self._y[vi])
            # self.model.addConstr(
            #     self._m - v <= max(self.values) * self._y[vi]
            # )
        self.model.addConstr(s[0] == self._y[0])
        self.model.addConstr(gp.quicksum(s) <= 1)
    
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

    @lazy_constraint("start", dependencies=["x"])
    def _start(self, dice: DiceSet) -> None:
        for i, d in enumerate(dice.dice):
            for k, v in enumerate(d):
                self._x[i, k].Start = v

    @lazy_constraint("balanced", dependencies=["w"])
    def _balanced(self) -> None:
        for i, j, fi, fj in iter_dice(self.faces):
            self.model.addConstr(
                gp.quicksum(
                    self._w[i, k, l]
                    for k in range(fi)
                    for l in range(fj)
                ) * self.faces[0] * self.faces[1] == gp.quicksum(
                    self._w[0, k, l]
                    for k in range(self.faces[0])
                    for l in range(self.faces[1])
                ) * fi * fj
            )

    @lazy_constraint("use_once", dependencies=["u"])
    def _use_once(self):
        for vi in self.value_idxs:
            self.model.addConstr(
                gp.quicksum(
                    self._u[i, k, vi]
                    for i in range(self.dice)
                    for k in range(self.faces[i])
                ) == 1
            )
    
    @lazy_constraint("_value_setter", dependencies=["u"])
    def _value_setter(self):
        self._u

    def set_values(self, values: list[int]):
        if self._build_started:
            raise Exception("Cannot set values after starting build (variable dimensions are already set)")

        self.values = values
        self.value_idxs = list(range(len(values)))
        self.add_constraint("_value_setter")

    def _get_result(self) -> DiceSet:
        return DiceSet([
            [round(self._x[i, k].X) for k in range(self.faces[i])]
            for i in range(self.dice)
        ])

    @lazy_var("ws", dependencies=["x"])
    def _ws(self) -> VarDict3D:
        ws = gp.tupledict()
        for i, j, fi, fj in iter_dice(self.faces):
            # Virtual faces: all (k1,k2) pairs for die i, sorted lex
            # Since x[i,k] is non-decreasing in k, x[i,k1]+x[i,k2] is
            # non-decreasing in k1 and k2 separately.
            virtual_i = [(k1, k2) for k1 in range(fi) for k2 in range(fi)]
            virtual_j = [(l1, l2) for l1 in range(fj) for l2 in range(fj)]
            vi_count = len(virtual_i)  # fi^2
            vj_count = len(virtual_j)  # fj^2

            for p, (k1, k2) in enumerate(virtual_i):
                for q, (l1, l2) in enumerate(virtual_j):
                    ws[i, p, q] = self.model.addVar(
                        vtype=gp.GRB.BINARY,
                        name=f"ws[{i},{p},{q}]"
                    )
                    # ws=1 => sum_i > sum_j  (i.e. diff >= 1)
                    self.model.addGenConstrIndicator(
                        ws[i, p, q], True,
                        self._x[i, k1] + self._x[i, k2] - self._x[j, l1] - self._x[j, l2],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    # ws=0 => sum_i <= sum_j  (i.e. diff <= 0)
                    self.model.addGenConstrIndicator(
                        ws[i, p, q], False,
                        self._x[i, k1] + self._x[i, k2] - self._x[j, l1] - self._x[j, l2],
                        gp.GRB.LESS_EQUAL, 0
                    )

            # # Monotonicity in q (fix p, increase q => sum_j increases => ws can only decrease)
            # for p in range(vi_count):
            #     for q in range(vj_count - 1):
            #         self.model.addConstr(ws[i, p, q + 1] <= ws[i, p, q])

            # # Monotonicity in p (fix q, increase p => sum_i increases => ws can only increase)
            # for p in range(vi_count - 1):
            #     for q in range(vj_count):
            #         self.model.addConstr(ws[i, p, q] <= ws[i, p + 1, q])

        return ws
    
    @lazy_var("rs", dependencies=["ws"])
    def _rs(self) -> Var:
        # r is the minimum win ratio of i against (i + 1) % n
        r_upper = 1 - 1 / (4 * math.cos(math.pi / (self.dice + 2)))

        r = self.model.addVar(0, r_upper, name="r")
        for i, j, fi, fj in iter_dice(self.faces):
            fi2, fj2 = fi*fi, fj*fj

            self.model.addConstr(
                gp.quicksum(
                    self._ws[i, k, l]
                    for k in range(fi2)
                    for l in range(fj2)
                ) >= r * fi2 * fj2
            )
        return r
        
    @lazy_constraint("reverse_nontransitive", dependencies=["ws"])
    def _reverse_nontransitive(self, eps: float = 1e-3):
        self.model.addConstr(self._rs >= 0.5 + eps)

    @lazy_objective("twice_max_min_ratio", dependencies=["r", "rs"])
    def _twice_max_min_ratio(self):
        return -self._rs
    