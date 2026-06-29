import itertools
from collections import defaultdict

from diceset import DiceSet
from .helpers import is_prime, qrs, qr_tournament

LEMMA5_A_RANKS = [
    [1, 4, 5],
    [2, 5, 1],
    [3, 2, 4],
    [4, 3, 2],
    [5, 1, 3],
]

def construct_paley_dice(p: int) -> DiceSet:
    """Construct P_p using (p-1)/2 faces"""
    assert p % 8 == 7 and is_prime(p)
    qr = qrs(p)
    k = p // 2
    return DiceSet([[k + j * p for j in range(k)]] + [
        [((k - i * qr[j]) % p) + j*p for j in range(k)]
        for i in range(1, p)
    ])

def _build_B_mapping():
    n_ranks = 5
    slot_vals = [s + 0.5 for s in range(n_ranks + 1)]
    mapping = {}
    for B in itertools.product(slot_vals, repeat=3):
        B = list(B)
        s = set()
        for j in range(5):
            wins = sum(1 for slot in range(3) if B[slot] > LEMMA5_A_RANKS[j][slot])
            if wins >= 2:
                s.add(j)
        s = frozenset(s)
        if s not in mapping:
            mapping[s] = [b for b in B]
    return mapping

_B_MAP = _build_B_mapping()

def beats(D1, D2):
    w = sum(1 for a in D1 for b in D2 if a > b)
    l = sum(1 for a in D1 for b in D2 if a < b)
    #assert w + l == len(D1) * len(D2)
    return w > l

def strongly_beats(D1, D2):
    w = sum(1 for a in D1 for b in D2 if a > b)
    l = sum(1 for a in D1 for b in D2 if a < b)
    #assert w + l == len(D1) * len(D2)
    return 2*w > len(D1) * len(D2)


def verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i != j and beats(dice[i], dice[j]) != bool(tournament[i][j]):
                return False
    return True


def strongly_verify(dice, tournament):
    n = len(dice)
    for i in range(n):
        for j in range(n):
            if i != j and strongly_beats(dice[i], dice[j]) != bool(tournament[i][j]):
                return False
    return True


def find_3face_rank_realization(target_t):
    n = len(target_t)

    def perms(): return itertools.permutations(range(1, n+1))

    for p0 in perms():
        for p1 in perms():
            for p2 in perms():
                ranks = [[p0[i], p1[i], p2[i]] for i in range(n)]
                dice = [[r + n*f for f, r in enumerate(ranks_i)] for ranks_i in ranks]
                if verify(dice, target_t):
                    return ranks
    
    assert False


def extend_by_5(dice: DiceSet, tournament: list[list[int]]) -> DiceSet:
    # This method does NOT work the way the paper says it does
    # I figured it out, but the default is only weakly nontransitive
    # So I had to change it to avoid draws
    
    n_old = dice.n
    n = n_old + 5
    assert n == len(tournament)
    d_old = dice.face_counts[0]
    k = d_old // 2
    dice_blocks = dice.as_blocks()
    # just a very large M to make it work
    M = 8*max(max(dice_blocks)) + 1

    def double(a, s=2): return [s*v for v in a]

    sub_t = [t[-5:] for t in tournament[-5:]]
    sub_3face = find_3face_rank_realization(sub_t)

    new_dice = []
    all_lane_counts = [defaultdict(int), defaultdict(int), defaultdict(int)]
    for i in range(n_old):
        target_subset = frozenset(j for j in range(5) if tournament[i][n_old + j])
        for j, b in enumerate(_B_MAP[target_subset]):
            all_lane_counts[j][b] += 1

    max_occ = max(max(x.values()) for x in all_lane_counts)
    max_occ *= 2
    lane_counts = [defaultdict(int), defaultdict(int), defaultdict(int)]
    for i in range(n_old):
        target_subset = frozenset(j for j in range(5) if tournament[i][n_old + j])
        B = _B_MAP[target_subset]
        B = double(B, max_occ)
        #print("Lanes", lane_counts)
        for j, b in enumerate(B):
            lane_counts[j][b] += 1
        B = [x + lane_counts[j][x] - 1 for j, x in enumerate(B)]
        blocks = dice_blocks[i] + B + [-b for b in B]
        new_dice.append(blocks)
        #print("B", B)
    
    #print("-" * 20)

    for i, (A_i, C_i) in enumerate(zip(LEMMA5_A_RANKS, sub_3face)):
        A_i = double(A_i, max_occ)
        C_minus_M = [v - M for v in C_i]
        neg_A = [M - v for v in A_i]
        
        D = [M + i] * (k-1)
        blocks = [-x for x in D] + D + C_minus_M + A_i + neg_A
        new_dice.append(blocks)
        #print("A", A_i)

    return DiceSet.from_blocks(new_dice, 1000).minimize()


