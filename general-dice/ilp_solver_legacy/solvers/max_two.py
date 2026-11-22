import gurobipy as gp

from solvers.core import DiceSolver, lazy_var, lazy_objective, lazy_constraint, Var, VarDict, VarDict2D, VarDict3D
from diceset import DiceSet

class MaxNDiceSolver(DiceSolver):
    def __init__(self, dice: int, distinct: int, faces: int, max_value: int | None = None) -> None:
        self.dice = dice
        self.distinct = distinct
        self.faces = faces
        self.max_value = max_value or dice * distinct

        super().__init__()

    @lazy_var("x")
    def _x(self) -> VarDict2D:
        x = self.model.addVars(self.dice, self.distinct, lb=0, ub=self.max_value, vtype=gp.GRB.INTEGER)
        
        for i in range(self.dice):
            for k in range(self.distinct - 1):
                self.model.addConstr(x[i, k] + 1 <= x[i, k + 1])

        return x  # type: ignore
    
    @lazy_var("m")
    def _m(self) -> VarDict:
        m = self.model.addVars(self.dice, lb=1, vtype=gp.GRB.INTEGER)
        for i in range(self.dice - 1):
            self.model.addConstr(m[i] <= m[i + 1])
        return m
    
    @lazy_var("y")
    def _y(self) -> VarDict2D:
        y = self.model.addVars(self.dice, self.distinct, lb=1, vtype=gp.GRB.INTEGER)
        
        for i in range(self.dice):
            self.model.addConstr(gp.quicksum(y[i, k] for k in range(self.distinct)) == self._m[i])
        return y  # type: ignore
    
    @lazy_var("w", dependencies=["x"])
    def _w(self) -> VarDict3D:
        w = self.model.addVars(self.dice, self.distinct, self.distinct, vtype=gp.GRB.CONTINUOUS, lb=0, ub=1)

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
                        gp.GRB.LESS_EQUAL, 1
                    )
                
                for l in range(self.distinct - 1):
                    self.model.addConstr(w[i, k, l + 1] <= w[i, k, l])
                    
            for k in range(self.distinct - 1):
                for l in range(self.distinct):
                    self.model.addConstr(w[i, k, l] <= w[i, k + 1, l])
                    
        return w  # type: ignore
    
    @lazy_var("z", dependencies=["w", "y"])
    def _z(self) -> VarDict2D:
        z = self.model.addVars(self.dice, self.distinct, lb=0, ub=self.faces, vtype=gp.GRB.INTEGER)
        
        for i in range(self.dice):
            j = (i + 1) % self.dice
            for k in range(self.distinct):
                self.model.addConstr(gp.quicksum(
                    self._w[i, k, l] * self._y[j, l]
                    for l in range(self.distinct)
                ) == z[i, k])

        return z  # type: ignore

    @lazy_var("r", dependencies=["f", "w", "a", "b"])
    def _r(self) -> Var:
        r = self.model.addVar(0, 0.75)

        f = self.model.addVars(self.dice, vtype=gp.GRB.INTEGER)

        for i in range(self.dice):
            self.model.addGenConstrNL(
                f[i],
                r * (self._m[i] * self._m[(i + 1) % self.dice]) - 
                gp.quicksum(
                    self._z[i, k] * self._y[i, k]
                    for k in range(self.distinct)
                )
            )
            
            self.model.addConstr(f[i] <= 0)

        return r

    @lazy_constraint("balanced", dependencies=["f"])
    def _balanced(self):
        for i in range(self.dice):
            self.model.addConstr(
                gp.quicksum(
                    self._z[i, k] * self._y[i, k]
                    for k in range(self.distinct)
                ) == gp.quicksum(
                    self._z[0, k] * self._y[0, k]
                    for k in range(self.distinct)
                ))
        
    @lazy_objective("max_min_ratio", dependencies=["r"])
    def _max_min_ratio(self):
        return -self._r
    
    @lazy_objective("min_faces", dependencies=["y"])
    def _min_faces(self):
        return gp.quicksum(self._m)

    def _get_result(self):
        return DiceSet.from_tuples([
            [(round(self._x[i, k].X), round(self._y[i, k].X)) for k in range(self.distinct)]
            for i in range(self.dice)
        ])