"""
CSC 2114 Artificial Intelligence - Assignment 4
Weighted Campus Route Finder: BFS, DFS, UCS, IDS, GBFS and A*

Group 10 (BSSE)
    1. NOMWESIGWA KEITH     23/U/16071/EVE
    2. WAMBUI MARIAM        23/U/18494/PS
    3. LUKAANYA GEORGE      23/U/0696
    4. MUSHEIJA ABRAHAM     23/U/12139/EVE
    5. NALUYANGE KEVIN      18/U/23394/EVE
    6. NABIRYE ANITAH       23/U/12826/EVE

FILE MAP (where to find things)
-------------------------------
  Section 1  Campus data: WEIGHTED_EDGES, COORDINATES, REQUIRED_PROBLEMS, build_graph
  Section 2  The heuristic h(place, goal) and H_SCALE_PERCENT
  Section 3  class Node, expand(), solution(), route_cost()
  Section 4  Frontier classes (FIFO, LIFO, Priority), the KEY FUNCTIONS, STRATEGIES table
  Section 5  search()  <- the ONE generic loop used by BFS, DFS, UCS, GBFS and A*
  Section 6  ids_search() <- the IDS driver (repeated depth-limited DFS)
  Section 7  check_heuristic()   (--check-heuristic)
  Section 8  format_result()     (output layout)
  Section 9  run_batch()         (--batch  -> results_log.csv)
  Section 10 run_scan()          (--scan   -> 182-pair summary)
  Section 11 prompts and main()  (interactive use and flags)

WHAT THIS PROGRAM DOES
----------------------
It finds a walking route between two places on a simplified model of the
Makerere campus (14 schools + 4 landmarks, 24 two-way edges). The cost of a
route is the sum of its edge weights, in metres. The optimal route is the
cheapest one.

Six search strategies share ONE generic search loop (see `search`):

  BFS  - queue (FIFO). Fewest hops. Ignores walking distances.
  DFS  - stack (LIFO). First route found going deep. Ignores distances.
  UCS  - priority queue ordered by g(n), the metres already walked.
         Optimal. Re-opens a state if a cheaper path to it is found.
  IDS  - iterative deepening: repeated depth-limited DFS (own driver,
         `ids_search`). Fewest hops, uses little memory.
  GBFS - priority queue ordered by h(n), the ESTIMATED metres still to go.
         Fast but not guaranteed cheapest. Never replaces a state.
  A*   - priority queue ordered by f(n) = g(n) + h(n). Optimal here because
         h is admissible and consistent, and the goal test happens when a
         node is REMOVED from the frontier.

HOW THE STRATEGIES DIFFER (everything else is shared)
-----------------------------------------------------
  strategy | frontier          | priority key   | reached rule
  ---------+-------------------+----------------+-------------------------------
  BFS      | FIFO queue        | -              | add child if state not reached
  DFS      | LIFO stack        | -              | add child if state not reached
  UCS      | priority queue    | g              | not reached, OR lower g
  GBFS     | priority queue    | h              | not reached (never replaced)
  A*       | priority queue    | g + h          | not reached, OR lower g
  IDS      | stack in a driver | -              | state not on the path to root

THE HEURISTIC
-------------
h(place, goal) = straight-line distance between the two places on the map,
rounded DOWN to whole metres (math.isqrt, so every machine gets identical
integers and ties are real ties). Only GBFS and A* (and the checking code
`check_heuristic`) may use h or COORDINATES. BFS, DFS, UCS and IDS never
touch them.

Python 3 standard library only (heapq is the only "search" helper used).

USAGE
-----
    python3 route_finder.py                       # interactive prompts
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a "A*"
    python3 route_finder.py -s "School of Law" -d "CoCIS" -a ALL
    python3 route_finder.py ... --trace           # one line per frontier event
    python3 route_finder.py ... --verbose         # max frontier size, IDS limits
    python3 route_finder.py ... --no-reached      # tree-like search (cap 10,000)
    python3 route_finder.py --check-heuristic     # verify h is consistent/admissible
    python3 route_finder.py --batch               # the 10 problems -> results_log.csv
    python3 route_finder.py --scan                # all 182 ordered school pairs
"""

import argparse
import csv
import heapq
import itertools
import math
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

