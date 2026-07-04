from __future__ import annotations

from typing import Self


class DiceSet:
    def __init__(self, dice: list[list[int]]) -> None:
        self.dice = [sorted(d) for d in dice]
        self.n = len(self.dice)
        self.faces = len(dice[0])

    def __str__(self) -> str:
        return str(self.dice)

    @classmethod
    def from_blocks(cls, blocks: list[list[int]], spacing: int | None = None) -> Self:
        spacing = spacing or len(blocks)
        return cls([[v + i * spacing for i, v in enumerate(b)] for b in blocks])

    def as_blocks(self) -> list[list[int]]:
        return [[v - i * self.n for i, v in enumerate(d)] for d in self.dice]

    def get_tournament_ratios(self) -> list[list[float]]:
        tour = []
        for d1 in self.dice:
            r = []
            for d2 in self.dice:
                wins = sum(a > b for a in d1 for b in d2)
                r.append(wins / (len(d1) * len(d2)))
            tour.append(r)
        return tour

    def get_tournament(self) -> list[list[int]]:
        tournament = []
        for d1 in self.dice:
            t = []
            for d2 in self.dice:
                wins = sum(a > b for a in d1 for b in d2)
                t.append(2 * wins > len(d1))
            tournament.append(t)
        return tournament
    
    @classmethod
    def from_file(cls, filename: str) -> Self:
        with open(filename) as f:
            return cls([
                [int(v) for v in x.split() if v]
                for x in f.readlines() if x
            ])
    
    def to_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            for die in self.dice:
                f.write(" ".join(map(str, die)) + "\n")
    
    def minimize(self) -> DiceSet:
        values = []
        for d in self.dice:
            values += d
        mapping = {x: i for i, x in enumerate(sorted(set(values)))}
        return DiceSet([[mapping[v] for v in d] for d in self.dice])
