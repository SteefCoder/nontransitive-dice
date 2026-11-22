# CLAUDE_SUMMARY

An overview of this repository, written by Claude when the GitHub repo and the
local working files were merged (Nov 2026). It covers what is where and how the
pieces relate. It is not a polished README; most code here is proof-of-concept
research code, and many files are dead ends or half-finished on purpose.

The project has two parts:

1. **`tournaments/`**: realizing tournaments, mostly **Paley tournaments
   P_p**, with a set of dice using as few faces per die as possible. This is
   the "proper research" part (it builds on Bednay–Bozoki, Angel–Davis and
   Purcell). It is motivated by the **n-player nontransitive dice** problem.
2. **`general-dice/`**: finding nontransitive dice with extra properties
   (maximum win ratio, equal means, few repeated values, primes only, ...),
   mostly by **ILP with Gurobi**.

---

## Layout

```
CLAUDE_SUMMARY.md       this file
README.md               placeholder (to be written)
requirements.txt        gurobipy, numpy, python-sat, tqdm (see "Dependencies")
tools/                  Nov 2026, WIP: fresh numpy DiceSet + Tournament classes
notes/
  message.md            draft mail to Nick (Jun 30). Best short summary of part 1
  rules.md              instructions for an AI assistant on how to answer
  pulp.md               unfinished draft of a PuLP API issue (unrelated)

tournaments/                    PART 1  (run everything from this folder)
  diceset.py                    DiceSet used by n-player/ (blocks, to/from file)
  n-player/                     main, committed line of work (Jun 29 onward)
    helpers.py                  Paley tournament, QRs, verify, subtournaments
    verify.py                   numpy verifier: `python n-player/verify.py FILE`
    angel_davis.py              Angel–Davis construction (n faces, any tournament)
    bednay_bozoki.py            Bednay–Bozoki extension step + "mixed" P_67/331/1163
    bb_direct.py                direct constructions for p = 8k+7 and p = 8k+3
    sat_solver.py               block-model SAT (CaDiCaL via python-sat)
    full_sat.py                 full SAT model (no block structure)
    linalg.py                   Nov: tournament from few linear orders (bounds,
                                McGarvey, Graver descent, exact ILP; needs scipy)
    linear_algebra.py           Nov: min-norm preimage of the margin map (PoC)
    fas_anneal/                 Aug: simulated annealing over k orderings (C)
      solver.c, paley.py        paley.py compiles solver.c on demand and drives it
      new_solver.c              Nov: unfinished generalization to any tournament
      sol_P_K.txt               K orderings for P_P (one permutation per line)
      paley_PPPP_K.txt          the same as dice (P dice, K faces)
      dice_PPPP_K.txt           a few dice files of the same kind
    results/                    all found dice sets (see naming below)
    best_results/               curated copy of the current best per p
  early/                        local experiments from Jun 16 to Jul 9, before n-player/
    block_model/                searches inside the block model
      cluade_v2.py              block-rank SAT, writes DIMACS -> paley_block_19_d5.sol
      cluade_v3.py              SAT with lazily added transitivity constraints
      cluade_ortools.py         SAT (pysat, despite the name)
      ilpsolver.py              Gurobi ILP of the block model
      satsolver.py              ILP warm-started from a C heuristic (hybrid)
      paley_driver.py + paley_search.c   C annealer via ctypes (builds libpaley.so)
      grb_full.py, grb_iterative.py, sat_iterative.py   Gurobi: full / slot-by-slot
      tries/                    backtracking in C (paley_backtrack.c, backtrack_v2.c
                                + paley.py driver), iterative ILPs, by_wins.py
                                (algebraic SAT: die i+1 = pi(die i)) -> paley_alg_perm_7_d3.sol
    constructions/
      bednay_bozoki.py          older local fork (extend_by_11, 34-dice seed for P_331)
      claude.py                 extension by 5 dice (Bednay–Bozoki lemma) for P_67
      n_player_intransitive.py  first n-player experiments (li_dice etc.)
      extend.py                 SAT extender: add dice + faces to an existing set
      bilevel_balanced.py, bilevel_gen.py   biclique decomposition of P_p -> dice
      greedy.py, greedy.c, check_intransitive.c, my_own.py   empty stubs
    extension_gadgets/          search for "witness" sets: k permutations of n
                                points such that every subset S has a die beating
                                exactly S. Its output (n_11_f_5.txt) is
                                EXTEND_SET_11 in n-player/bednay_bozoki.py
      new_problem.py/.c, new_problem_opt(2).c, new_problem_v2.c, climber.c,
      new_sat.py, sat_v3.py, n_11_f_5.txt
    results/                    early solutions (P_21, P_31, P_67, 37-dice sub of
                                P_67, four_player_dice.txt). Not duplicated elsewhere

general-dice/                   PART 2
  diceset.py                    DiceSet with count_wins / count_win_ratios (Jul 1),
                                which both ILP folders below need
  ilp_solver/                   refactored framework (Jun 29), smaller
    core/core.py, core/types.py SolverBase + lazy_var/objective/constraint decorators
    solvers/general.py          GeneralDiceSolver (cyclic nontransitive set)
    example/d6.py
  ilp_solver_legacy/            the pre-refactor framework (Jun 11–28); more features
    solvers/core.py             DiceSolver + lazy decorators
    solvers/general.py          ~2x the objectives/constraints of the refactor
    solvers/continuous.py       distinct values with fractional probabilities
    solvers/max_two.py          distinct values with integer multiplicities
    solvers/three_player.py     all-pairs / 3- and 4-player ILP (QR-based)
    solvers/tournament.py       ILP: dice for a given tournament (+ block version),
                                and ILP to *find* n-player tournaments
    example/                    d6, cont, max_two, tester, three, tune_three, wow,
                                tournament, construct (drivers for the above)
  prototype/                    first standalone Gurobi scripts (Jun 3–10)
    main.py, solvers.py         solve_by_distinct, solve_combination (primes, equal mean)
    niceify.py                  post-process a set to small values / equal means
    dicesolver.py, dicesolver_v2.py   first class-based solver, later became the framework
    diceset.py, primes.py, utils.py
  experiments/
    dice_factorize.py           sympy: dice as generating polynomials
```

