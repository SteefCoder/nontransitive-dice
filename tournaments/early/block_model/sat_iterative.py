from typing import Callable

import itertools
import random
import time

import gurobipy as gp


def reconstruct_dice(values: gp.tupledict[tuple[int, ...], gp.Var], n: int, faces: int) -> list[list[int]]:
    dice = [[0 for _ in range(faces)] for _ in range(n)]
    for (X, block), v in values.items():
        dice[X][block] = round(v.X) + block * n
    return dice

def solve_heuristic(tournament: list[list[int]], faces: int):
    pass


def build_model(model: gp.Model, tournament: list[list[int]], faces: int):
    n = len(tournament)
    threshold = faces // 2 + 1

    # values_bin[X, b, v] = 1 if X has value v in block b
    values_bin = model.addVars(n, faces, n, vtype=gp.GRB.BINARY)

    # values_int[X, b] = the value of X in block b
    values_int = model.addVars(n, faces, vtype=gp.GRB.INTEGER, lb=0, ub=n - 1)

    # slack[X, Y] = the number of wins X still needs over Y if T_XY = 1
    # slack = model.addVars(n, n, vtype=gp.GRB.INTEGER, lb=0)
    slack = gp.tupledict()

    # max_slack = max_XY slack[X, Y]
    max_slack = model.addVar(lb=0, vtype=gp.GRB.INTEGER)

    # wins[X, Y, b] = 1 if X > Y in block b
    # wins = model.addVars(n, n, faces, vtype=gp.GRB.BINARY)
    wins = gp.tupledict()

    for block in range(faces):
        for X in range(n):
            # each die can only have a single value per block
            model.addConstr(gp.quicksum(values_bin[X, block, v] for v in range(n)) == 1)

            # each value is determined by the binary variables
            model.addConstr(values_int[X, block] == gp.quicksum(v * values_bin[X, block, v] for v in range(n)))

        for v in range(n):
            # each value can only occur once per block
            # this is also implied by the constraint indicators
            model.addConstr(gp.quicksum(values_bin[X, block, v] for X in range(n)) == 1)
            pass

    for X in range(n):
        for Y in range(n):
            # it might be fine to just consider the X and Y where T_XY = 1
            # then we could generate some variables lazily
            #if X == Y:
            #    continue
            if not tournament[X][Y]:
                continue

            slack[X, Y] = model.addVar(lb=0, ub=1, vtype=gp.GRB.INTEGER)

            for block in range(faces):
                wins[X, Y, block] = model.addVar(vtype=gp.GRB.BINARY)

                # check who wins between X and Y on the block
                model.addGenConstrIndicator(
                    wins[X, Y, block], True,
                    values_int[X, block] - values_int[Y, block],
                    gp.GRB.GREATER_EQUAL, 1
                )
                # the -1 implies no draw, which is also technically implied
                # by the fact that each value is unique on a block.
                # changing it to 0 is fine if it helps performance
                model.addGenConstrIndicator(
                    wins[X, Y, block], False,
                    values_int[X, block] - values_int[Y, block],
                    gp.GRB.LESS_EQUAL, 0
                )
            
            total_wins = gp.quicksum(wins[X, Y, b] for b in range(faces))
            if tournament[X][Y]:
                # if T_XY, we need to get over the threshold
                # there should be no reward for going far over, hence the slack variable
                model.addConstr(total_wins + slack[X, Y] >= threshold)
            else:
                # not generally neccesary, since it is implied by slack[Y, X]
                model.addConstr(total_wins <= threshold - 1 + slack[X, Y])

            model.addConstr(max_slack >= slack[X, Y])

    # we give most priority to improving the maximum slack
    # to avoid the model ignoring some dice in favor of others
    model.setObjectiveN(max_slack, 0, 0, n)
    model.setObjectiveN(slack.sum(), 1, 0)
    return values_int, slack, max_slack


def solve_model(tournament: list[list[int]], faces: int, env: gp.Env, callback: Callable[[gp.Model, int], None]):
    with env, gp.Model(env=env) as model:
        values, slack, max_slack = build_model(model, tournament, faces)
        model.optimize(callback)
        
        if model.status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.INTERRUPTED) or model.SolCount == 0:
            return None
        
        dice = reconstruct_dice(values, len(tournament), faces)
        total_slack = round(slack.sum().getValue())
        return dice, total_slack, round(max_slack.X)


def create_qr_tournament(p: int) -> list[list[int]]:
    QR = { i**2 % p for i in range(1, p) }
    return [[int((j - i) % p in QR) for j in range(p)] for i in range(p)]


def get_tournament(dice: list[list[int]]):
    tour = []
    for d1 in dice:
        r = []
        for d2 in dice:
            wins = 0
            for v1 in d1:
                for v2 in d2:
                    if v1 > v2:
                        wins += 1
            if 2 * wins > len(d1) * len(d2):
                r.append(1)
            else:
                r.append(0)
        tour.append(r)
    return tour


def model_callback(model: gp.Model, where: int) -> None:
    pass


def main():
    faces = 7
    p = 19
    tournament = create_qr_tournament(p)

    env = gp.Env(params=dict(
        NoRelHeurTime=100,
        MIPFocus=3
    ))
    solution = solve_model(tournament, faces, env, model_callback)
    if solution is None:
        print("No solution found...")
        return
    
    dice, total_slack, max_slack = solution
    print(dice)
    new_tournament = get_tournament(dice)
    print("Verified: ", new_tournament == tournament)


if __name__ == '__main__':
    main()