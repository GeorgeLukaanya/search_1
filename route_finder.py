"""
CSC 2114 Artificial Intelligence - Practical 1
Makerere Campus Route Finder (BFS, DFS and UCS)

Group 10 (BSSE)
    1. NOMWESIGWA KEITH     23/U/16071/EVE
    2. WAMBUI MARIAM        23/U/18494/PS
    3. LUKAANYA GEORGE      23/U/0696
    4. MUSHEIJA ABRAHAM     23/U/12139/EVE
    5. NALUYANGE KEVIN      18/U/23394/EVE
    6. NABIRYE ANITAH       23/U/12826/EVE

Search over a simplified model of the Makerere main campus. Every
connection now carries a cost (approximate walking time in minutes).

  BFS - fewest hops (ignores costs, so it is NOT guaranteed cheapest)
  DFS - first route found going deep (ignores costs)
  UCS - uniform cost search: always expands the cheapest frontier node,
        so the route it returns has the lowest total cost.

Every result reports the number of hops; UCS also reports the total cost.
Python 3 standard library only.

Usage:
    python3 route_finder.py                 # interactive prompts
    python3 route_finder.py --no-reached    # tree-like search (no reached table)
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a DFS
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a UCS
"""

import argparse
import heapq
import itertools
from collections import deque


# ---------------------------------------------------------------------------
# The campus graph: (place A, place B, cost in minutes)
# NOTE: the costs are illustrative walking times. 
# ---------------------------------------------------------------------------

LANDMARKS = {
    "Main Building", "Freedom Square", "Main Library",
    "Central Teaching Facility",
}

EDGES = [
    ("Main Building", "Freedom Square", 3),
    ("Main Building", "Main Library", 2),
    ("Main Building", "School of Social Sciences", 4),
    ("Main Building", "School of Liberal and Performing Arts", 6),
    ("Freedom Square", "Main Library", 2),
    ("Freedom Square", "School of Law", 5),
    ("Freedom Square", "Central Teaching Facility", 4),
    ("Main Library", "School of Education", 5),
    ("Main Library", "School of Economics", 7),
    ("Central Teaching Facility", "CoCIS", 3),
    ("Central Teaching Facility", "School of Statistics and Planning", 2),
    ("CoCIS", "School of Statistics and Planning", 2),
    ("CoCIS", "School of Engineering", 4),
    ("School of Engineering", "School of the Built Environment", 2),
    ("School of Engineering", "Margaret Trowell School of Industrial and Fine Art", 5),
    ("School of the Built Environment", "Margaret Trowell School of Industrial and Fine Art", 3),
    ("Margaret Trowell School of Industrial and Fine Art", "School of Liberal and Performing Arts", 8),
    ("School of Education", "School of Social Sciences", 3),
    ("School of Education", "College of Natural Sciences", 6),
    ("College of Natural Sciences", "School of Food Technology, Nutrition and Bioengineering", 4),
    ("School of Food Technology, Nutrition and Bioengineering", "School of Agricultural Sciences", 5),
    ("School of Agricultural Sciences", "School of Veterinary Medicine", 6),
    ("School of Statistics and Planning", "School of Economics", 6),
    ("School of Economics", "School of Law", 3),
]

MAX_EXPANSIONS = 10_000  # safety cap so tree-like search always terminates


def build_graph(edges):
    """Return (adjacency list, costs).

    adjacency: {place: [neighbours sorted alphabetically]}
    costs:     {(a, b): cost} with both directions stored, because
               connections are two-way.
    """
    graph = {}
    costs = {}
    for a, b, cost in edges:
        if cost <= 0:
            raise ValueError(f"Edge {a!r} - {b!r} must have a positive cost")
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
        costs[(a, b)] = cost
        costs[(b, a)] = cost
    adjacency = {p: sorted(n, key=str.lower) for p, n in graph.items()}
    return adjacency, costs


GRAPH, COSTS = build_graph(EDGES)
PLACES = sorted(GRAPH, key=str.lower)

# ---------------------------------------------------------------------------
# Problem formulation
# ---------------------------------------------------------------------------

