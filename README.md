# C++ Chess Engine: Heuristic Evaluation & Performance Optimization
## Project Overview
A high-performance chess engine developed in C++20 utilizing a bitboard-based architecture and a minimax search algorithm. The project focuses on the intersection of game theory and computational efficiency, specifically investigating how heuristic adjustments and search optimizations impact engine strength across controlled benchmarks.

## Key Features
Search Architecture: Implemented a Minimax algorithm with Alpha-Beta pruning to significantly reduce the state-space search tree.

Move Generation: Leveraged bitwise operations and C++20 intrinsics (e.g., std::countr_zero) for high-speed move generation and piece-set manipulations.

Transposition Tables: Developed an std::unordered_map based transposition table to cache board hashes and evaluations, preventing redundant computations of identical positions across different search branches.

Dynamic Heuristics: Implemented state-dependent evaluation tables (e.g., KING_TABLE), which dynamically shift weight based on the presence of high-value pieces like the Queen to account for middlegame vs. endgame safety.

## Evaluation & Statistical Testing
To determine the effectiveness of version-over-version improvements, I developed a custom automated testing suite.

Head-to-Head Benchmarking: Conducted automated matches between engine revisions (e.g., searchTTM3 vs. searchTTWD) using a set of 20+ standardized board positions.

Statistical Noise Analysis: Investigated the probability of "true" skill improvement versus stochastic noise in limited testing samples. This involved analyzing Win/Draw/Loss ratios under strict time-control constraints (e.g., 100ms per move) to ensure that code changes resulted in mathematically significant gains in engine Elo.

## Technical Stack
Language: C++20

Key Libraries: [chess-library](https://disservin.github.io/chess-library/) (for core board representation)

Mathematical Concepts: Combinatorial Game Theory, Bitwise Logic, Statistical Evaluation.
