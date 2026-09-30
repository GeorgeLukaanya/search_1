# Makerere Campus Route Finder (BFS and DFS)

CSC 2114 Artificial Intelligence, Practical / Assignment 1.

`route_finder.py` finds a walking route between two places on a simplified
model of the Makerere University main campus (14 schools, 4 landmarks, 24
two-way connections). It uses uninformed search: Breadth-First Search (BFS)
or Depth-First Search (DFS). Every connection costs 1 hop.

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
Algorithm (BFS or DFS): bfs

Algorithm: BFS
Route: School of Law -> Freedom Square -> Main Building -> School of Liberal and Performing Arts -> Margaret Trowell School of Industrial and Fine Art
Cost (hops): 4
Nodes expanded: 12
```

### Command-line options

| Option | Meaning |
|---|---|
| `-s`, `--source` | Source place (skips that prompt) |
| `-d`, `--destination` | Destination place (skips that prompt) |
| `-a`, `--algorithm` | `BFS` or `DFS` (skips that prompt) |
| `--no-reached` | Turn off the reached table (tree-like search, capped at 10,000 expansions) |
| `-h`, `--help` | Show help |

Examples:

```bash
# Non-interactive run
python3 route_finder.py -s "School of Law" -d "CoCIS" -a DFS

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
  BFS and DFS differ only in the frontier:
  - BFS uses `FIFOFrontier`, a queue that removes from the front.
  - DFS uses `LIFOFrontier`, a stack that removes from the back.
- **Goal test:** a node is tested when it is removed from the frontier.
- **Reached table:** a state is added to `reached` when its node is generated, so
  the frontier never holds two nodes for the same place.
- **Ordering:** neighbours are always considered in alphabetical order. DFS pushes
  children in reverse order so that the alphabetically first neighbour is
  explored first.
- **Nodes expanded:** counts the nodes removed from the frontier that are not the
  goal and have their children generated.