# (x, y) position of every place on a flat map, in whole metres.
COORDINATES = {
    "Main Building": (500, 455),
    "Freedom Square": (565, 370),
    "Main Library": (610, 435),
    "Central Teaching Facility": (425, 220),
    "CoCIS": (380, 115),
    "School of Engineering": (155, 75),
    "School of the Built Environment": (80, 70),
    "Margaret Trowell School of Industrial and Fine Art": (40, 110),
    "School of Law": (700, 260),
    "School of Education": (665, 570),
    "School of Social Sciences": (560, 630),
    "School of Liberal and Performing Arts": (165, 520),
    "School of Economics": (720, 155),
    "School of Statistics and Planning": (425, 40),
    "College of Natural Sciences": (860, 745),
    "School of Food Technology, Nutrition and Bioengineering": (1065, 990),
    "School of Agricultural Sciences": (1170, 1115),
    "School of Veterinary Medicine": (1310, 1275),
}

# The ten problems every group must run (Part C1): (source, destination).
REQUIRED_PROBLEMS = [
    ("CoCIS", "School of Law"),
    ("School of Education", "School of Veterinary Medicine"),
    ("School of the Built Environment", "School of Law"),
    ("Margaret Trowell School of Industrial and Fine Art", "School of Veterinary Medicine"),
    ("School of Economics", "School of Liberal and Performing Arts"),
    ("CoCIS", "School of Statistics and Planning"),
    ("College of Natural Sciences", "School of Economics"),
    ("School of Social Sciences", "School of Engineering"),
    ("School of Food Technology, Nutrition and Bioengineering", "School of Law"),
    ("School of Agricultural Sciences", "Margaret Trowell School of Industrial and Fine Art"),
]

# Every strategy stops after this many expansions in tree-like mode so the
# program always terminates even when cycles make the search infinite.
MAX_EXPANSIONS = 10_000

# Scales the heuristic. Leave at 100 for submission; Part C3 changes it.
H_SCALE_PERCENT = 100

# Order in which ALL, --batch and the report list the algorithms.
ALGORITHM_ORDER = ["BFS", "DFS", "UCS", "IDS", "GBFS", "A*"]

# ---------------------------------------------------------------------------
# Message wording. The first two are given word for word in the assignment.
# The last two are not spelled out in the assignment text; they live here,
# in one place, so they can be matched to the Assignment 3 wording instantly.
# ---------------------------------------------------------------------------
CAP_MESSAGE = f"Search stopped: expansion cap ({MAX_EXPANSIONS}) reached."   # given
NO_ROUTE_MESSAGE = "No route found."                                         # given
SAME_PLACE_MESSAGE = ("Source and destination are the same place. "
                      "Please choose a different destination.")
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
SCHOOLS = [p for p in PLACES if p not in LANDMARKS]         # the 14 schools


# ===========================================================================
# 2. THE HEURISTIC (used ONLY by GBFS, A* and check_heuristic)
# ===========================================================================

def h(place, goal, coordinates=None):
    """Estimated metres still to walk from `place` to `goal`.

    = straight-line map distance, rounded down, times H_SCALE_PERCENT / 100.
    h(goal, goal) = 0.

    The search code always passes `coordinates` explicitly (so a modified
    copy of the coordinates is honoured). The fall-back to the module-level
    COORDINATES exists only so that h(place, goal) works exactly as written
    in the assignment when called by hand.
    """
    if coordinates is None:
        coordinates = COORDINATES
    (x1, y1), (x2, y2) = coordinates[place], coordinates[goal]
    return math.isqrt((x1 - x2) ** 2 + (y1 - y2) ** 2) * H_SCALE_PERCENT // 100


# ===========================================================================
# 3. SEARCH-TREE NODE AND PROBLEM HELPERS
# ===========================================================================

class Node:
    """A node of the search tree: STATE, PARENT, ACTION, PATH-COST, DEPTH."""

    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state                  # the place this node stands for
        self.parent = parent                # node it was generated from
        self.action = action                # "walk to <state>"
        self.path_cost = path_cost          # g(n): metres walked from the source
        self.depth = 0 if parent is None else parent.depth + 1   # hops from root

    def __repr__(self):
        return f"Node({self.state!r}, g={self.path_cost})"


def step_cost(graph, state, next_state):
    """Step cost c(s, a, s'): the weight of the edge s - s'."""
    return graph[state][next_state]


