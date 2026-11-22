from solvers.three_player import ThreePlayerSolver
import networkx as nx
import matplotlib.pyplot as plt


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

    plt.show()


def main():
    solver = ThreePlayerSolver(faces=12, dice=7)
    solver.add_objective("max_full")
    solver.add_constraint("full_three_player")
    # solver.model.Params.NoRelHeurTime = 300
    solver.model.Params.TuneTimeLimit = 100
    solver.model.Params.TimeLimit = 20
    solver.model.Params.TuneOutput = 3

    with solver.build():
        solver.model.tune()
        #dice = solver.solve()
        solver.model.write("best-params.prm")


if __name__ == '__main__':
    main()