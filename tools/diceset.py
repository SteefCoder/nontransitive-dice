from __future__ import annotations

from enum import auto, Enum
from typing import Self

import numpy as np

from tournament import Tournament


class DiceType(Enum):
    VALUES = auto()
    BLOCKS = auto()


class DiceSet:
    def __init__(self, dice: list[list[int]] | np.ndarray) -> None:
        self.values = np.array(dice, dtype=np.int32)
        self.n, self.faces = self.values.shape

    def __str__(self) -> str:
        return str(self.values)

    def get_tournament(self) -> Tournament:
        tournament = []
        for d1 in self.values:
            t = []
            for d2 in self.values:
                wins = np.sum(np.subtract.outer(d1, d2) > 0)
                t.append(2 * wins > self.faces**2)
            tournament.append(t)
        return Tournament(tournament)

    @classmethod
    def from_file(cls, filename: str) -> Self:
        with open(filename) as f:
            return cls([
                [int(v) for v in x.split() if v]
                for x in f.readlines() if x
            ])
    
    def to_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            for die in self.values:
                f.write(" ".join(map(str, die)) + "\n")
    
    def minimize(self) -> DiceSet:
        values = np.sort(np.unique(self.values.flatten()))
        mapping = {x: i for i, x in enumerate(values)}
        return DiceSet([[mapping[v] for v in die] for die in self.values])

    def check_tournament(self, tournament: Tournament) -> bool:
        for d1, t in zip(self.values, tournament.win_table):
            for d2 in self.values[t]:
                wins = np.sum(np.subtract.outer(d1, d2) > 0)
                if not 2 * wins > self.faces**2:
                    return False
        return True
    

class BlockDiceSet(DiceSet):
    def get_tournament(self) -> Tournament:
        tournament = []
        for die in self.values:
            wins = die > self.values
            sums = np.sum(wins, axis=1)
            tournament.append(sums > self.faces / 2)
        return Tournament(tournament)

    @classmethod
    def from_file(cls, filename: str) -> Self:
        with open(filename) as f:
            return cls([
                [int(v) for v in x.split() if v]
                for x in f.readlines() if x
            ])
    
    def to_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            for die in self.values:
                values = die + self.n*np.arange(self.faces)
                f.write(" ".join(map(str, values)) + "\n")
    
    def minimize(self) -> None:
        for i, ordering in enumerate(self.values.T):
            self.values[:, i] = np.argsort(ordering)

    def check_tournament(self, tournament: Tournament) -> bool:
        for die, t in zip(self.values, tournament.win_table):
            wins = die > self.values[t]
            sums = np.sum(wins, axis=1)
            if not np.all(sums > self.faces/2):
                return False
        return True
