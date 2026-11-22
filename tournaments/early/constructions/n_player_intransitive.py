import itertools
import math


def li_dice(n):
    assert not (n+1)%4
    w = tuple(sorted([((i+1)**2)%n for i in range(n//2)]))
    return list(zip(*sorted([[(i+j*k)%n+i*n*len(w)+w.index(j)*n for k in range(n)] for i in range(n) for j in w])))


def list_primes(n: int):
    primes = [2]
    i = 3
    while i < n:
        for p in primes:
            if i % p == 0:
                break
        else:
            primes.append(i)
        i += 2
    return primes



def get_tournament(dice: list[list[int]]):
    tour = []
    for d1 in dice:
        r = []
        for d2 in dice:
            wins = 0
            for v1 in d1:
                for v2 in d2:
                    if v1 > v2:
                        wins += 1
            if 2 * wins > len(d1) * len(d2):
                r.append(1)
            else:
                r.append(0)
        tour.append(r)
    #print_tournament(tour)
    return tour


def create_quadratic_residue_tournament(p: int):
    a = set()
    for i in range(1, p):
        a.add(i ** 2 % p)
    b = [1 if j in a else 0 for j in range(p)]
    tournament = []
    for i in range(p):
        tournament.append(b)
        b = [b[-1]] + b[:-1]
    return tournament


def print_tournament(tournament: list[list[int]]):
    for t in tournament:
        print(str(t) + ",")
    print("")
 

def check_tournament(tournament: list[list[int]], n: int):
    N = len(tournament)
    pred = [0] * N

    for i in range(N):
        mask = 0
        for j in range(N):
            if tournament[j][i]:
                mask |= 1 << j
        pred[i] = mask

    for v in itertools.combinations(range(N), n):
        mask = pred[v[0]]
        for vi in v[1:]:
            mask &= pred[vi]

        if mask == 0:
            return False
        
    for i in range(len(tournament)):
        if tournament[i][i] != 0:
            return False
        for j in range(i):
            if tournament[i][j] + tournament[j][i] != 1:
                return False
    return True


def create_dice(tournament: list[list[int]]):
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
                    if tournament[Y[i][j][0]][Y[i][j][1]]:
                        dice[Y[i][j][0]][i] = b
                        dice[Y[i][j][1]][i] = a
                    else:
                        dice[Y[i][j][0]][i] = a
                        dice[Y[i][j][1]][i] = b
                    break
    return dice


def create_n_player_dice(p: int, n: int):
    tournament = create_quadratic_residue_tournament(p)
    if not check_tournament(tournament, n):
        print(f"Tournament check failed for {n=} and {p=}")
        return None
    
    return create_dice(tournament)


def find_n_player_dice(n: int):
    p = [1, 3, 7, 19, 67, 331, 1163][n]
    tournament = create_quadratic_residue_tournament(p)
    return create_dice(tournament)


def main():
    n = 2
    p = [1, 3, 7, 19, 67, 331, 1163][n]
    dice = find_n_player_dice(n)
    print_tournament(dice)
    print_tournament(get_tournament(dice))
    print(check_tournament(get_tournament(dice), n))
    #li = li_dice([1, 3, 7, 19, 67, 331, 1163][n])
    #print_tournament(li)
    #print(check_tournament(get_tournament(li), n))

#main()
dice = [
    [3, 10, 17],
    [2, 8, 20],
    [1, 13, 16],
    [0, 11, 19],
    [6, 9, 15],
    [5, 7, 18],
    [4, 12, 14],
]
print_tournament(get_tournament(dice))
print(check_tournament(get_tournament(dice), 2))