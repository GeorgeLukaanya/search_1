"""
CSC 2114 Artificial Intelligence - Assignment 3
Weighted Campus Route Finder: BFS, DFS, UCS and IDS

Group 10 (BSSE)
    1. NOMWESIGWA KEITH     23/U/16071/EVE
    2. WAMBUI MARIAM        23/U/18494/PS
    3. LUKAANYA GEORGE      23/U/0696
    4. MUSHEIJA ABRAHAM     23/U/12139/EVE
    5. NALUYANGE KEVIN      18/U/23394/EVE
    6. NABIRYE ANITAH       23/U/12826/EVE

FILE MAP (where to find things)
-------------------------------
  Section 1  Campus data: WEIGHTED_EDGES, build_graph
  Section 2  class Node, expand(), solution(), route_cost()
  Section 3  Frontier classes (FIFO, LIFO, Priority), STRATEGIES table
  Section 4  search()  <- the ONE generic loop used by BFS, DFS and UCS
  Section 5  ids_search() <- the IDS driver (the same loop, depth-limited)
  Section 6  format_result()     (output layout)
  Section 7  prompts and main()  (interactive use and flags)

WHAT THIS PROGRAM DOES
----------------------
It finds a walking route between two places on a simplified model of the
Makerere campus (14 schools + 4 landmarks, 24 two-way edges). The cost of a
route is the sum of its edge weights, in metres. The optimal route is the
cheapest one.

Four uninformed search strategies:

  BFS  - queue (FIFO). Fewest hops. Ignores walking distances.
  DFS  - stack (LIFO). First route found going deep. Ignores distances.
  UCS  - priority queue ordered by PATH-COST, the metres already walked.
         Optimal. Re-opens a state if a cheaper path to it is found.
  IDS  - iterative deepening: a driver (`ids_search`) that reruns the same
         loop as a depth-limited DFS. Fewest hops, uses little memory.

HOW THE STRATEGIES DIFFER (everything else is shared)
-----------------------------------------------------
  strategy | frontier          | reached rule
  ---------+-------------------+------------------------------------------
  BFS      | FIFO queue        | add child if state not in reached
  DFS      | LIFO stack        | add child if state not in reached
  UCS      | priority queue    | not in reached, OR lower PATH-COST
  IDS      | stack in a driver | state not on the path from the root

The weights are read only by the step-cost function, UCS's priority queue
and the code that reports a route's cost; they never decide which node
BFS, DFS or IDS chooses next.

Python 3 standard library only (heapq is the only "search" helper used).

USAGE
-----
    python3 route_finder.py                       # interactive prompts
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a UCS
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a ALL
    python3 route_finder.py ... --trace           # UCS: one line per frontier event
    python3 route_finder.py ... --verbose         # max frontier size, IDS limits
    python3 route_finder.py ... --no-reached      # tree-like search (cap 10,000)
"""

import argparse
import heapq
import itertools
from collections import deque


# ===========================================================================
# 1. THE CAMPUS DATA (copied unchanged from the assignment)
# ===========================================================================

# The four landmarks; every other place is a school.
LANDMARKS = {
    "Main Building", "Freedom Square", "Main Library",
    "Central Teaching Facility",
}

# (place A, place B, walking distance in metres). Every edge is two-way.
WEIGHTED_EDGES = [
    ("Main Building", "Freedom Square", 120),
    ("Main Building", "Main Library", 150),
    ("Main Building", "School of Social Sciences", 200),
    ("Main Building", "School of Liberal and Performing Arts", 350),
    ("Freedom Square", "Main Library", 90),
    ("Freedom Square", "School of Law", 180),
    ("Freedom Square", "Central Teaching Facility", 220),
    ("Main Library", "School of Education", 160),
    ("Main Library", "School of Economics", 400),
    ("Central Teaching Facility", "CoCIS", 130),
    ("Central Teaching Facility", "School of Statistics and Planning", 300),
    ("CoCIS", "School of Statistics and Planning", 100),
    ("CoCIS", "School of Engineering", 250),
    ("School of Engineering", "School of the Built Environment", 90),
    ("School of Engineering", "Margaret Trowell School of Industrial and Fine Art", 140),
    ("School of the Built Environment", "Margaret Trowell School of Industrial and Fine Art", 70),
    ("Margaret Trowell School of Industrial and Fine Art", "School of Liberal and Performing Arts", 450),
    ("School of Education", "School of Social Sciences", 140),
    ("School of Education", "College of Natural Sciences", 300),
    ("College of Natural Sciences", "School of Food Technology, Nutrition and Bioengineering", 380),
    ("School of Food Technology, Nutrition and Bioengineering", "School of Agricultural Sciences", 200),
    ("School of Agricultural Sciences", "School of Veterinary Medicine", 260),
    ("School of Statistics and Planning", "School of Economics", 350),
    ("School of Economics", "School of Law", 120),
]

