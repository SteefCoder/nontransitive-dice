def prime_list(n: int) -> list[int]:
    # returns a list with 1 if i is prime and 0 otherwise
    # for i in range(n + 1)

    primes = []
    for i in range(2, n + 1):
        for p in primes:
            if i % p == 0:
                break
        else:
            primes.append(i)
    return primes
