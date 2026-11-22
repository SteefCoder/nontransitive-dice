import gurobipy as gp

from diceset import DiceSet
from utils import vardict
from primes import prime_list


def construct_by_distinct(faces: list[int], distinct: int | list[int], force_all_distinct: bool = False):
    model = gp.Model()
    n = len(faces)

    if isinstance(distinct, int):
        distinct = n * [distinct]
    
    assert len(distinct) == n

    M = n * max(distinct)

    r = model.addVar(0.5, 0.75)

    # x[i, k] = the kth (distinct) number appearing on i
    # y[i, k] = the amount of times the kth distinct number appears on i
    # w[i, k, l] = the kth number of i is larger than the lth number of j
    # z[i, k] = the amount of ways the kth number of i wins from j.
    x = vardict()
    y = vardict()
    w = vardict()
    z = vardict()
    for i in range(n):
        j = (i + 1) % n
        for k in range(distinct[i]):
            x[i, k] = model.addVar(0, M, vtype=gp.GRB.INTEGER)
            y[i, k] = model.addVar(0, faces[i], vtype=gp.GRB.INTEGER)
            z[i, k] = model.addVar(0, faces[j], vtype=gp.GRB.INTEGER)

            for l in range(distinct[j]):
                w[i, k, l] = model.addVar(vtype=gp.GRB.BINARY)

    if force_all_distinct:
        for i in range(n):
            j = (i + 1) % n
            for k in range(distinct[i]):
                model.addConstr(y[i, k] >= 1)
            
            for k in range(distinct[i] - 1):
                model.addConstr(
                    gp.quicksum(w[i, k + 1, l] - w[i, k, l] for l in range(distinct[j])) >= 1
                )

    for i in range(n):
        j = (i + 1) % n

        model.addConstr(
            gp.quicksum(y[i, k] for k in range(distinct[i])) == faces[i]
        )
        for k in range(distinct[i]):
            # this could also be linearized...
            model.addConstr(
                z[i, k] == gp.quicksum(w[i, k, l] * y[j, l] for l in range(distinct[j]))
            )
            model.addConstr(
                gp.quicksum(z[i, k] * y[i, k] for k in range(distinct[i])) >=
                r * faces[i] * faces[j]
            )

            for l in range(distinct[j]):
                wikl = w[i, k, l]
                diff = x[i, k] - x[j, l]
                model.addConstr(diff >= 1 - M*(1 - wikl))
                model.addConstr(-diff >= -M * wikl)

    for i in range(n):
        for k in range(distinct[i] - 1):
            model.addConstr(x[i, k] + 1 <= x[i, k + 1])

    model.setObjective(r, gp.GRB.MAXIMIZE)

    return model, x, y, r


def solve_by_distinct(faces: list[int], distinct: int | list[int], force_all_distinct: bool = False) -> tuple[DiceSet, float]:
    model, x, y, r = construct_by_distinct(faces, distinct, force_all_distinct)
    model.optimize()

    if isinstance(distinct, int):
        distinct = len(faces) * [distinct]

    results = []
    for i in range(len(faces)):
        die = []
        for k in range(distinct[i]):
            die.append((round(x[i, k].X), round(y[i, k].X)))

        results.append(die)
    
    return DiceSet.from_tuples(results), r.X


