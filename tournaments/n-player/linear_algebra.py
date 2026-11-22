#!/usr/bin/env python3
"""
Proof of concept: invert the margin map phi to realize a given tournament.

Technique (exactly as derived):
  phi : Q[S_n] -> Lambda^2 Q^n sends a profile to its pairwise majority margins.
  It is surjective, so x = A^T (A A^T)^{-1} b is the minimum-l2-norm preimage.
  Schur's Lemma diagonalizes A A^T on the two isotypic pieces of Lambda^2 Q^n
  (Borda / S^{(n-1,1)}, eigenvalue n!(n+1)/3; Condorcet / S^{(n-2,1,1)},
  eigenvalue n!/3), collapsing the pseudoinverse to the closed form

      x_L = (3/n!) [ <m_L, M> - <r, beta^L> / (n+1) ]

  where M is the target antisymmetric +-1 margin matrix, r_a = sum_b M_ab is the
  Copeland score of a, and beta^L_a = n+1-2*pos_L(a) is the Borda score ballot L
  awards a. No matrix is ever built and nothing is ever inverted.

Weights are exact rationals and may be negative; in the reversal quotient a
negative weight on L is a positive weight on the reversed ballot, so the report
converts everything to nonnegative weights at the end.
"""

import argparse
import math
import sys
from fractions import Fraction
from itertools import combinations, permutations


def parse_tournament(text):
    """Parse 'a>b,b>c,c>a' into (n, beats) with beats a set of ordered pairs."""
    beats, labels = set(), set()
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if ">" not in token:
            raise ValueError(f"cannot parse edge {token!r}; expected the form 'a>b'")
        winner, loser = (int(part) for part in token.split(">", 1))
        labels.update((winner, loser))
        if (loser, winner) in beats:
            raise ValueError(f"contradictory edges for pair {{{winner},{loser}}}")
        beats.add((winner, loser))
    n = max(labels)
    if labels != set(range(1, n + 1)):
        raise ValueError(f"vertices must be exactly 1..{n}, got {sorted(labels)}")
    missing = [(a, b) for a, b in combinations(range(1, n + 1), 2)
               if (a, b) not in beats and (b, a) not in beats]
    if missing:
        raise ValueError(f"tournament is incomplete; no edge for pairs {missing}")
    return n, beats


def margin_matrix(n, beats):
    """Target margin vector: +-1 on each pair, the smallest realizable choice."""
    return {(a, b): (1 if (a, b) in beats else -1)
            for a, b in combinations(range(1, n + 1), 2)}


def copeland_scores(n, M):
    """r_a = sum_b M_ab, using antisymmetry M_ba = -M_ab."""
    return {a: sum(M[(a, b)] if a < b else -M[(b, a)]
                   for b in range(1, n + 1) if b != a)
            for a in range(1, n + 1)}


def min_norm_profile(n, M):
    """Closed-form minimum-l2-norm preimage; yields (ballot, weight), weight != 0."""
    pairs = list(combinations(range(1, n + 1), 2))
    r = copeland_scores(n, M)
    scale = Fraction(3, math.factorial(n))
    for ballot in permutations(range(1, n + 1)):
        pos = {v: i for i, v in enumerate(ballot)}
        agreement = sum(M[(a, b)] * (1 if pos[a] < pos[b] else -1) for a, b in pairs)
        borda_corr = sum(r[a] * (n + 1 - 2 * (pos[a] + 1)) for a in range(1, n + 1))
        weight = scale * (agreement - Fraction(borda_corr, n + 1))
        if weight:
            yield ballot, weight


def realized_margins(n, profile):
    """Apply phi to a profile, so we can check the answer."""
    out = {}
    for a, b in combinations(range(1, n + 1), 2):
        total = Fraction(0)
        for ballot, weight in profile:
            pos = {v: i for i, v in enumerate(ballot)}
            total += weight if pos[a] < pos[b] else -weight
        out[(a, b)] = total
    return out


def to_nonnegative(profile):
    """A negatively weighted ballot is a positively weighted reversed ballot."""
    merged = {}
    for ballot, w in profile:
        key = ballot if w > 0 else tuple(reversed(ballot))
        merged[key] = merged.get(key, Fraction(0)) + abs(w)
    return [(ballot, w) for ballot, w in merged.items() if w]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tournament", nargs="?", default="1>2,2>3,3>1",
                    help="edges as 'a>b,b>c,...' over vertices 1..n (default: the 3-cycle)")
    ap.add_argument("--top", type=int, default=12, help="how many ballots to print")
    args = ap.parse_args(argv)

    n, beats = parse_tournament(args.tournament)
    if n > 8:
        print(f"refusing n={n}: the min-norm profile is dense, up to {n}! ballots.",
              file=sys.stderr)
        return 1
    M = margin_matrix(n, beats)
    profile = to_nonnegative(list(min_norm_profile(n, M)))

    assert realized_margins(n, profile) == {p: Fraction(v) for p, v in M.items()}, \
        "phi(x) != target"

    l1 = sum(w for _, w in profile)
    l2sq = sum(w * w for _, w in profile)
    r = copeland_scores(n, M)
    predicted = Fraction(3, math.factorial(n)) * (
        len(M) - Fraction(sum(v * v for v in r.values()), n + 1))

    print(f"n = {n},  tournament = {args.tournament}")
    print(f"Copeland scores r = {[r[a] for a in range(1, n + 1)]}")
    print(f"support = {len(profile)} of {math.factorial(n)} ballots")
    print(f"total voter weight |x|_1 = {l1} = {float(l1):.4f}")
    print(f"|x|_2^2 = {l2sq}   (closed form predicts {predicted})")
    print(f"\nprofile (largest {args.top} weights, ballots read best-to-worst):")
    for ballot, w in sorted(profile, key=lambda bw: (-bw[1], bw[0]))[:args.top]:
        print(f"   {str(w):>10}  x  {' > '.join(map(str, ballot))}")
    if len(profile) > args.top:
        print(f"   ... and {len(profile) - args.top} more")
    print("\nverified: phi(profile) equals the target margin vector exactly")
    return 0

print("EJJ")
if __name__ == "__main__":
    main()
