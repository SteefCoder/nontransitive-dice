import sys
import time

from pysat.solvers import Cadical300
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool, CNF
from tqdm import tqdm

from .helpers import get_subtournament, paley_tournament, qrs, choose_subtournament
from diceset import DiceSet

def build_model(tournament: list[list[int]], faces: int):
    n = len(tournament)
    solver = Cadical300()
    pool = IDPool()
    cnf = CNF()

    def wins(X: int, Y: int, i: int, j: int) -> int:
        return pool.id((X, Y, i, j)) if (X, i) < (Y, j) else -pool.id((Y, X, j, i))
    
    for X in range(n):
        for Y in range(n):
            if X == Y: continue
            for i in range(faces):
                for j in range(faces):
                    # cache the pool id's
                    wins(X, Y, i, j)
                    wins(Y, X, j, i)

    for X in tqdm(range(n)):
        for i in range(faces):
            for j in range(faces):
                lit = wins(X, X, i, j)
                clause = [lit] if i >= j else [-lit]
                solver.add_clause(clause)
                cnf.append(clause)

        for Y in range(n):
            for i in range(faces):
                for j in range(1, faces):
                    solver.add_clause([-wins(X, Y, i, j), wins(X, Y, i, j-1)])
                    cnf.append([-wins(X, Y, i, j), wins(X, Y, i, j-1)])

            for i in range(faces-1):
                for j in range(faces):
                    solver.add_clause([-wins(X, Y, i, j), wins(X, Y, i+1, j)])
                    cnf.append([-wins(X, Y, i, j), wins(X, Y, i+1, j)])

            if X == Y:
                continue

            # transitivity constraints
            for Z in range(n):
                if Z in (X, Y):
                    continue

                for i in range(faces):
                    for j in range(faces):
                        for k in range(faces):
                            # for every face i, X > Y and Y > Z implies X > Z
                            clause = [-wins(X, Y, i, j), -wins(Y, Z, j, k), wins(X, Z, i, k)]
                            solver.add_clause(clause)
                            cnf.append(clause)
    
            # tournament constraints
            if tournament[X][Y]:
                lits = [wins(X, Y, i, j) for i in range(faces) for j in range(faces)]
                card_cnf = CardEnc.atleast(lits, (faces**2)//2 + 1, encoding=EncType.totalizer, vpool=pool)
                solver.append_formula(card_cnf.clauses)
                for c in card_cnf.clauses:
                    cnf.append(c)

    cnf.to_file("model.cnf")
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
            v = sum(wins(X, Y, i, j) in vars for Y in range(n) for j in range(faces))
            die.append(v)
        blocks.append(die)
    
    return DiceSet(blocks)

def main():
    p = int(sys.argv[1])
    
    tournament = paley_tournament(p)
    
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
        filename = f"n-player/results/p_{p}_f_{faces}_fullsat.txt"
    else:
        filename = f"n-player/results/p_{p}_sub_{subsize}_f_{faces}_fullsat.txt"

    solution.to_file(filename)

    print(f"Solution found in {end - start:.02f}s.")
    print("Verified:", solution.get_tournament() == tournament)


if __name__ == '__main__':
    main()
