"""
CSC 2114 Artificial Intelligence - Practical 1
Makerere Campus Route Finder (BFS and DFS)

Uninformed search over a simplified model of the Makerere main campus.
Every connection costs 1 hop, so the optimal route is the one with the
fewest hops. Python 3 standard library only.

Usage:
    python3 route_finder.py                 # interactive prompts
    python3 route_finder.py --no-reached    # tree-like search (no reached table)
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a DFS
"""

import argparse
from collections import deque


# ---------------------------------------------------------------------------
# The campus graph (given - do not change)
# ---------------------------------------------------------------------------

LANDMARKS = {
    "Main Building", "Freedom Square", "Main Library",
    "Central Teaching Facility",
}

EDGES = [
    ("Main Building", "Freedom Square"), ("Main Building", "Main Library"),
    ("Main Building", "School of Social Sciences"),
    ("Main Building", "School of Liberal and Performing Arts"),
    ("Freedom Square", "Main Library"), ("Freedom Square", "School of Law"),
    ("Freedom Square", "Central Teaching Facility"),
    ("Main Library", "School of Education"), ("Main Library", "School of Economics"),
    ("Central Teaching Facility", "CoCIS"),
    ("Central Teaching Facility", "School of Statistics and Planning"),
    ("CoCIS", "School of Statistics and Planning"), ("CoCIS", "School of Engineering"),
    ("School of Engineering", "School of the Built Environment"),
    ("School of Engineering", "Margaret Trowell School of Industrial and Fine Art"),
    ("School of the Built Environment", "Margaret Trowell School of Industrial and Fine Art"),
    ("Margaret Trowell School of Industrial and Fine Art", "School of Liberal and Performing Arts"),
    ("School of Education", "School of Social Sciences"),
    ("School of Education", "College of Natural Sciences"),
    ("College of Natural Sciences", "School of Food Technology, Nutrition and Bioengineering"),
    ("School of Food Technology, Nutrition and Bioengineering", "School of Agricultural Sciences"),
    ("School of Agricultural Sciences", "School of Veterinary Medicine"),
    ("School of Statistics and Planning", "School of Economics"),
    ("School of Economics", "School of Law"),
]

MAX_EXPANSIONS = 10_000  # safety cap so tree-like search always terminates


def build_graph(edges):
    """Return an adjacency list {place: [neighbours sorted alphabetically]}.

    Connections are two-way, so each edge is added in both directions.
    Sorting here means every caller sees neighbours in alphabetical order.
    """
    graph = {}
    for a, b in edges:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    return {place: sorted(neighbours, key=str.lower) for place, neighbours in graph.items()}


GRAPH = build_graph(EDGES)
PLACES = sorted(GRAPH, key=str.lower)


# ---------------------------------------------------------------------------
# Problem formulation
# ---------------------------------------------------------------------------

class RouteProblem:
    """The five components of the search problem."""

    def __init__(self, initial, goal, graph=GRAPH):
        self.initial = initial          # 1. initial state
        self.goal = goal
        self.graph = graph

    def actions(self, state):
        """2. Actions(s): walk to any directly connected place (alphabetical)."""
        return self.graph[state]

    def result(self, state, action):
        """3. Result(s, a): the action 'walk to X' leads to state X."""
        return action

    def is_goal(self, state):
        """4. Goal test: are we at the destination?"""
        return state == self.goal

    def action_cost(self, state, action, next_state):
        """5. Step cost: every hop costs exactly 1."""
        return 1


# ---------------------------------------------------------------------------
# Search tree node
# ---------------------------------------------------------------------------

class Node:
    """A node in the search tree (STATE, PARENT, ACTION, PATH-COST)."""

    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.path_cost = path_cost

    def __repr__(self):
        return f"Node({self.state!r}, cost={self.path_cost})"


def expand(problem, node):
    """Generate the child nodes of `node`, in alphabetical order of state."""
    for action in problem.actions(node.state):
        child_state = problem.result(node.state, action)
        cost = node.path_cost + problem.action_cost(node.state, action, child_state)
        yield Node(child_state, parent=node, action=action, path_cost=cost)


def solution(node):
    """Follow PARENT pointers back to the root; return the places in order."""
    path = []
    while node is not None:
        path.append(node.state)
        node = node.parent
    return list(reversed(path))


# ---------------------------------------------------------------------------
# Frontiers: the only thing that differs between BFS and DFS
# ---------------------------------------------------------------------------

class FIFOFrontier:
    """Queue: add at the back, remove from the front (BFS)."""

    def __init__(self):
        self.items = deque()

    def add_children(self, children):
        # Alphabetical order in = alphabetical order out.
        self.items.extend(children)

    def pop(self):
        return self.items.popleft()

    def __len__(self):
        return len(self.items)


class LIFOFrontier:
    """Stack: add at the back, remove from the back (DFS)."""

    def __init__(self):
        self.items = []

    def add_children(self, children):
        # Push in reverse alphabetical order, so the alphabetically first
        # neighbour ends up on top of the stack and is explored first.
        self.items.extend(reversed(children))

    def pop(self):
        return self.items.pop()

    def __len__(self):
        return len(self.items)


STRATEGIES = {"BFS": FIFOFrontier, "DFS": LIFOFrontier}


# ---------------------------------------------------------------------------
# Generic search loop
# ---------------------------------------------------------------------------

