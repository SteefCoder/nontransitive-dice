from solvers import solve_by_distinct, solve_combination
from niceify import niceify
from diceset import DiceSet


def main2():
    faces = [20] * 4
    distinct = 3
    max_repeats = [5] * 3

    dice, r = solve_by_distinct(faces, distinct, False)
    print("r   :", r)
    print("dice:", dice.dice)
    # dice = DiceSet([[4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4], [2, 2, 2, 2, 2, 2, 2, 2, 8, 8, 8, 8], [1, 1, 1, 1, 1, 1, 6, 6, 6, 6, 6, 6], [0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5]])

    nice_dice = niceify(dice, max_repeats, equal_mean=True)
    print("new dice:", nice_dice.dice)


def main():
    faces = [4, 6, 8, 10, 12, 20]
    max_repeat = [1, 2, 2, 2, 2, 3]
    M = 100

    dice, r = solve_combination(faces, max_repeat, True, True, True, M)
    print(dice.dice)
    print(r)
    print(dice.count_wins())
    print(dice.count_win_ratios())


if __name__ == '__main__':
    main()
