/* Realise the Paley tournament P_p as a k-majority tournament.
 * Vertex a beats b iff a-b is a quadratic residue mod p.
 * An ordering is a permutation of the vertices; a vertex placed later wins.
 * The solution is valid when every pair has margin >= 1. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef struct {
    int p, k;
    signed char *adj;   /* adj[a*p+b] = +1 iff a beats b            */
    int *ord, *pos;     /* k x p: ordering and its inverse          */
    int *margin;        /* p x p, oriented: >= 1 means pair is right */
    int *weight;        /* p x p scratch for the ordering subproblem */
    int *va, *vb;       /* list of currently violated pairs          */
    int nviol;
    long long loss;     /* sum of hinge over all pairs               */
    unsigned rng;
} Solver;

static unsigned rnd(Solver *s) {
    s->rng ^= s->rng << 13; s->rng ^= s->rng >> 17; s->rng ^= s->rng << 5;
    return s->rng;
}
static double rnd01(Solver *s) { return (rnd(s) & 0xffffff) / (double)0x1000000; }
static int hinge(int m)   { return m >= 1 ? 0 : 1 - m; }
static long long slack(int m) { long long d = m - 1; return d > 0 ? d * d : 0; }

static void solver_init(Solver *s, int p, int kcap, unsigned seed) {
    int a, b, x;
    int *qr = calloc(p, sizeof(int));
    s->p = p; s->k = 0; s->rng = seed ? seed : 1;
    for (x = 1; x < p; x++) qr[(int)(((long long)x * x) % p)] = 1;
    s->adj = malloc((size_t)p * p);
    for (a = 0; a < p; a++)
        for (b = 0; b < p; b++) {
            int d = ((a - b) % p + p) % p;
            s->adj[a * p + b] = (a == b) ? 0 : (qr[d] ? 1 : -1);
        }
    s->ord    = malloc(sizeof(int) * (size_t)p * kcap);
    s->pos    = malloc(sizeof(int) * (size_t)p * kcap);
    s->margin = calloc((size_t)p * p, sizeof(int));
    s->weight = calloc((size_t)p * p, sizeof(int));
    s->va = malloc(sizeof(int) * (size_t)p * p / 2);
    s->vb = malloc(sizeof(int) * (size_t)p * p / 2);
    free(qr);
}
static void solver_free(Solver *s) {
    free(s->adj); free(s->ord); free(s->pos); free(s->margin);
    free(s->weight); free(s->va); free(s->vb);
}

static void sync_positions(Solver *s, int t) {
    int i, p = s->p, *o = s->ord + (size_t)t * p, *q = s->pos + (size_t)t * p;
    for (i = 0; i < p; i++) q[o[i]] = i;
}

/* Add (sign=+1) or remove (sign=-1) ordering t from the margin matrix. */
static void apply_ordering(Solver *s, int t, int sign) {
    int a, b, p = s->p, *q = s->pos + (size_t)t * p;
    for (a = 0; a < p; a++) {
        int qa = q[a];
        const signed char *row = s->adj + (size_t)a * p;
        int *m = s->margin + (size_t)a * p;
        for (b = a + 1; b < p; b++) {
            int c = row[b] * (qa > q[b] ? 1 : -1) * sign;
            m[b] += c; s->margin[(size_t)b * p + a] += c;
        }
    }
}
static long long total_loss(const Solver *s) {
    int a, b, p = s->p; long long L = 0;
    for (a = 0; a < p; a++) {
        const int *m = s->margin + (size_t)a * p;
        for (b = a + 1; b < p; b++) L += hinge(m[b]);
    }
    return L;
}
static long long total_margin(const Solver *s) {
    int a, b, p = s->p; long long M = 0;
    for (a = 0; a < p; a++) {
        const int *m = s->margin + (size_t)a * p;
        for (b = a + 1; b < p; b++) M += m[b];
    }
    return M;
}
static void collect_violations(Solver *s) {
    int a, b, p = s->p;
    s->nviol = 0;
    for (a = 0; a < p; a++) {
        const int *m = s->margin + (size_t)a * p;
        for (b = a + 1; b < p; b++)
            if (m[b] < 1) { s->va[s->nviol] = a; s->vb[s->nviol] = b; s->nviol++; }
    }
}