def expand(graph, node):
    """Generate the children of `node`, in alphabetical order of place name.

    Actions(s) = every neighbour of s; Result(s, a) = that neighbour.
    The child's PATH-COST is the parent's plus the step cost.
    """
    for neighbour in graph[node.state]:                 # alphabetical
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
# 4. FRONTIERS - where the strategies differ
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
    """Stack: add at the top, remove from the top (DFS)."""

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
    """Priority queue (heap) used by UCS, GBFS and A*.

    The ONLY thing that changes between those three is `key_fn(node, goal)`.
    Heap entries are  (key, state_name, counter, node)  so Python picks:
        1. the smallest key,
        2. then the alphabetically first state name,
        3. then the earliest inserted node (counter from itertools.count()).
    The counter is unique, so two nodes are never compared directly.

    `h_fn` is supplied only for GBFS/A*; it is used purely to print the h
    value in --trace output. UCS passes None, so UCS never computes h.
    """

    def __init__(self, goal, key_fn, h_fn=None, trace=False):
        self.goal = goal
        self.key_fn = key_fn
        self.h_fn = h_fn
        self.trace = trace
        self.heap = []
        self.counter = itertools.count()

    def add_children(self, children):
        for child in children:
            key = self.key_fn(child, self.goal)
            heapq.heappush(
                self.heap, (key, child.state.lower(), next(self.counter), child)
            )
            if self.trace:
                if self.h_fn is None:                                   # UCS
                    print(f"push {child.state} g={child.path_cost} key={key}")
                else:                                                   # GBFS, A*
                    print(f"push {child.state} g={child.path_cost} "
                          f"h={self.h_fn(child.state, self.goal)} key={key}")

    def pop(self):
        key, _, _, node = heapq.heappop(self.heap)
        if self.trace:
            print(f"pop {node.state} key={key}")
        return node

    def __len__(self):
        return len(self.heap)


# ---------------------------------------------------------------------------
# Priority key functions: key(node, goal). These are the whole difference
# between UCS, GBFS and A*.
# ---------------------------------------------------------------------------

def ucs_key(node, goal):
    """UCS: f(n) = g(n). Looks only at the cost already paid."""
    return node.path_cost


def make_gbfs_key(coordinates):
    """GBFS: f(n) = h(n). Looks only at the estimated cost still to go.
    (Deliberately never reads node.path_cost.)"""
    def key(node, goal):
        return h(node.state, goal, coordinates)
    return key


def make_astar_key(coordinates):
    """A*: f(n) = g(n) + h(n). Uses both."""
    def key(node, goal):
        return node.path_cost + h(node.state, goal, coordinates)
    return key


# ---------------------------------------------------------------------------
# Strategy table: a strategy = (how to build its frontier, its reached rule)
# ---------------------------------------------------------------------------

class Strategy:
    """Bundles the two things that define a graph-search strategy.

    make_frontier(goal, coordinates, trace) -> a new, empty frontier
    reopens: the REACHED RULE.
        False -> a child is added only if its state is not in reached
                 (BFS, DFS, GBFS; a state is never replaced).
        True  -> a child is also added if it reaches a known state with a
                 strictly lower g (UCS, A*); the old, costlier node becomes
                 "stale" and is discarded when it is eventually removed.
    """

    def __init__(self, name, make_frontier, reopens):
        self.name = name
        self.make_frontier = make_frontier
        self.reopens = reopens


def _heuristic_for_trace(coordinates):
    return lambda place, goal: h(place, goal, coordinates)


STRATEGIES = {
    "BFS": Strategy("BFS", lambda goal, coords, trace: FIFOFrontier(), False),
    "DFS": Strategy("DFS", lambda goal, coords, trace: LIFOFrontier(), False),
    "UCS": Strategy(
        "UCS",
        lambda goal, coords, trace: PriorityFrontier(goal, ucs_key, None, trace),
        True),
    "GBFS": Strategy(
        "GBFS",
        lambda goal, coords, trace: PriorityFrontier(
            goal, make_gbfs_key(coords), _heuristic_for_trace(coords), trace),
        False),
    "A*": Strategy(
        "A*",
        lambda goal, coords, trace: PriorityFrontier(
            goal, make_astar_key(coords), _heuristic_for_trace(coords), trace),
        True),
}
INFORMED = {"GBFS", "A*"}        # strategies allowed to use h / coordinates


# ===========================================================================
# 5. THE GENERIC SEARCH LOOP (BFS, DFS, UCS, GBFS, A*)
# ===========================================================================

