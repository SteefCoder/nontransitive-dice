#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

#define MAXN 17
#define MAXK 7

static int perm[MAXK][MAXN];
static int pos[MAXN][MAXK];

static int n, k;
static int threshold_count;
static int (*thresholds)[MAXK];
static int8_t **vote_counts;
static uint32_t *threshold_masks;
static int *mask_counts;
static int unique_masks;

static void random_perm(int r) {
    for (int i = 0; i < n; i++) {
        perm[r][i] = i;
    }
    for (int i = n - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        int tmp = perm[r][i];
        perm[r][i] = perm[r][j];
        perm[r][j] = tmp;
    }
}

static void build_thresholds(void) {
    threshold_count = 1;
    for (int r = 0; r < k; r++) {
        threshold_count *= (n + 1);
    }

    thresholds = (int (*)[MAXK])malloc((size_t)threshold_count * sizeof(*thresholds));
    if (!thresholds) {
        fprintf(stderr, "allocation failed for thresholds\n");
        exit(1);
    }

    int combo[MAXK];
    int idx = 0;

    void rec(int depth) {
        if (depth == k) {
            for (int r = 0; r < k; r++) {
                thresholds[idx][r] = combo[r];
            }
            idx++;
            return;
        }
        for (int v = 0; v <= n; v++) {
            combo[depth] = v;
            rec(depth + 1);
        }
    }

    rec(0);
    if (idx != threshold_count) {
        fprintf(stderr, "threshold generation mismatch\n");
        exit(1);
    }
}

static void compute_positions(void) {
    for (int r = 0; r < k; r++) {
        for (int i = 0; i < n; i++) {
            pos[perm[r][i]][r] = i;
        }
    }
}

static void init_state(void) {
    if (!vote_counts) {
        vote_counts = (int8_t **)malloc((size_t)n * sizeof(*vote_counts));
        if (!vote_counts) {
            fprintf(stderr, "allocation failed for vote_counts\n");
            exit(1);
        }
        for (int i = 0; i < n; i++) {
            vote_counts[i] = (int8_t *)malloc((size_t)threshold_count * sizeof(*vote_counts[i]));
            if (!vote_counts[i]) {
                fprintf(stderr, "allocation failed for vote_counts[%d]\n", i);
                exit(1);
            }
        }
    }
    if (!threshold_masks) {
        threshold_masks = (uint32_t *)malloc((size_t)threshold_count * sizeof(*threshold_masks));
        if (!threshold_masks) {
            fprintf(stderr, "allocation failed for threshold_masks\n");
            exit(1);
        }
    }
    if (!mask_counts) {
        mask_counts = (int *)calloc((size_t)(1u << n), sizeof(*mask_counts));
        if (!mask_counts) {
            fprintf(stderr, "allocation failed for mask_counts\n");
            exit(1);
        }
    } else {
        for (int m = 0; m < (1 << n); m++) {
            mask_counts[m] = 0;
        }
    }

    unique_masks = 0;
    for (int idx = 0; idx < threshold_count; idx++) {
        uint32_t mask = 0;
        for (int item = 0; item < n; item++) {
            int votes = 0;
            for (int r = 0; r < k; r++) {
                if (thresholds[idx][r] > pos[item][r]) {
                    votes++;
                }
            }
            vote_counts[item][idx] = (int8_t)votes;
            if (votes > k / 2) {
                mask |= (1u << item);
            }
        }
        threshold_masks[idx] = mask;
        mask_counts[mask]++;
        if (mask_counts[mask] == 1) {
            unique_masks++;
        }
    }
}

static void update_mask_for_threshold(int idx, int item, int old_votes, int new_votes) {
    int old_majority = old_votes > k / 2;
    int new_majority = new_votes > k / 2;
    if (old_majority == new_majority) {
        return;
    }

    uint32_t old_mask = threshold_masks[idx];
    uint32_t bit = 1u << item;
    uint32_t new_mask = old_mask ^ bit;

    if (mask_counts[old_mask] == 1) {
        unique_masks--;
    }
    mask_counts[old_mask]--;

    if (mask_counts[new_mask] == 0) {
        unique_masks++;
    }
    mask_counts[new_mask]++;
    threshold_masks[idx] = new_mask;
}

static void apply_swap_state(int row, int item_a, int item_b, int from_a, int to_a, int from_b, int to_b) {
    for (int idx = 0; idx < threshold_count; idx++) {
        int thr = thresholds[idx][row];
        int delta_a = (thr > to_a) - (thr > from_a);
        int delta_b = (thr > to_b) - (thr > from_b);

        int old_votes_a = vote_counts[item_a][idx];
        int new_votes_a = old_votes_a + delta_a;
        if (new_votes_a != old_votes_a) {
            vote_counts[item_a][idx] = (int8_t)new_votes_a;
            update_mask_for_threshold(idx, item_a, old_votes_a, new_votes_a);
        }

        int old_votes_b = vote_counts[item_b][idx];
        int new_votes_b = old_votes_b + delta_b;
        if (new_votes_b != old_votes_b) {
            vote_counts[item_b][idx] = (int8_t)new_votes_b;
            update_mask_for_threshold(idx, item_b, old_votes_b, new_votes_b);
        }
    }
}

