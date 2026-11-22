def greedy(p: int, d: int, tournament: list[list[int]]):
    decision_stack = []
    forced_stack = []

    dice = [[0 for _ in range(d)] for _ in range(p)]

    curr_die = 0
    while True:
        # make the current die win against 