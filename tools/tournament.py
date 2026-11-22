from __future__ import annotations

from typing import Self, Iterable

from gmpy2 import is_prime  # type: ignore
import numpy as np


class Tournament:
    def __init__(self, win_table: list[list[int]] | list[list[bool]] | np.ndarray) -> None:
        self.win_table = np.array(win_table, dtype=np.bool)
        shape = self.win_table.shape
        if len(shape) != 2 or shape[0] != shape[1]:
            raise ValueError
        self.n = len(self.win_table)

    def __str__(self) -> str:
        return "\n".join(" ".join("1" if v else "0" for v in x) for x in self.win_table)

    def __eq__(self, other: Tournament) -> bool:
        return np.array_equal(self.win_table, other.win_table)

    @classmethod
    def paley(cls, p: int) -> Self:
        residues = np.arange(1, p)**2 % p
        return cls.symmetric(np.isin(range(p), residues))
    
    @classmethod
    def symmetric(cls, first_row: list[int] | list[bool] | np.ndarray) -> Self:
        n = len(first_row)
        idx = np.subtract.outer(range(n), range(n)) % n
        win_table = np.array(first_row)[idx.T]
        return cls(win_table)
    
    def is_symmetric(self) -> bool:
        first_row = self.win_table[0]
        return self == Tournament.symmetric(first_row)
    
    def is_paley(self) -> bool:
        if not (self.n % 4 == 3 and is_prime(self.n)):
            return False

        return self == Tournament.paley(self.n)

    def get_subtournament(self, vertices: Iterable[int]) -> Tournament:
        vertices = np.array(vertices)
        return Tournament(self.win_table[vertices][:, vertices])
