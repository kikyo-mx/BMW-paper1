# License for author-controlled data and documentation

Copyright (c) 2026 Jiarui Gong and Baokuan Li.

The authors have approved Creative Commons Attribution 4.0 International
(CC BY 4.0) for the data and documentation in this repository that they are
authorized to license, subject to the scope and third-party exclusions below.

License: <https://creativecommons.org/licenses/by/4.0/>

Legal code: <https://creativecommons.org/licenses/by/4.0/legalcode.en>

## Material covered

- The author-controlled processed/de-identified calculation inputs and
  constructed production/inventory references in `data/input/input.npz`.
- The author-generated model solution arrays in
  `data/input/saved-reference.npz`, `saved-production_only.npz`,
  `saved-storage_only.npz`, and `saved-joint.npz`: `q`, `inventory`,
  `shop_load_MWh`, `grid_MWh`, `charge_MWh`, `discharge_MWh`, `soc_MWh`,
  `charge_mode`, and `k`.
- The author-generated configuration, objective regression baselines,
  source/integrity metadata and prior numerical verification reports, to the
  extent the authors hold the rights being licensed.
- The author-written README, input definitions, citation metadata and
  explanatory documentation, except any separately credited third-party
  material or license text.

## Material not covered by the authors' CC grant

- `data/input/price.npz` and its `price_CNY_per_MWh` array.
- The repeated `price_CNY_per_MWh` arrays inside the four saved-case archives.
- Any rights in the underlying third-party spot-price facts, published tariff
  components, source webpages, expressions or materials. A calculated hourly
  average or a scenario charge parameter does not transfer source rights to
  the authors.
- Third-party library software, which is referenced as a dependency and is not
  redistributed in this repository.

See `THIRD_PARTY_NOTICES.md` for the price source and the precise factual-data
boundary. The authors do not assign CC BY 4.0 to the price provider's material
or claim that a separate third-party open license was obtained.

The author-controlled Python code in `reproduce.py`, `verify_package.py`, and
`src/kernel.py` is licensed under the MIT License in `LICENSE`.

## Attribution

For covered data/documentation, credit Jiarui Gong and Baokuan Li, identify
version 0.1.0 of *Single-window reproduction of joint production and battery
scheduling under a common grid-import limit*, link to
<https://github.com/kikyo-mx/BMW-paper1>, link to CC BY 4.0, and indicate changes.
Use `CITATION.cff` for the software citation. Acknowledge the separate price
provider when using the price facts. Attribution must not imply endorsement by
the authors, their institutions, or the third-party provider.

This license scope does not change the scientific interpretation: the material
is a single retrospective 168-hour calculation window with constructed
production references and scenario parameters, not raw measured hourly
production or a complete research release.
