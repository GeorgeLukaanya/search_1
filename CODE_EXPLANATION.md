# How `route_finder.py` Works

CSC 2114 Artificial Intelligence, Assignment 4, Group 10 (BSSE)

The program finds a walking route across the Makerere campus with six
strategies: BFS, DFS, UCS, IDS, GBFS and A*. Five of them share one search
loop (`search()`); IDS is a driver (`ids_search()`) that reruns that same
loop with a depth limit. The file is split
into 11 numbered sections, listed in its opening docstring.

## 1. Campus data (Section 1)

- **`WEIGHTED_EDGES`** lists the 24 connections as `(place A, place B, metres)`,
  copied unchanged from the assignment, for example
  `("Main Building", "Freedom Square", 120)`.
- **`COORDINATES`** gives every place an `(x, y)` map position in metres. Only
  the heuristic uses it.
- **`REQUIRED_PROBLEMS`** holds the ten (source, destination) pairs for `--batch`.
- **`build_graph()`** turns the edges into `{place: {neighbour: weight}}`, both
  directions, with neighbours in alphabetical order. That ordering is the
  tie-break every strategy relies on.
- **`MAX_EXPANSIONS = 10_000`** stops tree-like search. **`H_SCALE_PERCENT = 100`**
  scales the heuristic (Part C3 changes it; the submitted file keeps 100).

## 2. The heuristic (Section 2)

```python
h(place, goal) = isqrt((x1 - x2)**2 + (y1 - y2)**2) * H_SCALE_PERCENT // 100
```

- The straight-line distance on the map, rounded **down** to whole metres, so
  every machine gets the same integers and ties are real ties.
- It depends on the goal: h(Law, Law) = 0, but h(Law, Veterinary Medicine) = 1184.
  It is computed per query; no fixed table could work.
- **Admissible:** every edge is at least as long as the straight line between
  its ends, so a real route can never be shorter than h.
- **Consistent:** by the triangle inequality, h(u) ≤ weight(u, v) + h(v) on
  every edge. This is why A* never needs to reopen a place (the scan reports 0).

## 3. Search-tree pieces (Section 3)

- **`Node`**: `state` (the place), `parent`, `action`, `path_cost` (g, metres
  walked so far) and `depth` (hops from the source, used by IDS).
- **`expand(graph, node)`** makes one child per neighbour, alphabetically. Each
  child's g is the parent's g plus the edge weight.
- **`solution(node)`** follows `parent` links back to the source and reverses
  them to give the route.
- **`route_cost(graph, route)`** adds up a route's edge weights. The printed
  cost comes from here, so BFS/DFS/IDS still report metres even though they
  never look at weights while searching.

## 4. Frontiers and key functions (Section 4)

| Frontier | Used by | Removes |
|---|---|---|
| `FIFOFrontier` | BFS | The oldest node (queue) |
| `LIFOFrontier` | DFS, IDS | The newest node (stack). Children are pushed in reverse so the alphabetically first is explored first |
| `PriorityFrontier` | UCS, GBFS, A* | The node with the smallest `(key, name, counter)` |

`PriorityFrontier` is shared by three strategies. The **key function** is the
only difference between them:

| Strategy | Key | Looks at |
|---|---|---|
| UCS | `ucs_key` = g(n) | Cost already paid |
| GBFS | `make_gbfs_key` = h(n) | Estimated cost still to go (never reads g) |
| A* | `make_astar_key` = g(n) + h(n) | Both |

Ties go to the alphabetically first place, then the earliest inserted node
(a counter from `itertools.count()`).

A **`Strategy`** bundles a frontier with a **reached rule** (`reopens`):

- `False` (BFS, DFS, GBFS): a child is kept only if its place is not yet in
  `reached`. A place is never replaced.
- `True` (UCS, A*): a child is also kept if it reaches a known place with a
  strictly lower g. It replaces the old record, and the old node becomes stale.

`STRATEGIES` maps each name to its `Strategy`.

## 5. The generic search loop (Section 5)

`search(graph, source, goal, strategy, coordinates, ...)` has no
`if algorithm == ...` branches:

