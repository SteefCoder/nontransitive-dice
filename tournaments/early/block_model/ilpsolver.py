import gurobipy as gp
from gurobipy import GRB

def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]

def solve_ilp(tournament, d, time_limit=600, threads=0):
    n = len(tournament)
    m = gp.Model("paley_dice")
    m.Params.OutputFlag = 1
    m.Params.TimeLimit = time_limit
    if threads: m.Params.Threads = threads

    # p[X,i,k] = 1 iff die X has rank k in slot i
    p = m.addVars(n, d, n, vtype=GRB.BINARY, name="p")
    # w[X,Y,i] = 1 iff X outranks Y in slot i  (only defined for X != Y)
    w = m.addVars(
        [(X, Y, i) for X in range(n) for Y in range(n) if X != Y for i in range(d)],
        vtype=GRB.BINARY, name="w"
    )

    # Permutation: each die has one rank per slot
    for X in range(n):
        for i in range(d):
            m.addConstr(gp.quicksum(p[X, i, k] for k in range(n)) == 1)
    # Each rank used by one die per slot
    for k in range(n):
        for i in range(d):
            m.addConstr(gp.quicksum(p[X, i, k] for X in range(n)) == 1)

    # Linking: w[X,Y,i] reflects rank ordering
    M = n
    for i in range(d):
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                diff = gp.quicksum(k * (p[X, i, k] - p[Y, i, k]) for k in range(n))
                m.addConstr(diff >= 1 - M * (1 - w[X, Y, i]))
                m.addConstr(diff <= -1 + M * w[X, Y, i])

    # Converse (redundant but speeds presolve)
    for X in range(n):
        for Y in range(X+1, n):
            for i in range(d):
                m.addConstr(w[X, Y, i] + w[Y, X, i] == 1)

    # Tournament cardinality
    threshold = d // 2 + 1
    for X in range(n):
        for Y in range(n):
            if X == Y or not tournament[X][Y]: continue
            m.addConstr(gp.quicksum(w[X, Y, i] for i in range(d)) >= threshold)

    # Slot symmetry break: order slots by w[0,1,i]
    for i in range(d - 1):
        m.addConstr(w[0, 1, i] >= w[0, 1, i+1])

    m.optimize()

    if m.Status == GRB.INFEASIBLE:
        return None, "infeasible"
    if m.SolCount == 0:
        return None, f"no solution ({m.Status})"

    # Reconstruct
    dice = []
    for X in range(n):
        faces = []
        for i in range(d):
            rank = next(k for k in range(n) if p[X, i, k].X > 0.5)
            faces.append(i * n + rank)
        dice.append(sorted(faces))
    return dice, "ok"

def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            w = sum(1 for a in dice[i] for b in dice[j] if a > b)
            l = sum(1 for a in dice[i] for b in dice[j] if a < b)
            if bool(tournament[i][j]) != (w > l): return False
    return True


if __name__ == "__main__":
    import sys, time
    pp = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    t = qr_tournament(pp)
    t0 = time.time()
    dice, status = solve_ilp(t, d)
    print(f"P_{pp}, d={d}: {status}  ({time.time()-t0:.1f}s)")
    if dice:
        for i, r in enumerate(dice): print(f"  die {i}: {r}")
        print(verify(dice, t))