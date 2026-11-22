# paley_lazy_transitivity.py
import time
from pysat.solvers import Solver, Cadical300, Cadical195
from pysat.formula import IDPool, CNF
from pysat.card import CardEnc, EncType
from tqdm import tqdm

def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]


def check_full_transitivity(model, n, d, V):
    violations = []
    for X in range(n):
        for Y in range(n):
            if Y == X: continue
            for Z in range(n):
                if Z == X or Z == Y: continue
                for i in range(d):
                    for j in range(d):
                        v_xy_ij = V(X, Y, i, j)
                        if v_xy_ij not in model:
                            continue
                        for k in range(d):
                            v_yz_jk = V(Y, Z, j, k)
                            if v_yz_jk not in model:
                                continue
                            v_xz_ik = V(X, Z, i, k)
                            if v_xz_ik not in model:
                                # Violation!
                                violations.append([-v_xy_ij, -v_yz_jk, v_xz_ik])
    return not violations, "violation found"


def solve(tournament, d, solver_name='cadical195', verbose=True,
          max_iterations=1000, max_batch=50000):
    n = len(tournament)
    pool = IDPool()

    def V(X, Y, i, j):
        return pool.id(('v', X, Y, i, j)) if X < Y else -pool.id(('v', Y, X, j, i))

    # Preallocate
    for X in range(n):
        for Y in range(X+1, n):
            for i in range(d):
                for j in range(d):
                    pool.id(('v', X, Y, i, j))

    cnf = CNF()

    # Reflexive (diagonal vars used as units)
    for X in tqdm(range(n)):
        for i in range(d):
            for j in range(d):
                lit = pool.id(('v', X, X, i, j))
                cnf.append([lit] if i >= j else [-lit])

    # Sorting
    for X in tqdm(range(n)):
        for Y in range(n):
            if X == Y: continue
            for i in range(d):
                for j in range(1, d):
                    cnf.append([-V(X, Y, i, j), V(X, Y, i, j-1)])
            for i in range(d-1):
                for j in range(d):
                    cnf.append([-V(X, Y, i, j), V(X, Y, i+1, j)])

    # Initial "diagonal" transitivity (cheap, propagates strongly)
    # Only add clauses where j is "in the middle" to seed the encoding.
    # Specifically: clauses where i == j or j == k (sorting-adjacent).
    for X in tqdm(range(n)):
        for Y in range(n):
            if Y == X: continue
            for Z in range(n):
                if Z == X or Z == Y: continue
                for i in range(d):
                    for j in range(d):
                        # case k = j: V(X,Y,i,j) ∧ V(Y,Z,j,j) → V(X,Z,i,j)
                        cnf.append([-V(X, Y, i, j), -V(Y, Z, j, j), V(X, Z, i, j)])

    # Cardinality
    threshold = d * d // 2 + 1
    for X in tqdm(range(n)):
        for Y in range(n):
            if X == Y or not tournament[X][Y]: continue
            lits = [V(X, Y, i, j) for i in range(d) for j in range(d)]
            card = CardEnc.atleast(lits=lits, bound=threshold,
                                   encoding=EncType.totalizer, vpool=pool)
            for cl in card.clauses:
                cnf.append(cl)

    solver = Cadical195(use_timer=True, incr=True)
    
    solver.append_formula(cnf.clauses)
    if verbose:
        print(f"Initial: {len(cnf.clauses)} clauses, {pool.top} vars")

    total_added = 0
    for iteration in range(max_iterations):
        sat = solver.solve()
        if not sat:
            if verbose:
                print(f"UNSAT after {iteration} refinements, {total_added} added clauses, {solver.time():.1f}s total")
            solver.delete()
            return None

        model = set(solver.get_model())

        # Find violated transitivity clauses
        violations = []
        for X in range(n):
            for Y in range(n):
                if Y == X: continue
                for Z in range(n):
                    if Z == X or Z == Y: continue
                    for i in range(d):
                        for j in range(d):
                            v_xy_ij = V(X, Y, i, j)
                            if v_xy_ij not in model:
                                continue
                            for k in range(d):
                                v_yz_jk = V(Y, Z, j, k)
                                if v_yz_jk not in model:
                                    continue
                                v_xz_ik = V(X, Z, i, k)
                                if v_xz_ik not in model:
                                    # Violation!
                                    violations.append([-v_xy_ij, -v_yz_jk, v_xz_ik])
                                    if len(violations) >= max_batch:
                                        break
                            if len(violations) >= max_batch: break
                        if len(violations) >= max_batch: break
                    if len(violations) >= max_batch: break
                if len(violations) >= max_batch: break
            if len(violations) >= max_batch: break

        if not violations:
            # Genuine solution
            if verbose:
                print(f"SAT after {iteration} refinements, {total_added} added clauses, {solver.time():.1f}s total")
            dice = reconstruct(model, n, d, V)
            ok, info = check_full_transitivity(model, n, d, V)
            if not ok:
                print(f"Hidden transitivity violation: {info}")

            solver.delete()
            return dice

        if verbose:
            print(f"  iter {iteration}: {len(violations)} violations, adding clauses ({solver.time():.1f}s)")
        for cl in violations:
            solver.add_clause(cl)
        total_added += len(violations)

    if verbose:
        print(f"Max iterations ({max_iterations}) reached")
    solver.delete()
    return None


def reconstruct(model, n, d, V):
    dice = []
    for X in range(n):
        faces = []
        for i in range(d):
            # Include Y = X: V(X,X,i,j) = 1 iff i >= j, contributes i+1
            v = (i + 1) + sum(
                1 for Y in range(n) for j in range(d)
                if X != Y and V(X, Y, i, j) in model
            )
            faces.append(v)
        dice.append(sorted(faces))
    return dice

def create_tournament(dice):
    n = len(dice)
    tournament = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j: continue
            w = sum(1 for a in dice[i] for b in dice[j] if a > b)
            l = sum(1 for a in dice[i] for b in dice[j] if a < b)
            tournament[i][j] = int(w > l)
    return tournament

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
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    solver_name = sys.argv[3] if len(sys.argv) > 3 else 'cadical300'

    t = qr_tournament(p)
    t0 = time.time()
    dice = solve(t, d, solver_name=solver_name)
    print(f"Total time: {time.time()-t0:.1f}s")
    if dice:
        for row in create_tournament(dice):
            print("  " + " ".join(map(str, row)))
        for i, row in enumerate(dice[:8]):
            print(f"  die {i}: {row}")
        if len(dice) > 8:
            print(f"  ... ({len(dice)-8} more)")
        print(f"verified: {verify(dice, t)}")
