from solvers.max_two import MaxNDiceSolver


def get_r(dice: int, faces: int, distinct: int) -> float:
    solver = MaxNDiceSolver(dice, distinct, faces)
    solver.add_objective("max_min_ratio")
    solver.add_objective("min_faces")
    solver.add_constraint("balanced")
    #solver.model.Params.OutputFlag = 0
    with solver.build():
        solver.model.addConstr(solver._x[0, 0] == 0)
        diceset = solver.solve()
        print(diceset)
        print(diceset.count_win_ratios())
        return solver._r.X


def main():
    dice = 5
    faces = 20
    distinct = 3

    r = get_r(dice, faces, distinct)
    print(faces, r)
if __name__ == '__main__':
    main()
