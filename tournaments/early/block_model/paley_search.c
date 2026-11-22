// paley_search.c
// Compile: gcc -O3 -march=native -shared -fPIC paley_search.c -o libpaley.so

#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <time.h>

// Simple xorshift64* PRNG
static uint64_t rng_state;
static inline uint64_t xrand(void) {
    uint64_t x = rng_state;
    x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
    rng_state = x;
    return x * 2685821657736338717ULL;
}
static inline int xrandint(int n) { return (int)(xrand() % (uint64_t)n); }
static inline double xrandf(void) { return (xrand() >> 11) * (1.0 / 9007199254740992.0); }

// Globals for the current problem (set by solve()).
// rank[i*n + X] = rank of die X in slot i
// slot_wins[X*n + Y] = number of slots where X outranks Y
// target[X*n + Y] = 1 if X should beat Y, 0 otherwise (target[X*n+X] = 0)
static int n, d;
static int *rank;
static int *slot_wins;
static int8_t *target;

static inline int violates(int X, int Y, int half2) {
    // half2 = 2 * (d/2 floor); beats iff 2*slot_wins[X][Y] > d
    if (X == Y) return 0;
    int beats = (2 * slot_wins[X*n + Y] > d);
    return beats != target[X*n + Y];
}

// Try swap of rank[i][X] and rank[i][Y]; returns delta in violation count
// and writes the slot_wins changes to a scratch buffer for possible revert.
// scratch layout: triples (a, b, dv), terminated by a == -1.
static int try_swap(int i, int X, int Y, int *scratch, int *n_changes) {
    int rx = rank[i*n + X], ry = rank[i*n + Y];
    int nc = 0;

    // Collect affected pairs and their dv
    for (int Z = 0; Z < n; Z++) {
        if (Z == X || Z == Y) continue;
        int rz = rank[i*n + Z];
        int old_xz = rx > rz, new_xz = ry > rz;
        if (old_xz != new_xz) {
            int dv = new_xz ? +1 : -1;
            scratch[3*nc+0] = X; scratch[3*nc+1] = Z; scratch[3*nc+2] = dv; nc++;
            scratch[3*nc+0] = Z; scratch[3*nc+1] = X; scratch[3*nc+2] = -dv; nc++;
        }
        int old_yz = ry > rz, new_yz = rx > rz;
        if (old_yz != new_yz) {
            int dv = new_yz ? +1 : -1;
            scratch[3*nc+0] = Y; scratch[3*nc+1] = Z; scratch[3*nc+2] = dv; nc++;
            scratch[3*nc+0] = Z; scratch[3*nc+1] = Y; scratch[3*nc+2] = -dv; nc++;
        }
    }
    // X vs Y always flips
    int old_xy = rx > ry;
    scratch[3*nc+0] = X; scratch[3*nc+1] = Y; scratch[3*nc+2] = old_xy ? -1 : +1; nc++;
    scratch[3*nc+0] = Y; scratch[3*nc+1] = X; scratch[3*nc+2] = old_xy ? +1 : -1; nc++;

    // Count violations among affected pairs BEFORE applying
    int old_v = 0;
    for (int k = 0; k < nc; k++) {
        int a = scratch[3*k], b = scratch[3*k+1];
        old_v += violates(a, b, d);
    }
    // Apply
    for (int k = 0; k < nc; k++) {
        int a = scratch[3*k], b = scratch[3*k+1], dv = scratch[3*k+2];
        slot_wins[a*n + b] += dv;
    }
    int new_v = 0;
    for (int k = 0; k < nc; k++) {
        int a = scratch[3*k], b = scratch[3*k+1];
        new_v += violates(a, b, d);
    }
    *n_changes = nc;
    return new_v - old_v;
}

static void revert_swap(int *scratch, int nc) {
    for (int k = 0; k < nc; k++) {
        int a = scratch[3*k], b = scratch[3*k+1], dv = scratch[3*k+2];
        slot_wins[a*n + b] -= dv;
    }
}

// Public entry point.
// target_in:  flat n*n int8 array
// rank_out:   flat d*n int array (preallocated by caller; receives best rank)
// returns: final cost (0 = success)
int solve(int n_, int d_, const int8_t *target_in, int *rank_out,
          double max_time, uint64_t seed)
{
    n = n_; d = d_;
    rng_state = seed ? seed : 0x9E3779B97F4A7C15ULL;

    target = (int8_t*)malloc(n*n);
    memcpy(target, target_in, n*n);

    rank = (int*)malloc(sizeof(int) * d * n);
    slot_wins = (int*)calloc(n * n, sizeof(int));

    // Initialize: identity in every slot
    for (int i = 0; i < d; i++)
        for (int X = 0; X < n; X++)
            rank[i*n + X] = X;
    for (int i = 0; i < d; i++)
        for (int X = 0; X < n; X++)
            for (int Y = 0; Y < n; Y++)
                if (rank[i*n+X] > rank[i*n+Y])
                    slot_wins[X*n+Y]++;

    int cost = 0;
    for (int X = 0; X < n; X++)
        for (int Y = 0; Y < n; Y++)
            cost += violates(X, Y, d);

    int best_cost = cost;
    int *best_rank = (int*)malloc(sizeof(int) * d * n);
    memcpy(best_rank, rank, sizeof(int) * d * n);

    int *scratch = (int*)malloc(sizeof(int) * 3 * (4*n + 4));

    clock_t start = clock();
    clock_t last_update = clock();
    while ( cost > 0 ) {
        double curr = ( (double) (clock() - start) ) / CLOCKS_PER_SEC;
        if (curr > max_time) break;

        int i = xrandint(d);
        int X = xrandint(n);
        int Y = xrandint(n);
        if (X == Y) continue;

        int nc;
        int delta = try_swap(i, X, Y, scratch, &nc);

        double T = 1.0 - curr / max_time;
        if (T < 0.01) T = 0.01;
        int accept;
        if (delta <= 0) {
            accept = 1;
        } else {
            double p = pow(0.1, (double)delta / T);
            accept = xrandf() < p;
        }
        if (accept) {
            int rx = rank[i*n + X], ry = rank[i*n + Y];
            rank[i*n + X] = ry; rank[i*n + Y] = rx;
            cost += delta;
            if (cost < best_cost) {
                if ((clock() - last_update) > CLOCKS_PER_SEC) {
                    printf("New best cost %d\n", best_cost);
                    last_update = clock();
                }
                best_cost = cost;
                memcpy(best_rank, rank, sizeof(int) * d * n);
            }
        } else {
            revert_swap(scratch, nc);
        }
    }
    printf("\n\n");

    memcpy(rank_out, best_rank, sizeof(int) * d * n);

    free(target); free(rank); free(slot_wins);
    free(best_rank); free(scratch);
    return best_cost;
}