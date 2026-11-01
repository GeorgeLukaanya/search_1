# Weighted Campus Route Finder (BFS, DFS, UCS, IDS, GBFS and A*)

CSC 2114 Artificial Intelligence, Assignment 4, Group 10 (BSSE).

`route_finder.py` finds a walking route between two places on a simplified
model of the Makerere University main campus (14 schools, 4 landmarks, 24
two-way connections). Every connection has a walking distance in metres, and
every place has an (x, y) map position. The cost of a route is the sum of its
edge weights; the optimal route is the cheapest one.

Requires Python 3 only (standard library; `heapq` is the only search helper).

## Algorithms

| Name | Frontier | Ordered by | Optimal? |
|---|---|---|---|
| `BFS` | FIFO queue | arrival | fewest hops, ignores metres |
| `DFS` | LIFO stack | arrival | no |
| `UCS` | priority queue | g(n), metres already walked | yes |
| `IDS` | stack in a driver loop | depth limit 0, 1, 2, … | fewest hops, ignores metres |
| `GBFS` | priority queue | h(n), estimated metres still to go | no |
| `A*` | priority queue | f(n) = g(n) + h(n) | yes |

## Heuristic

```
h(place, goal) = isqrt((x1 − x2)² + (y1 − y2)²) × H_SCALE_PERCENT / 100
```

The straight-line map distance, rounded down to whole metres.
`H_SCALE_PERCENT` must stay at 100 in the submitted file.

- **Admissible:** every edge weight is at least the straight-line distance
  between its two places, so h never overestimates the true cost.
- **Consistent:** for every edge, h(u) ≤ weight(u, v) + h(v).

`--check-heuristic` confirms both: 864 consistency checks and 306
admissibility pairs, 0 violations. Only GBFS, A* and the check use h or the
coordinates; BFS, DFS, UCS and IDS never touch them.

## Running

```bash
python3 route_finder.py
```

The program prompts for the source, destination and algorithm:

```
Algorithm: A*
Route: School of Social Sciences -> Main Building -> Freedom Square -> Central Teaching Facility -> CoCIS -> School of Statistics and Planning
Cost (metres): 770
Hops: 5
Nodes expanded: 7
Heuristic at source: 605
```

GBFS and A* print `Heuristic at source`; IDS prints `Final depth limit`.

### Command-line options

| Option | Meaning |
|---|---|
| `-s`, `--source` | Source place (skips that prompt) |
| `-d`, `--destination` | Destination place (skips that prompt) |
| `-a`, `--algorithm` | `BFS`, `DFS`, `UCS`, `IDS`, `GBFS`, `ASTAR` (or `A*`) or `ALL` |
| `--no-reached` | Tree-like search for BFS, DFS, UCS, GBFS and A*, capped at 10,000 expansions |
| `--trace` | UCS, GBFS, A*: print every push, pop, stale and replace event |
| `--verbose` | Print max frontier size (and per-limit lines for IDS) |
| `--check-heuristic` | Verify h is consistent and admissible, then exit |
| `--batch` | Run the ten required problems with all six algorithms; write `results_log.csv` (60 rows) |
| `--scan` | Compare UCS, A* and GBFS on all 182 ordered pairs of schools |
| `-h`, `--help` | Show help |

Examples:

```bash
# All six algorithms, one block each (quote A* so the shell doesn't expand it)
python3 route_finder.py -s "School of Law" -d "CoCIS" -a ALL
python3 route_finder.py -s "School of Law" -d "CoCIS" -a "A*" --trace

# Tree-like A*: finishes (2130 m, 112 expansions) where UCS hits the cap
python3 route_finder.py --no-reached \
    -s "Margaret Trowell School of Industrial and Fine Art" \
    -d "School of Veterinary Medicine" -a "A*"

python3 route_finder.py --check-heuristic
python3 route_finder.py --batch
python3 route_finder.py --scan
```

## Input rules

- Place and algorithm names are case-insensitive; leading and trailing spaces
  are ignored. Type the full place name.
- An unknown place prints the list of valid places and asks again. An unknown
  algorithm asks again.
- If the destination equals the source, the program says so and asks for a
  different destination.
- If no route exists, the program prints `No route found.`. In tree-like mode
  the cap prints `Search stopped: expansion cap (10000) reached.`

## Design summary

- **`Node`** stores `state`, `parent`, `action`, `path_cost` (g, in metres) and `depth`.
- **`solution(node)`** follows the parent pointers back to the root;
  **`route_cost()`** sums a route's edge weights.
- **`search()`** is the one generic loop for BFS, DFS, UCS, GBFS and A*. A
  `Strategy` supplies only the frontier and the reached rule, so the loop has
  no per-algorithm branches.
- **Key functions:** `ucs_key` = g, GBFS key = h, A* key = g + h. Heap entries
  are `(key, state name, counter, node)`: smallest key, then alphabetical
  name, then earliest inserted.
- **Reached rule:** BFS, DFS and GBFS never replace a place in `reached`. UCS
  and A* replace it when a strictly cheaper path appears, and silently drop
  the older, now stale entry when it is popped (not counted as expanded).
- **Goal test** happens when a node is removed from the frontier.
- **`ids_search()`** is its own driver: repeated depth-limited DFS that skips
  places already on the current path, summing expansions over all limits.
- **Nodes expanded** counts nodes removed from the frontier that are not the
  goal and have their children generated.
- Search functions receive the graph, coordinates and goal as arguments; they
  never read the module-level dictionaries.