/* Insertion local search on `weight`, maximising sum of weight[later][earlier]. */
static void refine_ordering(Solver *s, int t, int max_passes) {
    int p = s->p, pass, v, q, dest;
    int *o = s->ord + (size_t)t * p, *ps = s->pos + (size_t)t * p;
    for (pass = 0; pass < max_passes; pass++) {
        int improved = 0;
        for (v = 0; v < p; v++) {
            long long best = 0, cum = 0;
            const int *wv = s->weight + (size_t)v * p;
            int i = ps[v]; dest = i;
            for (q = i + 1; q < p; q++) { cum += 2LL * wv[o[q]]; if (cum > best) { best = cum; dest = q; } }
            cum = 0;
            for (q = i - 1; q >= 0; q--) { cum += 2LL * s->weight[(size_t)o[q] * p + v];
                                           if (cum > best) { best = cum; dest = q; } }
            if (dest == i) continue;
            if (dest > i) for (q = i; q < dest; q++) { o[q] = o[q + 1]; ps[o[q]] = q; }
            else          for (q = i; q > dest; q--) { o[q] = o[q - 1]; ps[o[q]] = q; }
            o[dest] = v; ps[v] = dest; improved = 1;
        }
        if (!improved) break;
    }
}

/* A near-optimal feedback-arc-set ordering from a random start.
 * refine_ordering already maximises agreement in the later-beats-earlier
 * convention, so the result needs no reversal. */
static void seed_ordering(Solver *s, int t) {
    int p = s->p, i, j, a, b, *o = s->ord + (size_t)t * p;
    for (a = 0; a < p; a++)
        for (b = 0; b < p; b++) s->weight[(size_t)a * p + b] = s->adj[(size_t)a * p + b];
    for (i = 0; i < p; i++) o[i] = i;
    for (i = p - 1; i > 0; i--) { j = rnd(s) % (i + 1); a = o[i]; o[i] = o[j]; o[j] = a; }
    sync_positions(s, t);
    refine_ordering(s, t, p > 600 ? 25 : 200);
}

/* Re-optimise each ordering against the others. Weights are boosting-style:
 * strongly positive on deficient pairs, mildly negative on over-satisfied ones
 * so that surplus margin is handed back. */
static void coordinate_sweep(Solver *s, double beta, double give_back) {
    int p = s->p, r, a, b, m, table[31];
    for (m = -14; m <= 16; m++) {
        double x = (m >= 2) ? -4.0 * give_back * (m - 1) * 64.0 : 64.0 * pow(beta, (double)m);
        int w = (int)x;
        if (m < 2 && w < 1) w = 1;
        if (w >  2000000) w =  2000000;
        if (w < -2000000) w = -2000000;
        table[m + 14] = w;
    }
    for (r = 0; r < s->k; r++) {
        int t = rnd(s) % s->k;
        apply_ordering(s, t, -1);
        for (a = 0; a < p; a++) {
            const int *mr = s->margin + (size_t)a * p;
            const signed char *ar = s->adj + (size_t)a * p;
            int *wr = s->weight + (size_t)a * p;
            for (b = a + 1; b < p; b++) {
                int mm = mr[b] < -14 ? -14 : (mr[b] > 16 ? 16 : mr[b]);
                int w = table[mm + 14] * ar[b];
                wr[b] = w; s->weight[(size_t)b * p + a] = -w;
            }
        }
        refine_ordering(s, t, p > 600 ? 8 : 30);
        apply_ordering(s, t, +1);
    }
}

static long long move_delta(const Solver *s, int t, int v, int from, int to) {
    int p = s->p, q; long long d = 0;
    const int *o = s->ord + (size_t)t * p, *m = s->margin + (size_t)v * p;
    const signed char *a = s->adj + (size_t)v * p;
    if (to > from) for (q = from + 1; q <= to; q++) d += hinge(m[o[q]] + 2 * a[o[q]]) - hinge(m[o[q]]);
    else           for (q = to; q < from; q++)      d += hinge(m[o[q]] - 2 * a[o[q]]) - hinge(m[o[q]]);
    return d;
}
static void move_apply(Solver *s, int t, int v, int from, int to) {
    int p = s->p, q, *o = s->ord + (size_t)t * p, *ps = s->pos + (size_t)t * p;
    if (to > from)
        for (q = from + 1; q <= to; q++) { int u = o[q];
            s->margin[(size_t)v * p + u] += 2 * s->adj[(size_t)v * p + u];
            s->margin[(size_t)u * p + v]  = s->margin[(size_t)v * p + u];
            o[q - 1] = u; ps[u] = q - 1; }
    else
        for (q = from - 1; q >= to; q--) { int u = o[q];
            s->margin[(size_t)v * p + u] -= 2 * s->adj[(size_t)v * p + u];
            s->margin[(size_t)u * p + v]  = s->margin[(size_t)v * p + u];
            o[q + 1] = u; ps[u] = q + 1; }
    o[to] = v; ps[v] = to;
}
/* Cheapest position for v within ordering t, found by one prefix scan. */
static long long best_position(const Solver *s, int t, int v, int *dest) {
    int p = s->p, q, i = s->pos[(size_t)t * p + v];
    const int *o = s->ord + (size_t)t * p, *m = s->margin + (size_t)v * p;
    const signed char *a = s->adj + (size_t)v * p;
    long long cum = 0, best = 0;
    *dest = i;
    for (q = i + 1; q < p; q++) { cum += hinge(m[o[q]] + 2 * a[o[q]]) - hinge(m[o[q]]);
                                  if (cum < best) { best = cum; *dest = q; } }
    cum = 0;
    for (q = i - 1; q >= 0; q--) { cum += hinge(m[o[q]] - 2 * a[o[q]]) - hinge(m[o[q]]);
                                   if (cum < best) { best = cum; *dest = q; } }
    return best;
}

