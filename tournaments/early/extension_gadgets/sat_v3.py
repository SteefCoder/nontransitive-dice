from itertools import chain, combinations, product
import time

from pysat.solvers import Cadical300
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from tqdm import tqdm

def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

def canonical_rep(S, n):
    return min(((S << k) | (S >> (n - k))) & ((1 << n) - 1) for k in range(n))


# def verify(dice: list[list[int]]):
#     n = len(dice)
#     f = len(dice[0])
#     for S in tqdm(powerset(range(n)), total=2**n):

def solve(n: int, f: int):
    pool = IDPool()
    solver = Cadical300()

    def V(X, Y, i):
        return pool.id(('v', X, Y, i)) if X < Y else -pool.id(('v', Y, X, i))
    
    def W(S, X, i):
        return pool.id(('w', S, X, i))
    
    for X in range(n):
        for Y in range(X):
            solver.add_clause([V(X, Y, 0)])

    for X in range(n):
        for Y in range(n):
            if X == Y:
                continue
            for Z in range(n):
                if Z in (X, Y):
                    continue
                
                for i in range(f):
                    solver.add_clause([-V(X, Y, i), -V(Y, Z, i), V(X, Z, i)])
    
    for S in tqdm(powerset(range(n)), total=2**n):
        for X in range(n):
            for Y in range(n):
                if X == Y:
                    continue
                for i in range(f):
                    solver.add_clause([-W(S, X, i), -V(X, Y, i), W(S, Y, i)])

        for X in range(n):
            lits = [W(S, X, i) for i in range(f)]
            if X in S:
                # for group in combinations(lits, f // 2 + 1):
                #     solver.add_clause(group)
                cnf = CardEnc.equals(lits, f // 2 + 1, vpool=pool, encoding=EncType.totalizer)
            else:
                cnf = CardEnc.equals(lits, f // 2, vpool=pool, encoding=EncType.totalizer)
                # for group in combinations(lits, f // 2):
                #     solver.add_clause([-g for g in group])
            solver.append_formula(cnf.clauses)
    
    print("Starting solve!")
    t0 = time.time()
    sat = solver.solve()
    print(solver.accum_stats())
    dt = time.time() - t0
    if not sat:
        return None, dt, {}
    model = set(solver.get_model())  # type: ignore
    # Reconstruct x_i^X = sum over (Y,j) of [X,Y]_{i,j}
    dice = []
    for X in range(n):
        face_vals = []
        for i in range(f):
            v = sum(1 for Y in range(n) if V(X, Y, i) in model)
            face_vals.append(v)
        dice.append(face_vals)

    witness_dice = {}
    for S in powerset(range(n)):
        face_vals = []
        for i in range(f):
            v = sum(1 for X in range(n) if W(S, X, i) in model)
            face_vals.append(v)
        witness_dice[S] = face_vals

    #print([W((0,), 0, i) in model for i in range(f)])
    #print([V(0)])

    return dice, dt, witness_dice


def beats(X, Y):
    wins = sum(X[i] > Y[i] for i in range(len(X)))
    return wins > len(X) / 2


def verify(dice, witness_dice):
    for S, witness in witness_dice.items():
        for X in range(len(dice)):
            b = beats(witness, dice[X])
            if (X in S and not b) or (X not in S and b):
                print(f"{S=}, {X=}, {witness=}, {dice[X]=}, {b=}")
                return False
    return True


def main():
    sol, dt, witness_dice = solve(14, 6)
    if sol is None:
        print("UNSAT")
        return
    
    #print(witness_dice)
    print(sol)
    print("Verified:", verify(sol, witness_dice))
    print("Time:", round(dt, 3))


# [[0, 8, 9, 4, 7], [1, 0, 10, 7, 9], [2, 9, 1, 10, 3], [3, 10, 4, 3, 6], [4, 2, 5, 5, 8], [5, 6, 0, 9, 2], [6, 4, 2, 0, 10], [7, 5, 6, 6, 1], [8, 3, 7, 2, 5], [9, 1, 8, 8, 0], [10, 7, 3, 1, 4]]

main()