# Every strategy stops after this many expansions in tree-like mode so the
# program always terminates even when cycles make the search infinite.
MAX_EXPANSIONS = 10_000

# Order in which ALL lists the algorithms.
ALGORITHM_ORDER = ["BFS", "DFS", "UCS", "IDS"]

# Message wording given word for word in the assignment.
CAP_MESSAGE = f"Search stopped: expansion cap ({MAX_EXPANSIONS}) reached."
NO_ROUTE_MESSAGE = "No route found."
IDS_EXTRA_LINE = "Final depth limit: {limit}"   # extra output line printed for IDS


def build_graph(edges):
    """Turn the edge list into a weighted adjacency structure.

    Returns {place: {neighbour: weight}}. Both directions are stored because
    every connection is two-way. Neighbours are stored in alphabetical order
    (case-insensitive), so iterating a place's neighbours is always
    alphabetical - the tie-breaking rule used by every strategy.
    """
    unsorted = {}
    for a, b, weight in edges:
        if weight <= 0:
            raise ValueError(f"Edge {a!r} - {b!r} must have a positive weight")
        unsorted.setdefault(a, {})[b] = weight
        unsorted.setdefault(b, {})[a] = weight
    return {
        place: {n: nbrs[n] for n in sorted(nbrs, key=str.lower)}
        for place, nbrs in sorted(unsorted.items(), key=lambda kv: kv[0].lower())
    }


GRAPH = build_graph(WEIGHTED_EDGES)
PLACES = sorted(GRAPH, key=str.lower)                       # all 18 places


# ===========================================================================
# 2. SEARCH-TREE NODE AND PROBLEM HELPERS
# ===========================================================================

class Node:
    """A node of the search tree: STATE, PARENT, ACTION, PATH-COST, DEPTH."""

    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state                  # the place this node stands for
        self.parent = parent                # node it was generated from
        self.action = action                # "walk to <state>"
        self.path_cost = path_cost          # metres walked from the source
        self.depth = 0 if parent is None else parent.depth + 1   # hops from root

    def __repr__(self):
        return f"Node({self.state!r}, g={self.path_cost})"


def neighbours(graph, state):
    """(neighbour, weight) pairs of `state`, in alphabetical order."""
    return list(graph[state].items())


def step_cost(graph, state, next_state):
    """Step cost c(s, a, s'): the weight of the edge s - s'."""
    return graph[state][next_state]


def expand(graph, node):
    """Generate the children of `node`, in alphabetical order of place name.

    Actions(s) = every neighbour of s; Result(s, a) = that neighbour.
    The child's PATH-COST is the parent's plus the step cost.
    """
    for neighbour, _ in neighbours(graph, node.state):      # alphabetical
        cost = node.path_cost + step_cost(graph, node.state, neighbour)
        yield Node(neighbour, parent=node, action=neighbour, path_cost=cost)


def is_goal(state, goal):
    """Goal test."""
    return state == goal


def solution(node):
    """Follow PARENT pointers back to the root; return the places in order."""
    path = []
    while node is not None:
        path.append(node.state)
        node = node.parent
    return list(reversed(path))


def route_cost(graph, route):
    """Total metres of a route (a list of places), summed edge by edge."""
    return sum(step_cost(graph, a, b) for a, b in zip(route, route[1:]))


# ===========================================================================
# 3. FRONTIERS - where the strategies differ
# ===========================================================================

class FIFOFrontier:
    """Queue: add at the back, remove from the front (BFS)."""

    def __init__(self):
        self.items = deque()

    def add_children(self, children):
        self.items.extend(children)             # alphabetical in = alphabetical out

    def pop(self):
        return self.items.popleft()

    def __len__(self):
        return len(self.items)


class LIFOFrontier:
    """Stack: add at the top, remove from the top (DFS, IDS)."""

    def __init__(self):
        self.items = []

    def add_children(self, children):
        # Push in REVERSE alphabetical order so the alphabetically first
        # neighbour ends up on top of the stack and is explored first.
        self.items.extend(reversed(children))

    def pop(self):
        return self.items.pop()

    def __len__(self):
        return len(self.items)


