#!/usr/bin/env python3
"""Build k-majority realisations of Paley tournaments, and inspect them.

A solution file has one ordering per line: a permutation of 0..p-1 written
weakest-first, so a vertex appearing later beats a vertex appearing earlier.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE, BINARY = ROOT / "solver.c", ROOT / "solver"


def build(force=False):
    stale = not BINARY.exists() or SOURCE.stat().st_mtime > BINARY.stat().st_mtime
    if force or stale:
        subprocess.run(["gcc", "-O3", "-march=native", "-o", str(BINARY),
                        str(SOURCE), "-lm"], check=True)
    return BINARY


def paley(p):
    """Sign matrix of the Paley tournament: +1 in entry (a, b) iff a beats b."""
    qr = np.zeros(p, bool)
    qr[(np.arange(1, p) ** 2) % p] = True
    x = np.arange(p)
    adj = np.where(qr[(x[:, None] - x[None, :]) % p], 1, -1).astype(np.int8)
    np.fill_diagonal(adj, 0)
    return adj


def load(path, p):
    """Read orderings, accepting either our format or the repo's dice format.

    Ours: k lines of p entries, each a permutation of 0..p-1, weakest first.
    Repo: p lines of k entries, values 1..pk, die a beating b iff b-a is a
    quadratic residue -- so its highest face belongs to our weakest vertex.
    """
    raw = np.array([[int(v) for v in line.split()] for line in open(path) if line.strip()])
    if raw.shape[1] == p and set(raw[0].tolist()) == set(range(p)):
        return raw
    if raw.shape[0] == p:
        return np.argsort(-raw, axis=0).T
    sys.exit(f"{path}: not a solution for p={p} (shape {raw.shape})")


def ranks(rows, p):
    out = np.empty_like(rows)
    for t, r in enumerate(rows):
        out[t, r] = np.arange(p)
    return out


def margins(rows, p):
    """Signed margin of every pair, oriented so that >= 1 means correct.

    Accumulated one ordering at a time: the full k x C(p,2) table is far too
    large to hold at p in the thousands.
    """
    adj = paley(p)
    iu = np.triu_indices(p, 1)
    tally = np.zeros(len(iu[0]), np.int32)
    for r in rows:
        pos = np.empty(p, np.int32)
        pos[r] = np.arange(p)
        tally += np.sign(pos[iu[0]] - pos[iu[1]]).astype(np.int32)
    return adj[iu] * tally, adj, iu


def correctness(rows, p, iu, adj, cols=None):
    """Per-ordering +1/-1 table of which pairs each ordering gets right."""
    a, b = (iu[0], iu[1]) if cols is None else (iu[0][cols], iu[1][cols])
    sub = adj[a, b].astype(np.int8)
    out = np.empty((len(rows), len(a)), np.int8)
    for t, r in enumerate(rows):
        pos = np.empty(p, np.int32)
        pos[r] = np.arange(p)
        out[t] = np.sign(pos[a] - pos[b]).astype(np.int8) * sub
    return out


def cmd_verify(args):
    rows = load(args.file, args.p)
    p, k = args.p, len(rows)
    ok = all(sorted(r.tolist()) == list(range(p)) for r in rows)
    mar, _, _ = margins(rows, p)
    valid = ok and mar.min() >= 1
    print(f"p={p} k={k} permutations={'ok' if ok else 'BAD'} "
          f"ties={(mar == 0).sum()} wrong={(mar < 0).sum()} of {len(mar)} pairs")
    print("VALID" if valid else "INVALID")
    return 0 if valid else 1


def cmd_stats(args):
    rows = load(args.file, args.p)
    p, k = args.p, len(rows)
    mar, adj, iu = margins(rows, p)
    npair = len(mar)
    errors = (k - mar) // 2                 # orderings wrong on each pair
    ceiling = (k - 1) // 2 * npair          # most any pair may afford
    sample = np.random.default_rng(0).choice(npair, min(npair, 20000), replace=False)
    table = correctness(rows, p, iu, adj, sample).astype(np.float32)
    corr = (table @ table.T) / table.shape[1]
    off = corr[~np.eye(k, dtype=bool)]
    rank_sum = ranks(rows, p).sum(0)
    hist = {v: int((mar == v).sum()) for v in sorted(set(mar.tolist()))[:6]}
    print(f"p={p} k={k}  waste={mar.sum() / npair:.3f}  margins={hist}")
    print(f"  agreement per ordering: {mar.sum() / k:.0f}"
          f"  ->  D/p^1.5 = {mar.sum() / k / p ** 1.5:.3f}")
    print(f"  pairwise correlation: {off.mean():+.4f}"
          f"   (theory -1/k = {-1 / k:+.4f}, from a sample of pairs)")
    print(f"  error packing: {errors.sum()} of at most {ceiling}"
          f" = {100 * errors.sum() / ceiling:.1f}%")
    print(f"  rank-sum spread: {rank_sum.std():.2f}"
          f"   (random baseline {np.sqrt(k * (p * p - 1) / 12):.1f})")
    prof = []
    for d in [1, 2, 5, p // 4, p // 2, p - 2]:
        hit = sum(int((adj[r[d:], r[:-d]] == 1).sum()) for r in rows)
        prof.append(f"d={d}:{hit / (k * (p - d)):.2f}")
    print("  agreement by positional distance: " + "  ".join(prof))


def cmd_dice(args):
    """write a solution in the repo's dice format"""
    rows = load(args.file, args.p)
    p, k = args.p, len(rows)
    mar, _, _ = margins(rows, p)
    if mar.min() < 1:
        sys.exit(f"{args.file}: not a valid realisation, refusing to export")
    faces = (np.arange(k)[None, :] * p) + (p - ranks(rows, p).T)
    assert sorted(faces.ravel().tolist()) == list(range(1, p * k + 1))
    out = args.out or f"paley_{p:04d}_{k}.txt"
    np.savetxt(out, faces, fmt="%d")
    print(f"{out}: {p} dice x {k} faces, values 1..{p * k}, "
          f"die a beats die b iff b-a is a quadratic residue")


