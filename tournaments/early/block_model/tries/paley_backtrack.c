// paley_backtrack.c
// Block-model backtracker for realizing a tournament with d-faced dice.
// Compile: gcc -O3 -march=native -shared -fPIC paley_backtrack.c -o libpaley_bt.so

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int n;            // number of dice
static int d;            // faces per die
static int8_t *target;   // n*n target tournament
static int *rank;        // rank[f*n + X] = X's rank in slot f, or -1 if unset
static int *slot_used;   // slot_used[f*n + r] = die assigned rank r in slot f, or -1
static int *wins;        // wins[X*n + Y] = current slot-wins of X over Y
static int *remaining_slots;  // slots still to be filled (counts down)
static int *required_sum;     // required sum of ranks for each die
static int *partial_sum;      // partial_sum[X] = sum of X's ranks so far

static long backtrack_calls;

// Check: given current state, can arc X -> Y still be satisfied?
// X must beat Y, so wins[X][Y] must reach > d/2 over remaining slots.
static inline int arc_feasible(int X, int Y, int slots_left) {
    int needed = d / 2 + 1;
    int current = wins[X*n + Y];
    int max_possible = current + slots_left;
    return max_possible >= needed;
}

// Check: given current state, can the "X loses to Y" requirement still hold?
// Equivalently, "Y beats X" must be feasible.
// (Both are checked symmetrically.)

// Check feasibility of all arcs given remaining slots.
static int feasible(int slots_left) {
    int half = d / 2;
    for (int X = 0; X < n; X++) {
        for (int Y = 0; Y < n; Y++) {
            if (X == Y) continue;
            int w = wins[X*n + Y];
            if (target[X*n + Y]) {
                // X must beat Y: need w + slots_left > half
                if (w + slots_left <= half) return 0;
            } else {
                // X must NOT beat Y: need w <= half  (since remaining slots could push it higher,
                // but if w already > half, we've lost)
                if (w > half) return 0;
            }
        }
    }
    return 1;
}

// After fully filling a slot, update wins from that slot's ranks.
static void apply_slot(int f) {
    for (int X = 0; X < n; X++) {
        for (int Y = 0; Y < n; Y++) {
            if (X == Y) continue;
            if (rank[f*n + X] > rank[f*n + Y]) {
                wins[X*n + Y]++;
            }
        }
    }
}

// Undo the wins update for slot f.
static void unapply_slot(int f) {
    for (int X = 0; X < n; X++) {
        for (int Y = 0; Y < n; Y++) {
            if (X == Y) continue;
            if (rank[f*n + X] > rank[f*n + Y]) {
                wins[X*n + Y]--;
            }
        }
    }
}

// Try to fill positions [pos..n-1] of slot f.
// At each position, we decide which die gets rank `pos`.
static int fill_slot(int f, int pos, int slots_left) {
    backtrack_calls++;
    if (pos == n) {
        // Slot complete. Apply its win contributions.
        apply_slot(f);
        // Check feasibility of remaining work.
        int result = 0;
        if (feasible(slots_left - 1)) {
            if (f == d - 1) {
                // All slots filled. Final check: every arc satisfied?
                for (int X = 0; X < n && !result; X++) {
                    for (int Y = 0; Y < n; Y++) {
                        if (X == Y) continue;
                        int beats = wins[X*n + Y] > d / 2;
                        if (beats != target[X*n + Y]) goto fail;
                    }
                }
                result = 1;
                fail:;
            } else {
                result = fill_slot(f + 1, 0, slots_left - 1);
            }
        }
        unapply_slot(f);
        return result;
    }

    // Pick a die for rank `pos` in slot f.
    for (int X = 0; X < n; X++) {
        if (rank[f*n + X] != -1) continue;  // X already placed in this slot

        // Sum constraint: X's partial sum + remaining ranks must equal required_sum[X].
        // After this assignment, X has used (f - first_slot_with_X_set + 1) slots... actually
        // we know X gets one rank per slot, so after this f+1-th slot, X has (f+1) ranks set.
        // partial_sum[X] becomes partial_sum[X] + pos.
        // Remaining slots for X: d - f - 1.
        // Min remaining sum: 0 + 1 + ... + (d-f-2) (but constrained by available ranks per slot).
        // Max remaining sum: (n-1) + (n-2) + ... + (n - d + f + 1).
        // Simpler bounds: 0 to (n-1)*(d-f-1).
        int new_partial = partial_sum[X] + pos;
        int min_future = 0;
        int max_future = (n - 1) * (d - f - 1);
        if (new_partial + min_future > required_sum[X]) continue;
        if (new_partial + max_future < required_sum[X]) continue;

        // Tentative placement.
        rank[f*n + X] = pos;
        slot_used[f*n + pos] = X;
        partial_sum[X] = new_partial;

        if (fill_slot(f, pos + 1, slots_left)) return 1;

        // Undo.
        rank[f*n + X] = -1;
        slot_used[f*n + pos] = -1;
        partial_sum[X] = new_partial - pos;
    }
    return 0;
}