def create_p_67():
    # 37 dice, 9 faces
    # d = [[15, 48, 81, 141, 170, 205, 254, 280, 317], [6, 42, 108, 138, 166, 209, 245, 268, 324], [16, 40, 106, 127, 185, 211, 228, 263, 333], [28, 38, 76, 146, 153, 213, 259, 260, 330], [31, 51, 75, 140, 176, 191, 257, 271, 315], [36, 63, 96, 130, 174, 214, 223, 266, 303], [34, 71, 88, 121, 168, 196, 249, 273, 308], [20, 64, 107, 117, 162, 194, 233, 290, 321], [37, 50, 77, 125, 184, 188, 256, 285, 307], [21, 59, 85, 136, 183, 198, 250, 279, 298], [4, 67, 79, 134, 165, 219, 248, 278, 309], [3, 45, 92, 148, 158, 208, 242, 286, 327], [25, 70, 90, 113, 177, 206, 258, 272, 304], [9, 58, 83, 131, 152, 222, 255, 287, 312], [35, 47, 109, 118, 159, 199, 252, 274, 313], [33, 52, 91, 135, 154, 195, 239, 295, 310], [13, 60, 86, 133, 164, 218, 224, 294, 316], [2, 44, 102, 116, 181, 204, 253, 281, 322], [18, 72, 97, 112, 175, 201, 235, 267, 329], [27, 54, 111, 126, 169, 190, 225, 277, 328], [26, 53, 93, 137, 157, 207, 237, 292, 301], [19, 41, 87, 139, 167, 202, 226, 288, 332], [5, 69, 80, 144, 160, 212, 244, 282, 299], [29, 68, 100, 114, 179, 187, 243, 262, 311], [14, 61, 95, 124, 182, 197, 227, 289, 305], [10, 73, 104, 119, 163, 186, 238, 275, 325], [12, 55, 101, 129, 156, 203, 236, 296, 314], [17, 66, 99, 120, 173, 200, 240, 283, 302], [7, 57, 105, 143, 171, 189, 231, 265, 326], [23, 46, 103, 145, 149, 221, 247, 261, 300], [30, 74, 82, 123, 151, 220, 232, 284, 297], [32, 62, 84, 115, 161, 210, 230, 269, 331], [1, 49, 110, 142, 178, 193, 229, 293, 306], [11, 43, 94, 132, 172, 215, 241, 270, 320], [24, 56, 89, 122, 180, 217, 234, 264, 319], [8, 39, 78, 147, 155, 216, 246, 291, 323], [22, 65, 98, 128, 150, 192, 251, 276, 318]]
    
    # 42 dice, 9 faces
    d = [[7, 49, 116, 140, 204, 221, 284, 321, 366], [10, 80, 113, 146, 190, 242, 264, 315, 352], [27, 72, 91, 167, 184, 231, 278, 322, 340], [14, 60, 122, 166, 171, 244, 259, 336, 338], [22, 59, 102, 131, 186, 243, 290, 318, 364], [29, 66, 92, 128, 177, 226, 294, 333, 361], [33, 73, 114, 150, 175, 218, 271, 320, 351], [38, 70, 98, 141, 200, 234, 257, 297, 377], [36, 58, 123, 133, 183, 228, 265, 327, 356], [4, 84, 104, 153, 197, 220, 276, 326, 345], [42, 55, 94, 144, 195, 251, 282, 304, 342], [18, 69, 89, 160, 187, 225, 262, 330, 370], [16, 81, 109, 157, 206, 213, 255, 295, 378], [1, 56, 124, 129, 196, 236, 268, 334, 372], [21, 48, 99, 163, 192, 246, 293, 300, 353], [40, 82, 125, 137, 173, 211, 292, 305, 350], [37, 71, 87, 161, 198, 249, 254, 302, 349], [34, 43, 111, 158, 178, 252, 253, 309, 368], [3, 83, 106, 149, 181, 227, 285, 306, 374], [13, 78, 117, 165, 193, 214, 272, 299, 357], [9, 46, 126, 142, 207, 239, 256, 331, 348], [24, 64, 88, 136, 199, 230, 288, 317, 354], [28, 57, 105, 156, 188, 215, 279, 310, 371], [25, 63, 96, 162, 182, 241, 263, 307, 362], [35, 45, 90, 134, 209, 219, 291, 303, 375], [12, 68, 112, 130, 208, 247, 275, 311, 337], [6, 65, 121, 138, 194, 237, 273, 308, 360], [39, 52, 107, 143, 174, 223, 287, 314, 358], [17, 44, 97, 152, 210, 212, 266, 328, 369], [11, 54, 93, 164, 203, 232, 281, 319, 344], [30, 61, 120, 145, 185, 217, 289, 312, 341], [19, 50, 108, 132, 172, 245, 274, 324, 376], [32, 51, 118, 148, 169, 233, 260, 323, 367], [31, 74, 85, 147, 180, 216, 280, 335, 355], [8, 76, 110, 127, 176, 248, 261, 325, 373], [41, 67, 103, 155, 191, 224, 270, 316, 339], [5, 47, 100, 135, 189, 250, 286, 329, 365], [15, 79, 95, 159, 179, 235, 277, 313, 346], [23, 75, 86, 151, 202, 229, 258, 332, 343], [20, 53, 119, 139, 201, 238, 267, 298, 363], [2, 62, 115, 168, 170, 240, 283, 296, 359], [26, 77, 101, 154, 205, 222, 269, 301, 347]]
    new_t = qr_tournament(67)

    dice = DiceSet(d)
    
    for i in (47, 52, 57, 62, 67):
        sub_t = [t[:i] for t in new_t[:i]]
        dice = extend_by_5(dice, sub_t)

        # for b in dice.dice:
        #     print(b)

        print(f"Part {i} verified:", verify(dice.dice, sub_t))
        print(f"Part {i} strongly verified:", strongly_verify(dice.dice, sub_t))

    with open("n-player/results/p_67_f_39_mixed.txt", "w") as f:
        for die in dice.dice:
            f.write(" ".join(map(str, die)) + "\n")

    print(dice.dice)


def main():
    dice = construct_paley_dice(47)
    with open("n-player/results/p_47_f_23.txt", "w") as f:
        for die in dice.dice:
            f.write(" ".join(map(str, die)) + "\n")

if __name__ == '__main__':
    create_p_67()