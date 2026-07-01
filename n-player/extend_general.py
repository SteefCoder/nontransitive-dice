import itertools
from collections import defaultdict

from tqdm import tqdm

from diceset import DiceSet
from .angel_davis import construct_tournament
from .helpers import is_prime, qrs, qr_tournament


EXTEND_SET_5 = [
    [1, 4, 5],
    [2, 5, 1],
    [3, 2, 4],
    [4, 3, 2],
    [5, 1, 3],
]
EXTEND_SET_11 = [
    [2, 14, 27, 43, 54],
    [5, 17, 30, 44, 46],
    [4, 13, 33, 41, 50],
    [6, 22, 25, 34, 53],
    [7, 19, 23, 42, 47],
    [9, 15, 24, 38, 55],
    [3, 20, 32, 40, 45],
    [10, 21, 26, 36, 48],
    [1, 18, 31, 37, 52],
    [8, 16, 28, 35, 51],
    [11, 12, 29, 39, 49],
]
EXTEND_SET_11 = [[v - i*len(EXTEND_SET_11) for i, v in enumerate(x)] for x in EXTEND_SET_11]


def beats(d1: list[int], d2: list[int]) -> bool:
    w = sum(1 for a in d1 for b in d2 if a > b)
    return 2*w > len(d1) * len(d2)

def verify(dice: DiceSet, tournament, show_progress: bool = False) -> bool:
    n = dice.n
    r = tqdm(range(n)) if show_progress else range(n)
    for i in r:
        for j in range(n):
            if i != j and beats(dice.dice[i], dice.dice[j]) != bool(tournament[i][j]):
                return False
    return True


def build_B_mapping(extend_set: list[list[int]]) -> dict[frozenset, list[int]]:
    n = len(extend_set)
    k = len(extend_set[0])
    slot_vals = [s + 0.5 for s in range(n + 1)]
    mapping = {}
    for B in tqdm(itertools.product(slot_vals, repeat=k)):
        B = list(B)
        s = set()
        for j in range(n):
            wins = sum(1 for slot in range(k) if B[slot] > extend_set[j][slot])
            if wins > k / 2:
                s.add(j)
        s = frozenset(s)
        if s not in mapping:
            mapping[s] = [b for b in B]
    assert len(mapping) == 2**n
    return mapping