class PriorityFrontier:
    """Priority queue (heap) ordered by PATH-COST (UCS).

    Heap entries are  (path_cost, state_name, counter, node)  so Python picks:
        1. the lowest cost,
        2. then the alphabetically first state name,
        3. then the earliest inserted node (counter from itertools.count()).
    The counter is unique, so two nodes are never compared directly.
    """

    def __init__(self, trace=False):
        self.trace = trace
        self.heap = []
        self.counter = itertools.count()

    def add_children(self, children):
        for child in children:
            heapq.heappush(
                self.heap,
                (child.path_cost, child.state.lower(), next(self.counter), child)
            )
            if self.trace:
                print(f"push {child.state} g={child.path_cost} key={child.path_cost}")

    def pop(self):
        key, _, _, node = heapq.heappop(self.heap)
        if self.trace:
            print(f"pop {node.state} key={key}")
        return node

    def __len__(self):
        return len(self.heap)


# ---------------------------------------------------------------------------
# Strategy table: a strategy = (how to build its frontier, its reached rule)
# ---------------------------------------------------------------------------

class Strategy:
    """Bundles the two things that define a graph-search strategy.

    make_frontier(trace) -> a new, empty frontier
    reopens: the REACHED RULE.
        False -> a child is added only if its state is not in reached
                 (BFS, DFS; a state is never replaced).
        True  -> a child is also added if it reaches a known state with a
                 strictly lower PATH-COST (UCS); the old, costlier node
                 becomes "stale" and is discarded when it is removed.
    """

    def __init__(self, name, make_frontier, reopens):
        self.name = name
        self.make_frontier = make_frontier
        self.reopens = reopens


STRATEGIES = {
    "BFS": Strategy("BFS", lambda trace: FIFOFrontier(), False),
    "DFS": Strategy("DFS", lambda trace: LIFOFrontier(), False),
    "UCS": Strategy("UCS", lambda trace: PriorityFrontier(trace), True),
}


# ===========================================================================
# 4. THE GENERIC SEARCH LOOP (BFS, DFS, UCS - and IDS through its driver)
# ===========================================================================

class SearchResult:
    """Everything a search reports back."""

    def __init__(self, graph, node, expanded, hit_cap=False, max_frontier=0,
                 limits=None, cutoff=False):
        self.graph = graph
        self.node = node                # goal node, or None if no route
        self.expanded = expanded        # removed from frontier, not goal, children generated
        self.hit_cap = hit_cap          # True if the 10,000-expansion cap stopped the search
        self.max_frontier = max_frontier    # largest frontier size seen
        self.limits = limits or []      # IDS only: [(limit, expanded), ...]
        self.cutoff = cutoff            # depth-limited runs: a node was cut at the limit

    @property
    def route(self):
        return solution(self.node) if self.node else None

    @property
    def cost(self):
        return self.node.path_cost if self.node else None

    @property
    def hops(self):
        return self.node.depth if self.node else None


