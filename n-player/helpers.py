import math

from tqdm import tqdm
import numpy as np

from diceset import DiceSet


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    
    for i in range(2, math.isqrt(n) + 1):
        if n % i == 0:
            return False
    
    return True


def qrs(p: int) -> list[int]:
    """Returns all quadratic residues of a prime `p`"""
    assert is_prime(p)
    return sorted({ i**2 % p for i in range(1, p) })


def paley_tournament(p: int) -> list[list[int]]:
    """Creates the `p`'th Paley tournament using the quadratic residues of `p`."""
    assert p % 4 == 3 and is_prime(p)
    QR = qrs(p)
    return [[int((j - i) % p in QR) for j in range(p)] for i in range(p)]


def beats(d1: list[int], d2: list[int]) -> bool:
    """Checks whether die `d1` strictly beats `d2`,
    assuming a block structure on `d1` and `d2`.
    """
    w = sum(a > b for a, b in zip(d1, d2))
    return 2*w > len(d1)


def verify(dice: DiceSet, tournament: list[list[int]], show_progress: bool = False) -> bool:
    """
    Checks whether a set of dice actually realizes a tournament,
    given that the dice adhere to a block structure. For larger sets,
    this function should be implemented in C for a speedup (or in numpy).
    """
    dice_arr = np.array(dice.dice, dtype=np.int32)
    tournament_arr = np.array(tournament, dtype=np.bool)

    r = zip(dice_arr, tournament_arr)
    if show_progress:
        r = tqdm(r, total=len(dice_arr))

    for die, t in r:
        wins = die > dice_arr[t]
        sums = np.sum(wins, axis=1)
        if not np.all(sums > dice.faces/2):
            return False
    return True


def get_subtournament(tournament: list[list[int]], subsize: int) -> list[list[int]]:
    return [t[:subsize] for t in tournament[:subsize]]


def choose_subtournament(tournament: list[list[int]], vertices: list[int]) -> list[list[int]]:
    new_tournament = []
    for v in vertices:
        new_tournament.append([tournament[v][w] for w in vertices])
    return new_tournament
