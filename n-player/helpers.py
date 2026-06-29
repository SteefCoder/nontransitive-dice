import math


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    
    for i in range(2, math.isqrt(n) + 1):
        if n % i == 0:
            return False
    
    return True

def qrs(p: int) -> list[int]:
    # quadratic residues of p
    return sorted({ i**2 % p for i in range(1, p) })

def qr_tournament(p: int) -> list[list[int]]:
    assert p % 4 == 3 and is_prime(p)
    return [[int((j - i) % p in qrs(p)) for j in range(p)] for i in range(p)]