/* Min-conflicts annealing: sample a broken pair, move one of its endpoints
 * inside an ordering that gets that pair wrong. */
static void anneal(Solver *s, double seconds, double t_hot, double t_cold, int greedy_pct) {
    clock_t start = clock();
    int p = s->p;
    while ((double)(clock() - start) / CLOCKS_PER_SEC < seconds && s->loss > 0) {
        double frac = (double)(clock() - start) / CLOCKS_PER_SEC / seconds;
        double temp = t_hot * pow(t_cold / t_hot, frac);
        long long budget, it;
        collect_violations(s);
        if (s->nviol == 0) return;
        budget = 4LL * s->nviol + 300;
        if (budget < 30000) budget = 30000;
        for (it = 0; it < budget && s->loss > 0; it++) {
            int v, t = -1, i, to, roll, tries;
            if (rnd(s) % 8) {
                int r = rnd(s) % s->nviol, a = s->va[r], b = s->vb[r];
                v = (rnd(s) & 1) ? a : b;
                for (tries = 0; tries < 24; tries++) {
                    int c = rnd(s) % s->k;
                    if (s->adj[(size_t)a * p + b] *
                        (s->pos[(size_t)c * p + a] > s->pos[(size_t)c * p + b] ? 1 : -1) == -1) { t = c; break; }
                }
                if (t < 0) t = rnd(s) % s->k;
            } else { v = rnd(s) % p; t = rnd(s) % s->k; }
            i = s->pos[(size_t)t * p + v];
            roll = rnd(s) % 100;
            if (roll < greedy_pct) {
                long long d = best_position(s, t, v, &to);
                if (to != i) { move_apply(s, t, v, i, to); s->loss += d; }
            } else {
                long long d;
                if (roll < greedy_pct + 8) to = rnd(s) % p;
                else {
                    to = i + (int)(rnd(s) % 21) - 10;
                    if (to < 0) to = 0;
                    if (to >= p) to = p - 1;
                }
                if (to == i) continue;
                d = move_delta(s, t, v, i, to);
                if (d <= 0 || exp(-(double)d / temp) > rnd01(s)) { move_apply(s, t, v, i, to); s->loss += d; }
            }
        }
    }
}

/* Squeeze surplus margin toward 1 without ever breaking feasibility. */
static void compact(Solver *s, double seconds) {
    clock_t start = clock();
    int p = s->p;
    while ((double)(clock() - start) / CLOCKS_PER_SEC < seconds) {
        int it;
        for (it = 0; it < 50000; it++) {
            int t = rnd(s) % s->k, v = rnd(s) % p, i = s->pos[(size_t)t * p + v];
            int to = i + (int)(rnd(s) % 15) - 7, q, ok = 1;
            const int *o = s->ord + (size_t)t * p;
            long long d = 0;
            if (to < 0) to = 0;
            if (to >= p) to = p - 1;
            if (to == i) continue;
            if (to > i) for (q = i + 1; q <= to; q++) { int u = o[q], m = s->margin[(size_t)v * p + u];
                            int n = m + 2 * s->adj[(size_t)v * p + u];
                            if (n < 1) { ok = 0; break; } d += slack(n) - slack(m); }
            else        for (q = to; q < i; q++) { int u = o[q], m = s->margin[(size_t)v * p + u];
                            int n = m - 2 * s->adj[(size_t)v * p + u];
                            if (n < 1) { ok = 0; break; } d += slack(n) - slack(m); }
            if (ok && d <= 0) move_apply(s, t, v, i, to);
        }
    }
}

