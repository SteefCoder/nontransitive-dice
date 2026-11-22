from itertools import permutations, product
from typing import List
from collections import defaultdict

def is_prime(n):
    if n<2: return False
    for d in range(2,int(n**0.5)+1):
        if n%d==0: return False
    return True

def qrs(p): return sorted({(x*x)%p for x in range(1,p)})

def qr_tournament(p): return [[int((j - i) % p in qrs(p)) for j in range(p)] for i in range(p)]

def qr_gen(p):
    k=(p-1)//2; m=k; facs=set(); d=2
    while d*d<=m:
        if m%d==0:
            facs.add(d)
            while m%d==0: m//=d
        d+=1
    if m>1: facs.add(m)
    for g in qrs(p):
        if g==1: continue
        if all(pow(g,k//f,p)!=1 for f in facs): return g
    raise RuntimeError

def build(p):
    """
    Values taken in {0,...,p-1}. die 0 has constant value (p-1)/2.
    Die i face j holds ((p-1)/2 - i*q^j) mod p, shifted by j*p so faces
    don't collide across rows.
    """
    assert p%8==7 and is_prime(p)
    k=(p-1)//2; q=qr_gen(p); m=(p-1)//2
    dice=[[m + j*p for j in range(k)]]
    for i in range(1,p):
        dice.append([((m - i*pow(q,j,p)) % p) + j*p for j in range(k)])
    return dice

LEMMA5_A_RANKS = [
    [1, 4, 5],
    [2, 5, 1],
    [3, 2, 4],
    [4, 3, 2],
    [5, 1, 3],
]


def _build_B_mapping():
    n_ranks = 5
    slot_vals = [s + 0.5 for s in range(n_ranks + 1)]
    mapping = {}
    for B in product(slot_vals, repeat=3):
        B = list(B)
        s = set()
        for j in range(5):
            wins = sum(1 for slot in range(3) if B[slot] > LEMMA5_A_RANKS[j][slot])
            if wins > 1:
                s.add(j)
        s = frozenset(s)
        if s not in mapping:
            mapping[s] = [round(2*b) for b in B]
    return mapping


_B_MAP = _build_B_mapping()


def extend(dice_ranks, new_tournament, C_sub_ranks, D_filler_ranks):
    """
    dice_ranks:     n_old dice, each a list of 2k+1 slot-ranks (integers)
    new_tournament: (n_old+5) x (n_old+5) target tournament matrix
    C_sub_ranks:    5 dice, each a list of 3 slot-ranks, realizing the subtournament on new vertices
    D_filler_ranks: 5 dice, each a list of k-1 slot-ranks (arbitrary; can be all zeros)
    Returns: dice (n_old + 5) with 2k+7 face values each (with additive terms applied).
    """
    n_old = len(dice_ranks)
    d_orig = len(dice_ranks[0])
    k = (d_orig - 1) // 2
    n = 5
    assert d_orig == 2*k + 1 and k >= 1
    assert len(new_tournament) == n_old + 5, f"{len(new_tournament)} != {n_old=} + 5"
    assert len(C_sub_ranks) == 5 and all(len(d) == 3 for d in C_sub_ranks)
    assert len(D_filler_ranks) == 5 and all(len(d) == k - 1 for d in D_filler_ranks)

    SCALE = 2
    max_orig = max(max(map(abs, d)) for d in dice_ranks)
    max_filler = max((max(d) for d in D_filler_ranks if d), default=0)
    max_C = max(max(d) for d in C_sub_ranks)
    M = max_orig + 1
    M_scaled = SCALE * M
    SLOT_OFFSET = 100_000

    def apply_slots(slot_values):
        return [v + slot * SLOT_OFFSET for slot, v in enumerate(slot_values)]

    new_dice_set = []

    target_counts = defaultdict(int)
    for i in range(n_old):
        target = frozenset(j for j in range(n) if new_tournament[i][n_old + j])
        target_counts[target] += 1
    
    SCALE = max(target_counts.values())
    print("Scale", SCALE)
    
    target_counts = defaultdict(int)
    for i in range(n_old):
        target_subset = frozenset(j for j in range(n) if new_tournament[i][n_old + j])
        B_ranks = _B_MAP[target_subset]
        B_scaled = [b for b in B_ranks]
        neg_B = [-b for b in B_scaled]
        print(neg_B)
        orig_scaled = [SCALE * v for v in dice_ranks[i]]
        slot_values = orig_scaled + B_scaled + neg_B
        new_dice_set.append(apply_slots(slot_values))
        target_counts[target_subset] += 1

    for j in range(n):
        D_j = [x + j for x in D_filler_ranks[j]]
        C_j = C_sub_ranks[j]
        A_j = LEMMA5_A_RANKS[j]
        neg_D_minus_M = [-SCALE * v - M_scaled for v in D_j]
        D_plus_M     = [ SCALE * v + M_scaled for v in D_j]
        C_minus_M    = [ SCALE * v - M_scaled for v in C_j]
        A_scaled     = [ SCALE * v for v in A_j]
        neg_A_plus_M = [-SCALE * v + M_scaled for v in A_j]
        print(neg_A_plus_M)
        slot_values = neg_D_minus_M + D_plus_M + C_minus_M + A_scaled + neg_A_plus_M
        new_dice_set.append(apply_slots(slot_values))

    return new_dice_set


def beats(D1, D2):
    w = sum(1 for a in D1 for b in D2 if a > b)
    l = sum(1 for a in D1 for b in D2 if a < b)

    return w > l


def strict_beats(D1, D2):
    return 2*sum(1 for a in D1 for b in D2 if a > b) > len(D1) * len(D2)


def get_tournament(dice):
    n = len(dice)
    tournament = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                tournament[i][j] = int(beats(dice[i], dice[j]))
    return tournament


def verify(dice, tournament):
    n = len(dice)
    errors = []
    for i in range(n):
        for j in range(n):
            if i == j: continue
            actual = beats(dice[i], dice[j])
            # if actual and not strict_beats(dice[i], dice[j]):
            #     print(i, j, dice[i], dice[j])
            #     assert False
            want = bool(tournament[i][j])
            if actual != want:
                errors.append((i, j, want, actual))
    return errors


def find_3face_rank_realization(target_t):
    n = len(target_t)
    for p0 in permutations(range(1, n+1)):
        for p1 in permutations(range(1, n+1)):
            for p2 in permutations(range(1, n+1)):
                ranks = [[p0[i], p1[i], p2[i]] for i in range(n)]
                dice = [[r + n*f for f, r in enumerate(ranks_i)] for ranks_i in ranks]
                if not verify(dice, target_t):
                    return ranks
    return None


def minimize(dice: list[list[int]]):
    values = []
    for d in dice:
        values += d
    mapping = {v: i for i, v in enumerate(sorted(set(values)))}
    return [[mapping[v] for v in d] for d in dice]


def extend_by_5(d, new_t):
    sub_t = [t[-5:] for t in new_t[-5:]]
    sub_3face = find_3face_rank_realization(sub_t)
    d_filler = [[0] * (len(d[0]) // 2 - 1) for _ in range(5)]
    return extend([[v - i*37 for i, v in enumerate(di)] for di in d], new_t, sub_3face, d_filler)


def main():
    d = [[15, 48, 81, 141, 170, 205, 254, 280, 317], [6, 42, 108, 138, 166, 209, 245, 268, 324], [16, 40, 106, 127, 185, 211, 228, 263, 333], [28, 38, 76, 146, 153, 213, 259, 260, 330], [31, 51, 75, 140, 176, 191, 257, 271, 315], [36, 63, 96, 130, 174, 214, 223, 266, 303], [34, 71, 88, 121, 168, 196, 249, 273, 308], [20, 64, 107, 117, 162, 194, 233, 290, 321], [37, 50, 77, 125, 184, 188, 256, 285, 307], [21, 59, 85, 136, 183, 198, 250, 279, 298], [4, 67, 79, 134, 165, 219, 248, 278, 309], [3, 45, 92, 148, 158, 208, 242, 286, 327], [25, 70, 90, 113, 177, 206, 258, 272, 304], [9, 58, 83, 131, 152, 222, 255, 287, 312], [35, 47, 109, 118, 159, 199, 252, 274, 313], [33, 52, 91, 135, 154, 195, 239, 295, 310], [13, 60, 86, 133, 164, 218, 224, 294, 316], [2, 44, 102, 116, 181, 204, 253, 281, 322], [18, 72, 97, 112, 175, 201, 235, 267, 329], [27, 54, 111, 126, 169, 190, 225, 277, 328], [26, 53, 93, 137, 157, 207, 237, 292, 301], [19, 41, 87, 139, 167, 202, 226, 288, 332], [5, 69, 80, 144, 160, 212, 244, 282, 299], [29, 68, 100, 114, 179, 187, 243, 262, 311], [14, 61, 95, 124, 182, 197, 227, 289, 305], [10, 73, 104, 119, 163, 186, 238, 275, 325], [12, 55, 101, 129, 156, 203, 236, 296, 314], [17, 66, 99, 120, 173, 200, 240, 283, 302], [7, 57, 105, 143, 171, 189, 231, 265, 326], [23, 46, 103, 145, 149, 221, 247, 261, 300], [30, 74, 82, 123, 151, 220, 232, 284, 297], [32, 62, 84, 115, 161, 210, 230, 269, 331], [1, 49, 110, 142, 178, 193, 229, 293, 306], [11, 43, 94, 132, 172, 215, 241, 270, 320], [24, 56, 89, 122, 180, 217, 234, 264, 319], [8, 39, 78, 147, 155, 216, 246, 291, 323], [22, 65, 98, 128, 150, 192, 251, 276, 318]]
    new_t = qr_tournament(67)

    parti_dice = d
    for i in (42, 47, 52, 57, 62, 67):
        parti = [t[:i] for t in new_t[:i]]
        parti_dice = extend_by_5(parti_dice, parti)
        print(f"Part {i} verfied:", verify(parti_dice, parti) == [])
        break

    #print(parti_dice)

main()