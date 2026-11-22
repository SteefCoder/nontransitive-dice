"""
Realising a tournament as a profile of linear orders, with as few ballots as possible.

Four stages, each of which stands alone:

  1. bounds(b, n)        lower bounds on the ballot count: parity, max margin,
                         the closed-form pseudoinverse norm, and (small n) the
                         exact l1 LP relaxation.
  2. mcgarvey(b, n)      a feasible warm start, O(n^2) ballots.
  3. descend(profile)    Graver augmentation using every move of weight <= 6.
  4. exact_ilp(b, n, k)  the compact k-slot linear-ordering ILP, exact.

Conventions
-----------
n           candidates 1..n
pairs       the C(n,2) unordered pairs in lexicographic order
ballot      a tuple giving a ranking, best first, e.g. (3,1,4,2)
margin      vector over `pairs`; entry for (a,b) is  #(a before b) - #(b before a)
profile     a list of ballots (repeats allowed)

A Graver element of the margin map corresponds to a perfectly tied ballot
multiset.  An improving move is therefore a sub-profile S replaced by a
strictly smaller T with phi(T) = phi(S); weight |S|+|T| <= 6 means |T| <= 2,
so `realise` only ever has to solve the k = 0, 1, 2 cases, which it does
exactly.
"""

from __future__ import annotations

import itertools
from collections import Counter
from fractions import Fraction
from math import factorial

import numpy as np


# ----------------------------------------------------------------------
# basics
# ----------------------------------------------------------------------

def make_pairs(n):
    return list(itertools.combinations(range(1, n + 1), 2))


def margin(profile, n, pairs=None):
    """Margin vector of a profile."""
    pairs = pairs or make_pairs(n)
    out = [0] * len(pairs)
    for L in profile:
        pos = {v: i for i, v in enumerate(L)}
        for k, (a, b) in enumerate(pairs):
            out[k] += 1 if pos[a] < pos[b] else -1
    return tuple(out)


def ballot_margin(L, pairs):
    pos = {v: i for i, v in enumerate(L)}
    return tuple(1 if pos[a] < pos[b] else -1 for a, b in pairs)


def tournament_from_edges(n, beats):
    """beats = iterable of ordered pairs (a, b) meaning a -> b. Returns b in {+-1}^C(n,2)."""
    beats = set(beats)
    out = []
    for a, c in make_pairs(n):
        if (a, c) in beats and (c, a) not in beats:
            out.append(1)
        elif (c, a) in beats and (a, c) not in beats:
            out.append(-1)
        else:
            raise ValueError(f"pair {{{a},{c}}} not oriented exactly once")
    return tuple(out)


def is_transitive(u, n, pairs):
    """u has +-1 entries; is the tournament it defines a linear order?"""
    score = {a: 0 for a in range(1, n + 1)}
    for k, (a, b) in enumerate(pairs):
        if u[k] > 0:
            score[a] += 1
        else:
            score[b] += 1
    return sorted(score.values()) == list(range(n))


def ballot_of(u, n, pairs):
    """The ballot whose margin vector is u, or None if u is not transitive."""
    if not all(abs(v) == 1 for v in u) or not is_transitive(u, n, pairs):
        return None
    score = {a: 0 for a in range(1, n + 1)}
    for k, (a, b) in enumerate(pairs):
        if u[k] > 0:
            score[a] += 1
        else:
            score[b] += 1
    return tuple(sorted(range(1, n + 1), key=lambda a: -score[a]))


# ----------------------------------------------------------------------
# 1. lower bounds
# ----------------------------------------------------------------------

def _reversal_reps(n):
    reps, seen = [], set()
    for L in itertools.permutations(range(1, n + 1)):
        if L in seen:
            continue
        seen.add(L)
        seen.add(L[::-1])
        reps.append(L)
    return reps


def pseudoinverse_norm(b, n, pairs=None):
    """
    ||phi^+(b)||_2 in closed form.  Schur's lemma makes phi phi^T a scalar on each
    of the two isotypic pieces of Lambda^2 Q^n, so no matrix is inverted:

        ||phi^+(b)||^2 = (6/n!) * ( ||b||^2 - (1/(n+1)) * sum_a r_a^2 )

    with r_a the Copeland score.  (The 6 rather than 3 is the reversal quotient.)
    Since ||x||_1 >= ||x||_2 >= ||phi^+(b)||_2 for every feasible x, this is a
    valid lower bound on the number of ballots.
    """
    pairs = pairs or make_pairs(n)
    full = {}
    for k, (a, c) in enumerate(pairs):
        full[(a, c)] = b[k]
        full[(c, a)] = -b[k]
    r = {a: sum(full[(a, c)] for c in range(1, n + 1) if c != a) for a in range(1, n + 1)}
    nb = sum(v * v for v in b)
    val = Fraction(6, factorial(n)) * (nb - Fraction(sum(r[a] ** 2 for a in r), n + 1))
    return float(val) ** 0.5, r


