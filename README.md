# Single-window reproduction of production and battery scheduling

This attachment contains one frozen 168-hour calculation window beginning at
2025-03-01 06:00:00, selected as the earliest common frozen window rather than by
its savings. It supports inspection and reproduction of four existing cases:
`reference`, `production_only`, `storage_only`, and `joint`. It is a bounded
review attachment; the full research code, full dataset, annual calculations,
other windows, heating scenarios, and investment assessments are not included.

The input consists of processed energy records derived from de-identified data,
constructed hourly production references and inventory profiles, and scenario
parameters. It is **not raw measured hourly production**, a device-level dataset,
or an observed implementation of the proposed scheduling interventions. No
original non-de-identified company records are included. Sharing the
de-identified material was authorized by the author. This package retains the
numerical values needed for the frozen calculation; it does not promise that a
case can never be associated with an author affiliation.

## Files and scientific boundary

`reproduce.py` is the execution entry point and `src/kernel.py` is its only local
scientific module. The kernel is byte-identical to the previously tested frozen
kernel. Its scientific constants and function bodies were extracted unchanged
from the upstream modules. `source-extraction.json` identifies the original
blocks, and `source-lineage.json` records the source file and block hashes without
personal absolute paths. Historical modules are not runtime dependencies and
are intentionally excluded.

`config.json` retains the prior configuration. The four cases use the same
maximum hourly mean grid-import power from the fixed-production, zero-storage
reference window as their grid-import limit. Storage cases use 20 MWh and 10 MW;
the central energy-charge adder is 110.625 CNY/MWh. Production response
coefficients, buffers and storage parameters remain scenario assumptions, not
identified equipment characteristics. Input units and array definitions are in
`data/INPUTS.md`.

`data/input/input.npz` and the four `saved-*.npz` regression trajectories are
unchanged copies of the frozen processed/construction files. `price.npz` contains
only the price array actually consumed by the entry point; that array is exactly
equal to the array in the source archive. Removing its unused duplicate
trajectory arrays does not change the scientific calculation.

## Checking without solving

Use Python 3.12. The previously verified environment used Python 3.12.14,
NumPy 2.3.5, pandas 3.0.1, and SciPy 1.16.2. Install the pinned requirements in
an environment of your choice:

```text
python -m pip install -r requirements.txt
python verify_package.py --check-imports
```

The checker verifies package hashes, syntax and numerical archive structure.
Its optional import check only imports the required libraries; it does not
import the scientific kernel, call the optimizer, or execute any case. A
different dependency version is reported as a mismatch with the prior
environment rather than treated as new scientific reproduction evidence.

## Running the four cases

Extract a fresh copy of this attachment into a new directory, install the pinned
requirements, and run:

```text
python reproduce.py
```

The entry point creates `outputs/reports/` and `outputs/data/`. It permits at most
four optimizer calls, with one child process per case, a 30-second child timeout,
and a 180-second supervision limit. Outputs are created exclusively and an
existing `outputs/reports/preflight.json` blocks a repeat. Preserve any results
or failures and use another fresh copy if a later independent run is needed.
Do not copy existing run outputs into the active output directory.

The old author-side preparation branch and its machine-specific paths were
removed. The input checks, independent algebraic audit, case execution and
supervision function bodies are unchanged. Normalized forward-slash manifest
paths and creation of the empty output directories are packaging changes only.
There is no random seed: mixed integer linear programming can have degenerate
optima, so feasible trajectories may differ. Acceptance compares independently
reconstructed costs and constraints, not pointwise trajectory equality.

## Prior verification and this packaging pass

`prior-verification/` preserves the report of the **already completed** local
reproduction: exactly four optimizer calls, four cases verified, and
`PASS_ONE_WINDOW_ONLY`. The maximum objective difference against the saved
baseline was 4.656612873077393e-10 CNY. These are prior results, not results of
rebuilding this attachment. The author-side reproduction did not perform an
annual rerun or demonstrate measured savings, future scheduling performance,
site implementation, storage investment returns, or empirical identification of
the scenario parameters.

This packaging pass did not run a scientific model or optimizer. It checked
structure, source hashes, unchanged scientific blocks, input array identity,
syntax, imports and ZIP integrity. Cross-machine solver reproduction has not
been performed. The complete research release remains outside this attachment.

## Approved licenses and publication-candidate status

The authors have approved public release of this single-window material at
<https://github.com/kikyo-mx/BMW-paper1> under the following scopes:

- Author-controlled Python code (`reproduce.py`, `verify_package.py`, and
  `src/kernel.py`): MIT License, in `LICENSE`.
- Author-controlled data and documentation that the authors are authorized to
  license: Creative Commons Attribution 4.0 International (CC BY 4.0), within
  the scope in `LICENSE-DATA.md`.
- Third-party price facts and their source rights are excluded from the authors'
  MIT/CC grant. The 168 hourly price inputs and their repetitions in saved-case
  archives retain attribution and source rights in `THIRD_PARTY_NOTICES.md`.

`CITATION.cff` identifies this software as version 0.1.0; it does not invent an
article publication, DOI or ORCID. At preparation time, this directory was a
local publication candidate and had not been uploaded by this task. The
candidate contains the bounded 25-file calculation package plus these four
license/citation/source notices. It is not the complete study matrix.
