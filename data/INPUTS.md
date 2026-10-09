# Frozen processed/construction arrays

The window has 168 consecutive one-hour slots. All archives contain numerical
arrays only. `allow_pickle=False` is used when they are opened.

| Archive / array | Meaning | Shape / units |
|---|---|---|
| input.npz / timestamp_ns | Frozen slot timestamps | 168, Unix nanoseconds |
| input.npz / observed | Processed electricity for press, body, paint, assembly | 168 x 4, MWh per slot |
| input.npz / qref | Constructed hourly production reference, not raw measured production | 168 x 4, vehicle-equivalent per slot |
| input.npz / inventory_start, inventory_end | Constructed reference inter-shop buffers | 168 x 3, vehicle-equivalent |
| input.npz / aux, pv | Processed non-production load and PV generation | 168, MWh per slot |
| input.npz / k | Fixed local response coefficients (scenario parameters) | 4, MWh per vehicle-equivalent |
| price.npz / price_CNY_per_MWh | Frozen mapped price input; adder is in config.json | 168, CNY/MWh |
| saved-CASE.npz / q, inventory | Previously saved optimized/reference trajectory | 168 x 4; 169 x 3, vehicle-equivalent |
| saved-CASE.npz / shop_load_MWh, grid_MWh | Saved model energy results | 168 x 4; 168, MWh per slot |
| saved-CASE.npz / charge_MWh, discharge_MWh, soc_MWh | Saved battery model results | 168; 168; 169, MWh |
| saved-CASE.npz / charge_mode, k | Saved charging-mode and coefficient checks | 168 dimensionless; 4 MWh per vehicle-equivalent |

The saved-case archives also preserve their frozen price, fee and peak-limit
metadata. Storage and production references are model results/constructions,
not telemetry from a deployed intervention. Source and transformation hashes
are documented in source-lineage.json. No original company spreadsheets, raw
meter records, equipment identifiers, personal paths or full-year inputs are
included.
