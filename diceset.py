from __future__ import annotations

from typing import Self


class DiceSet:
    def __init__(self, dice: list[list[int]]) -> None:
        self.dice = [sorted(d) for d in dice]
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
    
    @classmethod
    def from_blocks(cls, blocks: list[list[int]], spacing: int | None = None) -> Self:
        spacing = spacing or len(blocks)
        return cls([[v + i * spacing for i, v in enumerate(b)] for b in blocks])

    def as_blocks(self) -> list[list[int]]:
        return [[v - i * self.n for i, v in enumerate(d)] for d in self.dice]

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
    
    def get_tournament_ratios(self) -> list[list[float]]:
        tour = []
        for i, d1 in enumerate(self.dice):
            r = []
            for j, d2 in enumerate(self.dice):
                wins = 0
                for v1 in d1:
                    for v2 in d2:
                        if v1 > v2:
                            wins += 1
                r.append(wins / (len(d1) * len(d2)))
            tour.append(r)
        return tour

    def get_tournament(self) -> list[list[int]]:
        return [[int(v > 0.5) for v in x] for x in self.get_tournament_ratios()]

    def get_weak_tournament(self) -> list[list[int]]:
        ratios = self.get_tournament_ratios()
        return [[int(ratios[i][j] > ratios[j][i]) for j in range(self.n)] for i in range(self.n)]

    def minimize(self) -> DiceSet:
        values = []
        for d in self.dice:
            values += d
        mapping = {x: i for i, x in enumerate(sorted(set(values)))}
        return DiceSet([[mapping[v] for v in d] for d in self.dice])
