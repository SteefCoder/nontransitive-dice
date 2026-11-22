import sympy as sp


def die_to_poly(die: list[int]) -> sp.Poly:
    n = len(die)
    x = sp.symbols("x")
    return sp.Poly(sum(x**v / n for v in die))

def poly_to_die(poly: sp.Poly) -> list[int]:
    return poly.coeffs()


def main():
    poly = die_to_poly([1, 2, 3, 4, 5, 6])
    factors = sp.factor_list(poly)
    print(factors)
    print(poly_to_die(poly ** 2))


main()