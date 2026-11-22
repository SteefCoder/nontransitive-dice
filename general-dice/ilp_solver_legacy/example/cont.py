from solvers.continuous import ContinuousDiceSolver


def main():
    solver = ContinuousDiceSolver(dice=5, distinct=4)
    print(solver._dependencies)
    solver.add_objective("max_min_ratio")
    solver.add_constraint("balanced")
    solver.model.Params.NoRelHeurTime = 100
    with solver.build():
        dice = solver.solve()
        print(dice)
        print(solver._r.X)
    

if __name__ == '__main__':
    main()
