# Makerere Campus Route Finder (BFS, DFS, UCS, Greedy and A*)

CSC 2114 Artificial Intelligence, Practical / Assignment 1.

`route_finder.py` finds a walking route between two places on a simplified
model of the Makerere University main campus (14 schools, 4 landmarks, 24
two-way connections). It offers five search algorithms:

- **Uninformed:** Breadth-First Search (BFS), Depth-First Search (DFS) and
  Uniform-Cost Search (UCS).
- **Informed:** Greedy Best-First Search (`GREEDY`) and A* search (`A*`), which
  use a heuristic estimate of the remaining cost.

Every connection has a walking cost in minutes (see `EDGES` in
`route_finder.py`). BFS and DFS ignore these costs. BFS finds the route with the
fewest hops. UCS and A* find the route with the lowest total cost in minutes.
Greedy is fast but can return a more expensive route. The costs are
illustrative values, not measured walking times.

## Heuristic

Greedy and A* use

```
h(n) = 2 × (fewest hops from n to the destination)
```

where 2 minutes is the cheapest edge on the map.

- **Admissible:** any route from n needs at least that many hops, and every hop
  costs at least 2, so h never overestimates the true cost.
- **Consistent:** neighbouring places differ by at most one hop and every edge
  costs at least 2, so h(n) ≤ c(n, n′) + h(n′). This is why A* still returns the
  cheapest route while using the reached table.

Requires Python 3 only (standard library, no installs).

## Running

From this folder:

```bash
python3 route_finder.py
```

The program prompts for the source, destination and algorithm:

```
Source: school of law
Destination: margaret trowell school of industrial and fine art
Algorithm (BFS, DFS, UCS, GREEDY or A*): bfs

Algorithm: BFS
Route: School of Law -> Freedom Square -> Main Building -> School of Liberal and Performing Arts -> Margaret Trowell School of Industrial and Fine Art
Cost (hops): 4
Nodes expanded: 12
```

UCS prints the same lines, plus the cost of each leg and the total in minutes:

```
Algorithm: UCS
Route: School of Law -> School of Economics -> School of Statistics and Planning -> CoCIS -> School of Engineering -> Margaret Trowell School of Industrial and Fine Art
Cost (hops): 5
Leg costs:
  School of Law -> School of Economics: 3
  School of Economics -> School of Statistics and Planning: 6
  School of Statistics and Planning -> CoCIS: 2
  CoCIS -> School of Engineering: 4
  School of Engineering -> Margaret Trowell School of Industrial and Fine Art: 5
Total cost (min): 20
Nodes expanded: 14
```

On this pair, UCS takes one more hop than BFS but saves 2 minutes (20 against 22).

Greedy and A* print the same lines as UCS, plus `Heuristic h(source)`. On the
same pair, A* returns the same 20-minute route as UCS with 12 expansions instead
of 14. Greedy expands only 4 nodes, but returns the 22-minute route.

### Command-line options

| Option | Meaning |
|---|---|
| `-s`, `--source` | Source place (skips that prompt) |
| `-d`, `--destination` | Destination place (skips that prompt) |
| `-a`, `--algorithm` | `BFS`, `DFS`, `UCS`, `GREEDY` or `A*` (skips that prompt). `ASTAR` and `GBFS` also work |
| `--no-reached` | Turn off the reached table (tree-like search, capped at 10,000 expansions) |
| `-h`, `--help` | Show help |

Examples:

```bash
# Non-interactive run
python3 route_finder.py -s "School of Law" -d "CoCIS" -a DFS

# Cheapest route by walking time
python3 route_finder.py -s "School of Law" -d "CoCIS" -a UCS

# Informed search (quote A* so the shell doesn't expand it)
python3 route_finder.py -s "School of Law" -d "CoCIS" -a GREEDY
python3 route_finder.py -s "School of Law" -d "CoCIS" -a "A*"

# Tree-like DFS (no reached table): hits the 10,000-expansion cap
python3 route_finder.py --no-reached -s "School of Law" \
    -d "Margaret Trowell School of Industrial and Fine Art" -a DFS
```

Put quotes around any place name that contains spaces.

## Input rules

- Place names are case-insensitive, and leading or trailing spaces are ignored.
  You must type the full name.
- An unknown place prints the list of valid places and asks again. An unknown
  algorithm asks again.
- If the source equals the destination, the route is one place with cost 0.
- If no route exists, the program prints `No route found`.

## Valid places

**Landmarks:** Central Teaching Facility, Freedom Square, Main Building, Main Library.

**Schools:** CoCIS; College of Natural Sciences; Margaret Trowell School of
Industrial and Fine Art; School of Agricultural Sciences; School of Economics;
School of Education; School of Engineering; School of Food Technology,
Nutrition and Bioengineering; School of Law; School of Liberal and Performing
Arts; School of Social Sciences; School of Statistics and Planning; School of
Veterinary Medicine; School of the Built Environment.

## Design summary

- **`Node`** stores the four lecture fields: `state`, `parent`, `action` and `path_cost`.
- **`solution(node)`** follows the `parent` pointers back to the root and returns the route.
- **`search(problem, frontier_class, use_reached)`** is the single generic search loop.
  The algorithms differ only in the frontier:
  - BFS uses `FIFOFrontier`, a queue that removes from the front.
  - DFS uses `LIFOFrontier`, a stack that removes from the back.
  - UCS uses `PriorityFrontier`, a priority queue (`heapq`) that removes the
    node with the lowest path cost g(n). Ties are broken alphabetically, then
    by insertion order.
  - Greedy uses `GreedyFrontier`, ordered by h(n).
  - A* uses `AStarFrontier`, ordered by f(n) = g(n) + h(n).
  Both are subclasses of `PriorityFrontier` that override only `priority()`.
- **Goal test:** a node is tested when it is removed from the frontier.
- **Reached table:** a state is added to `reached` when its node is generated.
  For BFS and DFS, the frontier therefore never holds two nodes for the same
  place. UCS, Greedy and A* may re-reach a place when it finds a strictly cheaper path. It
  then skips the outdated, more expensive frontier entry when that entry is
  popped.
- **Path cost:** `RouteProblem.action_cost` returns the edge's cost in minutes.
  `Cost (hops)` is the number of steps in the route. UCS, Greedy and A* also
  print `Total cost (min)`.
- **Heuristic:** `RouteProblem.h(state)` uses a hop-distance table computed once
  per problem by a BFS outward from the destination (`hop_distances`).
- **Ordering:** neighbours are always considered in alphabetical order. DFS pushes
  children in reverse order so that the alphabetically first neighbour is
  explored first.
- **Nodes expanded:** counts the nodes removed from the frontier that are not the
  goal and have their children generated.
