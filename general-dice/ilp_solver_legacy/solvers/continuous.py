import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_objective, lazy_constraint, Var, VarDict, VarDict2D, VarDict3D


class ContinuousDiceSolver(DiceSolver):
    def __init__(self, dice: int, distinct: int, max_value: int | None = None) -> None:
        self.dice = dice
        self.distinct = distinct
        self.max_value = max_value or dice * distinct

        super().__init__()

    @lazy_var("x")
    def _x(self) -> VarDict2D:
        x = self.model.addVars(self.dice, self.distinct, lb=0, ub=self.max_value, vtype=gp.GRB.INTEGER)
        
        for i in range(self.dice):
            for k in range(self.distinct - 1):
                self.model.addConstr(x[i, k] + 1 <= x[i, k + 1])

        return x  # type: ignore
    
    @lazy_var("y", dependencies=["a", "b"])
    def _y(self) -> VarDict2D:
        y = self.model.addVars(self.dice, self.distinct, lb=0, ub=1)
        for i in range(self.dice):
            self.model.addConstr(gp.quicksum(y[i, k] for k in range(self.distinct)) == 1)
        return y  # type: ignore
    
    @lazy_var("w", dependencies=["x"])
    def _w(self) -> VarDict3D:
        w = self.model.addVars(self.dice, self.distinct, self.distinct, vtype=gp.GRB.BINARY)

        for i in range(self.dice):
            j = (i + 1) % self.dice
            for k in range(self.distinct):
                for l in range(self.distinct):
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
                
                for l in range(self.distinct - 1):
                    self.model.addConstr(w[i, k, l + 1] <= w[i, k, l])
                    
            for k in range(self.distinct - 1):
                for l in range(self.distinct):
                    self.model.addConstr(w[i, k, l] <= w[i, k + 1, l])
                    
        return w  # type: ignore
    
    @lazy_var("s")
    def _s(self) -> VarDict:
        return self.model.addVars(self.dice, lb=0, ub=0.75)

    @lazy_var("r", dependencies=["f", "w", "a", "b"])
    def _r(self) -> Var:
        r = self.model.addVar(0, 0.75)
        q = self.model.addVars(self.dice, self.distinct, self.distinct, lb=0, ub=1)

        for i in range(self.dice):
            j = (i + 1) % self.dice

            for k in range(self.distinct):
                for l in range(self.distinct):
                    self.model.addConstr(q[i, k, l] <= self._w[i, k, l])
                    self.model.addConstr(q[i, k, l] <= self._y[j, l])
                    self.model.addConstr(q[i, k, l] >= self._y[j, l] - (1 - self._w[i, k, l]))

            self.model.addConstr(self._s[i] == gp.quicksum(
                q[i, k, l] * self._y[i, k]
                for k in range(self.distinct)
                for l in range(self.distinct)
            ))

            self.model.addConstr(self._s[i] - r >= 0)

        return r
    
    @lazy_constraint("balanced", dependencies=["f"])
    def _balanced(self):
        for i in range(self.dice):
            self.model.addConstr(self._s[i] == self._s[0])

    @lazy_objective("max_min_ratio", dependencies=["r"])
    def _max_min_ratio(self):
        return -self._r

    def _get_result(self):
        return [
            [(round(self._x[i, k].X), self._y[i, k].X) for k in range(self.distinct)]
            for i in range(self.dice)
        ]
