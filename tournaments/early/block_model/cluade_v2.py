# paley_block_sat.py
import subprocess
import os
import time
from pysat.formula import IDPool
from pysat.card import CardEnc, EncType


def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]


def write_dimacs(tournament, d, path):
    """
    Block-rank encoding. Each die has d faces; face f of die X has value
    f*n + rank, where rank in {0..n-1} is X's rank in slot f (one permutation
    of n dice per slot).

    Variables:
      r(X, i, k) for k in 1..n-1: die X has rank >= k in slot i.
                                  (rank >= 0 is trivially true, so k starts at 1.)
      u(X, Y, i) for X != Y:      die X outranks die Y in slot i.

    Constraints:
      monotonicity:  r(X,i,k) -> r(X,i,k-1)            (for k >= 2)
      permutation:   exactly (n-k) dice have rank >= k in slot i
                     (totalizer or sequential encoding on r vars per (i,k))
      linking:       u(X,Y,i) <-> for all k: r(Y,i,k) -> r(X,i,k)
                     (implemented as one-direction implication + converse)
      converse:      u(X,Y,i) + u(Y,X,i) = 1
      cardinality:   if X beats Y in tournament: sum_i u(X,Y,i) >= d/2 + 1
      slot symmetry: u(0,1,i) >= u(0,1,i+1) for i = 0..d-2
    """
    n = len(tournament)
    pool = IDPool()

    def r(X, i, k):
        return pool.id(('r', X, i, k))

    def u(X, Y, i):
        return pool.id(('u', X, Y, i))

    # Preallocate
    for X in range(n):
        for i in range(d):
            for k in range(1, n):
                pool.id(('r', X, i, k))
    for X in range(n):
        for Y in range(n):
            if X == Y: continue
            for i in range(d):
                pool.id(('u', X, Y, i))

    f = open(path, 'wb', buffering=1 << 24)
    f.write(b"p cnf 0000000000 0000000000\n")
    n_clauses = 0

    def write_clause(lits):
        nonlocal n_clauses
        f.write(b' '.join(str(l).encode() for l in lits))
        f.write(b' 0\n')
        n_clauses += 1

    # Monotonicity: r(X,i,k) -> r(X,i,k-1) for k >= 2
    for X in range(n):
        for i in range(d):
            for k in range(2, n):
                write_clause([-r(X, i, k), r(X, i, k-1)])

    # Permutation per slot per rank-level k:
    # exactly (n-k) dice have rank >= k.
    # Use atleast (totalizer) and atmost (totalizer) on each (i, k).
    for i in range(d):
        for k in range(1, n):
            lits = [r(X, i, k) for X in range(n)]
            atleast = CardEnc.atleast(lits=lits, bound=n - k,
                                      encoding=EncType.seqcounter, vpool=pool)
            atmost = CardEnc.atmost(lits=lits, bound=n - k,
                                    encoding=EncType.seqcounter, vpool=pool)
            for cl in atleast.clauses + atmost.clauses:
                write_clause(cl)

    # Converse
    for X in range(n):
        for Y in range(X+1, n):
            for i in range(d):
                a, b = u(X, Y, i), u(Y, X, i)
                write_clause([a, b])
                write_clause([-a, -b])

    # Linking: u(X,Y,i) -> for all k: r(Y,i,k) -> r(X,i,k)
    # Combined with converse, this fully determines u from r.
    for X in range(n):
        for Y in range(n):
            if X == Y: continue
            for i in range(d):
                for k in range(1, n):
                    write_clause([-u(X, Y, i), -r(Y, i, k), r(X, i, k)])
    
    # Reverse linking: r(X,i,k) ∧ ¬r(Y,i,k) → u(X,Y,i)
    for X in range(n):
        for Y in range(n):
            if X == Y: continue
            for i in range(d):
                for k in range(1, n):
                    write_clause([-r(X, i, k), r(Y, i, k), u(X, Y, i)])
   
    # Slot symmetry break
    for i in range(d - 1):
        write_clause([u(0, 1, i), -u(0, 1, i+1)])

    # Cardinality: tournament arcs
    threshold = d // 2 + 1
    for X in range(n):
        for Y in range(n):
            if X == Y or not tournament[X][Y]: continue
            lits = [u(X, Y, i) for i in range(d)]
            card = CardEnc.atleast(lits=lits, bound=threshold,
                                   encoding=EncType.totalizer, vpool=pool)
            for cl in card.clauses:
                write_clause(cl)

    n_vars = pool.top
    f.seek(0)
    placeholder_len = len(b"p cnf 0000000000 0000000000")
    f.write(f"p cnf {n_vars} {n_clauses}".encode().ljust(placeholder_len) + b'\n')
    f.close()
    return n_vars, n_clauses


