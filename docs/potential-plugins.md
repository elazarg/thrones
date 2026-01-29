Here’s the cleaned-up landscape (beyond **Gambit** + **PyCID**) for **classical** EFG / NFG / MAID-ish analysis, with the main “what it’s actually good for” and the sharp limitations.

## EFG (extensive-form) — solvers that scale beyond Gambit-style enumeration

* **OpenSpiel (C++ core + Python)**
  Best “generalist” upgrade: lots of imperfect-information algorithms (CFR family, exploitability tooling, etc.) and a big benchmark suite. It can ingest Gambit-style games (there’s explicit Gambit interoperability documentation). ([GitHub][1])
  *Caveat:* it’s primarily an *environment + algorithms* stack; some workflows feel RL-shaped even if you’re doing pure analysis.

* **LiteEFG (C++ backend, Python-defined computation graphs)**
  If you’re iterating on regret-based / DP-style updates and want performance without writing C++. The core claim is: define the update rule in Python as a computation graph, execute fast in C++ across the tree. ([arXiv][2])
  *Caveat:* it’s a solver framework, not a modeling standard; expect format / integration work.

## NFG (normal-form) — alternatives that are either lighter than Gambit or cover niches better

* **Nashpy (Python)**
  Focused, readable 2-player matrix-game tooling: Lemke–Howson, support enumeration, etc. ([nashpy.readthedocs.io][3])
  *Caveat:* essentially bimatrix-focused; not a general N-player workhorse.

* **GameTheory.jl (Julia, QuantEcon)**
  Serious N-player normal-form support, including “compute all isolated equilibria” via homotopy continuation (`hc_solve`). ([GitHub][4])
  *Caveat:* Julia toolchain + numeric methods trade different failure modes than pivoting/LCP solvers.

* **lrslib / lrsnash (C)**
  A dedicated equilibrium-computation path via reverse-search vertex enumeration; `lrsnash` is explicitly for Nash equilibria in 2-person matrix games. ([cgm.cs.mcgill.ca][5])
  Practical note: even **pygambit** can call out to `lrsnash` for some mixed-equilibrium computations (so you can swap backends). ([gambitproject.readthedocs.io][6])

* **SageMath game theory module (Python interface)**
  General-purpose math system that includes normal-form game functionality (and can optionally use lrslib). ([doc.sagemath.org][7])
  *Caveat:* great glue / experimentation environment; not always the fastest “solver-first” option.

## MAID / influence-diagram ecosystem — reality check + what’s actually usable

MAID-specific *equilibrium* tooling is still sparse; PyCID is unusually central. The “Equilibrium Refinements for MAIDs” paper explicitly points to an open-source implementation, and that implementation is PyCID. ([arXiv][8])

What you can add around PyCID:

* **pyAgrum (C++ core + Python)**
  Strong influence-diagram + LIMID machinery (decision/utility nodes; inference that treats models as LIMIDs, with explicit “no forgetting” support). ([pyAgrum][9])
  How it helps you: fast single-agent MEU/LIMID solving as a primitive; you can wrap iterated best response yourself for multi-agent models when that’s acceptable.

* **DecisionProgramming.jl (Julia)**
  Influence diagrams solved via mixed-integer optimization (JuMP extension; explicitly MILP-powered). ([gamma-opt.github.io][10])
  *Key limitation:* it’s not “a MAID Nash solver”; it’s an optimization view of decision problems. Useful if your work naturally becomes “solve a constrained decision/coordination problem” or you want MILP hooks.

* **PyNFG (Python, network-form games)**
  Graphical-model–style representation of strategic environments (explicitly pitched as “translate a strategic environment into PGM language”). ([GitHub][11])
  *Caveat:* it’s old (you’ll feel it), but conceptually it’s closer to “graphical game representations” than most EFG/NFG libraries.

## Adjacent but often useful for “analysis-first” pipelines

* **EGTTools (Python + C++)**
  Evolutionary dynamics analysis (replicator dynamics, fixation probabilities, etc.) with simulation backends. ([GitHub][12])
  Not classical equilibrium computation, but very useful if you’re exploring dynamics / stability as analysis objects.

