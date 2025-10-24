### QORE: A Portfolio Engine and Research Lab
#### Overview
QORE is a simple portfolio engine and research lab.

#### Current Modules Available

##### Strategy
The brain for all your portfolio moves.
Creates, updates, freezes, and tracks every strategy/action (buy, sell, rebalance, experiment)
Handles status states: current, frozen (locked), or challenger (sandbox/test)

##### Data
Fetches and caches stock info, historical prices, fundamentals, and more
Keeps the asset info fresh for dashboards, analyses, and simulation

##### Past
Stores and organizes your entire archive of “frozen” strategies
Analyzes your track record and produces all your progress graphs and metrics—actual vs. target, time buffer, etc.

##### Common
Holds utilities: timezone handling, config, logging—keeps everything tidy and reusable

#### Phase 1 and Phase 2 Split

##### Phase 1
Focus on building the core features of QORE: strategy management, data fetching, past performance analysis
Develop a robust dashboard to display portfolio information and analytics

##### Phase 2
Introduce interactive simulation capabilities for testing wild hypotheses
Implement real-time transaction planning based on simulated results