from typing import Self


class DiceSet:
    def __init__(self, dice: list[list[int]]) -> None:
        self.dice = dice
        self.n = len(self.dice)
        self.face_counts = [len(d) for d in self.dice]

    def __str__(self) -> str:
        return str(self.dice)

    @classmethod
    def from_tuples(cls, tuples: list[list[tuple[int, int]]]) -> Self:
        dice = []
        for t in tuples:
            die = []
            for v, a in t:
                die += [v] * a
            dice.append(die)
        return cls(dice)

    def count_wins(self) -> list[tuple[int, int, int]]:
        ratios = []

        for i, die in enumerate(self.dice):
            j = (i + 1) % self.n

            win = loss = draw = 0
            for a in die:
                for b in self.dice[j]:
                    if a > b:
                        win += 1
                    elif a < b:
                        loss += 1
                    else:
                        draw += 1

            ratios.append((win, loss, draw))

        return ratios

    def count_win_ratios(self) -> list[float]:
        return [a / (a + b + c) for a, b, c in self.count_wins()]

    def is_nontransitive(self) -> bool:
        return all(x > 0.5 for x in self.count_win_ratios())
    