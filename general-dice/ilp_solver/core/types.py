import gurobipy as gp


Var = gp.Var
Var1D = gp.tupledict[int, gp.Var]
Var2D = gp.tupledict[tuple[int, int], gp.Var]
Var3D = gp.tupledict[tuple[int, int, int], gp.Var]
VarND = gp.tupledict[tuple[int, ...], gp.Var]