class SearchResult:
    """Everything a search reports back."""

    def __init__(self, graph, node, expanded, hit_cap=False, max_frontier=0,
                 reopened=0, limits=None):
        self.graph = graph
        self.node = node                # goal node, or None if no route
        self.expanded = expanded        # removed from frontier, not goal, children generated
        self.hit_cap = hit_cap          # True if the 10,000-expansion cap stopped the search
        self.max_frontier = max_frontier    # largest frontier size seen
        self.reopened = reopened        # re-reached an already-expanded state with lower g
        self.limits = limits or []      # IDS only: [(limit, expanded, outcome), ...]

    @property
    def route(self):
        return solution(self.node) if self.node else None

    @property
    def cost(self):
        return route_cost(self.graph, self.route) if self.node else None

    @property
    def hops(self):
        return len(self.route) - 1 if self.node else None


def search(graph, source, goal, strategy, coordinates=None,
           use_reached=True, trace=False, max_expansions=MAX_EXPANSIONS):
    """THE one search loop. The strategy only supplies the frontier and the
    reached rule; there is no `if algorithm == ...` inside this function.

    1. Make the root node and put it on the frontier (and in `reached`).
    2. If the frontier is empty -> failure ("No route found").
    3. Remove a node.
       a. STALE RULE (UCS, A*): if its g is larger than the g stored in
          `reached` for its state, a cheaper path was found after it was
          queued -> discard silently, NOT counted as expanded.
       b. GOAL TEST ON REMOVAL (not on generation). This is what makes UCS
          and A* return the cheapest route.
       c. Cap: stop if 10,000 nodes were already expanded.
    4. Expand it (count +1): generate its children in alphabetical order.
    5. REACHED RULE, per child:
         - state not in reached              -> keep it, record it.
         - state in reached, strategy reopens and child's g is strictly
           lower                             -> keep it, REPLACE the record.
         - otherwise                         -> discard the child.
    6. Add the surviving children to the frontier; go back to step 2.

    With use_reached=False (tree-like mode) there is no reached table:
    nothing is discarded, cycles are not detected, so the cap is what makes
    the search stop.
    """
    frontier = strategy.make_frontier(goal, coordinates, trace)
    root = Node(source)
    frontier.add_children([root])                                   # step 1
    reached = {source: root} if use_reached else None
    expanded_states = set()      # places already expanded (to count reopenings)
    expanded = 0
    reopened = 0
    max_frontier = len(frontier)

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
                                max_frontier=max_frontier, reopened=reopened)

        if expanded >= max_expansions:                              # 3c
            return SearchResult(graph, None, expanded, hit_cap=True,
                                max_frontier=max_frontier, reopened=reopened)

        expanded += 1                                               # step 4
        expanded_states.add(node.state)

        accepted = []
        for child in expand(graph, node):                           # step 5
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
                    if child.state in expanded_states:
                        reopened += 1       # a place we had ALREADY expanded
                reached[child.state] = child
            accepted.append(child)

        frontier.add_children(accepted)                             # step 6
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult(graph, None, expanded,                      # failure
                        max_frontier=max_frontier, reopened=reopened)


# ===========================================================================
# 6. ITERATIVE DEEPENING SEARCH (its own driver around a depth-limited DFS)
# ===========================================================================

def depth_limited_search(graph, source, goal, limit):
    """Depth-limited DFS with a stack.

    Cycle check: a child is skipped only if its state is already on the path
    from the root to its parent (no reached table). A node at depth == limit
    is not expanded (its children are not generated), so it does not count
    as expanded. Returns (goal_node_or_None, expanded, cutoff, max_stack).
    """
    stack = LIFOFrontier()
    stack.add_children([Node(source)])
    expanded = 0
    cutoff = False                      # True if some node was cut at the limit
    max_stack = len(stack)
    while len(stack) > 0:
        node = stack.pop()
        if is_goal(node.state, goal):                       # goal test on removal
            return node, expanded, cutoff, max_stack
        if node.depth == limit:         # at the limit: do not go deeper
            cutoff = True
            continue
        expanded += 1
        on_path = set(solution(node))   # places on the root -> node path
        children = [c for c in expand(graph, node) if c.state not in on_path]
        stack.add_children(children)    # reversed inside -> alphabetical first
        max_stack = max(max_stack, len(stack))
    return None, expanded, cutoff, max_stack


