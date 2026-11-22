# paley_hybrid.py
import ctypes
import time
import numpy as np
import gurobipy as gp
from gurobipy import GRB


def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]



def ranks_to_dice(rank, n, d):
    dice = []
    for X in range(n):
        faces = sorted(i * n + int(rank[i, X]) for i in range(d))
        dice.append(faces)
    return dice


def solve_ilp(tournament, d, warm_rank=None, time_limit=600, threads=-1, verbose=True):
    """ILP solve, optionally warm-started from `warm_rank` (d x n int array)."""
    n = len(tournament)
    m = gp.Model("paley_dice")
    m.Params.OutputFlag = 1 if verbose else 0
    #m.Params.TimeLimit = time_limit
    if threads:
        m.Params.Threads = threads

    p = m.addVars(n, d, n, vtype=GRB.BINARY, name="p")
    w = m.addVars(
        [(X, Y, i) for X in range(n) for Y in range(n) if X != Y for i in range(d)],
        vtype=GRB.BINARY, name="w",
    )

    # Permutation per slot
    for X in range(n):
        for i in range(d):
            m.addConstr(gp.quicksum(p[X, i, k] for k in range(n)) == 1)
    for k in range(n):
        for i in range(d):
            m.addConstr(gp.quicksum(p[X, i, k] for X in range(n)) == 1)

    # Linking w to ranks
    M = n
    for i in range(d):
        for X in range(n):
            for Y in range(n):
                if X == Y:
                    continue
                diff = gp.quicksum(k * (p[X, i, k] - p[Y, i, k]) for k in range(n))
                m.addConstr(diff >= 1 - M * (1 - w[X, Y, i]))
                m.addConstr(diff <= -1 + M * w[X, Y, i])

    # Converse
    for X in range(n):
        for Y in range(X + 1, n):
            for i in range(d):
                m.addConstr(w[X, Y, i] + w[Y, X, i] == 1)

    # Cardinality
    threshold = d // 2 + 1
    for X in range(n):
        for Y in range(n):
            if X == Y or not tournament[X][Y]:
                continue
            m.addConstr(gp.quicksum(w[X, Y, i] for i in range(d)) >= threshold)

    # Slot symmetry break
    for i in range(d - 1):
        m.addConstr(w[0, 1, i] >= w[0, 1, i + 1])

    # Warm start
    if warm_rank is not None:
        for X in range(n):
            for i in range(d):
                for k in range(n):
                    p[X, i, k].Start = 1.0 if int(warm_rank[i, X]) == k else 0.0
        for X in range(n):
            for Y in range(n):
                if X == Y:
                    continue
                for i in range(d):
                    w[X, Y, i].Start = 1.0 if warm_rank[i, X] > warm_rank[i, Y] else 0.0

    m.Params.MIPFocus = 1
    m.Params.NoRelHeurTime = 36000
    m.optimize()

    if m.Status == GRB.INFEASIBLE:
        return None, "infeasible"
    if m.SolCount == 0:
        return None, f"no_solution(status={m.Status})"

    rank = np.zeros((d, n), dtype=np.int32)
    for X in range(n):
        for i in range(d):
            for k in range(n):
                if p[X, i, k].X > 0.5:
                    rank[i, X] = k
                    break
    return ranks_to_dice(rank, n, d), "ok"


def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            wins = sum(1 for a in dice[i] for b in dice[j] if a > b)
            losses = sum(1 for a in dice[i] for b in dice[j] if a < b)
            if bool(tournament[i][j]) != (wins > losses):
                return False, (i, j)
    return True, None


if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    time_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600

    t = qr_tournament(p)
    dice, status = solve_ilp(t, d)
    print(f"\nResult: status = {status}")
    if dice is not None:
        for i, row in enumerate(dice):
            print(f"  die {i}: {row}")