def lp_lower_bound(b, n, max_columns=25000):
    """
    Exact optimum of  min ||x||_1  s.t.  Ax = b  over the reals, by enumerating
    all n!/2 reversal classes as columns.  A genuine lower bound on the integer
    ballot count.  Returns None when the column count is too large.
    """
    from scipy.optimize import linprog

    reps = _reversal_reps(n)
    if len(reps) > max_columns:
        return None
    pairs = make_pairs(n)
    A = np.array([ballot_margin(L, pairs) for L in reps], dtype=float).T
    Aeq = np.hstack([A, -A])
    res = linprog(np.ones(2 * A.shape[1]), A_eq=Aeq, b_eq=np.array(b, dtype=float),
                  bounds=(0, None), method="highs")
    return float(res.fun) if res.success else None


def bounds(b, n):
    """All available lower bounds on the number of ballots realising margins b."""
    pairs = make_pairs(n)
    pin, r = pseudoinverse_norm(b, n, pairs)
    out = {
        "parity": "ballot count = |b_p| mod 2 for every pair",
        "max_margin": max(abs(v) for v in b),
        "pseudoinverse_l2": pin,
        "copeland": tuple(sorted(r.values())),
    }
    lp = lp_lower_bound(b, n)
    if lp is not None:
        out["lp_l1"] = lp
    return out


# ----------------------------------------------------------------------
# 2. warm start
# ----------------------------------------------------------------------

def gadget(a, c, n):
    """Two ballots whose margins sum to +2 on pair (a,c) and 0 everywhere else."""
    rest = tuple(x for x in range(1, n + 1) if x not in (a, c))
    return [(a, c) + rest, tuple(reversed(rest)) + (a, c)]


