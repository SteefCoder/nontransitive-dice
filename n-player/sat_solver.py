import sys
import time

from pysat.solvers import Cadical300
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from tqdm import tqdm

from .helpers import get_subtournament, paley_tournament, verify, qrs, choose_subtournament
from diceset import DiceSet


def build_model(tournament: list[list[int]], faces: int):
    n = len(tournament)
    solver = Cadical300()
    pool = IDPool()

    def wins(X: int, Y: int, i: int) -> int:
        return pool.id((X, Y, i)) if X < Y else -pool.id((Y, X, i))
    
    for X in tqdm(range(n)):
        for Y in range(n):
            if X == Y:
                continue

            # transitivity constraints
            for Z in range(n):
                if Z in (X, Y):
                    continue

                for i in range(faces):
                    # for every face i, X > Y and Y > Z implies X > Z
                    clause = [-wins(X, Y, i), -wins(Y, Z, i), wins(X, Z, i)]
                    solver.add_clause(clause)
    
            lits = [wins(X, Y, i) for i in range(faces)]
    
            # tournament constraints
            if tournament[X][Y]:
                card_cnf = CardEnc.atleast(lits, faces//2 + 1, encoding=EncType.totalizer, vpool=pool)
                solver.append_formula(card_cnf.clauses)

    return solver, wins


def solve(tournament: list[list[int]], faces: int) -> DiceSet | None:
    n = len(tournament)

    solver, wins = build_model(tournament, faces)

    print("Starting solve!")
    sat = solver.solve()
    if not sat:
        return None

    vars: set[int] = set(solver.get_model())  # type: ignore

    blocks = []
    for X in range(n):
        die = []
        for i in range(faces):
            v = sum(wins(X, Y, i) in vars for Y in range(n))
            die.append(v)
        blocks.append(die)
    
    return DiceSet.from_blocks(blocks)


def main():
    p = int(sys.argv[1])
    
    tournament = paley_tournament(p)

    vertices = [0] + qrs(p)
    tournament = choose_subtournament(tournament, vertices)

    if len(sys.argv) > 3:
        subsize = int(sys.argv[2])
        faces = int(sys.argv[3])
        tournament = get_subtournament(tournament, subsize)
        print(f"Solving for P_{p} subtournament with {subsize=} and {faces=}.")
    else:
        faces = int(sys.argv[2])
        subsize = p
        print(f"Solving for P_{p} tournament with {faces=}.")

    start = time.time()
    solution = solve(tournament, faces)
    end = time.time()
    if solution is None:
        print(f"No solution found ({end - start:.02f}s)")
        return
    
    if subsize == p:
        filename = f"n-player/results/p_{p}_f_{faces}_sat.txt"
    else:
        filename = f"n-player/results/p_{p}_sub_{subsize}_f_{faces}_sat.txt"

    #solution.to_file(filename)

    print(f"Solution found in {end - start:.02f}s.")
    print("Verified:", verify(solution, tournament))


if __name__ == '__main__':
    main()