def search(graph, source, goal, strategy, use_reached=True, trace=False,
           max_expansions=MAX_EXPANSIONS, depth_limit=None, cycle_check=False):
    """THE one search loop. The strategy only supplies the frontier and the
    reached rule; there is no `if algorithm == ...` inside this function.

    1. Make the root node and put it on the frontier (and in `reached`).
    2. If the frontier is empty -> failure ("No route found.").
    3. Remove a node.
       a. STALE RULE (UCS): if its PATH-COST is larger than the cost stored
          in `reached` for its state, a cheaper path was found after it was
          queued -> discard silently, NOT counted as expanded.
       b. GOAL TEST ON REMOVAL (not on generation). This is what makes UCS
          return the cheapest route.
       c. Cap: stop if 10,000 nodes were already expanded.
    4. Expand it (count +1): generate its children in alphabetical order.
    5. REACHED RULE, per child:
         - state not in reached              -> keep it, record it.
         - state in reached, strategy reopens and child's cost is strictly
           lower                             -> keep it, REPLACE the record.
         - otherwise                         -> discard the child.
    6. Add the surviving children to the frontier; go back to step 2.

    With use_reached=False (tree-like mode) there is no reached table:
    nothing is discarded, cycles are not detected, so the cap is what makes
    the search stop.

    IDS reuses this same loop (see `ids_search`) with two extra switches:
      depth_limit - a node at this depth is goal-tested but NOT expanded and
                    not counted; it sets `cutoff` on the result.
      cycle_check - a child is not generated if its place is already on the
                    path from the root to its parent.
    """
    frontier = strategy.make_frontier(trace)
    root = Node(source)
    frontier.add_children([root])                                   # step 1
    reached = {source: root} if use_reached else None
    expanded = 0
    max_frontier = len(frontier)
    cutoff = False               # depth-limited runs: some node was cut at the limit

    while len(frontier) > 0:                                        # step 2
        node = frontier.pop()                                       # step 3

        # 3a. stale node: a cheaper route to this place was found later.
        if reached is not None and strategy.reopens \
                and node.path_cost > reached[node.state].path_cost:
            if trace:
                print(f"stale {node.state}")
            continue

        if is_goal(node.state, goal):                               # 3b
            return SearchResult(graph, node, expanded,
                                max_frontier=max_frontier, cutoff=cutoff)

        if depth_limit is not None and node.depth == depth_limit:  # IDS limit
            cutoff = True                                           # not expanded
            continue

        if expanded >= max_expansions:                              # 3c
            return SearchResult(graph, None, expanded, hit_cap=True,
                                max_frontier=max_frontier)

        expanded += 1                                               # step 4

        on_path = set(solution(node)) if cycle_check else ()
        accepted = []
        for child in expand(graph, node):                           # step 5
            if child.state in on_path:                              # IDS cycle check
                continue
            if reached is not None:
                seen = reached.get(child.state)
                if seen is not None:
                    # Already reached. Keep the child only if this strategy
                    # re-opens states AND the new path is strictly cheaper.
                    if not (strategy.reopens and child.path_cost < seen.path_cost):
                        continue
                    if trace:
                        print(f"replace {child.state} "
                              f"g={seen.path_cost} -> {child.path_cost}")
                reached[child.state] = child
            accepted.append(child)

        frontier.add_children(accepted)                             # step 6
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult(graph, None, expanded,                      # failure
                        max_frontier=max_frontier, cutoff=cutoff)


# ===========================================================================
# 5. ITERATIVE DEEPENING SEARCH (a driver around the same generic loop)
# ===========================================================================

def ids_search(graph, source, goal):
    """IDS driver: depth limits 0, 1, 2, ... until the goal is found.

    Each iteration is the generic `search` loop with a stack (the DFS
    strategy), the reached table OFF, the cycle check ON and a depth limit;
    the driver does not duplicate the loop. Expansions are summed over ALL
    iterations. It stops with "no route" after an iteration in which nothing
    was cut off (the whole reachable space was searched); the limit never
    exceeds the number of places minus one.
    """
    total_expanded = 0
    max_stack = 1
    limits = []
    for limit in range(len(graph)):                 # 0 .. places - 1
        r = search(graph, source, goal, STRATEGIES["DFS"], use_reached=False,
                   depth_limit=limit, cycle_check=True)
        total_expanded += r.expanded
        max_stack = max(max_stack, r.max_frontier)
        limits.append((limit, r.expanded))
        if r.node is not None or not r.cutoff:
            break
    return SearchResult(graph, r.node, total_expanded,
                        max_frontier=max_stack, limits=limits)


def run_algorithm(name, graph, source, goal, use_reached=True, trace=False):
    """Dispatch a canonical algorithm name to its search function.

    This single choice happens OUTSIDE the generic loop. The graph is passed
    in as an argument.
    """
    if name == "IDS":
        return ids_search(graph, source, goal)
    return search(graph, source, goal, STRATEGIES[name],
                  use_reached=use_reached, trace=trace and name == "UCS")


# ===========================================================================
# 6. OUTPUT FORMATTING
# ===========================================================================

def format_result(name, result, verbose=False):
    """Format one algorithm's answer in the Assignment 3 layout."""
    lines = [f"Algorithm: {name}"]
    if result.node is None:
        if result.hit_cap:
            lines.append(CAP_MESSAGE)
        lines.append(NO_ROUTE_MESSAGE)
        lines.append(f"Nodes expanded: {result.expanded}")
    else:
        route = result.route
        # Independent check: the cost the search built up must equal the
        # cost recomputed edge by edge from the graph.
        assert result.cost == route_cost(result.graph, route), "path-cost bug"
        lines.append("Route: " + " -> ".join(route))
        lines.append(f"Cost (metres): {result.cost}")
        lines.append(f"Hops: {result.hops}")
        lines.append(f"Nodes expanded: {result.expanded}")
        if name == "IDS":                          # IDS prints the limit that worked
            lines.append(IDS_EXTRA_LINE.format(limit=result.limits[-1][0]))
    if verbose:
        lines.append(f"Max frontier size: {result.max_frontier}")
        if name == "IDS":
            for limit, expanded in result.limits:
                lines.append(f"limit {limit}: expanded {expanded}")
    return "\n".join(lines)