// Public entry point.
// target_in : n*n int8 array, target[X*n+Y] = 1 if X must beat Y
// rank_out  : d*n int array, receives solution rank matrix if found
// returns: 1 if solved, 0 if not
int solve(int n_in, int d_in, const int8_t *target_in, int *rank_out, long *calls_out) {
    n = n_in; d = d_in;
    target = (int8_t*)malloc(n*n);
    memcpy(target, target_in, n*n);
    for (int X = 0; X < n; X++) target[X*n + X] = 0;

    rank = (int*)malloc(sizeof(int) * d * n);
    slot_used = (int*)malloc(sizeof(int) * d * n);
    wins = (int*)calloc(n * n, sizeof(int));
    partial_sum = (int*)calloc(n, sizeof(int));
    required_sum = (int*)malloc(sizeof(int) * n);
    for (int X = 0; X < n; X++) {
        // Each die's total rank sum: in a permutation per slot, every die gets exactly
        // d ranks. The total across all dice is d * (0+1+...+(n-1)) = d*n*(n-1)/2.
        // Spread equally: each die gets d*(n-1)/2.
        // This requires d*(n-1) to be even; if not, equal-sum is impossible.
        required_sum[X] = d * (n - 1) / 2;
    }
    int sum_feasible = (d * (n - 1)) % 2 == 0;

    for (int i = 0; i < d * n; i++) { rank[i] = -1; slot_used[i] = -1; }

    // Initial fixing: rank[0][i] = i for i in 0..n-1.
    // This pins slot 0 to the identity permutation, breaking the slot-0 relabeling symmetry.
    // for (int i = 0; i < n; i++) {
    //     rank[0 * n + i] = i;
    //     slot_used[0 * n + i] = i;
    //     partial_sum[i] += i;
    // }

    backtrack_calls = 0;
    int found = 0;
    if (sum_feasible) {
        // Apply slot 0's win contributions.
        // apply_slot(0);
        // if (feasible(d - 1)) {
        //     if (d == 1) {
        //         // Single slot; check completion directly.
        //         found = 1;
        //         for (int X = 0; X < n && found; X++) {
        //             for (int Y = 0; Y < n; Y++) {
        //                 if (X == Y) continue;
        //                 int beats = wins[X*n + Y] > d / 2;
        //                 if (beats != target[X*n + Y]) { found = 0; break; }
        //             }
        //         }
        //     } else {
        //         found = fill_slot(1, 0, d - 1);
        //     }
        // }
        // unapply_slot(0);
        found = fill_slot(0, 0, d);
    }

    // int oskar_ranks[3][7] = {
    //     {0, 5, 3, 1, 6, 4, 2},  // slot 0 ranks for dice 0..6
    //     {4, 0, 3, 6, 2, 5, 1},  // slot 1
    //     {5, 4, 3, 2, 1, 0, 6},  // slot 2
    // };
    // for (int i = 0; i < 3; ++i) {
    //     for (int j = 0; j < 7; ++j) {
    //         rank[7 * i + j] = oskar_ranks[i][j];
    //     }
    // }
    // found = 1;

    if (found) {
        memcpy(rank_out, rank, sizeof(int) * d * n);
    }
    if (calls_out) *calls_out = backtrack_calls;

    free(target); free(rank); free(slot_used);
    free(wins); free(partial_sum); free(required_sum);
    return found;
}