class SearchResult:
    def __init__(self, node, expanded, hit_cap=False):
        self.node = node            # goal node, or None if no route
        self.expanded = expanded    # nodes removed, not goal, children generated
        self.hit_cap = hit_cap      # True if the expansion cap stopped the search

    @property
    def route(self):
        return solution(self.node) if self.node else None

    @property
    def cost(self):
        return self.node.path_cost if self.node else None


def search(problem, frontier_class, use_reached=True, max_expansions=MAX_EXPANSIONS):
    """Generic search; the strategy is chosen only by `frontier_class`.

    1. Create the root node from the initial state.
    2. Put it on the frontier (and in reached, if graph search).
    3. Loop: if the frontier is empty, return failure.
    4. Remove a node; if it passes the goal test, return it.
    5. Otherwise expand it (count it as expanded).
    6. For each child: in graph search skip it if its state is already
       in reached, else record it in reached.
    7. Add the surviving children to the frontier and repeat.

    With use_reached=False this is tree-like search: repeated states are
    not detected, so the expansion cap is needed to guarantee termination.
    """
    node = Node(problem.initial)                                   # step 1
    frontier = frontier_class()
    frontier.add_children([node])                                  # step 2
    reached = {problem.initial: node} if use_reached else None
    expanded = 0

    while len(frontier) > 0:                                       # step 3
        node = frontier.pop()                                      # step 4
        if problem.is_goal(node.state):
            return SearchResult(node, expanded)
        if expanded >= max_expansions:
            return SearchResult(None, expanded, hit_cap=True)
        expanded += 1                                              # step 5
        children = []
        for child in expand(problem, node):
            if use_reached:                                        # step 6
                if child.state in reached:
                    continue
                reached[child.state] = child
            children.append(child)
        frontier.add_children(children)                            # step 7

    return SearchResult(None, expanded)                            # failure


def find_route(source, destination, algorithm, use_reached=True):
    """Convenience wrapper: canonical names in, SearchResult out."""
    problem = RouteProblem(source, destination)
    return search(problem, STRATEGIES[algorithm], use_reached=use_reached)


# ---------------------------------------------------------------------------
# User interface
# ---------------------------------------------------------------------------

_PLACE_LOOKUP = {p.lower(): p for p in PLACES}


def match_place(text):
    """Case-insensitive, whitespace-trimmed lookup. Returns None if unknown."""
    return _PLACE_LOOKUP.get(text.strip().lower())


def match_algorithm(text):
    algo = text.strip().upper()
    return algo if algo in STRATEGIES else None


def print_valid_places():
    print("Valid places are:")
    for p in PLACES:
        kind = "landmark" if p in LANDMARKS else "school"
        print(f"  - {p} ({kind})")


def format_result(algorithm, result):
    lines = [f"Algorithm: {algorithm}"]
    if result.node is None:
        if result.hit_cap:
            lines.append(f"No route found (stopped at the {MAX_EXPANSIONS:,}-expansion cap)")
        else:
            lines.append("No route found")
    else:
        lines.append("Route: " + " -> ".join(result.route))
        lines.append(f"Cost (hops): {result.cost}")
    lines.append(f"Nodes expanded: {result.expanded}")
    return "\n".join(lines)


def prompt_place(label):
    while True:
        text = input(f"{label}: ")
        place = match_place(text)
        if place:
            return place
        print(f"Unknown place: {text.strip()!r}")
        print_valid_places()


def prompt_algorithm():
    while True:
        text = input("Algorithm (BFS or DFS): ")
        algo = match_algorithm(text)
        if algo:
            return algo
        print(f"Unknown algorithm: {text.strip()!r}. Please enter BFS or DFS.")


def main():
    parser = argparse.ArgumentParser(description="Makerere Campus Route Finder (BFS/DFS)")
    parser.add_argument("-s", "--source", help="source place")
    parser.add_argument("-d", "--destination", help="destination place")
    parser.add_argument("-a", "--algorithm", help="BFS or DFS")
    parser.add_argument("--no-reached", action="store_true",
                        help="turn the reached table off (tree-like search)")
    args = parser.parse_args()
    use_reached = not args.no_reached

    print("Makerere Campus Route Finder")
    if not use_reached:
        print(f"[tree-like search: reached table OFF, cap {MAX_EXPANSIONS:,} expansions]")
    print()

    try:
        # Command-line values are validated the same way; a bad one falls
        # back to the interactive prompt instead of crashing.
        source = match_place(args.source) if args.source else None
        if args.source and not source:
            print(f"Unknown place: {args.source.strip()!r}")
            print_valid_places()
        source = source or prompt_place("Source")

        destination = match_place(args.destination) if args.destination else None
        if args.destination and not destination:
            print(f"Unknown place: {args.destination.strip()!r}")
            print_valid_places()
        destination = destination or prompt_place("Destination")

        algorithm = match_algorithm(args.algorithm) if args.algorithm else None
        if args.algorithm and not algorithm:
            print(f"Unknown algorithm: {args.algorithm.strip()!r}. Please enter BFS or DFS.")
        algorithm = algorithm or prompt_algorithm()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    result = find_route(source, destination, algorithm, use_reached=use_reached)
    print()
    print(format_result(algorithm, result))


if __name__ == "__main__":
    main()
