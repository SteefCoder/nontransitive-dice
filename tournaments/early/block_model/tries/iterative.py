import gurobipy as gp
from gurobipy import GRB
import itertools
import random
import time

import random

def deficit_seed(tournament, new_slots, n, current_wins, max_d, rng=None):
    """
    Return new_slots permutations (lists of length n).
    For each slot, greedily assign ranks: dice with the largest deficit
    (missing wins on must-win arcs) get the highest ranks.
    """
    if rng is None:
        rng = random.Random(hash(time.time()))
    final_threshold = max_d // 2 + 1
    wins = [row[:] for row in current_wins]
    seed_ranks = []

    for slot in range(new_slots):
        # Compute deficit per die: sum over must-win arcs of (threshold - current_wins).
        deficit = [0] * n
        for X in range(n):
            for Y in range(n):
                if X == Y or not tournament[X][Y]: continue
                d = final_threshold - wins[X][Y]
                if d > 0:
                    deficit[X] += d

        # Tie-break with random noise so repeated calls explore differently.
        keys = [(deficit[X] + rng.random() * 0.1, X) for X in range(n)]
        # Highest deficit gets highest rank
        keys.sort(reverse=True)
        slot_rank = [0] * n
        for rank, (_, X) in enumerate(reversed(keys)):
            # 'reversed' so the smallest deficit gets rank 0; highest deficit gets rank n-1
            slot_rank[X] = rank
        seed_ranks.append(slot_rank)

        # Update wins as if this slot were chosen
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                if slot_rank[X] > slot_rank[Y]:
                    wins[X][Y] += 1

    return seed_ranks

def incremental_solve(tournament, max_d, verbose=True):
    n = len(tournament)
    fixed_ranks = []  # list of length-n lists; each is a permutation
    wins = [[0]*n for _ in range(n)]

    while len(fixed_ranks) < max_d:
        k = len(fixed_ranks)
        new_slots = 2 if k > 0 else 5 # start with 1 to get odd d
        target_d = k + new_slots
        threshold = target_d // 2 + 1

        m = gp.Model()
        #m.Params.OutputFlag = 0
        #m.Param
        m.Params.NoRelHeurTime = 100
        m.Params.TimeLimit = 300
        m.Params.MIPFocus = 3

        # Variables: p[X, s, r] for new slots s in {0..new_slots-1}, rank r
        p = m.addVars(n, new_slots, n, vtype=GRB.BINARY, name="p") # binary
        s = m.addVars(n, n, vtype=GRB.INTEGER, lb=0, ub=target_d, name="slack")  # integer
        

        m.NumStart = 3
        m.update()
        #seed = list(range(n))
        #random.shuffle(seed)
        for i in range(m.NumStart):
            m.Params.StartNumber = i
            seed = deficit_seed(tournament, new_slots, n, wins, max_d, random.Random(hash((i + 1) * time.time())))
            for X in range(n):
                for slot in range(new_slots):
                    for r in range(n):
                        p[X, slot, r].Start = int(seed[slot][X] == r)

        # Permutation constraints
        for slot in range(new_slots):
            for X in range(n):
                m.addConstr(gp.quicksum(p[X, slot, r] for r in range(n)) == 1)
            for r in range(n):
                m.addConstr(gp.quicksum(p[X, slot, r] for X in range(n)) == 1)

        # Win indicators per pair per new slot
        # wins_slot[X, Y, slot] = 1 iff X outranks Y in this new slot
        wins_slot = m.addVars(n, n, new_slots, vtype=GRB.BINARY, name="ws")
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                for slot in range(new_slots):
                    rank_X = gp.quicksum(r * p[X, slot, r] for r in range(n))
                    rank_Y = gp.quicksum(r * p[Y, slot, r] for r in range(n))
                    # wins_slot = 1 iff rank_X > rank_Y
                    m.addGenConstrIndicator(wins_slot[X, Y, slot], True, rank_X - rank_Y, GRB.GREATER_EQUAL, 1)
                    m.addGenConstrIndicator(wins_slot[X, Y, slot], False, rank_X - rank_Y, GRB.LESS_EQUAL, -1)

                    # m.addConstr(rank_X - rank_Y >= 1 - n * (1 - wins_slot[X, Y, slot]))
                    # m.addConstr(rank_X - rank_Y <= -1 + n * wins_slot[X, Y, slot])

        max_s = m.addVar(lb=0, vtype=GRB.INTEGER)
        # Slack constraints
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                total_wins = wins[X][Y] + gp.quicksum(wins_slot[X, Y, slot] for slot in range(new_slots))
                if tournament[X][Y]:
                    m.addConstr(total_wins + s[X, Y] >= threshold)
                else:
                    m.addConstr(total_wins <= threshold - 1 + s[X, Y])
                # m.addConstr(max_s >= s[X, Y])

        # Objective: minimize total slack, with secondary objective on max slack
        m.setObjective(gp.quicksum(s[X, Y] for X in range(n) for Y in range(n) if X != Y),
                      GRB.MINIMIZE)
        # m.setObjective(max_s)

        m.optimize()

        if m.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT) or m.SolCount == 0:
            if verbose: print(f"  iter {k}: solver failed ({m.Status})")
            return None

        total_slack = m.ObjVal
        if verbose:
            print(f"  iter {k} -> {target_d} slots: total slack = {total_slack}")

        # Extract new slot rankings
        for slot in range(new_slots):
            new_rank = [0] * n
            for X in range(n):
                for r in range(n):
                    if p[X, slot, r].X > 0.5:
                        new_rank[X] = r
                        break
            fixed_ranks.append(new_rank)
            # Update wins
            for X in range(n):
                for Y in range(n):
                    if X == Y: continue
                    if new_rank[X] > new_rank[Y]:
                        wins[X][Y] += 1

        if total_slack == 0:
            if verbose: print(f"  solved with d = {target_d}")
            return reconstruct_dice(fixed_ranks, n)

    return None  # max_d exceeded

def reconstruct_dice(fixed_ranks, n):
    """
    fixed_ranks: list of d permutations, each a length-n list where
                 fixed_ranks[slot][X] = X's rank (0..n-1) in that slot.
    Returns: list of n dice, each a sorted list of d face values.
             Face value of die X in slot i is i*n + fixed_ranks[i][X].
    """
    d = len(fixed_ranks)
    dice = []
    for X in range(n):
        faces = sorted(i * n + fixed_ranks[i][X] for i in range(d))
        dice.append(faces)
    return dice

def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]

def check_tournament(tournament: list[list[int]], n: int):
    N = len(tournament)
    pred = [0] * N

    for i in range(N):
        mask = 0
        for j in range(N):
            if tournament[j][i]:
                mask |= 1 << j
        pred[i] = mask

    for v in itertools.combinations(range(N), n):
        mask = pred[v[0]]
        for vi in v[1:]:
            mask &= pred[vi]

        if mask == 0:
            return False
        
    for i in range(len(tournament)):
        if tournament[i][i] != 0:
            return False
        for j in range(i):
            if tournament[i][j] + tournament[j][i] != 1:
                return False
    return True


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
    #print_tournament(tour)
    return tour

max_d = 11
tournament = qr_tournament(19)
dice = incremental_solve(tournament, max_d)
if dice:
    new_tournament = get_tournament(dice)
    print(new_tournament)
    print(new_tournament == tournament)
    print(check_tournament(new_tournament, 2))
    print("Sides", len(dice[0]))