from .helpers import qr_tournament

from tqdm import tqdm


def strongly_beats(D1, D2):
    w = sum(1 for a in D1 for b in D2 if a > b)

    return 2*w > len(D1) * len(D2)

def strongly_verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i != j and strongly_beats(dice[i], dice[j]) != bool(tournament[i][j]):
                return False
    return True

def construct_tournament(tour):
    n = len(tour)
    K = n // 2
    Y = [
        [((i - (j + 1)) % n, (i + (j + 1)) % n) for j in range(K)]
        for i in range(n)
    ]

    dice = [
        [0 for _ in range(n)]
        for _ in range(n)
    ]
    for k in tqdm(range(n)):
        for i in range(n):
            if i == k:
                dice[i][i] = n*i + 1
                continue

            for j in range(K):
                if k in Y[i][j]:
                    a = n*i + 2*(j + 1)
                    b = n*i + 2*(j + 1) + 1
                    y0, y1 = Y[i][j]
                    if tour[y0][y1]:
                        dice[y0][i] = b
                        dice[y1][i] = a
                    else:
                        dice[y0][i] = a
                        dice[y1][i] = b
                    break

    return dice


def main():
    p = 1163
    tournament = qr_tournament(p)
    dice = construct_tournament(tournament)
    with open(f"n-player/results/p_{p}_f_{p}_angel.txt", "w") as f:
        for die in dice:
            f.write(" ".join(map(str, die)) + "\n")

    print("Verified:", strongly_verify(dice, tournament))


main()