static void perform_swap(int row, int i, int j) {
    int item_a = perm[row][i];
    int item_b = perm[row][j];
    int from_a = pos[item_a][row];
    int from_b = pos[item_b][row];

    int tmp = perm[row][i];
    perm[row][i] = perm[row][j];
    perm[row][j] = tmp;

    pos[item_a][row] = j;
    pos[item_b][row] = i;

    apply_swap_state(row, item_a, item_b, from_a, j, from_b, i);
}

static int evaluate_swap(int row, int i, int j) {
    int item_a = perm[row][i];
    int item_b = perm[row][j];
    int from_a = pos[item_a][row];
    int from_b = pos[item_b][row];

    int tmp = perm[row][i];
    perm[row][i] = perm[row][j];
    perm[row][j] = tmp;

    pos[item_a][row] = j;
    pos[item_b][row] = i;
    apply_swap_state(row, item_a, item_b, from_a, j, from_b, i);

    int score = unique_masks;

    apply_swap_state(row, item_a, item_b, j, from_a, i, from_b);
    tmp = perm[row][i];
    perm[row][i] = perm[row][j];
    perm[row][j] = tmp;
    pos[item_a][row] = from_a;
    pos[item_b][row] = from_b;

    return score;
}

static int score(void) {
    return unique_masks;
}

static int verify(void) {
    int total_masks = 1 << n;
    uint8_t *seen = (uint8_t *)calloc((size_t)total_masks, sizeof(*seen));
    if (!seen) {
        fprintf(stderr, "memory allocation failed\n");
        exit(1);
    }

    int max_t = n + 1;
    for (int t0 = 0; t0 < max_t; t0++) {
    for (int t1 = 0; t1 < max_t; t1++) {
    for (int t2 = 0; t2 < max_t; t2++) {
    for (int t3 = 0; t3 < max_t; t3++) {
    for (int t4 = 0; t4 < max_t; t4++) {
        int t[MAXK] = {t0, t1, t2, t3, t4};
        uint32_t mask = 0;
        for (int item = 0; item < n; item++) {
            int votes = 0;
            for (int r = 0; r < k; r++) {
                if (t[r] > pos[item][r]) {
                    votes++;
                }
            }
            if (votes > k / 2) {
                mask |= (1u << item);
            }
        }
        seen[mask] = 1;
    }}}}}

    int ok = 1;
    for (int m = 0; m < total_masks; m++) {
        if (!seen[m]) {
            ok = 0;
            break;
        }
    }
    free(seen);
    return ok;
}

int main(void) {
    srand((unsigned)time(NULL));

    n = 12;
    k = 5;

    build_thresholds();

    int global_best = -1;
    int best_restart = 0;
    clock_t start = clock();

    for (int restart = 0; restart < 3; restart++) {
        for (int r = 0; r < k; r++) {
            random_perm(r);
        }
        compute_positions();
        init_state();

        int current_score = score();
        int restart_best = current_score;

        for (int iter = 0; iter < 1000; iter++) {
            int best_row = -1, best_i = -1, best_j = -1;
            int best_candidate_score = current_score;

            for (int sample = 0; sample < 8; sample++) {
                int row = rand() % k;
                int i = 1 + rand() % (n - 1);
                int j = 1 + rand() % (n - 1);
                if (i == j) continue;

                int cand = evaluate_swap(row, i, j);
                if (cand > best_candidate_score) {
                    best_candidate_score = cand;
                    best_row = row;
                    best_i = i;
                    best_j = j;
                }
            }

            if (best_row >= 0 && best_candidate_score > current_score) {
                perform_swap(best_row, best_i, best_j);
                current_score = score();
                if (current_score > restart_best) {
                    restart_best = current_score;
                }
            } else if (rand() % 100 < 15) {
                int row = rand() % k;
                int i = 1 + rand() % (n - 1);
                int j = 1 + rand() % (n - 1);
                if (i != j) {
                    perform_swap(row, i, j);
                    current_score = score();
                }
            }

            if (iter % 250 == 0) {
                printf("restart %d iter %d: score = %d\n", restart, iter, current_score);
            }
        }

        if (restart_best > global_best) {
            global_best = restart_best;
            best_restart = restart;
        }

        printf("restart %d best = %d\n", restart, restart_best);
    }

    double elapsed = (double)(clock() - start) / CLOCKS_PER_SEC;
    printf("Global best = %d / %d\n", global_best, 1 << n);
    printf("Best restart = %d\n", best_restart);
    printf("Elapsed: %.3f s\n", elapsed);
    printf("Verified: %d\n", verify());

    for (int i = 0; i < n; i++) {
        free(vote_counts[i]);
    }
    free(vote_counts);
    free(threshold_masks);
    free(mask_counts);
    free(thresholds);

    return 0;
}
