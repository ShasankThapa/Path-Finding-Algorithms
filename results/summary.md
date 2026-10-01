# A* (8-dir) vs JPS benchmark

Mode: full. Every JPS and A* cost matched the official Moving AI optimal length.
Exceptions, checked JPS against A* instead: random grids, and maps marked 'random pairs'
(no .scen file, so no official answers).
Medians over queries. Speedup = A* time / JPS time and expansion ratio = A* nodes / JPS nodes,
each computed per query before taking the median. Times are Python wall-clock search time.

| Group | Queries | A* nodes | JPS nodes | JPS cells scanned | A* ms | JPS ms | Speedup | Expansion ratio |
|---|---|---|---|---|---|---|---|---|
| AR0070SR (Baldur's Gate II) | 30 | 32038 | 68 | 39328 | 478.2 | 99.7 | 3.08x | 372.5x |
| arena2 (Dragon Age) | 30 | 3540 | 46 | 10128 | 45.6 | 24.2 | 1.82x | 57.7x |
| den312d (Dragon Age) | 30 | 238 | 19 | 668 | 2.6 | 1.7 | 1.86x | 14.3x |
| maze512-1-2 (maze, random pairs) | 30 | 25254 | 7008 | 25371 | 172.9 | 115.1 | 1.65x | 3.6x |
| maze512-16-2 (maze) | 30 | 106480 | 286 | 113310 | 1450.3 | 316.8 | 5.37x | 383.2x |
| random, 0% walls | 60 | 270 | 3 | 23488 | 3.6 | 57.4 | 0.08x | 90.0x |
| random, 10% walls | 60 | 303 | 88 | 1101 | 4.5 | 3.4 | 0.99x | 3.1x |
| random, 20% walls | 60 | 620 | 241 | 1600 | 7.0 | 6.4 | 1.09x | 2.4x |
| random, 30% walls | 60 | 916 | 386 | 1794 | 8.4 | 6.9 | 1.20x | 2.3x |
| random, 40% walls | 60 | 1184 | 482 | 1666 | 10.4 | 7.2 | 1.32x | 2.5x |
