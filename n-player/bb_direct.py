from .helpers import paley_tournament, is_prime, qrs, verify
from diceset import DiceSet


def build_paley_7mod8(p: int) -> DiceSet:
    assert p % 8 == 7 and is_prime(p)
    k = p // 2
    qr = qrs(p)
    blocks = [[k]*k]
    for i in range(1, p):
        blocks.append([(k - i*qr[j]) % p for j in range(k)])
    return DiceSet.from_blocks(blocks)


def build_paley_3mod8(p: int, c: int) -> DiceSet:
    k = p // 2
    m = k // 2
    qr = qrs(p)
    blocks = [[p]*(m+1) + [-1]*m + [0, 0]]
    for i in range(1, p):
        block = [(c - i*qr[j]) % p for j in range(k)]
        if i in qr:
            block += [p + i - 1, -i]
        else:
            block += [i, p - i]
        blocks.append(block)
    return DiceSet.from_blocks(blocks, spacing=4*p)


def find_c(p: int) -> int | None:
    # try c = p - 2 first
    tournament = paley_tournament(p)

    for c in range(p):
        dice = build_paley_3mod8(p, c)
        if verify(dice, tournament):
            return c

    return None


def create_p331():
    p = 331
    tournament = paley_tournament(p)
    dice = build_paley_3mod8(p, 6)
    verified = verify(dice, tournament)
    print("Verified:", verified)
    if verified:
        dice.to_file(f"n-player/results/p_{p}_f_{dice.faces}_newbednay.txt")


def create_p1163():
    p = 1163
    c = find_c(p)
    if not c:
        return
    tournament = paley_tournament(p)
    dice = build_paley_3mod8(p, c)
    verified = verify(dice, tournament)
    print("Verified:", verified)
    if verified:
        dice.to_file(f"n-player/results/p_{p}_f_{dice.faces}_newbednay.txt")

if __name__ == '__main__':
    create_p1163()