def parse_solution(path):
    is_sat = None
    assignment = []
    with open(path) as f:
        for line in f:
            if line.startswith('s '):
                is_sat = 'UNSATISFIABLE' not in line and 'SATISFIABLE' in line
            elif line.startswith('v '):
                assignment.extend(int(x) for x in line[2:].split() if int(x) != 0)
    if not is_sat:
        return None
    return set(assignment)


def reconstruct_dice(model, n, d):
    """Recompute the rank from the truth values of r(X,i,k)."""
    pool = IDPool()
    # Allocate r in the same order as during writing
    for X in range(n):
        for i in range(d):
            for k in range(1, n):
                pool.id(('r', X, i, k))

    def r_id(X, i, k):
        return pool.id(('r', X, i, k))

    dice = []
    for X in range(n):
        faces = []
        for i in range(d):
            # rank = max k such that r(X,i,k) is true, or 0 if none
            rank = sum(1 for k in range(1, n) if r_id(X, i, k) in model)
            faces.append(i * n + rank)
        dice.append(sorted(faces))
    return dice


def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            w = sum(1 for a in dice[i] for b in dice[j] if a > b)
            l = sum(1 for a in dice[i] for b in dice[j] if a < b)
            if bool(tournament[i][j]) != (w > l): return False
    return True


def solve(p, d, cadical_binary='cadical', time_limit=None, keep_files=False):
    tournament = qr_tournament(p)
    n = len(tournament)
    cnf_path = f'paley_block_{p}_d{d}.cnf'
    sol_path = f'paley_block_{p}_d{d}.sol'

    print(f"Writing DIMACS to {cnf_path}...")
    t0 = time.time()
    n_vars, n_clauses = write_dimacs(tournament, d, cnf_path)
    t1 = time.time()
    size_mb = os.path.getsize(cnf_path) / 1e6
    print(f"  {n_vars} vars, {n_clauses} clauses, {size_mb:.1f} MB ({t1-t0:.1f}s)")

    print(f"Running {cadical_binary}...")
    cmd = [cadical_binary, cnf_path]
    if time_limit:
        cmd.extend(['-t', str(time_limit)])
    with open(sol_path, 'w') as out:
        result = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE)
    t2 = time.time()
    print(f"  finished in {t2-t1:.1f}s")

    model = parse_solution(sol_path)
    if not keep_files:
        os.remove(cnf_path)
        os.remove(sol_path)

    if model is None:
        print("  UNSAT")
        return None
    dice = reconstruct_dice(model, n, d)
    print(f"  verified: {verify(dice, tournament)}")
    return dice


if __name__ == "__main__":
    import sys
    p = int(sys.argv[1])
    d = int(sys.argv[2])
    binary = sys.argv[3] if len(sys.argv) > 3 else 'cadical300'
    dice = solve(p, d, cadical_binary=binary)
    if dice:
        for i, row in enumerate(dice[:8]):
            print(f"  die {i}: {row}")
        if len(dice) > 8:
            print(f"  ... ({len(dice)-8} more)")
