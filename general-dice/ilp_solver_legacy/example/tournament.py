from solvers.tournament import TournamentSolver
from diceset import DiceSet

import networkx as nx
import matplotlib.pyplot as plt
import random
import time


def solve_heuristic(tournament: list[list[int]], faces: int, seed: int):
    rng = random.Random(seed)
    n = len(tournament)
    threshold = faces**2 // 2 + 1

    wins = [[0] * n for _ in range(n)]
    blocks = []
    for _ in range(faces):
        deficit = [0] * n
        for X in range(n):
            for Y in range(n):
                if not tournament[X][Y]:
                    continue

                d = threshold - wins[X][Y]
                if d > 0:
                    deficit[X] += d

        key_ordering = [(deficit[X] + rng.random() * 0.1, X) for X in range(n)]
        key_ordering.sort()
        block = [0] * n
        for rank, (_, X) in enumerate(key_ordering):
            block[X] = rank
        blocks.append(block)

        for X in range(n):
            for Y in range(n):
                if block[X] > block[Y]:
                    wins[X][Y] += 1
    
    return [[blocks[b][X] + n*b for b in range(faces)] for X in range(n)]


def calculate_objective(dice: DiceSet, tournament: list[list[int]]) -> int:
    faces = dice.face_counts[0]
    n = len(tournament)
    t = [[round(v*faces**2) for v in x] for x in dice.tournament()]
    return sum(
        max(faces**2 // 2 + 1 - t[i][j], 0)
        for i in range(n)
        for j in range(n)
        if tournament[i][j]
    )

def print_tournament(tournament: list[list[float]]):
    for t in tournament:
        for v in t:
            if v > 0.5:
                print("1 ", end="")
            else:
                print("0 ", end="")
        print("")
    print("")

    G = nx.DiGraph()
    edges = [
        (i, j, round(v2, 3))
        for i, l in enumerate(tournament)
        for j, v2 in enumerate(l)
        if v2 > 0.5
    ]
    G.add_weighted_edges_from(edges)
    layout = nx.circular_layout(G)
    nx.draw(G, layout, with_labels=True)

    edge_labels = nx.get_edge_attributes(G, "weight")

    nx.draw_networkx_edge_labels(G, layout, edge_labels=edge_labels)

    plt.show()


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


def main():
    faces = 30
    tournament = create_quadratic_residue_tournament(67)
    solver = TournamentSolver(faces=faces, tournament=tournament)
    #solver.add_objective("max_min_ratio")
    solver.add_objective("min_slack")
    # solver.add_constraint("constraint_tournament_strong")
    # solver.add_constraint("equal_mean")

    solver.model.Params.MIPFocus = 1
    solver.model.Params.NoRelHeurTime = 1000
    #solver.model.Params.TuneCriterion = 1
    with solver.build():
        print("solver built")
        dice = [solve_heuristic(tournament, faces, hash((i + 1) * time.time())) for i in range(100)]
        
        pairs = [(DiceSet(x), calculate_objective(DiceSet(x), tournament)) for x in dice]
        pairs.sort(key=lambda x: x[1])
        dice = list(reversed([x[0] for x in pairs][:5]))
        solver.set_start(*dice)
        print("initial dice created")
        # start_dice = [[1, 22, 44, 79, 94], [5, 16, 53, 74, 92], [11, 30, 51, 68, 80], [21, 26, 50, 60, 83], [20, 31, 42, 59, 88], [13, 37, 39, 67, 84], [6, 10, 63, 72, 89], [35, 38, 40, 49, 78], [15, 24, 48, 66, 87], [7, 19, 58, 65, 91], [4, 25, 57, 73, 81], [9, 28, 55, 71, 77], [8, 33, 47, 70, 82], [18, 29, 46, 62, 85], [12, 34, 43, 56, 95], [23, 36, 41, 54, 86], [17, 32, 52, 64, 75], [3, 14, 61, 69, 93], [2, 27, 45, 76, 90]]
        # start_dice = [[v - 1 for v in x] for x in start_dice]
        # t = [[int(v > 0.5) for v in x] for x in DiceSet(start_dice).tournament()]
        # solver.set_start(DiceSet(start_dice))
        # solver.model.Params.PoolSearchMode = 2
        # solver.model.Params.PoolSolutions = 2
        dice = solver.solve()
        # print("Preverified", t == tournament)
        # print("Equal?", dice == start_dice)
        if not dice:
            print("No dice found...")
            return
        #print(dice.count_win_ratios())
        t = [[int(v > 0.5) for v in x] for x in dice.tournament()]
        #print(t)
        print(dice)
        print("Verfied: ", t == tournament)


if __name__ == '__main__':
    main()