# ===========================================================================
# 7. USER INTERFACE
# ===========================================================================

_PLACE_LOOKUP = {p.lower(): p for p in PLACES}

ALGORITHM_CHOICES = "BFS, DFS, UCS, IDS or ALL"


def match_place(text):
    """Case-insensitive, whitespace-trimmed place lookup (None if unknown)."""
    return _PLACE_LOOKUP.get(text.strip().lower())


def match_algorithm(text):
    """Return a canonical name, "ALL", or None if the text is not recognised."""
    algo = text.strip().upper()
    return algo if algo in ALGORITHM_ORDER or algo == "ALL" else None


def print_valid_places():
    print("Valid places are:")
    for p in PLACES:
        kind = "landmark" if p in LANDMARKS else "school"
        print(f"  - {p} ({kind})")


def prompt_place(label):
    """Ask until the user types a known place."""
    while True:
        text = input(f"{label}: ")
        place = match_place(text)
        if place:
            return place
        print(f"Unknown place: {text.strip()!r}")
        print_valid_places()


def prompt_algorithm():
    """Ask until the user types a known algorithm."""
    while True:
        text = input(f"Algorithm ({ALGORITHM_CHOICES}): ")
        algo = match_algorithm(text)
        if algo:
            return algo
        print(f"Unknown algorithm: {text.strip()!r}. Please enter {ALGORITHM_CHOICES}.")


def main():
    """Entry point: read the flags, then answer one route query."""
    parser = argparse.ArgumentParser(
        description="Weighted Makerere Campus Route Finder (BFS, DFS, UCS, IDS)")
    parser.add_argument("-s", "--source", help="source place")
    parser.add_argument("-d", "--destination", help="destination place")
    parser.add_argument("-a", "--algorithm", help=ALGORITHM_CHOICES)
    parser.add_argument("--no-reached", "--noreached", action="store_true",
                        dest="no_reached",
                        help="tree-like search for BFS/DFS/UCS (cap 10,000)")
    parser.add_argument("--trace", action="store_true",
                        help="UCS: print push, pop, stale and replace events")
    parser.add_argument("--verbose", action="store_true",
                        help="print max frontier size (and IDS per-limit lines)")
    args = parser.parse_args()
    use_reached = not args.no_reached

    # Order: source -> destination -> algorithm. A value given on the command
    # line is validated exactly like typed input; a bad one falls back to the
    # prompt instead of crashing.
    print("Makerere Campus Route Finder")
    if not use_reached:
        print(f"[tree-like search: reached table OFF, cap {MAX_EXPANSIONS:,} expansions]")
    print()

    try:
        source = match_place(args.source) if args.source else None
        if args.source and not source:
            print(f"Unknown place: {args.source.strip()!r}")
            print_valid_places()
        source = source or prompt_place("Source")

        destination = match_place(args.destination) if args.destination else None
        if args.destination and not destination:
            print(f"Unknown place: {args.destination.strip()!r}")
            print_valid_places()
        # Source equal to destination is allowed: every algorithm returns a
        # one-place route with cost 0, hops 0 and 0 nodes expanded.
        destination = destination or prompt_place("Destination")

        algorithm = match_algorithm(args.algorithm) if args.algorithm else None
        if args.algorithm and not algorithm:
            print(f"Unknown algorithm: {args.algorithm.strip()!r}. "
                  f"Please enter {ALGORITHM_CHOICES}.")
        algorithm = algorithm or prompt_algorithm()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    # ALL runs the four algorithms in the fixed order BFS, DFS, UCS, IDS.
    names = ALGORITHM_ORDER if algorithm == "ALL" else [algorithm]
    blocks = []
    for name in names:
        result = run_algorithm(name, GRAPH, source, destination,
                               use_reached=use_reached, trace=args.trace)
        blocks.append(format_result(name, result, verbose=args.verbose))
    print()
    print("\n\n".join(blocks))          # one block per algorithm, blank line between


if __name__ == "__main__":
    main()
