# Contributing to sonolumen

Thanks for your interest in contributing! sonolumen is a single-bubble
sonoluminescence and cavitation plasma simulator. Bug reports, physics
corrections, new presets, and code improvements are all welcome.

## Development setup

```bash
git clone https://github.com/Mando-369/sonolumen.git
cd sonolumen

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev,ui]"
```

## Running the test suite

```bash
pytest -v
```

The validation suite under `tests/test_validation.py` reproduces the
canonical SBSL case from `cavitation_research/11_simulator_spec.md` §11.5.
Please make sure it still passes before opening a PR.

## Submitting a change

1. Open an issue first if the change is large or changes physics behaviour —
   it's much faster to align on the approach before you write code.
2. Fork the repo and create a topic branch from `main`.
3. Keep commits focused and write descriptive messages. Reference a dossier
   section (e.g. `§9.3`) when the change implements or corrects something
   from `cavitation_research/`.
4. Run `pytest -v` and make sure everything passes.
5. Open a PR against `main`. The PR template will ask you for a summary,
   a test plan, and screenshots if you touched the UI.

## Style

- Python 3.11+, type hints encouraged on new public surfaces.
- SI units everywhere — convert at the boundary, not inside the physics core.
- Cross-reference the dossier (`cavitation_research/`) when adding equations
  or physics options. Equation numbers like `E12` should match the spec.
- Avoid adding dependencies unless they unlock a clearly useful capability.

## Reporting bugs

File an issue with:
- A minimal reproducer (preset name, or a `SimulationConfig` snippet).
- The expected vs actual behaviour.
- Your platform and Python version.
- Stack trace if applicable.

## Reporting physics issues

If you think a physics result is wrong:
- Cite the dossier section the code implements (e.g. `§9.3` / `E14`).
- Describe what the expected reference value or scaling is, with a citation.
- Attach the scenario JSON or a `SimulationConfig` that reproduces it.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License (see `LICENSE`).