---

## Part 1: realizing Paley tournaments

**Problem.** A tournament T on n vertices is *realized* by n dice if die X
beats die Y (P > 1/2) exactly when X → Y in T. The goal is to use as few faces
per die as possible. The Paley tournament P_p (p prime, p ≡ 3 mod 4: a beats b
iff a − b is a quadratic residue) has the property that every small set of dice
is beaten by some other die. That property is what makes **n-player**
nontransitive dice: P_19 gives 4 players, P_67 gives 5, P_331 gives 6 and
P_1163 gives 7. These are the "minimum number of dice" cases, all with
p = 8k+3.

**Block model.** Almost all code uses this model. Face *i* of every die lies in
its own value range (block/slot *i*), so a die is one rank per slot, and the
whole set is *k* permutations of the dice. X beats Y iff X outranks Y in a
majority of slots. Realizing T with k faces is therefore the same as writing T
as a **k-majority tournament** of k linear orders. The FAS annealer, linalg.py
and the `sol_*` files work in this language.

**Approaches, in chronological order**
- Known constructions: Bednay–Bozoki 2013 ((p−1)/2 faces for p = 8k+7, plus
  extending by a few dice with a few extra faces), and Angel–Davis 2016/17
  (n faces for any tournament). See `n-player/angel_davis.py` and
  `n-player/bednay_bozoki.py`.
- SAT in the style of Purcell 2023: `early/block_model/` first, then
  `n-player/sat_solver.py` and `full_sat.py`. These work up to about 40 dice.
- **Mixed**: SAT on a subtournament, then extension with the Bednay–Bozoki
  step (`*_mixed.txt`, seeds `p_67_sub_37/42`, `p_1163_sub_74`).
- Direct construction for p = 8k+3 (`bb_direct.py`, `*_newbednay.txt`),
  giving (p+3)/2 faces.
- FAS simulated annealing (Aug): by far the best results so far.

**Best known results** (from `best_results/`, faces per die):

| p | 19 | 23 | 31 | 43 | 47 | 59 | 67 | 71 | 79 | 83 | 103 | 331 | 1163 |
|---|----|----|----|----|----|----|----|----|----|----|-----|-----|------|
| faces | 5 (SAT) | 7 | 7 | 9 | 11 | 13 | 13 | 15 | 15 | 17 | 19 | 53 | 185 |

All are FAS unless marked. `fas_anneal/sol_163_33.txt` (P_163, 33 orderings)
checks out as valid but has no copy in `best_results/`.
`fas_anneal/sol_19_5.txt` is **not** a valid realization (P_19 with 5 faces
comes from SAT).

