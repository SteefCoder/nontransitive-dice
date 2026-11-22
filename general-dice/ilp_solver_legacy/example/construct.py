from solvers.tournament import NPlayerTournamentCreator
from diceset import DiceSet
import itertools


def is_square(n):
    x = n // 2
    seen = set([x])
    while x * x != n:
        x = (x + (n // x)) // 2
        if x in seen: return False
        seen.add(x)
    return True

def quadratic_residue_tournament(p: int):
    a = set()
    for i in range(1, p):
        a.add(i ** 2 % p)
    b = [1 if j in a else 0 for j in range(p)]
    tournament = []
    for i in range(p):
        tournament.append(b)
        b = [b[-1]] + b[:-1]
    return tournament


def print_tournament(tournament: list[list[float]]):
    for t in tournament:
        print("[ ", end="")
        for v in t:
            if v > 0.5:
                print("1, ", end="")
            else:
                print("0, ", end="")
        print("],")
    print("")

def check_tournament(tournament: list[list[int | float]], n: int):
    N = len(tournament)
    for v in itertools.combinations(range(N), n):
        for k in range(N):
            if all(tournament[k][x] > 0.5 for x in v):
                break
        else:
            print(f"No result for {v=}")
            return False
        
    # for i in range(len(tournament)):
    #     for j in range(i):
    #         if tournament[i][j] + tournament[j][i] != 1:
    #             return False
    return True

def main():
    n = 4
    for d in range(67, 68):
        creator = NPlayerTournamentCreator(d, n)
        #creator.add_constraint("n_player", (n - 1) // 2)
        creator.add_constraint("main")
        #creator.model.Params.OutputFlag = 0
        with creator.build():
            print(f"Built {d=}")
            tour = creator.solve()
            if tour:
                print_tournament(tour)
                if not check_tournament(tour, n):
                    print(f"Check for {d=} failed")
                else:
                    #print_tournament(tour)
                    print(f"Check for {d=} succeeded")
                    return
            else:
                print(f"No tournament found for {d=}")

#main()

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
    for k in range(n):
        for i in range(n):
            if i == k:
                dice[i][i] = n*i + 1
                continue

            for j in range(K):
                if k in Y[i][j]:
                    a = n*i + 2*(j + 1)
                    b = n*i + 2*(j + 1) + 1
                    if tour[Y[i][j][0]][Y[i][j][1]]:
                        dice[Y[i][j][0]][i] = b
                        dice[Y[i][j][1]][i] = a
                    else:
                        dice[Y[i][j][0]][i] = a
                        dice[Y[i][j][1]][i] = b
                    break
    
            else:
                print(i, j, k, Y[i])
                raise Exception("What the helly")
    return dice

def test():
    tour = quadratic_residue_tournament(19)
    #tour = [[0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0], [0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1], [1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1], [1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0], [0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0], [0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0], [0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0], [0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1], [1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0], [0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1], [1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0], [0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1], [1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1], [1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1], [1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0], [0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0], [0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1], [1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0]]
    print(len(tour), [len(x) for x in tour])
    dice = construct_tournament(tour)
 
    t = DiceSet(dice).tournament()
    t2 = [[1 if x > 0.5 else 0 for x in v] for v in t]
    assert t2 == tour

    print_tournament(t)
    print(check_tournament(t, 3))
    print(check_tournament(tour, 3))
    
    print(dice)

#tour = [[0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0], [0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1], [1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1], [1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0], [0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0], [0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0], [0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0], [0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1], [1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0], [0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1], [1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0], [0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1], [1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1], [1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1], [1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0], [0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0], [0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1], [1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0]]
tour = quadratic_residue_tournament(19)

tour = [[0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0], [0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1], [1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0], [0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0], [0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1], [1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0], [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0], [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1], [1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0]]
print_tournament(tour)
print(check_tournament(tour, 2))
#test()
#main()