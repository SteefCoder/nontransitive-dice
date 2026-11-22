import gurobipy as gp

from diceset import DiceSet
from utils import vardict


def construct_niceify(
    dice: DiceSet,
    max_repeats: list[int],
    equal_mean: bool = False,
    equal_eyes: bool = False
):
    model = gp.Model()

    M = 100

    # maximum value for all numbers
    m = model.addVar(0, M, vtype=gp.GRB.INTEGER)

    # x[i, k] = value of ith dice on face k
    x = vardict()
    for i, faces in enumerate(dice.face_counts):
        for k in range(faces):
            x[i, k] = model.addVar(0, M, vtype=gp.GRB.INTEGER)
            model.addConstr(x[i, k] <= m)

        for k in range(faces - 1):
            model.addConstr(x[i, k] <= x[i, k + 1])

        for k in range(faces - max_repeats[i]):
            model.addConstr(x[i, k] + 1 <= x[i, k + max_repeats[i]])

    for i in range(dice.n):
        j = (i + 1) % dice.n
        fi, fj = dice.face_counts[i], dice.face_counts[j]

        if equal_mean:
            model.addConstr(
                gp.quicksum(x[i, k] for k in range(fi)) * fj ==
                gp.quicksum(x[j, l] for l in range(fj)) * fi
            )
        
        if equal_eyes:
            for k in range(fi // 2):
                model.addConstr(
                    x[i, k] + x[i, fi - k - 1] == x[i, k + 1] + x[i, fi - k - 2]
                )

        for k, a in enumerate(dice.dice[i]):
            for l, b in enumerate(dice.dice[j]):
                xa = x[i, k]
                xb = x[j, l]
                if a < b:
                    model.addConstr(xa + 1 <= xb)
                elif b < a:
                    model.addConstr(xb + 1 <= xa)
                else:
                    model.addConstr(xa - xb == 0)

    u = model.addVars(M + 1, vtype=gp.GRB.BINARY)
    is_val = vardict()
    for i, faces in enumerate(dice.face_counts):
        for k in range(faces):
            for v in range(M + 1):
                is_val[i, k, v] = model.addVar(vtype=gp.GRB.BINARY)
            
            model.addConstr(
                gp.quicksum(is_val[i, k, v] for v in range(M + 1)) == 1
            )
            model.addConstr(
                gp.quicksum(v * is_val[i, k, v] for v in range(M + 1)) == x[i, k]
            )
    
    for v in range(M + 1):
        model.addConstr(
            gp.quicksum(
                is_val[i, k, v]
                for i, faces in enumerate(dice.face_counts)
                for k in range(faces)
            ) >= u[v]
        )
        model.addConstr(m - v <= M * u[v])
    
    return model, x

def niceify(
    dice: DiceSet,
    max_repeats: list[int],
    equal_mean: bool = False,
    equal_eyes: bool = False
) -> DiceSet:
    model, x = construct_niceify(dice, max_repeats, equal_mean, equal_eyes)
    model.optimize()
    new_dice = [
        [round(x[i, k].X) for k in range(faces)]
        for i, faces in enumerate(dice.face_counts)
    ]
    return DiceSet(new_dice)