**Results file naming** (`n-player/results`, `best_results`):
`p_{p}_f_{faces}_{method}.txt` or `p_{p}_sub_{size}_f_{faces}_{method}.txt`
for a subtournament on the first `size` vertices. One die per line. The method
is one of `sat`, `fullsat`, `bednay`, `newbednay`, `angel`, `mixed` or `fas`.
The older `early/results/` use `die i: [...]` lines.

**References** (full citations in `notes/message.md`): Bednay & Bozóki 2013;
Angel & Davis, J. Combin. Des. 2017; Purcell, Amer. Math. Monthly 2023.

## Part 2: general nontransitive dice (ILP)

The framework builds a Gurobi model lazily. Variables, objectives and
constraints are declared with `@lazy_var / @lazy_objective / @lazy_constraint`
and dependencies, so only what the requested objectives and constraints need is
built. Typical use (see the `example/` folders):

```python
solver = GeneralDiceSolver(faces=6, dice=4)
solver.add_objective("max_min_ratio")
solver.add_constraint("max_repeat", 1)
with solver.build():
    dice = solver.solve()
```

`ilp_solver_legacy/solvers/general.py` has the full menu:
- objectives: max_min_ratio, max_avg_ratio, min_max_value, min_max_repeats,
  min_avg_repeats, max_winloss, twice_max_min_ratio
- constraints: equal_mean, balanced, no_skip_values, use_once, use_n_times,
  use_all_n_times, max_repeat, is_nontransitive, reverse_nontransitive, start

The refactored `ilp_solver/` keeps only a subset of these.

## Running things / import roots

Nothing is installed as a package. Imports resolve relative to the working
directory:
- **Part 1:** `cd tournaments && python -m n-player.sat_solver` (or
  `bb_direct`, `bednay_bozoki`, ...). Scripts import `diceset` from there and
  write to `n-player/results/...`. `fas_anneal/paley.py` runs from anywhere.
- **ILP refactor:** `cd general-dice/ilp_solver && PYTHONPATH=.. python -m example.d6`
- **ILP legacy:** `cd general-dice/ilp_solver_legacy && PYTHONPATH=.. python -m example.d6`
- **Prototype:** `cd general-dice/prototype && python main.py`
- `early/` scripts are mostly self-contained. The few that import `diceset`
  need `PYTHONPATH=tournaments`. The C files need compiling first (the compile
  line is in the header comment where there is one).

Dependencies not listed in `requirements.txt`: `scipy` (linalg.py), `sympy`
(dice_factorize.py), `networkx` and `matplotlib` (legacy three/tournament
examples), `gmpy2` (tools/), and a Gurobi licence for everything ILP.

## Known loose ends (left as-is)

- `angel_davis.py` uses `from helpers import ...` (absolute), while the other
  n-player files use relative imports. Under `python -m` it, and
  `bednay_bozoki.py` which imports it, need `n-player/` on `PYTHONPATH` as well.
- `general-dice/prototype/utils.py` does not define `vardict`, which
  `solvers.py` and `niceify.py` import.
- `tools/` is not used by anything yet. It uses bare `from tournament import`.
- Stubs and unfinished files: `new_solver.c`, `new_problem_v2.c` (does not
  compile), `my_own.py`, `greedy.*`, `check_intransitive.c`.
- `.gitignore` covers `*.so` but not compiled C executables (`climber`,
  `fas_anneal/solver`, ...).

## What was removed in the merge

Only files that can be regenerated, duplicates or empty files were removed:
- compiled binaries: `climber`, `new_problem`, `new_problem_opt(2)`,
  `libpaley.so`, `tries/libpaley_bt.so`, and `n-player/fas_anneal/solver`
  (paley.py rebuilds it)
- `__pycache__/`
- the DIMACS inputs `paley_alg_perm_7_d3.cnf` (22 MB) and
  `paley_block_19_d5.cnf` (their `.sol` outputs are kept), and the Gurobi
  export `model.lp`
- `tuned.prm` and `best-params.prm` (Gurobi tuning output that contained the
  licence ID)
- duplicates: the local copies of `README.md` and `.gitignore`, the older
  local `requirements.txt` (still in git history), and `test_result.txt`
  (identical to `n-player/results/p_331_f_281_mixed.txt`)
- empty files: a second `tuned.prm` and `verify.c`
