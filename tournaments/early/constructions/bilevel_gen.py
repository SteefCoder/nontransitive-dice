import sys
import numpy as np
from bilevel_balanced import decompose, bits
from diceset import DiceSet



def qrs(p: int) -> list[int]:
    """Returns all quadratic residues of a prime `p`"""
    residues = np.unique(np.arange(1, p)**2 % p)
    residues.sort()
    return residues.tolist()


def paley_tournament(p: int) -> list[list[int]]:
    """Creates the `p`'th Paley tournament using the quadratic residues of `p`."""
    #assert p % 4 == 3 and is_prime(p)
    QR = qrs(p)
    t = np.subtract.outer(range(p), range(p)) % p
    return np.isin(t, QR).astype(np.int16).T.tolist()


def verify(dice: DiceSet, tournament: list[list[int]], show_progress: bool = False) -> bool:
    """
    Checks whether a set of dice actually realizes a tournament,
    given that the dice adhere to a block structure. For larger sets,
    this function should be implemented in C for a speedup (or in numpy).
    """
    dice_arr = np.array(dice.dice, dtype=np.int32)
    tournament_arr = np.array(tournament, dtype=np.bool)

    r = zip(dice_arr, tournament_arr)

    for die, t in r:
        wins = die > dice_arr[t]
        sums = np.sum(wins, axis=1)
        if not np.all(sums > dice.face_counts[0]/2):
            return False
    return True

def choose_subtournament(tournament: list[list[int]], vertices: list[int]) -> list[list[int]]:
    new_tournament = []
    for v in vertices:
        new_tournament.append([tournament[v][w] for w in vertices])
    return new_tournament


def main():
    p = int(sys.argv[1])
    t = paley_tournament(p)

    # t = choose_subtournament(t, list(range(11, p)))
    #t = choose_subtournament(t, [0] + qrs(p))

    p = len(t)

    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    outdir = sys.argv[3] if len(sys.argv) > 3 else "."
    layers, total, covered = decompose(t, seeds, 10 * p)
    rows = []
    for blocks in layers:
        r1 = []; r2 = []
        for (A, B) in blocks:
            r1 += sorted(bits(A)) + sorted(bits(B))
        for (A, B) in reversed(blocks):
            r2 += sorted(bits(A), reverse=True) + sorted(bits(B), reverse=True)
        rows.append(r1); rows.append(r2)
    rows = rows[:-1]                                  # drop one voter -> odd (margins stay in {1,3})
    m = len(rows)
    dice = [[] for _ in range(p)]
    for r, row in enumerate(rows):
        for idx, v in enumerate(row):
            dice[v].append(r * p + (p - idx))          # banded: earlier position -> higher value
    dice = [sorted(d) for d in dice]

    dice = DiceSet(dice)
    print("Dice", dice.n)
    print("Faces", dice.face_counts[0])
    print("Ratio (higher=better)", dice.n / np.log(dice.n) / dice.face_counts[0])
    print("Verified", verify(dice, t))

main()