# How `route_finder.py` Works

CSC 2114 Artificial Intelligence, Group 10 (BSSE)

All five algorithms (BFS, DFS, UCS, Greedy Best-First and A*) run through the
same search function.
The only thing that changes is which node gets picked next.

## 1. The campus map

- **`EDGES`** lists every connection as `(place A, place B, minutes)`, for example
  `("Main Building", "Freedom Square", 3)`. The minutes are illustrative walking
  times, not measured ones.
- **`build_graph()`** turns that list into two dictionaries:
  - **`GRAPH`** maps each place to its neighbours, sorted alphabetically. Every
    edge is stored both ways, because paths are two-way.
  - **`COSTS`** maps a pair like `("School of Law", "School of Economics")` to its
    cost, `3`. Both directions are stored.
- **`MAX_EXPANSIONS = 10_000`** is the safety limit for tree-like search.

## 2. The problem definition (`RouteProblem`)

These are the five parts of a search problem from the lecture:

| Part | Code | Meaning |
|---|---|---|
| Initial state | `self.initial` | Where you start |
| Actions | `actions(s)` | The neighbours of `s`, in alphabetical order |
| Transition | `result(s, a)` | Walking to place X puts you at X |
| Goal test | `is_goal(s)` | Are we at the destination? |
| Step cost | `action_cost(...)` | The edge's minutes, from `COSTS` |

`RouteProblem` also has a sixth method, used only by Greedy and A*:

- **`h(state)`**, the heuristic: an estimate of the minutes left from `state` to
  the goal.

  ```
  h(n) = 2 × (fewest hops from n to the goal)
  ```

  - 2 is the cheapest edge on the map (`min_cost`).
  - The hop counts come from `hop_distances()`, a BFS run once outward from the
    goal when the problem is created.
  - **Admissible:** any route from n needs at least that many hops, and each
    costs at least 2, so h never overestimates.
  - **Consistent:** neighbours differ by at most one hop and every edge costs at
    least 2, so h(n) ≤ c(n, n′) + h(n′).

## 3. Search tree pieces

- **`Node`** has the four lecture fields:
  - `state`: the place
  - `parent`: the node it came from
  - `action`: the place walked to
  - `path_cost`: total minutes so far
- **`expand(problem, node)`** creates one child node per neighbour. Each child's
  cost is the parent's cost plus the edge cost.
- **`solution(node)`** follows the `parent` links back to the start, then reverses
  the list to give the route.

**State vs node:** a state is just a place. A node is a place plus how you got
there. The same place can appear in several nodes with different costs.

## 4. The frontiers

This is the only part that differs between the algorithms:

| Class | Algorithm | Picks next |
|---|---|---|
| `FIFOFrontier` | BFS | The oldest node (queue): shallowest first |
| `LIFOFrontier` | DFS | The newest node (stack): deepest first |
| `PriorityFrontier` | UCS | The cheapest node so far: lowest g(n) |
| `GreedyFrontier` | Greedy | The node that looks closest to the goal: lowest h(n) |
| `AStarFrontier` | A* | The best estimated total: lowest f(n) = g(n) + h(n) |

`GreedyFrontier` and `AStarFrontier` are subclasses of `PriorityFrontier`. They
override only `priority(node)`, which returns the number the heap is ordered by.
Every frontier receives the problem when it is created, so the informed ones
can call `problem.h()`.

- **DFS ordering.** DFS pushes children in reverse alphabetical order. That leaves
  the alphabetically first neighbour on top of the stack, so it is explored first.
- **UCS ties.** UCS stores each node as `(cost, name, counter, node)`, so equal
  costs are broken alphabetically, then by insertion order. The results are
  always the same.
- **`reopens`.** Each frontier has this flag. UCS, Greedy and A* set it to `True`, meaning
  "I may come back to a place if I find a cheaper way there."

`STRATEGIES` maps the name the user types (`BFS`, `DFS`, `UCS`, `GREEDY` or
`A*`) to its frontier class. `ASTAR`, `A-STAR` and `GBFS` are accepted as
aliases.

## 5. The search loop (`search()`)

This follows the lecture's seven steps:

1. Make a root node for the start place.
2. Put it on the frontier and in `reached`.
3. While the frontier isn't empty:
4. Remove a node. If it's the goal, return it. **The goal test happens on
   removal, not when the node is created.**
5. Otherwise count it as expanded.
6. For each child, skip it if its place is already in `reached`. UCS, Greedy
   and A* make one exception: it keeps the child if this path is strictly cheaper.
7. Add the surviving children to the frontier.

The priority-queue algorithms (UCS, Greedy, A*) need two extra checks:

- **When adding children:** keep a child if it's a cheaper way to a place already
  in `reached`, and record it as the new best.