def ids_search(graph, source, goal):
    """IDS driver: depth limits 0, 1, 2, ... until the goal is found.

    Expansions are summed over ALL iterations. The driver stops with
    "no route" after a pass in which nothing was cut off (the whole space
    within reach has been searched).
    """
    total_expanded = 0
    max_stack = 1
    limits = []
    limit = 0
    while True:
        node, expanded, cutoff, stack_peak = depth_limited_search(
            graph, source, goal, limit)
        total_expanded += expanded
        max_stack = max(max_stack, stack_peak)
        outcome = "goal found" if node else ("cutoff" if cutoff else "exhausted")
        limits.append((limit, expanded, outcome))
        if node is not None:
            return SearchResult(graph, node, total_expanded,
                                max_frontier=max_stack, limits=limits)
        if not cutoff:
            return SearchResult(graph, None, total_expanded,
                                max_frontier=max_stack, limits=limits)
        limit += 1


def run_algorithm(name, graph, source, goal, coordinates,
                  use_reached=True, trace=False):
    """Dispatch a canonical algorithm name to its search function.

    This single choice happens OUTSIDE the generic loop. Graph, coordinates
    and goal are all passed in as arguments.
    """
    if name == "IDS":
        return ids_search(graph, source, goal)
    return search(graph, source, goal, STRATEGIES[name], coordinates,
                  use_reached=use_reached, trace=trace)


# ===========================================================================
# 7. HEURISTIC CHECKS (B1)
# ===========================================================================

def check_heuristic(graph, coordinates):
    """Verify the two properties the A* optimality argument needs.

    1. Consistency: for every goal and every DIRECTED edge u -> v,
           h(u, goal) <= weight(u, v) + h(v, goal).
       (18 goals x 48 directed edges = 864 checks.)
    2. Admissibility: for every ordered pair of distinct places,
           h(place, goal) <= the cost UCS finds from place to goal.
       (18 x 17 = 306 pairs.)

    Returns (consistency_checks, consistency_violations,
             admissibility_pairs, admissibility_violations).
    """
    c_checks = c_bad = 0
    for goal in graph:
        for u in graph:
            for v, weight in graph[u].items():
                c_checks += 1
                if h(u, goal, coordinates) > weight + h(v, goal, coordinates):
                    c_bad += 1

    a_pairs = a_bad = 0
    for goal in graph:
        for place in graph:
            if place == goal:
                continue
            a_pairs += 1
            optimal = search(graph, place, goal, STRATEGIES["UCS"]).cost
            if h(place, goal, coordinates) > optimal:
                a_bad += 1
    return c_checks, c_bad, a_pairs, a_bad


# ===========================================================================
# 8. OUTPUT FORMATTING
# ===========================================================================

def format_result(name, result, source, goal, coordinates, verbose=False):
    """Format one algorithm's answer in the Assignment 3/4 layout."""
    lines = [f"Algorithm: {name}"]
    if result.node is None:
        if result.hit_cap:
            lines.append(CAP_MESSAGE)
        lines.append(NO_ROUTE_MESSAGE)
        lines.append(f"Nodes expanded: {result.expanded}")
    else:
        route = result.route
        lines.append("Route: " + " -> ".join(route))
        lines.append(f"Cost (metres): {result.cost}")
        lines.append(f"Hops: {result.hops}")
        lines.append(f"Nodes expanded: {result.expanded}")
        if name in INFORMED:                       # GBFS and A* print h(source)
            lines.append(f"Heuristic at source: {h(source, goal, coordinates)}")
        if name == "IDS":                          # IDS prints the limit that worked
            lines.append(IDS_EXTRA_LINE.format(limit=result.limits[-1][0]))
    if verbose:
        lines.append(f"Max frontier size: {result.max_frontier}")
        if name == "IDS":
            for limit, expanded, outcome in result.limits:
                lines.append(f"  Depth limit {limit}: {expanded} expanded, {outcome}")
    return "\n".join(lines)


# ===========================================================================
# 9. --batch : the ten required problems -> results_log.csv
# ===========================================================================

CSV_HEADER = ["problem", "source", "destination", "algorithm",
              "route", "cost_m", "hops", "nodes_expanded"]


