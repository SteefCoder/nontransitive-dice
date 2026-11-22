import ctypes
import os
import numpy as np

_lib = ctypes.CDLL(os.path.abspath("libpaley_bt.so"))
_lib.solve.argtypes = [
    ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_int8),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_long),
]
_lib.solve.restype = ctypes.c_int


def qr_tournament(p):
    Q = {i*i % p for i in range(1, p)}
    return [[1 if (j-i) % p in Q else 0 for j in range(p)] for i in range(p)]


def solve(tournament, d):
    n = len(tournament)
    target = np.array(tournament, dtype=np.int8).flatten()
    rank_out = np.zeros(d * n, dtype=np.int32)
    calls = ctypes.c_long(0)
    found = _lib.solve(
        n, d,
        target.ctypes.data_as(ctypes.POINTER(ctypes.c_int8)),
        rank_out.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        ctypes.byref(calls),
    )
    if not found:
        return None, calls.value
    rank = rank_out.reshape(d, n)
    dice = []
    for X in range(n):
        faces = sorted(i * n + int(rank[i, X]) for i in range(d))
        dice.append(faces)
    return dice, calls.value


if __name__ == "__main__":
    import sys, time
    p = int(sys.argv[1])
    d = int(sys.argv[2])
    t = qr_tournament(p)
    t0 = time.time()
    dice, calls = solve(t, d)
    dt = time.time() - t0
    print(f"P_{p}, d={d}: {calls} calls, {dt:.2f}s")
    if dice:
        for i, row in enumerate(dice[:8]):
            print(f"  die {i}: {row}")
    else:
        print("  no solution")