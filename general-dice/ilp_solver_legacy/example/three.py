from solvers.three_player import ThreePlayerSolver
import networkx as nx
import matplotlib.pyplot as plt
import itertools

def print_tournament(tournament: list[list[float]]):
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

    print([[int(v > 0.5) for v in t] for t in tournament])

    plt.show()

def check_tournament(tournament: list[list[int]], n: int):
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
    #             print(f"t[{i},{j}] + t[{j},{i}] != 1")
    #             return False
    return True



def main():
    solver = ThreePlayerSolver(dice=67, faces=27)
    # solver.add_objective("max_full")
    solver.add_constraint("full_three_player")
    # solver.add_constraint("equal_mean")

    solver.model.Params.MIPFocus = 1
    solver.model.Params.NoRelHeurTime = 100

    with solver.build():
        dice = solver.solve()
        print(dice)
        print(dice.count_win_ratios())
        t = dice.tournament()
        print_tournament(t)
        print(check_tournament(t, 2))


if __name__ == '__main__':
    main()