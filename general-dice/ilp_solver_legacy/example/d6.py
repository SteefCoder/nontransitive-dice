from solvers.general import GeneralDiceSolver


def list_primes(n: int) -> list[int]:
    primes = []
    i = 2
    while len(primes) < n:
        for p in primes:
            if i % p == 0:
                break
        else:
            primes.append(i)
        i += 1
    return primes


def print_latex(dice: list[list[int]]) -> None:
    print("\\\\\n".join(" & ".join(str(x) for x in i) for i in dice))


def main():
    faces = 8
    dice = 3
    shift = 1000

    primes = list_primes((faces * dice) // 2 + shift)
    # if sum(primes) % 3 != 0:
    #     return
    #print(sum(primes), sum(primes) % 3)
    #print(primes)
    solver = GeneralDiceSolver(faces=faces, dice=dice)
    solver.add_objective("max_min_ratio")
    #solver.add_objective("max_winloss")

    #solver.add_constraint("balanced")
    solver.add_constraint("max_repeat", 1)
    solver.add_constraint("equal_mean")
    #solver.add_constraint("no_skip_values")
    # solver.add_constraint("reverse_nontransitive")
    # solver.add_constraint("is_nontransitive")
    #solver.add_constraint("no_skip_values")
    solver.add_constraint("use_n_times", 2)
    solver.set_values(primes)
    solver.model.Params.MIPFocus = 1
    solver.model.Params.NoRelHeurTime = 200
    solver.model.Params
    #solver.model.Params.OutputFlag = 0
    with solver.build():
        #solver.model.addConstr(solver._r >= 0.501)
        dice = solver.solve()
        if not dice:
            return
        print(dice)
        print(dice.count_wins())
        print(dice.count_win_ratios())
        print(dice.means())
        print(dice.roll_twice().count_wins())
        print_latex(dice.dice)
        return dice
    

if __name__ == '__main__':
    main()