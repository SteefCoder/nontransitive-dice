import gurobipy as gp


def so_cicle(n):
    model = gp.Model()
    # model.Params.OutputFlag = 0
    a = model.addVars(n, lb=0, ub=200, vtype=gp.GRB.INTEGER)
    b = model.addVars(n, lb=1, ub=200, vtype=gp.GRB.INTEGER)
    q = model.addVars(n - 1, lb=1, vtype=gp.GRB.INTEGER)
    r = model.addVar(0, 0.75)

    for i in range(n):
        model.addConstr(a[i] <= b[i])

    model.setObjective(r, gp.GRB.MAXIMIZE)
    for i in range(n - 1):
        model.addGenConstrNL(q[i], b[i]*b[i+1])
        model.addConstr(q[i] - a[i]*b[i+1] + a[i]*a[i+1] == r*q[i])
    model.addConstr(b[n-1] - a[n-1] == r*b[n-1])
    model.addConstr(a[0] == r*b[0])
    model.optimize()
    return r.X


print(so_cicle(4))