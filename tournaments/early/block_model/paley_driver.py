# paley_driver.py
import ctypes
import os
import numpy as np

_lib = ctypes.CDLL(os.path.abspath("libpaley.so"))
_lib.solve.argtypes = [
    ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_int8),
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_double,
    ctypes.c_uint64,
]
_lib.solve.restype = ctypes.c_int

def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]

def search(tournament, d, max_time=10, seed=1):
    n = len(tournament)
    target = np.array(tournament, dtype=np.int8).flatten()
    for X in range(n):
        target[X*n + X] = 0
    rank_out = np.zeros(d * n, dtype=np.int32)

    cost = _lib.solve(
        n, d,
        target.ctypes.data_as(ctypes.POINTER(ctypes.c_int8)),
        rank_out.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        max_time, seed,
    )
    if cost != 0:
        return None, cost
    rank = rank_out.reshape(d, n)
    dice = []
    for X in range(n):
        faces = sorted(i * n + int(rank[i, X]) for i in range(d))
        dice.append(faces)
    return dice, 0

def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            w = sum(1 for a in dice[i] for b in dice[j] if a > b)
            l = sum(1 for a in dice[i] for b in dice[j] if a < b)
            if bool(tournament[i][j]) != (w > l): return False
    return True


if __name__ == "__main__":
    import sys, time
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    iters = int(sys.argv[3]) if len(sys.argv) > 3 else 2_000_000
    t = qr_tournament(p)
    t0 = time.time()
    dice, cost = search(t, d, iters)
    dt = time.time() - t0
    if dice is None:
        print(f"P_{p}, d={d}: best cost = {cost}  ({dt:.2f}s)")
    else:
        for i, r in enumerate(dice): print(f"  die {i}: {r}")
        print(f"P_{p}, d={d}: solved in {dt:.2f}s")
        print(verify(dice, t))