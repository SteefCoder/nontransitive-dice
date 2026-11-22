#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

#define MAXN 13
#define MAXK 11

static int perm[MAXK][MAXN];
static int pos[MAXK][MAXN];

static int n, k;

// ----------------------------
// contribution cache
// contrib[i][mask] = whether subset mask is produced by element i
// ----------------------------
static unsigned char contrib[MAXN][1 << MAXN];

// ----------------------------
// global seen counts
// ----------------------------
static int seen[1 << MAXN];

// ----------------------------
// recompute positions
// ----------------------------
static inline void compute_positions() {
    for (int r = 0; r < k; r++) {
        for (int i = 0; i < n; i++) {
            pos[perm[r][i]][r] = i;
        }
    }
}

// ----------------------------
// build full score table (baseline)
// ----------------------------
static inline void build_all() {

    for (int m = 0; m < (1 << n); m++)
        seen[m] = 0;

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
}

// ----------------------------
// full score
// ----------------------------
static inline int score() {
    build_all();

    int cnt = 0;
    for (int m = 0; m < (1 << n); m++)
        cnt += seen[m];

    return cnt;
}

// ----------------------------
// swap helper
// ----------------------------
static inline void swap(int r, int a, int b) {
    int tmp = perm[r][a];
    perm[r][a] = perm[r][b];
    perm[r][b] = tmp;
}

// ----------------------------
// initialize random perms
// ----------------------------
static void random_perm(int r) {
    for (int i = 0; i < n; i++) perm[r][i] = i;

    for (int i = n - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        int tmp = perm[r][i];
        perm[r][i] = perm[r][j];
        perm[r][j] = tmp;
    }
}

// ----------------------------
// hill step with annealing
// ----------------------------
static void step(double temp) {

    int best_score = score();

    int br = -1, bi = -1, bj = -1;

    for (int r = 0; r < k; r++) {
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {

                swap(r, i, j);
                compute_positions();

                int s = score();

                int delta = s - best_score;

                if (delta > 0 ||
                   (temp > 0 && exp(delta / temp) > (double)rand()/RAND_MAX)) {

                    best_score = s;
                    br = r; bi = i; bj = j;
                }

                swap(r, i, j);
                compute_positions();
            }
        }
    }

    if (br != -1) {
        swap(br, bi, bj);
        compute_positions();
    } else {
        int r = rand() % k;
        int i = rand() % n;
        int j = rand() % n;
        swap(r, i, j);
        compute_positions();
    }
}

// ----------------------------
static void print() {
    printf("\nSolution:\n");
    for (int r = 0; r < k; r++) {
        printf("pi_%d = [", r+1);
        for (int i = 0; i < n; i++) {
            printf("%d ", perm[r][i]);
        }
        printf("]\n");
    }
}

// ----------------------------
int main() {

    srand(time(NULL));

    n = 11;
    k = 5;

    for (int r = 0; r < k; r++)
        random_perm(r);

    compute_positions();

    int best = score();
    printf("Initial score: %d / %d\n", best, 1 << n);

    for (int iter = 0; iter < 20000; iter++) {

        double temp = 1.0 - (double)iter / 20000.0; // annealing

        step(temp);

        int s = score();

        if (s > best) {
            best = s;
            printf("iter %d: best = %d\n", iter, best);
        }

        if (best == (1 << n)) {
            printf("FULL SOLUTION FOUND!\n");
            break;
        }
    }

    print();
    printf("Final best = %d / %d\n", best, 1 << n);

    return 0;
}