/* Discard one ordering, chosen at random among the least damaging. */
static void drop_ordering(Solver *s) {
    int p = s->p, t, n = 0, best = -1;
    long long *cost = malloc(sizeof(long long) * s->k);
    int *cand = malloc(sizeof(int) * s->k);
    for (t = 0; t < s->k; t++) {
        apply_ordering(s, t, -1); cost[t] = total_loss(s); apply_ordering(s, t, +1);
        if (best < 0 || cost[t] < cost[best]) best = t;
    }
    for (t = 0; t < s->k; t++) if (cost[t] <= cost[best] + cost[best] / 20 + 2) cand[n++] = t;
    t = cand[rnd(s) % n];
    apply_ordering(s, t, -1);
    memmove(s->ord + (size_t)t * p, s->ord + (size_t)(t + 1) * p, sizeof(int) * (size_t)p * (s->k - t - 1));
    s->k--;
    for (t = 0; t < s->k; t++) sync_positions(s, t);
    free(cost); free(cand);
}
static void write_solution(const Solver *s, const char *prefix) {
    char name[256]; int t, i;
    FILE *f;
    snprintf(name, sizeof name, "%s_%d_%d.txt", prefix, s->p, s->k);
    f = fopen(name, "w");
    for (t = 0; t < s->k; t++) {
        for (i = 0; i < s->p; i++) fprintf(f, "%d ", s->ord[(size_t)t * s->p + i]);
        fputc('\n', f);
    }
    fclose(f);
    printf("SOLVED k=%d file=%s\n", s->k, name); fflush(stdout);
}
static int load_solution(Solver *s, const char *path) {
    FILE *f = fopen(path, "r"); int rows = 0, i;
    if (!f) return 0;
    for (;;) {
        for (i = 0; i < s->p; i++)
            if (fscanf(f, "%d", &s->ord[(size_t)rows * s->p + i]) != 1) { fclose(f); return rows; }
        rows++;
    }
}

/* Search at the current k; on success shrink k by two and continue. */
static void run(Solver *s, double seconds, int kmin, const char *prefix) {
    size_t bytes = sizeof(int) * (size_t)s->p * s->k;
    int *snapshot = malloc(bytes);
    long long best;
    clock_t start = clock();
    int round = 0, t;
    s->loss = total_loss(s); best = s->loss;
    memcpy(snapshot, s->ord, bytes);
    printf("START p=%d k=%d loss=%lld\n", s->p, s->k, s->loss); fflush(stdout);
    while ((double)(clock() - start) / CLOCKS_PER_SEC < seconds) {
        if (s->loss == 0) {
            compact(s, seconds / 40.0);
            s->loss = total_loss(s);
            if (s->loss > 0) continue;
            printf("WASTE k=%d value=%.3f seconds=%.1f\n", s->k,
                   (double)total_margin(s) / ((double)s->p * (s->p - 1) / 2),
                   (double)(clock() - start) / CLOCKS_PER_SEC);
            write_solution(s, prefix);
            if (s->k <= kmin + 1) break;
            drop_ordering(s); drop_ordering(s);
            s->loss = total_loss(s); best = s->loss; round = 0;
            bytes = sizeof(int) * (size_t)s->p * s->k;
            memcpy(snapshot, s->ord, bytes);
            continue;
        }
        if (round < 10) coordinate_sweep(s, 0.50 + 0.12 * (round % 3), 0.05);
        s->loss = total_loss(s);
        anneal(s, seconds / 40.0, round < 10 ? 1.0 : 0.5, 0.03, round < 10 ? 25 : 12);
        s->loss = total_loss(s); round++;
        if (s->loss < best) { best = s->loss; memcpy(snapshot, s->ord, bytes); }
        else if (rnd(s) % 3) {
            memcpy(s->ord, snapshot, bytes);
            memset(s->margin, 0, sizeof(int) * (size_t)s->p * s->p);
            for (t = 0; t < s->k; t++) { sync_positions(s, t); apply_ordering(s, t, +1); }
            s->loss = total_loss(s);
        }
    }
    printf("FINAL k=%d loss=%lld best=%lld\n", s->k, s->loss, best);
    free(snapshot);
}

static const char *opt(int argc, char **argv, const char *key, const char *def) {
    int i;
    for (i = 1; i + 1 < argc; i += 2) if (!strcmp(argv[i], key)) return argv[i + 1];
    return def;
}
int main(int argc, char **argv) {
    Solver s;
    int p = atoi(opt(argc, argv, "--p", "67"));
    int k = atoi(opt(argc, argv, "--k", "15"));
    double seconds = atof(opt(argc, argv, "--seconds", "60"));
    unsigned seed = (unsigned)atoi(opt(argc, argv, "--seed", "1"));
    int kmin = atoi(opt(argc, argv, "--kmin", "3"));
    const char *init = opt(argc, argv, "--init", NULL);
    const char *prefix = opt(argc, argv, "--prefix", "sol");
    int t, rows = 0;
    solver_init(&s, p, k + 4096, seed);
    if (init) {
        rows = load_solution(&s, init);
        if (rows == 0) { fprintf(stderr, "cannot read %s\n", init); return 1; }
        s.k = rows;
        for (t = 0; t < s.k; t++) { sync_positions(&s, t); apply_ordering(&s, t, +1); }
        while (s.k > k) drop_ordering(&s);
    } else {
        s.k = k;
        for (t = 0; t < s.k; t++) { seed_ordering(&s, t); apply_ordering(&s, t, +1); }
    }
    run(&s, seconds, kmin, prefix);
    solver_free(&s);
    return 0;
}