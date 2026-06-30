from pysat.solvers import Minicard, Cadical300, Cadical195, Solver
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
import time
from tqdm import tqdm
import numpy as np

def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]

def solve(tournament, d):
    n = len(tournament)
    pool = IDPool()

    def V(X, Y, i, j):
        # [X,Y]_{i,j}: face i of X >= face j of Y
        if j < i:
            return pool.id('true')
        if j > i:
            return pool.id('false')

        return pool.id(('v', X, Y, i, j)) if X < Y else -pool.id(('v', Y, X, j, i))

    solver = Cadical300()
    # Reflexive
    for X in range(n):
        for i in range(d):
            for j in range(d):
                lit = V(X, X, i, j)
                solver.add_clause([lit] if i >= j else [-lit])

    solver.add_clause([pool.id('true')])
    solver.add_clause([-pool.id('false')])

    for X in tqdm(range(n)):
        for Y in range(X + 1, n):
            if X == Y: continue
            for i in range(d):
                for j in range(d):
                    # cache the pool id's
                    V(X, Y, i, j)
                    V(Y, X, j, i)

    # # Sorting: faces ascending within each die
    # for X in tqdm(range(n)):
    #     for Y in range(X):
    #         for i in range(d):
    #             for j in range(1, d):
    #                 solver.add_clause([-V(X, Y, i, j), V(X, Y, i, j-1)])  # horizontal
    #         for i in range(d-1):
    #             for j in range(d):
    #                 solver.add_clause([-V(X, Y, i, j), V(X, Y, i+1, j)])  # vertical

    # Transitivity
    for X in tqdm(range(n)):
        for Y in range(n):
            for Z in range(n):
                if Z in (X, Y): continue
                for i in range(d):
                    solver.add_clause([-V(X, Y, i, i), -V(Y, Z, i, i), V(X, Z, i, i)])
    # Cardinality (lower-bound only, half the pairs)
    threshold = d // 2 + 1
    for X in tqdm(range(n)):
        for Y in range(n):
            if X == Y or not tournament[X][Y]: continue
            lits = [V(X, Y, i, i) for i in range(d)]
            card_cnf = CardEnc.atleast(lits=lits, bound=threshold,
                                        encoding=EncType.totalizer, vpool=pool)
            solver.append_formula(card_cnf.clauses)

    print("Starting solve!")
    t0 = time.time()
    sat = solver.solve()
    print(solver.accum_stats())
    dt = time.time() - t0
    if not sat:
        return None, dt
    model = set(solver.get_model())
    # Reconstruct x_i^X = sum over (Y,j) of [X,Y]_{i,j}
    dice = []
    for X in range(n):
        face_vals = []
        for i in range(d):
            v = sum(1 for Y in range(n) for j in range(d) if V(X, Y, i, j) in model)
            face_vals.append(v)
        dice.append(sorted(face_vals))
    return dice, dt

def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            w = sum(1 for a in dice[i] for b in dice[j] if a > b)
            if bool(tournament[i][j]) != (2*w > len(dice[i])*len(dice[j])): return False
    return True

if __name__ == "__main__":
    import sys
    p = int(sys.argv[1])
    d = int(sys.argv[2])
    
    s = int(sys.argv[3]) if len(sys.argv) > 3 else p
    t = [x[:s] for x in qr_tournament(p)[:s]]
    print(f"P_{p}, d={d}:")
    sol, dt = solve(t, d)
    if sol is None:
        print(f"  UNSAT ({dt:.1f}s)")
    else:
        # for i, row in enumerate(sol):
        #     print(f"  die {i}: {row}")
        #print(sol)
        if s == p:
            filename = f"n-player/results/p_{p}_f_{d}_sat.txt"
        else:
            filename = f"n-player/results/p_{p}_sub_{s}_f_{d}_sat.txt"
        with open(filename, "w") as f:
            for die in sol:
                f.write(" ".join(map(str, die)) + "\n")

        print(f"  verified: {verify(sol, t)}  ({dt:.1f}s)")
