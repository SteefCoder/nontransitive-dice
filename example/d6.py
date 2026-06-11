from solvers.general import GeneralDiceSolver


def main():
    solver = GeneralDiceSolver(faces=6, dice=4)
    solver.add_objective("max_min_ratio")
    solver.add_constraint("max_repeat", 1)
    with solver.build():
        dice = solver.solve()
        print(dice)
        print(dice.count_win_ratios())

if __name__ == '__main__':
    main()