def run_batch(graph, coordinates, problems=REQUIRED_PROBLEMS,
              path="results_log.csv"):
    """Run every problem with all six algorithms; write 60 data rows."""
    rows = []
    for number, (source, goal) in enumerate(problems, start=1):
        for name in ALGORITHM_ORDER:
            r = run_algorithm(name, graph, source, goal, coordinates)
            rows.append([
                number, source, goal, name,
                " -> ".join(r.route) if r.node else "",
                r.cost if r.node else "",
                r.hops if r.node else "",
                r.expanded,
            ])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    print(f"Wrote {path} ({len(rows)} rows)")


# ===========================================================================
# 10. --scan : UCS, A* and GBFS on all 182 ordered pairs of schools
# ===========================================================================

def run_scan(graph, coordinates, schools=SCHOOLS):
    """Compare UCS, A* and GBFS on every ordered pair of distinct schools
    (direction matters because h depends on the goal) and print a summary."""
    # 14 x 13 = 182 ordered pairs: A->B and B->A are different problems.
    pairs = [(s, d) for s in schools for d in schools if s != d]

    # --- counters for the summary lines (one per printed line) ---
    astar_equals_ucs = astar_fewer = astar_same = 0   # A* against UCS
    gbfs_costlier = gbfs_fewer_nodes = beat_but_lost = 0   # GBFS against A*
    tot_ucs = tot_astar = tot_gbfs = 0                # total nodes expanded
    reopened = 0                                      # A* re-opened states
    extra_total = extra_max = 0                       # extra metres paid by GBFS
    lost_cases = []                                   # pairs GBFS 'won' on nodes but lost on cost

    for source, goal in pairs:
        # Solve the same problem three ways (graph-search mode, reached table ON).
        ucs = run_algorithm("UCS", graph, source, goal, coordinates)    # optimal baseline
        astar = run_algorithm("A*", graph, source, goal, coordinates)
        gbfs = run_algorithm("GBFS", graph, source, goal, coordinates)

        tot_ucs += ucs.expanded
        tot_astar += astar.expanded
        tot_gbfs += gbfs.expanded
        reopened += astar.reopened

        if astar.cost == ucs.cost:
            astar_equals_ucs += 1
        if astar.expanded < ucs.expanded:
            astar_fewer += 1
        elif astar.expanded == ucs.expanded:
            astar_same += 1

        # GBFS 'costlier' = it walked more metres than A* (which equals optimal).
        # GBFS 'fewer'    = it expanded strictly fewer nodes than A*.
        costlier = gbfs.cost > astar.cost
        fewer = gbfs.expanded < astar.expanded
        if costlier:
            gbfs_costlier += 1
            extra = gbfs.cost - astar.cost
            extra_total += extra
            extra_max = max(extra_max, extra)
        if fewer:
            gbfs_fewer_nodes += 1
        if costlier and fewer:
            beat_but_lost += 1
            lost_cases.append((source, goal, astar, gbfs))

    # Mean extra metres, rounded half-up to a whole number.
    mean_extra = (2 * extra_total + gbfs_costlier) // (2 * gbfs_costlier) \
        if gbfs_costlier else 0

    print(f"Scan of {len(pairs)} ordered school pairs")
    print(f"A* returned the UCS cost: {astar_equals_ucs}")
    print(f"A* expanded fewer nodes than UCS: {astar_fewer}")
    print(f"A* expanded the same number as UCS: {astar_same}")
    print(f"GBFS returned a costlier route than A*: {gbfs_costlier}")
    print(f"GBFS expanded fewer nodes than A*: {gbfs_fewer_nodes}")
    print(f"GBFS beat A* on nodes but lost on cost: {beat_but_lost}")
    print(f"Total nodes expanded (UCS / A* / GBFS): "
          f"{tot_ucs} / {tot_astar} / {tot_gbfs}")
    print(f"A* reopened states: {reopened}")
    print(f"Mean extra metres when GBFS is costlier: {mean_extra}")
    print(f"Largest extra metres: {extra_max}")
    # One line per "beat on nodes, lost on cost" pair, alphabetical.
    lost_cases.sort(key=lambda c: (c[0].lower(), c[1].lower()))
    for source, goal, astar, gbfs in lost_cases:
        print(f"{source} -> {goal}: A* {astar.cost} m / {astar.expanded} nodes, "
              f"GBFS {gbfs.cost} m / {gbfs.expanded} nodes")


# ===========================================================================
# 11. USER INTERFACE
# ===========================================================================

_PLACE_LOOKUP = {p.lower(): p for p in PLACES}