* **MFGLib (Python)**
  Mean-field game equilibria for large-population limits (if your “classical” work starts drifting toward large-agent regimes). ([arXiv][13])

## What I’d treat as “probably misleading” from the drafts you pasted

* **cadCAD** is primarily a simulation/validation framework, not a classical game solver. It’s relevant if you later want policy/behavioral model sweeps, not equilibrium computation. ([GitHub][14])
* **rgamer** is genuinely nice for visualization / teaching small games, but it’s not a serious solver stack. ([yukiyanai.github.io][15])
* “OpenSpiel loads .nfg” is *likely true in practice* (there’s explicit `load_nfg_game` usage in OpenSpiel-related codebases and discussion), but it’s less cleanly documented than `.efg` interoperability—so I’d verify against the exact OpenSpiel commit you’re using before depending on it. ([GitLab][16])

If you tell me which direction you’re pushing hardest right now—(i) large imperfect-info EFGs, (ii) N-player general-sum NFGs, or (iii) MAID-ish graphical games with causal semantics—I can narrow this to the 2–4 tools that will actually add new capability (rather than overlap with Gambit/PyCID).

[1]: https://github.com/deepmind/open_spiel/blob/master/open_spiel/python/pybind11/pyspiel.cc?utm_source=chatgpt.com "open_spiel/open_spiel/python/pybind11/pyspiel.cc at master"
[2]: https://arxiv.org/abs/2407.20351?utm_source=chatgpt.com "LiteEFG: An Efficient Python Library for Solving Extensive-form Games"
[3]: https://nashpy.readthedocs.io/en/stable/text-book/lemke-howson.html?utm_source=chatgpt.com "The Lemke Howson Algorithm — Nashpy 0.0.43 documentation"
[4]: https://github.com/QuantEcon/GameTheory.jl?utm_source=chatgpt.com "QuantEcon/GameTheory.jl: Algorithms and data structures ..."
[5]: https://cgm.cs.mcgill.ca/~avis/C/lrslib/man/man1/lrsnash.1.html?utm_source=chatgpt.com "Man page of lrsnash"
[6]: https://gambitproject.readthedocs.io/en/latest/api/pygambit.nash.enummixed_solve.html?utm_source=chatgpt.com "pygambit.nash.enummixed_solve - Read the Docs"
[7]: https://doc.sagemath.org/html/en/reference/game_theory/sage/game_theory/normal_form_game.html?utm_source=chatgpt.com "Normal form games with N players. - Game Theory"
[8]: https://arxiv.org/abs/2102.05008?utm_source=chatgpt.com "Equilibrium Refinements for Multi-Agent Influence Diagrams: Theory and Practice"
[9]: https://pyagrum.readthedocs.io/en/1.16.0/infdiag.html?utm_source=chatgpt.com "Influence Diagram and LIMIDS - pyAgrum - Read the Docs"
[10]: https://gamma-opt.github.io/DecisionProgramming.jl/dev/?utm_source=chatgpt.com "Home · DecisionProgramming.jl"
[11]: https://github.com/jwbono/PyNFG?utm_source=chatgpt.com "PyNFG - A Python package for modeling and solving ..."
[12]: https://github.com/Socrats/EGTTools?utm_source=chatgpt.com "Socrats/EGTTools: Toolbox for Evolutionary Game Theory."
[13]: https://arxiv.org/abs/2304.08630?utm_source=chatgpt.com "MFGLib: A Library for Mean-Field Games"
[14]: https://github.com/cadCAD-org/cadCAD?utm_source=chatgpt.com "cadCAD-org/cadCAD: Design, simulate, validate, and ..."
[15]: https://yukiyanai.github.io/rgamer/?utm_source=chatgpt.com "rgamer: Learn Game Theory Using R"
[16]: https://gitlab.fel.cvut.cz/game-theory-aic/open_spiel_public_state_cfr/-/blob/master/open_spiel/python/tests/nfg_game_test.py?ref_type=heads&utm_source=chatgpt.com "open_spiel/python/tests/nfg_game_test.py · master"
