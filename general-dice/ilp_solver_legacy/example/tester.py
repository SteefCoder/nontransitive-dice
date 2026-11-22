from solvers.general import GeneralDiceSolver
from fractions import Fraction

def get_r(dice: int, faces: int) -> float:
    solver = GeneralDiceSolver(faces, dice)
    solver.add_objective("max_min_ratio")
    solver.add_constraint("balanced")
    solver.model.Params.OutputFlag = 0
    with solver.build():
        diceset = solver.solve()

        return solver._r.X


def upper_r(dice: int) -> float:
    solver = GeneralDiceSolver(20, dice)
    solver.add_objective("max_min_ratio")
    solver.model.Params.OutputFlag = 0
    with solver.build():
        diceset = solver.solve()

        return solver._r.X


def main():
    dice = 5
    max_faces = 25
    eps = 1e-5

    upper = upper_r(dice)
    print("Best possible r:", upper)
    

    best_faces = 0
    best_r = 0
    for faces in range(3, max_faces):
        r = get_r(dice, faces)
        if r > best_r:
            best_faces = faces
            best_r = r

        print(faces, r, Fraction.from_float(r).limit_denominator())
        
        #if r + eps >= upper:
        #    break
    

    print(best_faces, best_r, Fraction.from_float(best_r).limit_denominator())
  

if __name__ == '__main__':
    main()
