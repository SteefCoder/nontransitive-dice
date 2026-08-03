import sys

import numpy as np


def qrs(p: int) -> list[int]:
    """Returns all quadratic residues of a prime `p`"""
    residues = np.unique(np.arange(1, p)**2 % p)
    residues.sort()
    return residues.tolist()


def paley_tournament(p: int):
    """Creates the `p`'th Paley tournament using the quadratic residues of `p`."""
    #assert p % 4 == 3 and is_prime(p)
    QR = qrs(p)
    t = np.subtract.outer(range(p), range(p)) % p
    return np.isin(t, QR).astype(np.bool)


def verify(dice: np.ndarray, tournament: np.ndarray) -> bool:
    """
    Checks whether a set of dice actually realizes a tournament,
    given that the dice adhere to a block structure.
    """
    r = zip(dice, tournament)

    for die, t in r:
        wins = die > dice[t]
        sums = np.sum(wins, axis=1)
        if not np.all(sums > dice.shape[1]/2):
            return False
    return True


def main():
    file = sys.argv[1]
    dice = np.loadtxt(file, dtype=np.int32)
    if dice.shape[0] < dice.shape[1]:
        dice = dice.T
    tournament = paley_tournament(dice.shape[0])
    print("Verified:", verify(dice, tournament) or verify(dice, tournament.T))


main()