def mcgarvey(b, n):
    """
    Feasible profile with margins exactly b.  One reference ballot plus
    (b_p - m_p)/2 copies of the gadget  1 - (a c)  for each pair.
    Requires every b_p to have the same parity.
    """
    pairs = make_pairs(n)
    par = {abs(v) % 2 for v in b}
    if len(par) > 1:
        raise ValueError("margins must all share a parity to be realisable")
    L0 = tuple(range(1, n + 1))
    profile = [] if (b[0] % 2 == 0) else [L0]
    base = margin(profile, n, pairs)
    for k, (a, c) in enumerate(pairs):
        d = b[k] - base[k]
        assert d % 2 == 0
        for _ in range(abs(d) // 2):
            profile += gadget(a, c, n) if d > 0 else gadget(c, a, n)
    return profile

def fromfile(file):
    a = np.loadtxt(file, dtype=np.int32)
    return [tuple(map(int, x)) for x in (a - a.shape[0]*np.arange(a.shape[1])).T]

# ----------------------------------------------------------------------
# 3. Graver descent
# ----------------------------------------------------------------------

def _linear_extensions(n, forced, cap=200000):
    """All linear orders extending the strict relation `forced` (dict a -> set)."""
    preds = {a: set() for a in range(1, n + 1)}
    for a, tos in forced.items():
        for c in tos:
            preds[c].add(a)
    out, count = [], 0

    def rec(placed, remaining):
        nonlocal count
        if count > cap:
            return
        if not remaining:
            out.append(tuple(placed))
            count += 1
            return
        for a in sorted(remaining):
            if preds[a] & remaining:
                continue
            rec(placed + [a], remaining - {a})

    rec([], set(range(1, n + 1)))
    return out


def realise(u, k, n, pairs):
    """
    A list of exactly k ballots with margin vector u, or None.
    Exact for k in {0, 1, 2}; k > 2 is refused (weight-6 moves never need it).
    """
    if k == 0:
        return [] if all(v == 0 for v in u) else None
    if any(abs(v) > k or (abs(v) - k) % 2 for v in u):
        return None
    if k == 1:
        L = ballot_of(u, n, pairs)
        return [L] if L else None
    if k > 3:
        raise ValueError("realise supports k <= 3")

    forced = {a: set() for a in range(1, n + 1)}
    for idx, (a, c) in enumerate(pairs):
        if u[idx] == k:
            forced[a].add(c)
        elif u[idx] == -k:
            forced[c].add(a)
    for L1 in _linear_extensions(n, forced):
        m1 = ballot_margin(L1, pairs)
        need = tuple(x - y for x, y in zip(u, m1))
        rest = realise(need, k - 1, n, pairs)
        if rest is not None:
            return [L1] + rest
    return None


def find_move(profile, n, pairs, max_s=6, max_weight=6):
    """
    An improving Graver move of weight |S|+|T| <= max_weight, returned as
    (indices_to_remove, ballots_to_add), or None.  Prefers the largest reduction.
    """
    P = len(profile)
    for s in range(2, min(max_s, P) + 1):
        for idx in itertools.combinations(range(P), s):
            S = [profile[i] for i in idx]
            u = margin(S, n, pairs)
            for t in range(0, min(3, s - 2) + 1):
                if s + t > max_weight:
                    continue
                T = realise(u, t, n, pairs)
                if T is not None:
                    return idx, T
    return None


def descend(profile, n, verbose=False, max_weight=6):
    """Greedy Graver augmentation.  Returns the reduced profile."""
    pairs = make_pairs(n)
    target = margin(profile, n, pairs)
    profile = list(profile)
    for max_s in (4, 5, 6, 7, 8):
        if max_s > max_weight:
            break
        while True:
            mv = find_move(profile, n, pairs, max_s=max_s, max_weight=max_weight)
            if mv is None:
                break
            idx, T = mv
            keep = [L for i, L in enumerate(profile) if i not in set(idx)]
            profile = keep + T
            if verbose:
                print(f"    move |S|={len(idx)} -> |T|={len(T)};  ballots now {len(profile)}")
    assert margin(profile, n, pairs) == target, "descent changed the margins"
    return profile


# ----------------------------------------------------------------------
# 4. exact ILP
# ----------------------------------------------------------------------

def exact_ilp(b, n, k, mode="exact", time_limit=60.0):
    """
    Is there a profile of exactly k ballots with margins b (mode='exact') or with
    the same signs as b (mode='tournament')?  Returns the profile or None.

    One block of C(n,2) binaries per ballot slot, with the 3-dicycle inequalities
    cutting out the linear orders.  Polynomial in n for fixed k.
    """
    from scipy.optimize import milp, LinearConstraint, Bounds

    pairs = make_pairs(n)
    m = len(pairs)
    pidx = {p: i for i, p in enumerate(pairs)}
    nv = k * m

    def var(t, a, c):
        return t * m + pidx[(a, c)]

    rows, lo, hi = [], [], []

    for t in range(k):
        for a, c, d in itertools.combinations(range(1, n + 1), 3):
            row = np.zeros(nv)
            row[var(t, a, c)] = 1.0
            row[var(t, c, d)] = 1.0
            row[var(t, a, d)] = -1.0
            rows.append(row)
            lo.append(0.0)
            hi.append(1.0)

    for j, p in enumerate(pairs):
        row = np.zeros(nv)
        for t in range(k):
            row[var(t, *p)] = 1.0
        if mode == "exact":
            if (b[j] + k) % 2:
                return None
            rows.append(row)
            lo.append((b[j] + k) / 2)
            hi.append((b[j] + k) / 2)
        else:
            rows.append(row)
            if b[j] > 0:
                lo.append((k + 1) / 2)
                hi.append(float(k))
            else:
                lo.append(0.0)
                hi.append((k - 1) / 2)

    A = np.array(rows)
    res = milp(c=np.zeros(nv),
               constraints=LinearConstraint(A, np.array(lo), np.array(hi)),
               integrality=np.ones(nv),
               bounds=Bounds(0, 1),
               options={"time_limit": time_limit})
    if not res.success or res.x is None:
        return None

    z = np.round(res.x).astype(int)
    profile = []
    for t in range(k):
        wins = {a: 0 for a in range(1, n + 1)}
        for a, c in pairs:
            if z[var(t, a, c)]:
                wins[a] += 1
            else:
                wins[c] += 1
        profile.append(tuple(sorted(range(1, n + 1), key=lambda a: -wins[a])))
    return profile


def minimum_ballots(b, n, mode="exact", kmax=9, time_limit=60.0):
    """Smallest k for which exact_ilp succeeds, with the witnessing profile."""
    for k in range(1, kmax + 1):
        if mode == "exact" and (b[0] + k) % 2:
            continue
        p = exact_ilp(b, n, k, mode=mode, time_limit=time_limit)
        if p is not None:
            return k, p
    return None, None


# ----------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------

def solve(b, n, use_ilp=True, verbose=True):
    pairs = make_pairs(n)
    if verbose and False:

        print(f"n = {n},  target margins = {b}")
        bd = bounds(b, n)
        print(f"  Copeland scores        {bd['copeland']}")
        print(f"  max |margin|           {bd['max_margin']}")
        print(f"  pseudoinverse l2 bound {bd['pseudoinverse_l2']:.4f}")
        if "lp_l1" in bd:
            print(f"  LP l1 relaxation       {bd['lp_l1']:.4f}")

    start = mcgarvey(b, n)
    #start = fromfile("fas_anneal/paley_0007_7.txt")

    if verbose:
        print(f"  McGarvey warm start    {len(start)} ballots")
    red = descend(start, n, verbose=verbose)
    if verbose:
        print(f"  after Graver descent   {len(red)} ballots")

    if use_ilp:
        k, prof = minimum_ballots(b, n)
        if k is not None:
            if verbose:
                print(f"  ILP optimum            {k} ballots")
            assert margin(prof, n, pairs) == tuple(b)
            return prof
    return red


if __name__ == "__main__":
    import random

    random.seed(7)
    for n in (19,):
        s = 1
        qrs = { i**2 % n for i in range(1, n - 1) }
        pairs = make_pairs(n)
        b = tuple(s if ((b - a) % n) in qrs else -s for a, b in pairs)
        #b = (1, -1, -1, -1, 1, 5, -3, -7, -3, -3, -1, -3, -5, -1, 3, -1, -1, 3, 1, 3, 7)
        print("=" * 66)
        print(b)
        prof = solve(b, n, use_ilp=False)
        print("  profile:", [".".join(map(str, L)) for L in prof])
        print("  check   :", margin(prof, n) == b)
