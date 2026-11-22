from itertools import permutations
import random

# ---------------------------------------------------------
# Fast verifier
# ---------------------------------------------------------

def verify(perms):
    k = len(perms)
    n = len(perms[0])

    # points[i][j] = coordinate j of point i
    points = list(zip(*perms))

    realised = bytearray(1 << n)

    for thresh in __import__("itertools").product(range(1, n + 2), repeat=k):

        mask = 0

        for i, p in enumerate(points):

            votes = 0
            votes += thresh[0] > p[0]
            votes += thresh[1] > p[1]
            votes += thresh[2] > p[2]

            if k >= 5:
                votes += thresh[3] > p[3]
                votes += thresh[4] > p[4]

            if votes > k // 2:
                mask |= 1 << i

        realised[mask] = 1

    return all(realised)

# ---------------------------------------------------------
# Random search
# ---------------------------------------------------------

def random_search(n, k, trials=100000):

    identity = list(range(1, n+1))

    for t in range(trials):

        perms = [identity]

        for _ in range(k-1):
            p = identity[:]
            random.shuffle(p)
            perms.append(p)

        if verify(perms):
            print("FOUND")
            return perms

    return None


# ---------------------------------------------------------
# Hill climbing
# ---------------------------------------------------------

def score(perms):

    k = len(perms)
    n = len(perms[0])

    points = list(zip(*perms))

    realised = bytearray(1 << n)

    from itertools import product

    for thresh in product(range(1, n+2), repeat=k):

        mask = 0

        for i,p in enumerate(points):

            votes = 0

            for a,b in zip(thresh,p):
                votes += a>b

            if votes > k//2:
                mask |= 1<<i

        realised[mask]=1

    return sum(realised)


def hill_climb(n,k,steps=100000):

    identity=list(range(1,n+1))
    perms=[identity]

    for _ in range(k-1):
        p=identity[:]
        random.shuffle(p)
        perms.append(p)

    best=score(perms)

    print(best)

    while best<(1<<n):

        improved=False

        for _ in range(steps):

            q=[x[:] for x in perms]

            perm=random.randrange(1,k)

            i,j=random.sample(range(n),2)

            q[perm][i],q[perm][j]=q[perm][j],q[perm][i]

            s=score(q)

            if s>=best:

                perms=q
                best=s

                print(best)

                improved=True

                if best==(1<<n):
                    return perms

        if not improved:
            break

    return perms


sol = hill_climb(11, 5)
print(sol)
print(verify(sol))