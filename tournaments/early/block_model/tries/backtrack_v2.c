// paley_backtrack.c
// Block-model backtracker with incremental pruning.
// Compile: gcc -O3 -march=native -shared -fPIC paley_backtrack.c -o libpaley_bt.so

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int n, d;
static int8_t *target;
static int *rank;          // rank[f*n + X] = X's rank in slot f, or -1
static int *slot_used;     // slot_used[f*n + r] = die at rank r in slot f, or -1
static int *wins;          // wins[X*n + Y] = slot-wins of X over Y so far
static int *required_sum;
static int *partial_sum;
static int *placed_in_slot;  // placed_in_slot[f] = bitmask-equivalent count; actually just track explicitly
static int8_t *die_placed;   // die_placed[f*n + X] = 1 if die X is placed in slot f

static long backtrack_calls;

// Threshold: X beats Y iff wins[X*n+Y] > half_d, i.e., wins >= half_d + 1.
static int half_d;
static int win_threshold;  // half_d + 1

// After placing die X at rank `pos` in slot f, update wins against all dice already
// placed in this slot, and check feasibility for all affected arcs.
// Returns 1 if all arcs remain feasible, 0 if pruned.
static int place_and_check(int f, int X, int pos) {
    int slots_remaining_after = d - f - 1;

    // Update wins against dice already placed in this slot.
    for (int Y = 0; Y < n; Y++) {
        if (Y == X) continue;
        if (!die_placed[f*n + Y]) continue;
        int r_Y = rank[f*n + Y];
        if (pos > r_Y) wins[X*n + Y]++;
        else           wins[Y*n + X]++;
    }

    // Check feasibility for all pairs involving X.
    // For arcs X->Y (target=1): need final wins[X][Y] >= win_threshold.
    //   Max future contribution: slots_remaining_after + (1 if Y unplaced in this slot, else 0).
    // For arcs Y->X (target=1): similar with roles swapped.
    // For arcs X loses to Y (target[X][Y]=0): need final wins[X][Y] <= half_d.
    //   I.e., current wins[X][Y] <= half_d (can only increase).
    for (int Y = 0; Y < n; Y++) {
        if (Y == X) continue;
        int y_placed_here = die_placed[f*n + Y];
        // Slots where pair (X,Y) is not yet resolved:
        //  - slots_remaining_after, plus the current slot if Y not placed.
        int unresolved = slots_remaining_after + (y_placed_here ? 0 : 1);

        // X must beat Y
        if (target[X*n + Y]) {
            if (wins[X*n + Y] + unresolved < win_threshold) return 0;
        } else {
            if (wins[X*n + Y] > half_d) return 0;
        }
        // Y must beat X
        if (target[Y*n + X]) {
            if (wins[Y*n + X] + unresolved < win_threshold) return 0;
        } else {
            if (wins[Y*n + X] > half_d) return 0;
        }
    }
    return 1;
}

// Reverse the wins updates from place_and_check.
static void unplace(int f, int X, int pos) {
    for (int Y = 0; Y < n; Y++) {
        if (Y == X) continue;
        if (!die_placed[f*n + Y]) continue;
        int r_Y = rank[f*n + Y];
        if (pos > r_Y) wins[X*n + Y]--;
        else           wins[Y*n + X]--;
    }
}

// Final check after all slots filled.
static int final_check(void) {
    for (int X = 0; X < n; X++) {
        for (int Y = 0; Y < n; Y++) {
            if (X == Y) continue;
            int beats = wins[X*n + Y] > half_d;
            if (beats != target[X*n + Y]) return 0;
        }
    }
    return 1;
}

// Fill position `pos` of slot f. pos goes 0..n-1; when pos == n, slot is done.
static int fill_slot(int f, int pos) {
    backtrack_calls++;

    if (pos == n) {
        // Slot complete. Move to next slot or final check.
        if (f == d - 1) {
            return final_check();
        }
        return fill_slot(f + 1, 0);
    }

    // Try each die not yet placed in this slot for rank `pos`.
    for (int X = 0; X < n; X++) {
        if (die_placed[f*n + X]) continue;

        // Sum bounds pruning
        int new_partial = partial_sum[X] + pos;
        int slots_remaining_for_X = d - f - 1;  // future slots
        int min_future = 0;
        int max_future = (n - 1) * slots_remaining_for_X;
        if (new_partial + min_future > required_sum[X]) continue;
        if (new_partial + max_future < required_sum[X]) continue;

        // Tentatively place X at rank pos in slot f.
        rank[f*n + X] = pos;
        slot_used[f*n + pos] = X;
        die_placed[f*n + X] = 1;
        partial_sum[X] = new_partial;

        // Update wins and prune.
        if (place_and_check(f, X, pos)) {
            if (fill_slot(f, pos + 1)) return 1;
        }

        // Undo.
        unplace(f, X, pos);
        rank[f*n + X] = -1;
        slot_used[f*n + pos] = -1;
        die_placed[f*n + X] = 0;
        partial_sum[X] = new_partial - pos;
    }
    return 0;
}

int solve(int n_in, int d_in, const int8_t *target_in, int *rank_out, long *calls_out) {
    n = n_in; d = d_in;
    half_d = d / 2;
    win_threshold = half_d + 1;

    target = (int8_t*)malloc(n*n);
    memcpy(target, target_in, n*n);
    for (int X = 0; X < n; X++) target[X*n + X] = 0;

    rank = (int*)malloc(sizeof(int) * d * n);
    slot_used = (int*)malloc(sizeof(int) * d * n);
    die_placed = (int8_t*)calloc(d * n, sizeof(int8_t));
    wins = (int*)calloc(n * n, sizeof(int));
    partial_sum = (int*)calloc(n, sizeof(int));
    required_sum = (int*)malloc(sizeof(int) * n);

    int sum_feasible = (d * (n - 1)) % 2 == 0;
    for (int X = 0; X < n; X++) required_sum[X] = d * (n - 1) / 2;

    for (int i = 0; i < d * n; i++) { rank[i] = -1; slot_used[i] = -1; }

    backtrack_calls = 0;
    int found = 0;
    if (sum_feasible) {
        found = fill_slot(0, 0);
    }

    if (found) memcpy(rank_out, rank, sizeof(int) * d * n);
    if (calls_out) *calls_out = backtrack_calls;

    free(target); free(rank); free(slot_used); free(die_placed);
    free(wins); free(partial_sum); free(required_sum);
    return found;
}