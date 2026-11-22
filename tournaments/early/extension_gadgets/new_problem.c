#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MAXN 17
#define MAXK 7

static int perm[MAXK][MAXN];
static int pos[MAXN][MAXK];

static int n, k;

static inline void compute_positions() {
    for (int r = 0; r < k; r++) {
        for (int i = 0; i < n; i++) {
            pos[perm[r][i]][r] = i;
        }
    }
}

static inline int score() {
    compute_positions();

    int total_masks = 1 << n;
    char *seen = (char*)calloc(total_masks, sizeof(char));

    int max_t = n + 1;

    for (int t0 = 0; t0 < max_t; t0++)
    for (int t1 = 0; t1 < max_t; t1++)
    for (int t2 = 0; t2 < max_t; t2++)
    for (int t3 = 0; t3 < max_t; t3++)
    for (int t4 = 0; t4 < max_t; t4++) {

        int t[MAXK] = {t0, t1, t2, t3, t4};
        int mask = 0;

        for (int i = 0; i < n; i++) {
            int votes = 0;

            for (int r = 0; r < k; r++) {
                if (t[r] > pos[i][r]) votes++;
            }

            if (votes > k / 2) {
                mask |= (1 << i);
            }
        }

        seen[mask] = 1;
    }

    int cnt = 0;
    for (int m = 0; m < total_masks; m++) {
        cnt += seen[m];
    }

    free(seen);
    return cnt;
}

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

int verify() {
    // compute_positions();

    int total_masks = 1 << n;

    // stack allocation (fast, no malloc)
    char *seen = (char*)calloc(total_masks, sizeof(char));
    if (!seen) {
        printf("Memory allocation failed\n");
        exit(1);
    }

    int max_t = n + 1;

    for (int t0 = 0; t0 < max_t; t0++) {
    for (int t1 = 0; t1 < max_t; t1++) {
    for (int t2 = 0; t2 < max_t; t2++) {
    for (int t3 = 0; t3 < max_t; t3++) {
    for (int t4 = 0; t4 < max_t; t4++) {

        int t[MAXK] = {t0, t1, t2, t3, t4};

        int mask = 0;

        for (int i = 0; i < n; i++) {
            int votes = 0;

            for (int r = 0; r < k; r++) {
                if (t[r] > pos[i][r]) {
                    votes++;
                }
            }

            if (votes > k / 2) {
                mask |= (1 << i);
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

int main() {
    srand(time(NULL));

    n = 12;
    k = 5;

    for (int r = 0; r < k; r++) {
        random_perm(r);
    }

    int best = score();
    printf("Initial score: %d / %d\n", best, 1 << n);

    for (int iter = 0; iter < 10000; iter++) {

        int r = rand() % k;
        int i = 1 + rand() % (n - 1);
        int j = 1 + rand() % (n - 1);

        if (i == j) continue;

        // swap
        int tmp = perm[r][i];
        perm[r][i] = perm[r][j];
        perm[r][j] = tmp;

        pos[perm[r][i]][r] = i;
        pos[perm[r][j]][r] = j;

        int s = score();

        if (s >= best) {
            best = s;
        } else {
            // revert
            tmp = perm[r][i];
            perm[r][i] = perm[r][j];
            perm[r][j] = tmp;

            pos[perm[r][i]][r] = i;
            pos[perm[r][j]][r] = j;
        }

        if (iter % 1000 == 0) {
            printf("iter %d: best = %d\n", iter, best);
        }

        if (best == (1 << n)) {
            printf("FULL SOLUTION FOUND!\n");
            break;
        }
    }

    printf("Final best = %d / %d\n", best, 1 << n);

    for (int r = 0; r < k; r++) {
        printf("perm %d: ", r);
        for (int i = 0; i < n; i++) {
            printf("%d ", perm[r][i] + 1);
        }
        printf("\n");
    }

    printf("Verified: %d\n", verify());

    return 0;
}