def extend_step(dice: DiceSet, tournament: list[list[int]], extend_set: list[list[int]], B_mapping: dict[frozenset, list[int]]) -> DiceSet:
    # I figured it out, but the default is only weakly nontransitive
    # So I had to change it to avoid draws
    # I also added a more general approach to be able to use any extend set

    ext = len(extend_set)
    lanes = len(extend_set[0])
    n_old = dice.n
    n = n_old + ext
    assert n == len(tournament), f"{n=}, {len(tournament)=}"
    d_old = dice.face_counts[0]
    k = d_old // 2
    dice_blocks = dice.as_blocks()

    # just a very large M to make it work
    M = 8*max(max(dice_blocks)) + 1

    def double(a, s=2): return [s*v for v in a]

    sub_t = [t[-ext:] for t in tournament[-ext:]]
    sub_faces = construct_tournament(sub_t)
    #print(sub_11face)

    new_dice = []
    all_lane_counts = [defaultdict(int) for _ in range(lanes)]
    for i in range(n_old):
        target_subset = frozenset(j for j in range(ext) if tournament[i][n_old + j])
        for j, b in enumerate(B_mapping[target_subset]):
            all_lane_counts[j][b] += 1

    max_occ = max(max(x.values()) for x in all_lane_counts)
    max_occ *= 2
    lane_counts = [defaultdict(int) for _ in range(lanes)]
    for i in range(n_old):
        target_subset = frozenset(j for j in range(ext) if tournament[i][n_old + j])
        B = B_mapping[target_subset]
        B = double(B, max_occ)
        #print("Lanes", lane_counts)
        for j, b in enumerate(B):
            lane_counts[j][b] += 1
        B = [x + lane_counts[j][x] - 1 for j, x in enumerate(B)]
        blocks = dice_blocks[i] + B + [-b for b in B]
        new_dice.append(blocks)

    for i, (A_i, C_i) in enumerate(zip(extend_set, sub_faces)):
        A_i = double(A_i, max_occ)
        a = (ext + lanes)//2
        C_minus_M = [v - M for v in C_i[:a]]
        C_plus_M = [v + M for v in C_i[a:]]
        neg_A = [M - v for v in A_i]
        
        D = [M + i] * (k - ext//2)
        blocks = [-x for x in D] + D + C_minus_M + C_plus_M + A_i + neg_A
        new_dice.append(blocks)

    return DiceSet.from_blocks(new_dice, 100_000).minimize()


def create_tournament(tournament: list[list[int]], seed: DiceSet, extend_set: list[list[int]]):
    step = len(extend_set)
    n = len(tournament)
    assert (n - seed.n) % step == 0
    B_mapping = build_B_mapping(extend_set)
    dice = seed
    for i in range(seed.n + step, n + 1, step):
        sub_t = [t[:i] for t in tournament[:i]]
        dice = extend_step(dice, sub_t, extend_set, B_mapping)
    return dice


def create_p_67():
    # 42 dice, 9 faces
    d = [[7, 49, 116, 140, 204, 221, 284, 321, 366], [10, 80, 113, 146, 190, 242, 264, 315, 352], [27, 72, 91, 167, 184, 231, 278, 322, 340], [14, 60, 122, 166, 171, 244, 259, 336, 338], [22, 59, 102, 131, 186, 243, 290, 318, 364], [29, 66, 92, 128, 177, 226, 294, 333, 361], [33, 73, 114, 150, 175, 218, 271, 320, 351], [38, 70, 98, 141, 200, 234, 257, 297, 377], [36, 58, 123, 133, 183, 228, 265, 327, 356], [4, 84, 104, 153, 197, 220, 276, 326, 345], [42, 55, 94, 144, 195, 251, 282, 304, 342], [18, 69, 89, 160, 187, 225, 262, 330, 370], [16, 81, 109, 157, 206, 213, 255, 295, 378], [1, 56, 124, 129, 196, 236, 268, 334, 372], [21, 48, 99, 163, 192, 246, 293, 300, 353], [40, 82, 125, 137, 173, 211, 292, 305, 350], [37, 71, 87, 161, 198, 249, 254, 302, 349], [34, 43, 111, 158, 178, 252, 253, 309, 368], [3, 83, 106, 149, 181, 227, 285, 306, 374], [13, 78, 117, 165, 193, 214, 272, 299, 357], [9, 46, 126, 142, 207, 239, 256, 331, 348], [24, 64, 88, 136, 199, 230, 288, 317, 354], [28, 57, 105, 156, 188, 215, 279, 310, 371], [25, 63, 96, 162, 182, 241, 263, 307, 362], [35, 45, 90, 134, 209, 219, 291, 303, 375], [12, 68, 112, 130, 208, 247, 275, 311, 337], [6, 65, 121, 138, 194, 237, 273, 308, 360], [39, 52, 107, 143, 174, 223, 287, 314, 358], [17, 44, 97, 152, 210, 212, 266, 328, 369], [11, 54, 93, 164, 203, 232, 281, 319, 344], [30, 61, 120, 145, 185, 217, 289, 312, 341], [19, 50, 108, 132, 172, 245, 274, 324, 376], [32, 51, 118, 148, 169, 233, 260, 323, 367], [31, 74, 85, 147, 180, 216, 280, 335, 355], [8, 76, 110, 127, 176, 248, 261, 325, 373], [41, 67, 103, 155, 191, 224, 270, 316, 339], [5, 47, 100, 135, 189, 250, 286, 329, 365], [15, 79, 95, 159, 179, 235, 277, 313, 346], [23, 75, 86, 151, 202, 229, 258, 332, 343], [20, 53, 119, 139, 201, 238, 267, 298, 363], [2, 62, 115, 168, 170, 240, 283, 296, 359], [26, 77, 101, 154, 205, 222, 269, 301, 347]]
    seed = DiceSet(d)
    tournament = qr_tournament(67)
    p67 = create_tournament(tournament, seed, EXTEND_SET_5)
    faces = p67.face_counts[0]
    # with open(f"n-player/results/p_67_f_{faces}.txt", "w") as f:
    #     for die in p67.dice:
    #         f.write(" ".join(map(str, die)) + "\n")

    #print(dice.dice)
    print("Written dice to file...")
    strong = verify(p67, tournament)
    print("Strongly verified:", strong)


def create_p_331():
    tournament = qr_tournament(331)
    
    # 34 dice, 11 faces
    # found with SAT
    d = [[34, 68, 101, 135, 169, 189, 224, 258, 291, 326, 341], [33, 67, 99, 129, 162, 181, 215, 245, 287, 320, 351], [11, 46, 102, 136, 170, 201, 208, 242, 301, 308, 350], [9, 41, 86, 106, 146, 198, 236, 267, 299, 334, 354], [29, 47, 85, 124, 159, 186, 218, 249, 288, 321, 370], [28, 66, 98, 108, 158, 180, 213, 243, 283, 317, 368], [32, 65, 96, 127, 148, 171, 207, 240, 274, 323, 374], [10, 54, 77, 116, 144, 197, 235, 266, 298, 333, 345], [12, 42, 81, 111, 150, 196, 232, 265, 295, 329, 359], [25, 58, 78, 134, 166, 185, 217, 247, 275, 312, 363], [22, 35, 73, 105, 140, 203, 238, 270, 304, 338, 343], [1, 49, 83, 107, 139, 200, 237, 269, 296, 330, 357], [3, 52, 79, 115, 143, 192, 228, 262, 306, 328, 355], [4, 43, 72, 110, 149, 204, 226, 260, 305, 327, 362], [19, 57, 87, 133, 165, 184, 222, 251, 276, 309, 358], [15, 50, 69, 118, 137, 193, 229, 268, 303, 336, 346], [21, 45, 90, 114, 151, 187, 220, 254, 290, 325, 365], [31, 60, 88, 128, 161, 172, 210, 252, 284, 318, 352], [14, 36, 70, 109, 152, 190, 234, 272, 300, 339, 348], [13, 55, 84, 131, 167, 188, 221, 255, 278, 307, 360], [27, 64, 82, 117, 157, 175, 214, 244, 286, 319, 369], [26, 63, 97, 112, 154, 179, 212, 241, 280, 313, 364], [30, 59, 93, 126, 145, 177, 206, 239, 279, 322, 373], [8, 44, 75, 119, 142, 195, 233, 271, 297, 332, 344], [6, 62, 100, 130, 164, 173, 223, 248, 277, 314, 366], [24, 61, 80, 121, 156, 178, 211, 253, 285, 311, 372], [20, 51, 95, 120, 153, 174, 205, 257, 282, 316, 367], [7, 40, 92, 103, 138, 194, 231, 263, 293, 337, 347], [5, 39, 74, 123, 141, 191, 230, 261, 292, 340, 353], [2, 37, 71, 104, 155, 202, 225, 264, 302, 331, 361], [16, 56, 94, 132, 168, 182, 216, 246, 273, 310, 356], [18, 48, 91, 125, 160, 176, 209, 256, 281, 315, 371], [17, 38, 89, 113, 147, 199, 227, 259, 294, 335, 342], [23, 53, 76, 122, 163, 183, 219, 250, 289, 324, 349]]
    seed = DiceSet(d)

    p331 = create_tournament(tournament, seed, EXTEND_SET_11)
    faces = p331.face_counts[0]

    with open(f"n-player/results/p_331_f_{faces}.txt", "w") as f:
        for die in p331.dice:
            f.write(" ".join(map(str, die)) + "\n")

    print("Written dice to file...")
    strong = verify(p331, tournament, show_progress=True)
    print("Strongly verified:", strong)


def main():
    # dice = construct_paley_dice(47)
    # with open("n-player/results/p_47_f_23.txt", "w") as f:
    #     for die in dice.dice:
    #         f.write(" ".join(map(str, die)) + "\n")
    pass


if __name__ == '__main__':
    create_p_331()
