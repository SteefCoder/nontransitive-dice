#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MAXN 17
#define K 5

static int n = 12;

static int perm[K][MAXN];
static int pos[MAXN][K];

/* ---------- functions to implement later ---------- */

void random_perm(int r);
void update_positions(void);

int score(void);
int verify(void);

/* ----------------------------------------------- */


static void build_state(
    int t0,
    int t1,
    int t2,
    int t3,
    int t4)
{
    mask = 0;

    for (int i = 0; i < n; i++) {

        int v =
            (t0 > pos[i][0]) +
            (t1 > pos[i][1]) +
            (t2 > pos[i][2]) +
            (t3 > pos[i][3]) +
            (t4 > pos[i][4]);

        votes[i] = v;

        if (v >= 3)
            mask |= 1u << i;
    }
}

static void print_solution(void)
{
    for (int r = 0; r < K; r++) {
        printf("perm %d: ", r);
        for (int i = 0; i < n; i++)
            printf("%d ", perm[r][i] + 1);
        printf("\n");
    }
}

int main(void)
{
    srand((unsigned)time(NULL));

    for (int r = 0; r < K; r++)
        random_perm(r);

    update_positions();

    int best = score();

    printf("Initial score = %d / %d\n", best, 1 << n);

    for (int iter = 0; iter < 10000; iter++) {

        int r = rand() % K;

        int a = 1 + rand() % (n - 1);
        int b = 1 + rand() % (n - 1);

        if (a == b)
            continue;

        int x = perm[r][a];
        int y = perm[r][b];

        perm[r][a] = y;
        perm[r][b] = x;

        pos[x][r] = b;
        pos[y][r] = a;

        int s = score();

        if (s >= best) {
            best = s;
        } else {

            perm[r][a] = x;
            perm[r][b] = y;

            pos[x][r] = a;
            pos[y][r] = b;
        }

        if ((iter % 1000) == 0)
            printf("iter %5d   best = %d\n", iter, best);

        if (best == (1 << n))
            break;
    }

    printf("\nFinal score = %d / %d\n", best, 1 << n);

    print_solution();

    printf("Verified = %d\n", verify());
}