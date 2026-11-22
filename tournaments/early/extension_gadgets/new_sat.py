NEW_RANKS = [
    [10, 7, 3, 8, 4, 1, 6, 2, 9, 5, 11], 
    [5, 4, 1, 3, 6, 11, 8, 9, 10, 7, 2], 
    [1, 11, 8, 2, 10, 6, 7, 9, 4, 5, 3], 
    [11, 2, 9, 10, 3, 4, 6, 7, 5, 8, 1], 
    [9, 5, 7, 2, 3, 6, 8, 4, 11, 1, 10],
]

from tqdm import tqdm
from itertools import product

def build_pos(perms):
    n = len(perms[0])
    k = len(perms)

    pos = [[0]*k for _ in range(n)]
    for r in range(k):
        for i, p in enumerate(perms[r]):
            pos[i][r] = p
    return pos


def realizable_subset(S, pos, n, k):
    majority = k // 2

    # brute force thresholds
    for t in product(range(n+1), repeat=k):

        ok = True

        for i in range(n):
            votes = 0

            for r in range(k):
                if pos[i][r] < t[r]:
                    votes += 1

            inS = (S >> i) & 1

            if (votes > majority) != inS:
                ok = False
                break

        if ok:
            return True

    return False


def verify(perms):
    n = len(perms[0])
    k = len(perms)

    pos = build_pos(perms)

    total = 1 << n

    bad = []

    for S in tqdm(range(total)):
        if not realizable_subset(S, pos, n, k):
            bad.append(S)
            print(S)
            return False

    if not bad:
        print("VERIFIED: all subsets realizable")
        return True

    print(f"FAILED: {len(bad)} / {total} subsets not realizable")
    print("Example failing subsets:")
    for b in bad[:10]:
        print(bin(b)[2:].zfill(n))

    return False

print(verify(NEW_RANKS))