1. Put the root node on the frontier and in `reached`.
2. If the frontier is empty, fail with `No route found.`
3. Remove a node.
   - **Stale rule (UCS, A*):** if its g is higher than the g stored in
     `reached` for its place, a cheaper path was found later. Discard it; it
     is not counted as expanded.
   - **Goal test on removal**, not when generated. This is what makes UCS and
     A* return the cheapest route.
   - **Cap:** stop after 10,000 expansions.
4. Expand it (count +1) and generate its children alphabetically.
5. Apply the strategy's reached rule to each child.
6. Add the kept children to the frontier and repeat.

With `--no-reached` there is no `reached` table: nothing is discarded, cycles
aren't detected, and the cap is what ends a runaway search.

The search receives the graph, coordinates and goal as **arguments**; it never
reads the module-level dictionaries (the marking runs it on modified
coordinates).

## 6. Iterative deepening (Section 6)

`ids_search()` calls the generic `search()` with limits 0, 1, 2, … until it
finds the goal. It doesn't have a loop of its own; `search()` takes two extra
switches for it:

- **`depth_limit`**: a node at this depth is goal-tested but not expanded or
  counted, and the run is marked as *cut off*.
- **`cycle_check`**: a child is skipped if its place is already on the path
  from the source. There's no `reached` table in IDS.

Each pass uses the DFS stack frontier. The limit never goes above 17 (places − 1).
- Expansions are summed over **all** passes, which is why IDS counts are high
  (324 on problem 4).
- If a pass finishes without cutting anything off, there is no route.

`run_algorithm()` is the one place that picks between `ids_search` and the
generic `search`.

## 7. Worked example: A* vs GBFS, Social Sciences → Statistics and Planning

A* trace (`--trace`), key = g + h:

```
pop School of Social Sciences key=605
push Main Building g=200 h=421 key=621
push School of Education g=140 h=581 key=721
pop Main Building key=621
push Freedom Square g=320 h=358 key=678
push Main Library g=350 h=436 key=786
pop Freedom Square key=678
push Central Teaching Facility g=540 h=180 key=720
pop Central Teaching Facility key=720
push CoCIS g=670 h=87 key=757
push School of Statistics and Planning g=840 h=0 key=840
pop School of Education key=721
replace Main Library g=350 -> 300
pop Main Library key=736
pop CoCIS key=757
replace School of Statistics and Planning g=840 -> 770
pop School of Statistics and Planning key=770      ← goal
```

(Some pushes are left out.)

- **Goal test on removal matters.** Statistics and Planning is first generated
  through Central Teaching Facility at 840 m. That edge is 300 m on foot but
  only 180 m on the map, so h was misleading. A* doesn't stop there: it finds
  the 100 m link from CoCIS, replaces the record with g = 770, and pops that
  node first.
- **Result:** A* 770 m, 5 hops, 7 expanded. UCS gets the same 770 m but expands
  11 nodes.
- **GBFS** looks only at h. It takes the Central Teaching Facility edge
  straight to the goal: 840 m, 4 hops, 4 expanded. It's faster but 70 m longer,
  because it never weighs what the path has already cost.

## 8. Checks, output and tools (Sections 7–11)

- **`check_heuristic()`** (`--check-heuristic`) tests consistency on 18 goals ×
  48 directed edges = 864 checks, and admissibility on 306 ordered pairs
  against UCS costs. Expected: 0 violations each.
- **`format_result()`** prints:

  ```
  Algorithm: A*
  Route: <place 1> -> ... -> <place n>
  Cost (metres): <integer>
  Hops: <integer>
  Nodes expanded: <integer>
  Heuristic at source: <integer>     (GBFS and A* only)
  ```

  IDS adds `Final depth limit: <n>`. `--verbose` adds `Max frontier size`.
- **`run_batch()`** (`--batch`) runs the ten required problems with all six
  algorithms and writes `results_log.csv` (60 rows).
- **`run_scan()`** (`--scan`) compares UCS, A* and GBFS on all 182 ordered
  school pairs. It prints the summary counts, then every pair where GBFS
  expanded fewer nodes than A* but returned a costlier route.
- **`main()`** handles the flags, then asks for source, destination and
  algorithm.
  - Names are case-insensitive and trimmed.
  - Unknown names ask again.
  - A destination equal to the source gives a one-place route: cost 0, hops 0,
    0 nodes expanded.
  - `ALL` runs the six algorithms in order, one block each.