_ALGORITHM_ALIASES = {"ASTAR": "A*"}
ALGORITHM_CHOICES = "BFS, DFS, UCS, IDS, GBFS, ASTAR (or A*) or ALL"


def match_place(text):
    """Case-insensitive, whitespace-trimmed place lookup (None if unknown)."""
    return _PLACE_LOOKUP.get(text.strip().lower())


def match_algorithm(text):
    """Return a canonical name, "ALL", or None if the text is not recognised."""
    algo = text.strip().upper()
    algo = _ALGORITHM_ALIASES.get(algo, algo)
    return algo if algo in STRATEGIES or algo in ("IDS", "ALL") else None


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
    """Entry point: read the flags, then either run a tool (--check-heuristic,
    --batch, --scan) or answer one route query interactively."""
    # Flags with a hyphen (--no-reached, --check-heuristic) also accept the
    # un-hyphenated spelling, so either form from the handout works.
    parser = argparse.ArgumentParser(
        description="Weighted Makerere Campus Route Finder "
                    "(BFS, DFS, UCS, IDS, GBFS, A*)")
    parser.add_argument("-s", "--source", help="source place")
    parser.add_argument("-d", "--destination", help="destination place")
    parser.add_argument("-a", "--algorithm",
                        help=ALGORITHM_CHOICES + ' (quote A* in the shell: "A*")')
    parser.add_argument("--no-reached", "--noreached", action="store_true",
                        dest="no_reached",
                        help="tree-like search for BFS/DFS/UCS/GBFS/A* (cap 10,000)")
    parser.add_argument("--trace", action="store_true",
                        help="UCS/GBFS/A*: print push, pop, stale and replace events")
    parser.add_argument("--verbose", action="store_true",
                        help="print max frontier size (and IDS per-limit lines)")
    parser.add_argument("--check-heuristic", "--checkheuristic", action="store_true",
                        dest="check_heuristic",
                        help="verify consistency and admissibility of h, then exit")
    parser.add_argument("--batch", action="store_true",
                        help="run the ten required problems, write results_log.csv")
    parser.add_argument("--scan", action="store_true",
                        help="UCS vs A* vs GBFS on all 182 ordered school pairs")
    args = parser.parse_args()
    use_reached = not args.no_reached

    # ---- Non-interactive tools: run, print, exit ---------------------------
    if args.check_heuristic:
        c, cv, a, av = check_heuristic(GRAPH, COORDINATES)
        print(f"Consistency: {c} checks, {cv} violations")
        print(f"Admissibility: {a} pairs, {av} violations")
        return
    if args.batch:
        run_batch(GRAPH, COORDINATES)
        return
    if args.scan:
        run_scan(GRAPH, COORDINATES)
        return

    # ---- Interactive / single-query mode -----------------------------------
    # Order: source -> destination -> algorithm. A value given on the command
    # line is validated exactly like typed input; a bad one falls back to the
    # prompt instead of crashing.
    print("Makerere Campus Route Finder")
    if not use_reached:
        print(f"[tree-like search: reached table OFF, cap {MAX_EXPANSIONS:,} expansions]")
    print()

    try:
        # A bad command-line value is reported, then the program falls back
        # to the interactive prompt instead of crashing.
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
        while destination == source:
            print(SAME_PLACE_MESSAGE)
            destination = prompt_place("Destination")

        algorithm = match_algorithm(args.algorithm) if args.algorithm else None
        if args.algorithm and not algorithm:
            print(f"Unknown algorithm: {args.algorithm.strip()!r}. "
                  f"Please enter {ALGORITHM_CHOICES}.")
        algorithm = algorithm or prompt_algorithm()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    # ALL runs the six algorithms in the fixed order BFS, DFS, UCS, IDS, GBFS, A*.
    names = ALGORITHM_ORDER if algorithm == "ALL" else [algorithm]
    blocks = []
    for name in names:
        if args.trace and algorithm == "ALL" and name in STRATEGIES:
            print(f"--- trace: {name} ---")
        result = run_algorithm(name, GRAPH, source, destination, COORDINATES,
                               use_reached=use_reached, trace=args.trace)
        blocks.append(format_result(name, result, source, destination,
                                    COORDINATES, verbose=args.verbose))
    print()
    print("\n\n".join(blocks))          # one block per algorithm, blank line between


if __name__ == "__main__":
    main()
