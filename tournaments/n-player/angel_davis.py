from helpers import paley_tournament, verify

from diceset import DiceSet


def construct_tournament(tournament: list[list[int]]) -> DiceSet:
    """
    Constructs a set of dice realizing `tournament`
    using the method by Angel and Davis.
    It will have `n` faces per die.
    Returns the dice in block form.
    """
    n = len(tournament)
    K = n // 2
    Y = [
        [((i - (j + 1)) % n, (i + (j + 1)) % n) for j in range(K)]
        for i in range(n)
    ]
    dice = [
        [0 for _ in range(n)]
        for _ in range(n)
    ]
    for k in range(n):
        for i in range(n):
            if i == k:
                dice[i][i] = n*i + 1
                continue

            for j in range(K):
                if k in Y[i][j]:
                    a = n*i + 2*(j + 1)
                    b = n*i + 2*(j + 1) + 1
                    y0, y1 = Y[i][j]
                    if tournament[y0][y1]:
                        dice[y0][i] = b
                        dice[y1][i] = a
                    else:
                        dice[y0][i] = a
                        dice[y1][i] = b
                    break

    return DiceSet.from_blocks(dice)


def main():
    p = 19
    tournament = paley_tournament(p)
    dice = construct_tournament(tournament)
    dice.to_file(f"n-player/results/p_{p}_f_{p}_angel.txt")
    print("Verified:", verify(dice, tournament))


if __name__ == '__main__':
    main()
