import gurobipy as gp
from gurobipy import GRB
import random


def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]


def deficit_seed(tournament, d, n):
    """Generate d permutations greedily, placing deficit dice high."""
    final_threshold = d // 2 + 1
    wins = [[0]*n for _ in range(n)]
    seeds = []
    rng = random.Random()
    for slot in range(d):
        deficit = [0] * n
        for X in range(n):
            for Y in range(n):
                if X == Y or not tournament[X][Y]: continue
                miss = final_threshold - wins[X][Y]
                if miss > 0:
                    deficit[X] += miss
        keys = sorted([(deficit[X] + rng.random() * 0.01, X) for X in range(n)])
        rank_s = [0] * n
        for rank, (_, X) in enumerate(keys):
            rank_s[X] = rank
        seeds.append(rank_s)
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                if rank_s[X] > rank_s[Y]:
                    wins[X][Y] += 1
    return seeds


def solve_full(tournament, d, time_limit=600, verbose=True):
    """
    Single-shot solve: all d slots are variables, no fixing.
    Objective: minimize total slack. Zero slack means tournament realized.
    """
    n = len(tournament)
    threshold = d // 2 + 1
    
    m = gp.Model("paley_full")
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.TimeLimit = time_limit
    m.Params.MIPFocus = 1
    m.Params.NoRelHeurTime = time_limit // 4
    
    # p[X, slot, r] = 1 iff die X has rank r in slot
    p = m.addVars(n, d, n, vtype=GRB.BINARY, name="p")
    s_slack = m.addVars(n, n, vtype=GRB.INTEGER, lb=0, name="slack")
    
    # Permutation constraints per slot
    for slot in range(d):
        for X in range(n):
            m.addConstr(gp.quicksum(p[X, slot, r] for r in range(n)) == 1)
        for r in range(n):
            m.addConstr(gp.quicksum(p[X, slot, r] for X in range(n)) == 1)
    
    # Win indicators per pair per slot
    wins_slot = m.addVars(n, d, n, vtype=GRB.BINARY, name="ws")
    # Note: indexing as (X, slot, Y) for cache friendliness — adjust below
    # Actually let's keep the natural (X, Y, slot) ordering
    wins_slot = m.addVars(n, n, d, vtype=GRB.BINARY, name="ws")
    
    for slot in range(d):
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                rank_X = gp.quicksum(r * p[X, slot, r] for r in range(n))
                rank_Y = gp.quicksum(r * p[Y, slot, r] for r in range(n))
                m.addConstr(rank_X - rank_Y >= 1 - n * (1 - wins_slot[X, Y, slot]))
                m.addConstr(rank_X - rank_Y <= -1 + n * wins_slot[X, Y, slot])
    
    # Tournament slack
    for X in range(n):
        for Y in range(n):
            if X == Y: continue
            total_wins = gp.quicksum(wins_slot[X, Y, slot] for slot in range(d))
            if tournament[X][Y]:
                m.addConstr(total_wins + s_slack[X, Y] >= threshold)
            else:
                m.addConstr(total_wins <= threshold - 1 + s_slack[X, Y])
    
    # Slot symmetry break: order slots by w[0,1,slot] non-increasing
    for slot in range(d - 1):
        m.addConstr(wins_slot[0, 1, slot] >= wins_slot[0, 1, slot + 1])
    
    # Warm start
    seed = deficit_seed(tournament, d, n)
    for slot in range(d):
        for X in range(n):
            for r in range(n):
                p[X, slot, r].Start = 1.0 if seed[slot][X] == r else 0.0
    
    m.setObjective(gp.quicksum(s_slack[X, Y] for X in range(n) for Y in range(n) if X != Y),
                   GRB.MINIMIZE)
    m.optimize()
    
    if m.SolCount == 0:
        return None, None
    
    total_slack = m.ObjVal
    
    # Extract
    fixed_ranks = []
    for slot in range(d):
        rank_s = [0] * n
        for X in range(n):
            for r in range(n):
                if p[X, slot, r].X > 0.5:
                    rank_s[X] = r
                    break
        fixed_ranks.append(rank_s)
    
    dice = [sorted(slot * n + fixed_ranks[slot][X] for slot in range(d)) for X in range(n)]
    return dice, total_slack


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
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    time_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    
    t = qr_tournament(p)
    dice, slack = solve_full(t, d, time_limit=time_limit)
    if dice is None:
        print(f"P_{p}, d={d}: no solution found")
    else:
        ok = verify(dice, t)
        print(f"P_{p}, d={d}: slack={slack}, {'verified' if ok else 'verification FAILED'}")
        for i, row in enumerate(dice[:8]):
            print(f"  die {i}: {row}")
        if len(dice) > 8:
            print(f"  ... ({len(dice)-8} more)")