- **When removing a node:** if the node costs more than the best known path to its
  place, it's an outdated entry, so skip it.

`use_reached=False` (the `--no-reached` flag) turns the `reached` table off,
which gives tree-like search. The 10,000-expansion limit stops it from running
forever around cycles.

```
function SEARCH(problem, Frontier, use_reached):
    1. node ← Node(problem.initial)
    2. frontier ← Frontier containing node
       reached ← {problem.initial: node}          (only if use_reached)
       expanded ← 0
    3. while frontier is not empty:
    4.     node ← frontier.POP()                  (FIFO, LIFO, or lowest g / h / g+h)
           if priority frontier and node.path_cost > reached[node.state].path_cost: skip it (outdated)
           if problem.IS-GOAL(node.state): return node, expanded
           if expanded = 10,000: return failure (cap reached)
    5.     expanded ← expanded + 1
    6.     for each child in EXPAND(node), in alphabetical order:
               if use_reached:
                   if child.state in reached and not (priority frontier and child is strictly cheaper):
                       skip this child
                   reached[child.state] ← child
    7.     frontier.ADD(remaining children)
    return failure                                (prints "No route found")
```

## 6. Worked example: UCS from School of Law to CoCIS

This is the order in which UCS removes nodes from the frontier (`g` is minutes
so far):

```
pop School of Law                     (g=0)
pop School of Economics               (g=3)
pop Freedom Square                    (g=5)
pop Main Library                      (g=7)   ← reached via Freedom Square (5+2)
pop Main Building                     (g=8)
pop Central Teaching Facility         (g=9)
pop School of Statistics and Planning (g=9)
pop Main Library                      (g=10)  ← outdated copy via Economics (3+7), skipped
pop CoCIS                             (g=11)  ← goal
```

Result: School of Law → School of Economics → School of Statistics and Planning
→ CoCIS, 3 hops, 11 minutes, 7 nodes expanded.

- **Re-reaching a place.** Main Library was first reached through Economics at
  10 minutes. A cheaper way through Freedom Square (7) turned up later. The old
  copy at 10 still came off the heap, and UCS skipped it.
- **Why test on removal.** CoCIS was first created through Central Teaching
  Facility at 12 minutes (9+3). Then it was found through Statistics and Planning
  at 11 (9+2). Because UCS checks for the goal only when a node is removed, the
  11-minute path comes off first and wins. Checking when nodes are created would
  have returned the 12-minute route.
- **BFS on the same pair** returns School of Law → Freedom Square → Central
  Teaching Facility → CoCIS. That's also 3 hops but takes 12 minutes, because
  BFS ignores costs.

## 7. Worked example: A* vs Greedy, Built Environment to School of Law

A* removes nodes in order of f = g + h (abbreviations: SBE = Built Environment,
ENG = Engineering, MT = Margaret Trowell, SSP = Statistics and Planning,
CTF = Central Teaching Facility, FS = Freedom Square, ECO = Economics):

```
pop SBE    g= 0 h=10 f=10
pop ENG    g= 2 h= 8 f=10
pop MT     g= 3 h= 8 f=11
pop CoCIS  g= 6 h= 6 f=12
pop SSP    g= 8 h= 4 f=12
pop CTF    g= 9 h= 4 f=13
pop FS     g=13 h= 2 f=15
pop ECO    g=14 h= 2 f=16
pop LAW    g=17 h= 0 f=17   ← goal
```

A* returns SBE → ENG → CoCIS → SSP → ECO → LAW: 17 minutes, 8 nodes expanded.
UCS finds the same route but expands 11 nodes.

Greedy looks only at h, so it goes SBE → MT → LPA → MB → FS → LAW. It expands
just 5 nodes, but the route costs **25 minutes**. Greedy never checks how
expensive the path so far has been: the long walk from MT to LPA (8 minutes)
doesn't count against it.

## 8. Results and user interface

- **`SearchResult`** holds the goal node, the expansion count and whether the
  limit was hit. It also gives `route`, `cost` (minutes) and `hops`.
- **`find_route()`** is a one-line wrapper: it builds the problem, picks the
  frontier and runs `search`.
- **`match_place()`** looks names up ignoring case and leading or trailing
  spaces.
- **`format_result()`** prints the output format the brief requires:

  ```
  Algorithm: BFS
  Route: <place 1> -> <place 2> -> ... -> <place n>
  Cost (hops): <integer>
  Nodes expanded: <integer>
  ```

  For UCS, Greedy and A* it also prints the cost of each leg and
  `Total cost (min)`. Greedy and A* also print `Heuristic h(source)`.
- **`main()`** reads the command-line options (`-s`, `-d`, `-a`, `--no-reached`)
  and asks for anything missing. A bad name gives an error and asks again rather
  than crashing. Ctrl+C or Ctrl+D exits cleanly.