class RouteProblem:
    """The five components of the search problem."""

    def __init__(self, initial, goal, graph=GRAPH, costs=COSTS):
        self.initial = initial          # 1. initial state
        self.goal = goal
        self.graph = graph
        self.costs = costs

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
        """5. Step cost: the cost attached to the connection."""
        return self.costs[(state, next_state)]


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
# Frontiers: the only thing that differs between BFS, DFS and UCS
# ---------------------------------------------------------------------------

class FIFOFrontier:
    """Queue: add at the back, remove from the front (BFS)."""

    reopens = False  # a state is never worth re-reaching in BFS

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

    reopens = False

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


class PriorityFrontier:
    """Priority queue ordered by path cost (UCS).

    Ties are broken alphabetically by state name, then by insertion order,
    so results are deterministic.
    """

    # UCS must be allowed to re-reach a state if the new path is cheaper.
    reopens = True

    def __init__(self):
        self.heap = []
        self.counter = itertools.count()

    def add_children(self, children):
        for child in children:
            heapq.heappush(
                self.heap,
                (child.path_cost, child.state.lower(), next(self.counter), child),
            )

    def pop(self):
        return heapq.heappop(self.heap)[-1]

    def __len__(self):
        return len(self.heap)


STRATEGIES = {"BFS": FIFOFrontier, "DFS": LIFOFrontier, "UCS": PriorityFrontier}


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

    @property
    def hops(self):
        return len(self.route) - 1 if self.node else None


def search(problem, frontier_class, use_reached=True, max_expansions=MAX_EXPANSIONS):
    """Generic search; the strategy is chosen only by `frontier_class`.

    1. Create the root node from the initial state.
    2. Put it on the frontier (and in reached, if graph search).
    3. Loop: if the frontier is empty, return failure.
    4. Remove a node; if it passes the goal test, return it.
       (The goal test happens on removal, not generation. This is what
       makes UCS return the cheapest route.)
    5. Otherwise expand it (count it as expanded).
    6. For each child: in graph search skip it if its state is already
       in reached, unless the strategy re-opens states and this path is
       strictly cheaper; otherwise record it in reached.
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
        if use_reached and frontier_class.reopens \
                and node.path_cost > reached[node.state].path_cost:
            continue  # stale entry: a cheaper path to this state was found later
        if problem.is_goal(node.state):
            return SearchResult(node, expanded)
        if expanded >= max_expansions:
            return SearchResult(None, expanded, hit_cap=True)
        expanded += 1                                              # step 5
        children = []
        for child in expand(problem, node):
            if use_reached:                                        # step 6
                seen = reached.get(child.state)
                if seen is not None and not (
                    frontier_class.reopens and child.path_cost < seen.path_cost
                ):
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
        route = result.route
        lines.append("Route: " + " -> ".join(route))
        lines.append(f"Cost (hops): {result.hops}")
        if algorithm == "UCS":
            # Show the cost of each leg so the total can be checked by eye.
            legs = [f"{a} -> {b}: {COSTS[(a, b)]}" for a, b in zip(route, route[1:])]
            if legs:
                lines.append("Leg costs:")
                lines.extend(f"  {leg}" for leg in legs)
            lines.append(f"Total cost (min): {result.cost}")
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
        text = input("Algorithm (BFS, DFS or UCS): ")
        algo = match_algorithm(text)
        if algo:
            return algo
        print(f"Unknown algorithm: {text.strip()!r}. Please enter BFS, DFS or UCS.")


def main():
    parser = argparse.ArgumentParser(description="Makerere Campus Route Finder (BFS/DFS/UCS)")
    parser.add_argument("-s", "--source", help="source place")
    parser.add_argument("-d", "--destination", help="destination place")
    parser.add_argument("-a", "--algorithm", help="BFS, DFS or UCS")
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
            print(f"Unknown algorithm: {args.algorithm.strip()!r}. Please enter BFS, DFS or UCS.")
        algorithm = algorithm or prompt_algorithm()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    result = find_route(source, destination, algorithm, use_reached=use_reached)
    print()
    print(format_result(algorithm, result))


if __name__ == "__main__":
    main()
