#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdbool.h>


typedef struct {
    int n, k;
    signed char *tournament;
    int *weights;

    int *orderings;
    int *positions;

    int *va;
    int *vb;
} Solver;


inline double time_since(time_t start) {
    return (double)(clock() - start) / CLOCKS_PER_SEC;
}

static unsigned int random() {
    static int rng = 1;
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return rng;
}


int anneal(Solver *solver, double seconds) {
    int n = solver->n;
    int loss = 0;
    unsigned int rng = clock();
    
    time_t start = clock();
    while (time_since(start) < seconds && loss > 0) {
        int nviolations = collect_violations(solver);

        for (int iter = 0; iter < 30000 && loss > 0; ++iter) {
            int t = -1;
            if (random() & 8 == 0) {
                int r = random() % nviolations;
                int choice = (random() & 1) ? solver->va[r] : solver-
            }
        }
    }
}