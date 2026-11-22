from typing import Callable

import itertools
import random
import time

import gurobipy as gp


def reconstruct_dice(values: gp.tupledict[tuple[int, ...], gp.Var], n: int, faces: int) -> list[list[int]]:
    dice = [[0 for _ in range(faces)] for _ in range(n)]
    for (X, block), v in values.items():
        dice[X][block] = round(v.X)
    return dice


def solve_heuristic(tournament: list[list[int]], faces: int, seed: int):
    rng = random.Random(seed)
    n = len(tournament)
    threshold = faces // 2 + 1

    wins = [[0] * n for _ in range(n)]
    blocks = []
    for _ in range(faces):
        deficit = [0] * n
        for X in range(n):
            for Y in range(n):
                if not tournament[X][Y]:
                    continue

                d = threshold - wins[X][Y]
                if d > 0:
                    deficit[X] += d

        key_ordering = [(deficit[X] + rng.random() * 0.1, X) for X in range(n)]
        key_ordering.sort()
        block = [0] * n
        for rank, (_, X) in enumerate(key_ordering):
            block[X] = rank
        blocks.append(block)

        for X in range(n):
            for Y in range(n):
                if block[X] > block[Y]:
                    wins[X][Y] += 1
    
    return blocks

def build_model(model: gp.Model, tournament: list[list[int]], faces: int):
    n = len(tournament)
    threshold = faces ** 2 // 2 + 1
    max_v = n * faces

    # values_bin[X, b, v] = 1 if X has value v in block b
    # values_bin = model.addVars(n, faces, max_v, vtype=gp.GRB.BINARY)

    # values_int[X, b] = the value of X in block b
    values_int = model.addVars(n, faces, vtype=gp.GRB.INTEGER, lb=0, ub=max_v - 1)

    # slack[X, Y] = the number of wins X still needs over Y if T_XY = 1
    slack = gp.tupledict()

    # max_slack = max_XY slack[X, Y]
    max_slack = model.addVar(lb=0, vtype=gp.GRB.INTEGER)

    # wins[X, Y, bX, bY] = 1 if X in block bX > Y in block bY
    wins = gp.tupledict()

    # for block in range(faces):
    #     for X in range(n):
    #         # each die can only have a single value per block
    #         model.addConstr(gp.quicksum(values_bin[X, block, v] for v in range(max_v)) == 1)

    #         # each value is determined by the binary variables
    #         model.addConstr(values_int[X, block] == gp.quicksum(v * values_bin[X, block, v] for v in range(max_v)))

    # for v in range(max_v):
    #     # each value can only occur once
    #     # this is also implied by the constraint indicators
    #     model.addConstr(gp.quicksum(values_bin[X, block, v] for X in range(n) for block in range(faces)) == 1)

    for X in range(n):
        for Y in range(n):
            if not tournament[X][Y]:
                continue

            slack[X, Y] = model.addVar(lb=0, ub=faces, vtype=gp.GRB.INTEGER)

            total_wins = 0
            for bX in range(faces):
                for bY in range(faces):
                    wxy = wins[X, Y, bX, bY] = model.addVar(vtype=gp.GRB.BINARY)
                    total_wins += wxy
                    # check who wins between X and Y on the block
                    model.addGenConstrIndicator(
                        wxy, True,
                        values_int[X, bX] - values_int[Y, bY],
                        gp.GRB.GREATER_EQUAL, 1
                    )
                    # the -1 implies no draw, which is also technically implied
                    # by the fact that each value is unique on a block.
                    # changing it to 0 is fine if it helps performance
                    model.addGenConstrIndicator(
                        wxy, False,
                        values_int[X, bX] - values_int[Y, bY],
                        gp.GRB.LESS_EQUAL, -1
                    )

            #     for bY in range(faces - 1):
            #         model.addConstr(wins[X, Y, bX, bY + 1] <= wins[X, Y, bX, bY])
            
            # for bX in range(faces - 1):
            #     for bY in range(faces):
            #         model.addConstr(wins[X, Y, bX, bY] <= wins[X, Y, bX + 1, bY])

            # if T_XY, we need to get over the threshold
            # there should be no reward for going far over, hence the slack variable
            model.addConstr(total_wins + slack[X, Y] >= threshold)


    # we give most priority to improving the maximum slack
    # to avoid the model ignoring some dice in favor of others
    #model.setObjectiveN(max_slack, 0, 0)
    #model.addConstr(max_slack == 0)
    model.setObjective(slack.sum())
    # model.setObjective(-t)
    # return values_int, values_bin, slack, max_slack
    return values_int, slack, max_slack



def solve_model(tournament: list[list[int]], faces: int, start_values: list[list[int]], env: gp.Env, callback: Callable[[gp.Model, int], None]):
    with gp.Model(env=env) as model:
        values_int, slack, max_slack = build_model(model, tournament, faces)
        print(start_values)
        for X in range(len(tournament)):
            for block in range(faces):
                values_int[X, block].Start = start_values[X][block]

        model.optimize(callback)
        
        if model.status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.INTERRUPTED) or model.SolCount == 0:
            return None
        
        dice = reconstruct_dice(values_int, len(tournament), faces)
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


def solve_incremental(p: int, max_faces: int, env: gp.Env, callback: Callable[[gp.Model, int], None]):
    tournament = create_qr_tournament(p)

    blocks = []
    last_faces = 0
    faces = 1
    while faces <= max_faces:
        new_blocks = []
        for i in range(p):
            block = list(range(faces))
            random.shuffle(block)
            new_blocks.append([x + p * i for x in block])

        values = [[blocks[b][X] for b in range(faces)] for X in range(p)]
        solution = solve_model(tournament, faces, blocks + values, env, callback)
        if not solution:
            faces += 2
            continue
        
        dice, total_slack, max_slack = solution
        if total_slack == 0 and max_slack == 0:
            return dice
        
        blocks = dice

        last_faces = faces
        faces += 2

    return dice


def solve_at_once():
    faces = 5
    p = 19
    tournament = create_qr_tournament(p)

    env = gp.Env(params=dict(
        NoRelHeurTime=100,
        TimeLimit=100,
        MIPFocus=1
    ))
    start_blocks = solve_heuristic(tournament, faces, hash(time.time()))

    solution = solve_model(tournament, faces, start_blocks, env, model_callback)
    if solution is None:
        print("No solution found...")
        return
    
    dice, total_slack, max_slack = solution
    print(dice)
    new_tournament = get_tournament(dice)
    print("Verified: ", new_tournament == tournament)


def main():
    max_faces = 17
    p = 19
    env = gp.Env(params=dict(
        NoRelHeurTime=100,
        #TimeLimit=100,
        MIPFocus=1,
        Cuts=3
    ))
    dice = solve_incremental(p, max_faces, env, model_callback)
    if dice:
        print(dice)
        new_tournament = get_tournament(dice)
        print(new_tournament)
        print("Verified: ", new_tournament == create_qr_tournament(p))

if __name__ == '__main__':
    main()