def construct_combination(
    faces: list[int],
    max_repeat: list[int],
    equal_mean: bool,
    use_primes: bool,
    use_all: bool,
    M: int,
):
    model = gp.Model()
    n = len(faces)

    primes = prime_list(M)

    # m = the largest number used
    # r = the smallest win ratio
    # x[i, k] = the kth number on the ith dice
    # u[i, k, v] = 1 if x[i, k] == v
    # y[v] = 1 if v is used
    # w[i, k, l] = 1 if x[i, k] > x[j, l]
    # z[i] = the maximum amount of repetitions of a value on i
    m = model.addVar(0, M - 1, vtype=gp.GRB.INTEGER)
    r = model.addVar(0, 0.75)
    y = model.addVars(M, vtype=gp.GRB.BINARY)
    z = model.addVars(n, vtype=gp.GRB.INTEGER)
    x = vardict()
    u = vardict()
    w = vardict()
    for i in range(n):
        j = (i + 1) % n
        fi, fj = faces[i], faces[j]
        for k in range(fi):
            x[i, k] = model.addVar(0, M - 1, vtype=gp.GRB.INTEGER)
            for v in range(M):
                u[i, k, v] = model.addVar(vtype=gp.GRB.BINARY)
            for l in range(fj):
                w[i, k, l] = model.addVar(vtype=gp.GRB.BINARY)

    for i in range(n):
        j = (i + 1) % n
        fi, fj = faces[i], faces[j]

        # minimum ratio
        model.addConstr(
            gp.quicksum(w[i, k, l] for k in range(fi) for l in range(fj)) >= r * fi * fj
        )

        # equal means
        if equal_mean:
            model.addConstr(
                gp.quicksum(x[i, k] for k in range(fi)) * fj ==
                gp.quicksum(x[j, l] for l in range(fj)) * fi
            )

        for k in range(fi):
            # each face has one value
            if use_primes:
                model.addConstr(
                    gp.quicksum(primes[v] * u[i, k, v] for v in range(M)) == 1
                )
            model.addConstr(
                gp.quicksum(u[i, k, v] for v in range(M)) == 1
            )
            # the value should be equal to x[i, k]
            model.addConstr(
                gp.quicksum(u[i, k, v] * v for v in range(M)) == x[i, k]
            )
            # m is the largest number used
            model.addConstr(x[i, k] <= m)

            # set condition for w
            for l in range(fj):
                #model.addConstr(x[i, k] - x[j, l] >= 1 - M*(1 - w[i, k, l]))
                #model.addConstr(x[j, l] - x[i, k] >= -M * w[i, k, l])
                model.addGenConstrIndicator(w[i, k, l], True, x[i, k] - x[j, l], gp.GRB.GREATER_EQUAL, 1)

            # x[j, l+1] >= x[j, l] so x[i, k] <= x[j, l] implies x[i, k] <= x[j, l+1]
            for l in range(fj - 1):
                model.addConstr(w[i, k, l + 1] <= w[i, k, l])
        
        for k in range(fi - 1):
            # x is ordered in increasing order
            model.addConstr(x[i, k] <= x[i, k + 1])
            # x[i, k+1] >= x[i, k] so x[i, k] > x[j, l] implies x[i, k+1] > x[j, l]
            for l in range(fj):
                model.addConstr(w[i, k, l] <= w[i, k + 1, l])

        for k in range(fi - max_repeat[i]):
            # maximum repetition for each number
            model.addConstr(x[i, k] + 1 <= x[i, k + max_repeat[i]])
            
    for v in range(M):
        if use_all:
            # each value is used at least once
            model.addConstr(
                gp.quicksum(u[i, k, v] for i in range(n) for k in range(faces[i])) >= y[v]
            )
            if use_primes:
                model.addConstr(m - v <= M * y[v] + M * (1 - primes[v]))
            else:
                model.addConstr(m - v <= M * y[v])

        # z[i] counts the maximum amount of times any number appears per dice
        for i in range(n):
            model.addConstr(
                z[i] >= gp.quicksum(u[i, k, v] for k in range(faces[i]))
            )

    # counting the number of nonzero values along
    # u[i, k, v]
    # where k goes from 0 to faces[i]
    
    model.setObjectiveN(r, 0, 2)
    model.setObjectiveN(gp.quicksum(w), 1, 1)
    #model.setObjectiveN(-gp.quicksum(z), 2, 0)
    model.setObjectiveN(-m, 2, 0)
    model.ModelSense = gp.GRB.MAXIMIZE
    return model, x, r


def solve_combination(
    faces: list[int],
    max_repeat: list[int],
    equal_mean: bool,
    use_primes: bool,
    use_all: bool,
    M: int,
) -> tuple[DiceSet, float]:
    model, x, r = construct_combination(faces, max_repeat, equal_mean, use_primes, use_all, M)
    model.optimize()

    dice = [
        [round(x[i, k].X) for k in range(f)]
        for i, f in enumerate(faces)
    ]
    return DiceSet(dice), r.X


"""
primes + equal mean + use_all 3xd12
[[2, 11, 13, 17, 19, 23, 29, 31, 79, 83, 89, 97], [2, 3, 5, 7, 13, 53, 59, 61, 67, 71, 73, 79], [2, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67]]
[0.5208333333333334, 0.5208333333333334, 0.5208333333333334]

primes + equal mean + M=150 3xd12
[[17, 19, 23, 29, 31, 37, 43, 103, 107, 109, 113, 127], [3, 5, 7, 11, 73, 79, 83, 89, 97, 101, 103, 107], [37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 127]]
[0.5902777777777778, 0.5902777777777778, 0.5833333333333334]
"""