def call_solver(p, k, seconds, seed, init, kmin, rounds, prefix, quiet=False):
    cmd = [str(build()), "--p", str(p), "--k", str(k), "--rounds", str(rounds),
           "--seconds", str(seconds), "--seed", str(seed), "--kmin", str(kmin),
           "--prefix", prefix]
    if init:
        cmd += ["--init", str(init)]
    start = time.time()
    res = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    stdout = ""
    for stdout_line in res.stdout:
        print(stdout_line, end="")
        stdout += stdout_line
    res.stdout.close()
    res.wait()
    found = dict(re.findall(r"SOLVED k=(\d+) file=(\S+)", stdout))
    loss = re.search(r"FINAL k=\d+ loss=\d+ best=(\d+)", stdout)
    return {int(a): b for a, b in found.items()}, int(loss.group(1)) if loss else None


def cmd_join(args):
    """Concatenate split part files back into one solution."""
    with open(args.out, "wb") as out:
        for part in sorted(args.parts):
            out.write(open(part, "rb").read())
    rows = load(args.out, args.p)
    print(f"{args.out}: {len(rows)} orderings from {len(args.parts)} parts")


def cmd_solve(args):
    solved, best = call_solver(args.p, args.k, args.seconds, args.seed,
                               args.init, args.kmin, args.rounds, args.prefix)
    if not solved:
        print(f"no solution at k={args.k}; best residual loss {best}")


def cmd_ladder(args):
    """Warm-start down from a known solution, retrying a rung before giving up."""
    k, init, best = args.k, args.init, None
    while k >= args.kmin:
        attempt = 0
        while attempt < args.retries:
            solved, loss = call_solver(args.p, k, args.seconds, args.seed + attempt,
                                       init, k, args.rounds, args.prefix, quiet=True)
            if k in solved:
                best, init = k, solved[k]
                print("")
                break
            attempt += 1
            print(f"k={k:4d}  attempt {attempt}/{args.retries} residual loss {loss}")
        else:
            print(f"stopping at k={k}; best verified solution is k={best}")
            return
        k -= args.step


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve", help="search for a realisation with k orderings")
    s.add_argument("p", type=int)
    s.add_argument("k", type=int)
    s.add_argument("--seconds", type=float, default=60)
    s.add_argument("--rounds", type=int, default=40)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--init", help="warm start from a solution file")
    s.add_argument("--kmin", type=int, default=3, help="keep shrinking k down to this")
    s.add_argument("--prefix", default="sol")
    s.set_defaults(func=cmd_solve)

    l = sub.add_parser("ladder", help="repeatedly shrink k, warm starting each rung")
    l.add_argument("p", type=int)
    l.add_argument("k", type=int)
    l.add_argument("--init")
    l.add_argument("--step", type=int, default=2)
    l.add_argument("--seconds", type=float, default=60)
    l.add_argument("--rounds", type=int, default=40)
    l.add_argument("--seed", type=int, default=1)
    l.add_argument("--retries", type=int, default=3)
    l.add_argument("--kmin", type=int, default=3)
    l.add_argument("--prefix", default="sol")
    l.set_defaults(func=cmd_ladder)

    j = sub.add_parser("join", help="rebuild a solution from split part files")
    j.add_argument("p", type=int)
    j.add_argument("out")
    j.add_argument("parts", nargs="+")
    j.set_defaults(func=cmd_join)

    for name, fn, extra in [("verify", cmd_verify, False),
                            ("stats", cmd_stats, False),
                            ("dice", cmd_dice, True)]:
        c = sub.add_parser(name, help=fn.__doc__ or f"{name} a solution file")
        c.add_argument("p", type=int)
        c.add_argument("file")
        if extra:
            c.add_argument("--out")
        c.set_defaults(func=fn)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()