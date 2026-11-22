import gurobipy as gp
from gurobipy import GRB
import itertools
import random

import random

def deficit_seed(tournament, new_slots, n, current_wins, max_d, rng=None):
    """
    Return new_slots permutations (lists of length n).
    For each slot, greedily assign ranks: dice with the largest deficit
    (missing wins on must-win arcs) get the highest ranks.
    """
    if rng is None:
        rng = random.Random()
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

    LOOKBACK = 3

    while len(fixed_ranks) < max_d:
        k_committed = len(fixed_ranks)
        lookback = min(LOOKBACK, k_committed)
        k_frozen = k_committed - lookback   # slots we keep fixed
        new_slots = 2 if k_committed > 0 else 5
        
        # Total slots being optimized this iteration: lookback (revisable) + new_slots
        optimizing_slots = lookback + new_slots
        target_d = k_frozen + optimizing_slots
        threshold = target_d // 2 + 1
        
        # Recompute wins from only the frozen slots (since lookback ones become variable)
        frozen_wins = [[0]*n for _ in range(n)]
        for slot_idx in range(k_frozen):
            rank_s = fixed_ranks[slot_idx]
            for X in range(n):
                for Y in range(n):
                    if X == Y: continue
                    if rank_s[X] > rank_s[Y]:
                        frozen_wins[X][Y] += 1
        
        if verbose:
            print(f"  iter {k_committed}: frozen={k_frozen}, lookback={lookback}, new={new_slots} -> {target_d}")
        
        m = gp.Model()
        m.Params.NoRelHeurTime = 240
        m.Params.TimeLimit = 200
        m.Params.MIPFocus = 1
        
        # Variables for all optimizing slots (lookback + new)
        p = m.addVars(n, optimizing_slots, n, vtype=GRB.BINARY, name="p")
        s_slack = m.addVars(n, n, vtype=GRB.INTEGER, lb=0, name="slack")
        
        # Warm start: lookback slots from current fixed_ranks, new slots from deficit seed
        seed_new = deficit_seed(tournament, new_slots, n, frozen_wins, max_d)
        # Actually compute wins after applying lookback slots, then seed the new ones from that
        lookback_wins = [row[:] for row in frozen_wins]
        for i in range(lookback):
            rank_s = fixed_ranks[k_frozen + i]
            for X in range(n):
                for Y in range(n):
                    if X == Y: continue
                    if rank_s[X] > rank_s[Y]:
                        lookback_wins[X][Y] += 1
        seed_new = deficit_seed(tournament, new_slots, n, lookback_wins, max_d)
        
        for slot in range(optimizing_slots):
            for X in range(n):
                for r in range(n):
                    if slot < lookback:
                        target_rank = fixed_ranks[k_frozen + slot][X]
                    else:
                        target_rank = seed_new[slot - lookback][X]
                    p[X, slot, r].Start = int(target_rank == r)
        
        # Permutation constraints
        for slot in range(optimizing_slots):
            for X in range(n):
                m.addConstr(gp.quicksum(p[X, slot, r] for r in range(n)) == 1)
            for r in range(n):
                m.addConstr(gp.quicksum(p[X, slot, r] for X in range(n)) == 1)
        
        # Win indicators
        wins_slot = m.addVars(n, n, optimizing_slots, vtype=GRB.BINARY, name="ws")
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                for slot in range(optimizing_slots):
                    rank_X = gp.quicksum(r * p[X, slot, r] for r in range(n))
                    rank_Y = gp.quicksum(r * p[Y, slot, r] for r in range(n))
                    m.addConstr(rank_X - rank_Y >= 1 - n * (1 - wins_slot[X, Y, slot]))
                    m.addConstr(rank_X - rank_Y <= -1 + n * wins_slot[X, Y, slot])
        
        # Slack constraints (using frozen_wins, not total wins, since lookback is now variable)
        for X in range(n):
            for Y in range(n):
                if X == Y: continue
                total_wins = frozen_wins[X][Y] + gp.quicksum(wins_slot[X, Y, slot] for slot in range(optimizing_slots))
                if tournament[X][Y]:
                    m.addConstr(total_wins + s_slack[X, Y] >= threshold)
                else:
                    m.addConstr(total_wins <= threshold - 1 + s_slack[X, Y])
        
        m.setObjective(gp.quicksum(s_slack[X, Y] for X in range(n) for Y in range(n) if X != Y),
                    GRB.MINIMIZE)
        m.optimize()
        
        if m.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED) or m.SolCount == 0:
            if verbose: print(f"    solver failed ({m.Status})")
            return None
        
        total_slack = m.ObjVal
        if verbose:
            print(f"    total slack = {total_slack}")
        
        # Extract all optimizing slots — replace the lookback ones and append the new ones
        new_optimized_ranks = []
        for slot in range(optimizing_slots):
            rank_s = [0] * n
            for X in range(n):
                for r in range(n):
                    if p[X, slot, r].X > 0.5:
                        rank_s[X] = r
                        break
            new_optimized_ranks.append(rank_s)
        
        # Replace lookback slots, then append new ones
        fixed_ranks = fixed_ranks[:k_frozen] + new_optimized_ranks
        
        # Recompute wins from the new fixed_ranks
        wins = [[0]*n for _ in range(n)]
        for rank_s in fixed_ranks:
            for X in range(n):
                for Y in range(n):
                    if X == Y: continue
                    if rank_s[X] > rank_s[Y]:
                        wins[X][Y] += 1
        
        if total_slack == 0:
            if verbose: print(f"  solved with d = {len(fixed_ranks)}")
            return reconstruct_dice(fixed_ranks, n)

    return None

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

max_d = 47
tournament = qr_tournament(67)
dice = incremental_solve(tournament, max_d)
if dice:
    new_tournament = get_tournament(dice)
    print(new_tournament)
    print(new_tournament == tournament)
    print(check_tournament(new_tournament, 2))
    print("Sides", len(dice[0]))