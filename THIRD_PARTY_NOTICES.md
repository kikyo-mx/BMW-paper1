# Third-party price facts and dependencies

## Liaoning public spot-price source

The manuscript's reference [11] identifies:

Liaoning Provincial Development and Reform Commission. Electricity spot-price
disclosure, 2025 daily records. Official data portal:
<https://fgw.ln.gov.cn/fgw/xxgk/xhdj/index.shtml>.

The manuscript records an access date of 14 September 2026. The official portal
and its attribution were checked again during preparation on 8 October 2026;
this packaging task did not redownload or revalidate the complete 2025 daily
response archive.

The supplied price input contains only the 168 numerical hourly price facts
actually used in this frozen calculation window. The authors' processing
treats source quarter-hour labels as interval ends and averages four consecutive
quarter-hour prices for each hour with equal within-hour energy allocation.
The same 168 prices are repeated as frozen regression metadata in the four
saved-case NPZ archives. These repetitions do not add other price windows.

Affected arrays:

- `data/input/price.npz`: `price_CNY_per_MWh`.
- `data/input/saved-reference.npz`, `saved-production_only.npz`,
  `saved-storage_only.npz`, and `saved-joint.npz`: `price_CNY_per_MWh`.

No webpage prose, page design, chart, image, downloadable source attachment,
complete annual price archive, or raw daily-response snapshot is included.
The processed numerical price facts are credited to the official provider;
they are not presented as original author-created measurements.

The official website displays a notice reserving permission for reuse of site
content and copyright in the Commission's name. The repository records that
notice and retains the source rights. The authors' MIT and CC BY 4.0 grants do
not license the provider's material, and this notice does not claim that a
separate third-party open license or permission was obtained. It does not make
a legal determination about rights in numerical facts or applicable exceptions.

The central additive charge of 110.625 CNY/MWh is a scenario parameter formed
from the published-component reference settings described in manuscript
reference [12], rather than a measured or confirmed factory tariff. Underlying
published tariff facts also retain their source rights.

## Referenced software dependencies

The code uses NumPy, pandas and SciPy. Their software is not vendored here;
`requirements.txt` identifies the prior verified dependency versions. Each
dependency retains its own license. The authors' MIT grant covers only their
Python files in this repository.
