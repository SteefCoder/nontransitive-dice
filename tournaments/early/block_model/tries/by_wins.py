# paley_algebraic_sat.py
import subprocess
import os
import time
from pysat.formula import IDPool, CNF
from pysat.card import CardEnc, EncType


def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]


def encode(tournament, d, path, restrict_affine=False):
    """
    Algebraic-restricted: there exists a permutation π on {1..nd} such that
    die i+1 = π(die i) for all i. Search over (die 0, π) jointly.

    If restrict_affine: π must be affine on Z_{nd}: π(v) = (a*v + b) mod (nd) + 1.
    """
    n = len(tournament)
    V = n * d  # max face value
    pool = IDPool()

    # g(i, v) = 1 iff value v (in 1..V) is a face of die i
    def g(i, v): return pool.id(('g', i, v))
    # pi(u, v) = 1 iff permutation maps u -> v
    def pi(u, v): return pool.id(('pi', u, v))
    # h(i, u, v) = g(i, u) AND pi(u, v) — auxiliary for the recurrence
    def h(i, u, v): return pool.id(('h', i, u, v))

    # Preallocate for nice ordering
    for i in range(n):
        for v in range(1, V+1):
            pool.id(('g', i, v))
    if not restrict_affine:
        for u in range(1, V+1):
            for v in range(1, V+1):
                pool.id(('pi', u, v))

    f = open(path, 'wb', buffering=1 << 24)
    f.write(b"p cnf 0000000000 0000000000\n")
    n_clauses = 0

    def w(lits):
        nonlocal n_clauses
        f.write(b' '.join(str(l).encode() for l in lits))
        f.write(b' 0\n')
        n_clauses += 1

    # Each die has exactly d faces
    for i in range(n):
        lits = [g(i, v) for v in range(1, V+1)]
        for cl in CardEnc.equals(lits=lits, bound=d,
                                 encoding=EncType.totalizer, vpool=pool).clauses:
            w(cl)

    # Across all dice, each value used exactly once
    # (since dice partition {1..V} into n groups of d)
    for v in range(1, V+1):
        lits = [g(i, v) for i in range(n)]
        for cl in CardEnc.equals(lits=lits, bound=1,
                                 encoding=EncType.totalizer, vpool=pool).clauses:
            w(cl)

    if restrict_affine:
        # π is affine: π(v) = ((a*(v-1) + b) mod V) + 1 for some (a, b)
        # with gcd(a, V) = 1.
        # Enumerate (a, b) choices and encode as selector variables.
        from math import gcd
        valid_a = [a for a in range(1, V+1) if gcd(a, V) == 1]
        # Selector sel(a, b) = 1 iff (a, b) is chosen
        def sel(a, b): return pool.id(('sel', a, b))
        sel_lits = [sel(a, b) for a in valid_a for b in range(V)]
        # Exactly one (a, b) chosen
        for cl in CardEnc.equals(lits=sel_lits, bound=1,
                                 encoding=EncType.totalizer, vpool=pool).clauses:
            w(cl)
        # For each (a, b) chosen, the permutation is fixed.
        # Encode: sel(a, b) -> for all i, v: g(i+1, v) <-> g(i, π_{a,b}^{-1}(v))
        # where π_{a,b}(v) = ((a*(v-1) + b) mod V) + 1
        for a in valid_a:
            a_inv = pow(a, -1, V)
            for b in range(V):
                s = sel(a, b)
                for i in range(n - 1):
                    for v in range(1, V+1):
                        # π_{a,b}(u) = v  iff  u = π_{a,b}^{-1}(v) = ((v-1-b)*a_inv mod V)+1
                        u = ((v - 1 - b) * a_inv) % V + 1
                        # s -> (g(i+1, v) <-> g(i, u))
                        w([-s, -g(i+1, v), g(i, u)])
                        w([-s, g(i+1, v), -g(i, u)])
                # Closure: die n-1 -> die 0 via π
                for v in range(1, V+1):
                    u = ((v - 1 - b) * a_inv) % V + 1
                    w([-s, -g(0, v), g(n-1, u)])
                    w([-s, g(0, v), -g(n-1, u)])
    else:
        # General π: permutation on {1..V}, each row and column has exactly one true.
        for u in range(1, V+1):
            lits = [pi(u, v) for v in range(1, V+1)]
            for cl in CardEnc.equals(lits=lits, bound=1,
                                     encoding=EncType.totalizer, vpool=pool).clauses:
                w(cl)
        for v in range(1, V+1):
            lits = [pi(u, v) for u in range(1, V+1)]
            for cl in CardEnc.equals(lits=lits, bound=1,
                                     encoding=EncType.totalizer, vpool=pool).clauses:
                w(cl)

        # h(i, u, v) <-> g(i, u) AND pi(u, v)
        for i in range(n):
            for u in range(1, V+1):
                for v in range(1, V+1):
                    hv = h(i, u, v)
                    gu = g(i, u)
                    pv = pi(u, v)
                    w([-hv, gu])
                    w([-hv, pv])
                    w([hv, -gu, -pv])

        # g(i+1, v) <-> exists u: h(i, u, v)
        for i in range(n - 1):
            for v in range(1, V+1):
                # forward: g(i+1, v) -> OR h(i, u, v)
                clause = [-g(i+1, v)] + [h(i, u, v) for u in range(1, V+1)]
                w(clause)
                # backward: for each u, h(i, u, v) -> g(i+1, v)
                for u in range(1, V+1):
                    w([-h(i, u, v), g(i+1, v)])

        # Closure: die n-1 mapped by π gives die 0
        for v in range(1, V+1):
            clause = [-g(0, v)] + [h(n-1, u, v) for u in range(1, V+1)]
            w(clause)
            for u in range(1, V+1):
                w([-h(n-1, u, v), g(0, v)])

    # Tournament constraints
    # For arc i -> j: wins of i over j >= threshold = d^2//2 + 1
    # wins = #{(u, v) : g(i, u) AND g(j, v) AND u > v}
    # Use auxiliaries win_uv(i, j, u, v) for u > v
    threshold = d * d // 2 + 1
    for i in range(n):
        for j in range(n):
            if i == j: continue
            arc_lits = []
            for u in range(1, V+1):
                for v in range(1, u):
                    aux = pool.id(('win', i, j, u, v))
                    # aux <-> g(i, u) AND g(j, v)
                    w([-aux, g(i, u)])
                    w([-aux, g(j, v)])
                    w([aux, -g(i, u), -g(j, v)])
                    arc_lits.append(aux)
            if tournament[i][j]:
                for cl in CardEnc.atleast(lits=arc_lits, bound=threshold,
                                          encoding=EncType.totalizer, vpool=pool).clauses:
                    w(cl)
            else:
                for cl in CardEnc.atmost(lits=arc_lits, bound=threshold - 1,
                                         encoding=EncType.totalizer, vpool=pool).clauses:
                    w(cl)

    n_vars = pool.top
    f.seek(0)
    placeholder = b"p cnf 0000000000 0000000000"
    f.write(f"p cnf {n_vars} {n_clauses}".encode().ljust(len(placeholder)) + b'\n')
    f.close()
    return n_vars, n_clauses, pool


