# Potential Plugins

Game theory libraries that could be wrapped as future plugins.

---

## EFG (extensive-form) — solvers that scale beyond Gambit-style enumeration

* **LiteEFG (C++ backend, Python-defined computation graphs)**
  If you're iterating on regret-based / DP-style updates and want performance without writing C++. The core claim is: define the update rule in Python as a computation graph, execute fast in C++ across the tree. ([arXiv][2])
  *Caveat:* it's a solver framework, not a modeling standard; expect format / integration work.

## NFG (normal-form) — alternatives that are either lighter than Gambit or cover niches better

* **Nashpy (Python)**
  Focused, readable 2-player matrix-game tooling: Lemke–Howson, support enumeration, etc. ([nashpy.readthedocs.io][3])
  *Caveat:* essentially bimatrix-focused; not a general N-player workhorse.

* **GameTheory.jl (Julia, QuantEcon)**
  Serious N-player normal-form support, including "compute all isolated equilibria" via homotopy continuation (`hc_solve`). ([GitHub][4])
  *Caveat:* Julia toolchain + numeric methods trade different failure modes than pivoting/LCP solvers.

* **lrslib / lrsnash (C)**
  A dedicated equilibrium-computation path via reverse-search vertex enumeration; `lrsnash` is explicitly for Nash equilibria in 2-person matrix games. ([cgm.cs.mcgill.ca][5])
  Practical note: even **pygambit** can call out to `lrsnash` for some mixed-equilibrium computations (so you can swap backends). ([gambitproject.readthedocs.io][6])

* **SageMath game theory module (Python interface)**
  General-purpose math system that includes normal-form game functionality (and can optionally use lrslib). ([doc.sagemath.org][7])
  *Caveat:* great glue / experimentation environment; not always the fastest "solver-first" option.

## MAID / influence-diagram ecosystem

* **pyAgrum (C++ core + Python)**
  Strong influence-diagram + LIMID machinery (decision/utility nodes; inference that treats models as LIMIDs, with explicit "no forgetting" support). ([pyAgrum][9])
  How it helps: fast single-agent MEU/LIMID solving as a primitive; you can wrap iterated best response yourself for multi-agent models when that's acceptable.

* **DecisionProgramming.jl (Julia)**
  Influence diagrams solved via mixed-integer optimization (JuMP extension; explicitly MILP-powered). ([gamma-opt.github.io][10])
  *Key limitation:* it's not "a MAID Nash solver"; it's an optimization view of decision problems. Useful if your work naturally becomes "solve a constrained decision/coordination problem" or you want MILP hooks.

* **PyNFG (Python, network-form games)**
  Graphical-model–style representation of strategic environments (explicitly pitched as "translate a strategic environment into PGM language"). ([GitHub][11])
  *Caveat:* it's old (you'll feel it), but conceptually it's closer to "graphical game representations" than most EFG/NFG libraries.

## Other useful libraries

* **MFGLib (Python)**
  Mean-field game equilibria for large-population limits (if your "classical" work starts drifting toward large-agent regimes). ([arXiv][13])

* **Axelrod (Python)**
  Research tool for the Iterated Prisoner's Dilemma with extensive strategy library. ([GitHub][17])

---

## Not recommended

* **cadCAD** is primarily a simulation/validation framework, not a classical game solver. It's relevant if you later want policy/behavioral model sweeps, not equilibrium computation. ([GitHub][14])
* **rgamer** is genuinely nice for visualization / teaching small games, but it's not a serious solver stack. ([yukiyanai.github.io][15])

[2]: https://arxiv.org/abs/2407.20351 "LiteEFG: An Efficient Python Library for Solving Extensive-form Games"
[3]: https://nashpy.readthedocs.io/en/stable/text-book/lemke-howson.html "The Lemke Howson Algorithm — Nashpy documentation"
[4]: https://github.com/QuantEcon/GameTheory.jl "QuantEcon/GameTheory.jl"
[5]: https://cgm.cs.mcgill.ca/~avis/C/lrslib/man/man1/lrsnash.1.html "Man page of lrsnash"
[6]: https://gambitproject.readthedocs.io/en/latest/api/pygambit.nash.enummixed_solve.html "pygambit.nash.enummixed_solve"
[7]: https://doc.sagemath.org/html/en/reference/game_theory/sage/game_theory/normal_form_game.html "Normal form games with N players - SageMath"
[9]: https://pyagrum.readthedocs.io/en/1.16.0/infdiag.html "Influence Diagram and LIMIDS - pyAgrum"
[10]: https://gamma-opt.github.io/DecisionProgramming.jl/dev/ "DecisionProgramming.jl"
[11]: https://github.com/jwbono/PyNFG "PyNFG"
[13]: https://arxiv.org/abs/2304.08630 "MFGLib: A Library for Mean-Field Games"
[14]: https://github.com/cadCAD-org/cadCAD "cadCAD"
[15]: https://yukiyanai.github.io/rgamer/ "rgamer"
[17]: https://github.com/Axelrod-Python/Axelrod "Axelrod"
