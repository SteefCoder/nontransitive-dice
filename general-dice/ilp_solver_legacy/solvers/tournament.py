import math

import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_constraint, lazy_objective, Var, VarDict, VarDict2D, VarDict3D, VarDictND
from diceset import DiceSet
from tqdm import tqdm


def iter_distinct_dice(tournament: list[list[int]]):
    dice = len(tournament)
    for i in range(dice):
        for j in range(dice):
            if tournament[i][j]:
                yield i, j


class TournamentSolver(DiceSolver):
    def __init__(self, faces: int, tournament: list[list[int]], enforce_losses: bool = False) -> None:
        self.dice = len(tournament)
        self.tournament = tournament
        self.enforce_losses = enforce_losses
        self.faces = faces
        self.max_value = self.faces * self.dice - 1

        super().__init__()

    def set_start(self, *starts: DiceSet) -> None:
        self.model.NumStart = len(starts)
        for i, dice in enumerate(starts):
            self.model.Params.StartNumber = i
            for i, die in enumerate(dice.dice):
                for j, v in enumerate(die):
                    self._x[i, j].Start = v

            for i, j in iter_distinct_dice(self.tournament):
                for k in range(self.faces):
                    for l in range(self.faces):
                        self._w[i, j, k, l].Start = int(dice.dice[i][k] > dice.dice[j][l])

    def _get_result(self) -> DiceSet:
        return DiceSet([
            [round(self._x[i, k].X) for k in range(self.faces)]
            for i in range(self.dice)
        ])
    
    @lazy_var("x")
    def _x(self) -> VarDict2D:
        # x[i, k] is the kth number on the ith dice
        x = gp.tupledict()
        for i in range(self.dice):
            for k in range(self.faces):
                x[i, k] = self.model.addVar(0, self.max_value, vtype=gp.GRB.INTEGER, name=f"x[{i},{k}]")
            for k in range(self.faces - 1):
                self.model.addConstr(x[i, k] <= x[i, k + 1])
        return x

    @lazy_var("w", dependencies=["x"])
    def _w(self) -> VarDictND:
        # w = 1 if x[i, k] > x[j, l]
        w = gp.tupledict()
        for i, j in tqdm(iter_distinct_dice(self.tournament)):
            for k in range(self.faces):
                for l in range(self.faces):
                    wi = self.model.addVar(vtype=gp.GRB.BINARY, name=f"w[{i},{j},{k},{l}]")
                    w[i, j, k, l] = wi
                    self.model.addGenConstrIndicator(
                        wi, True,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    self.model.addGenConstrIndicator(
                        wi, False,
                        self._x[i, k] - self._x[j, l],
                        gp.GRB.LESS_EQUAL, -1
                    )

                for l in range(self.faces - 1):
                    self.model.addConstr(w[i, j, k, l + 1] <= w[i, j, k, l])

            for k in range(self.faces - 1):
                for l in range(self.faces):
                    self.model.addConstr(w[i, j, k, l] <= w[i, j, k + 1, l])

        return w

    @lazy_var("tr", dependencies=["w"])
    def _tr(self) -> VarDict2D:
        r = gp.tupledict()
        for i, j in iter_distinct_dice(self.tournament):
            r[i, j] = self.model.addVar(vtype=gp.GRB.INTEGER)
            
            self.model.addConstr(gp.quicksum(
                self._w[i, j, k, l]
                for k in range(self.faces)
                for l in range(self.faces)
            ) == r[i, j])

        return r
    
    @lazy_constraint("constraint_tournament_weak", dependencies=["w"])
    def _constraint_tournament_weak(self):
        for i, j in iter_distinct_dice(self.tournament):
            self.model.addConstr(
                self._tr[i, j] - self._tr[j, i] >= 1
            )

    @lazy_constraint("constraint_tournament_strong", dependencies=["w"])
    def _constraint_tournament_strong(self):
        for i, j in iter_distinct_dice(self.tournament):
            self.model.addConstr(
                self._tr[i, j] >= 1 + self.faces**2 // 2
            )

        # for i in range(self.dice):
        #     self.model.addConstr(gp.quicksum(
        #         self._x[i, k] for k in range(self.faces)
        #     ) == self.faces * (self.dice * self.faces - 1) // 2)

    @lazy_objective("max_min_ratio")
    def _max_min_ratio(self):
        r = self.model.addVar(0, 0.75)
        for i, j in iter_distinct_dice(self.tournament):
            if self.tournament[i][j]:
                self.model.addConstr(
                    r <= self._tr[i, j] / (self.faces * self.faces)
                )
        return -r

    @lazy_objective("min_slack")
    def _min_slack(self):
        s = gp.tupledict()
        threshold = self.faces**2 // 2 + 1
        for i, j in iter_distinct_dice(self.tournament):
            s[i, j] = self.model.addVar(lb=0, ub=self.faces**2, vtype=gp.GRB.INTEGER)
            self.model.addConstr(self._tr[i, j] + s[i, j] >= threshold)
        
        # for i in range(self.dice):
        #     self.model.addConstr(gp.quicksum(
        #         self._x[i, k] for k in range(self.faces)
        #     ) == self.faces * (self.dice * self.faces - 1) // 2)

        # max_s = self.model.addVar(lb=0, ub=3, vtype=gp.GRB.INTEGER)
        # for i in range(self.dice):
        #     self.model.addConstr(gp.quicksum(s[i, j] for j in range(self.dice) if self.tournament[i][j]) <= max_s)

        return s.sum()


class BlockTournamentSolver(DiceSolver):
    def __init__(self, faces: int, tournament: list[list[int]], enforce_losses: bool = False) -> None:
        self.dice = len(tournament)
        self.tournament = tournament
        self.enforce_losses = enforce_losses
        self.faces = faces

        super().__init__()

    @lazy_var("x")
    def _x(self):
        x = gp.tupledict()
        for i in range(self.faces):
            for d in range(self.dice):
                print(i, d)
                x[i, d] = self.model.addVar(0, vtype=gp.GRB.INTEGER)
                
        return x

    @lazy_var("w")
    def _w(self):
        w = gp.tupledict()
        for i in range(self.faces):
            for d1 in range(self.dice):
                for d2 in range(d1):
                    print(i, d1, d2)
                    w[i, d1, d2] = self.model.addVar(vtype=gp.GRB.BINARY)
                    self.model.addGenConstrIndicator(
                        w[i, d1, d2], True,
                        self._x[i, d1] - self._x[i, d2],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    self.model.addGenConstrIndicator(
                        w[i, d1, d2], False,
                        self._x[i, d1] - self._x[i, d2],
                        gp.GRB.LESS_EQUAL, -1
                    )

                    w[i, d2, d1] = 1 - w[i, d1, d2]
        return w
    
    @lazy_constraint("main")
    def _main(self):
        for d1 in range(self.dice):
            for d2 in range(d1):
                if d1 == d2:
                    continue

                if self.tournament[d1][d2]:
                    self.model.addConstr(gp.quicksum(
                        2*self._w[i, d1, d2] - 1
                        for i in range(self.faces)
                    ) >= 1)
                else:
                    self.model.addConstr(gp.quicksum(
                        2*self._w[i, d1, d2] - 1
                        for i in range(self.faces)
                    ) <= -1)


    def _get_result(self) -> DiceSet:
        dice = [
            [round(self._x[i, d].X) for i in range(self.faces)]
            for d in range(self.dice)
        ]
        for i in range(self.faces):
            for d in range(self.dice):
                dice[d][i] += i * self.faces
        return DiceSet(dice)

class TournamentCreator(DiceSolver):
    def __init__(self, dice: int) -> None:
        self.dice = dice
        super().__init__()

    def _get_result(self) -> list[list[int]]:
        return [
            [round(self._t[i, j].X) if i != j else 0 for j in range(self.dice)]
            for i in range(self.dice)
        ]

    @lazy_var("t")
    def _t(self) -> VarDict2D:
        t = gp.tupledict()
        for i in range(self.dice):
            for j in range(self.dice):
                if i == j:
                    continue
                t[i, j] = self.model.addVar(vtype=gp.GRB.BINARY)

        for i in range(self.dice):
            for j in range(i):
                self.model.addConstr(t[i, j] + t[j, i] <= 1)
        return t
    
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

    @lazy_constraint("three_player", dependencies=["p3"])
    def _full_three_player(self):
        for i in range(self.dice):
            for j in range(i):
                self.model.addConstr(gp.quicksum(
                    self._p3[i, j, k]
                    for k in range(self.dice)
                    if k not in (i, j)
                ) >= 1)

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

    @lazy_constraint("full_four_player", dependencies=["p4"])
    def _full_four_player(self):
        for i in range(self.dice):
            # for j in range(i):
            #     for k in range(j):
            #         self.model.addConstr(gp.quicksum(
            #             self._p4[i, j, k, l]
            #             for l in range(self.dice)
            #             if l not in (i, j, k)
            #         ) >= 1)
            self.model.addConstr(gp.quicksum(
                self._t[i, j] for j in range(self.dice) if i != j
            ) == 9)
            self.model.addConstr(self._t[i, (i + 1) % self.dice] == 1)
    
    @lazy_constraint("n_player")
    def _n_player(self, n):
        for i in range(self.dice):
            self.model.addConstr(gp.quicksum(
                self._t[i, j] for j in range(self.dice) if i != j
            ) == n)
            self.model.addConstr(self._t[i, (i + 1) % self.dice] == 1)


class NPlayerTournamentCreator(DiceSolver):
    def __init__(self, dice: int, n: int) -> None:
        self.dice = dice
        self.n = n
        super().__init__()
    
    @lazy_var("a")
    def _a(self):
        return self.model.addVars(self.dice, vtype=gp.GRB.BINARY)
    
    @lazy_var("p3")
    def _p3(self) -> VarDict3D:
        p = gp.tupledict()
        d = (self.dice - 1) // 2
        for i in range(self.dice):
            for v1 in range(1, self.dice):
                for v2 in range(1, d + 1):
                    p[i, v1, v2] = self.model.addVar(vtype=gp.GRB.BINARY)
                    self.model.addGenConstrAnd(
                        p[i, v1, v2],
                        [self._a[i], self._a[(i + v1) % self.dice], self._a[(i + v2) % self.dice]]
                    )
        return p

    @lazy_var("p4")
    def _p4(self) -> VarDict3D:
        p = gp.tupledict()
        d = (self.dice - 1) // 2
        for i in range(self.dice):
            for v1 in range(1, self.dice):
                for v2 in range(1, d + 1):
                    #for v3 in range(1, d + 1):
                    p[i, v1, v2] = self.model.addVar(vtype=gp.GRB.BINARY)
                    self.model.addGenConstrAnd(
                        p[i, v1, v2],
                        [self._a[i], self._a[(i + v1) % self.dice], self._a[(i + v2) % self.dice]]
                    )
        return p

    @lazy_constraint("main", dependencies=["a"])
    def _main(self):
        d = (self.dice - 1) // 2
        for v1 in range(1, self.dice):
            for v2 in range(1, d + 1):
                self.model.addConstr(gp.quicksum(
                    self._p3[i, v1, v2]
                    for i in range(self.dice)
                ) >= 1)
        self.model.addConstr(gp.quicksum(self._a) == d)
        self.model.addConstr(self._a[0] == 0)

        for i in range(1, d + 1):
            self.model.addConstr(self._a[i] + self._a[self.dice - i] == 1)
    
    def _get_result(self) -> list[list[int]]:
        a = [round(self._a[i].X) for i in range(self.dice)]
        tournament = []
        for i in range(self.dice):
            tournament.append(a)
            a = [a[-1]] + a[:-1]
        return tournament