def parse_solution(path):
    is_sat = None
    model = []
    with open(path) as f:
        for line in f:
            if line.startswith('s '):
                is_sat = 'SATISFIABLE' in line and 'UN' not in line
            elif line.startswith('v '):
                model.extend(int(x) for x in line[2:].split() if int(x) != 0)
    return set(model) if is_sat else None


def reconstruct_dice(model, n, d):
    V = n * d
    pool = IDPool()
    # Re-allocate g vars in the same order as during writing
    for i in range(n):
        for v in range(1, V+1):
            pool.id(('g', i, v))

    def g_id(i, v): return pool.id(('g', i, v))

    dice = []
    for i in range(n):
        faces = sorted(v for v in range(1, V+1) if g_id(i, v) in model)
        dice.append(faces)
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


def solve(p, d, restrict_affine=False, cadical='cadical', time_limit=600,
          keep_files=False):
    tournament = qr_tournament(p)
    n = len(tournament)
    tag = 'affine' if restrict_affine else 'perm'
    cnf_path = f'paley_alg_{tag}_{p}_d{d}.cnf'
    sol_path = f'paley_alg_{tag}_{p}_d{d}.sol'

    print(f"P_{p}, d={d}, mode={tag}")
    print(f"  encoding to {cnf_path}...")
    t0 = time.time()
    n_vars, n_clauses, _ = encode(tournament, d, cnf_path, restrict_affine=restrict_affine)
    t1 = time.time()
    size_mb = os.path.getsize(cnf_path) / 1e6
    print(f"  {n_vars} vars, {n_clauses} clauses, {size_mb:.1f} MB ({t1-t0:.1f}s)")

    print(f"  solving with {cadical}...")
    cmd = [cadical, cnf_path]
    if time_limit:
        cmd.extend(['-t', str(time_limit)])
    with open(sol_path, 'w') as out:
        subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL)
    t2 = time.time()
    print(f"  solver finished in {t2-t1:.1f}s")

    model = parse_solution(sol_path)
    if not keep_files:
        os.remove(cnf_path)
        os.remove(sol_path)

    if model is None:
        print(f"  UNSAT")
        return None
    dice = reconstruct_dice(model, n, d)
    ok = verify(dice, tournament)
    print(f"  {'verified' if ok else 'verification FAILED'}")
    return dice


if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    mode = sys.argv[3] if len(sys.argv) > 3 else 'affine'
    binary = sys.argv[4] if len(sys.argv) > 4 else 'cadical'
    restrict = (mode == 'affine')

    dice = solve(p, d, restrict_affine=restrict, cadical=binary)
    if dice:
        for i, row in enumerate(dice[:8]):
            print(f"  die {i}: {row}")
        if len(dice) > 8:
            print(f"  ... ({len(dice)-8} more)")