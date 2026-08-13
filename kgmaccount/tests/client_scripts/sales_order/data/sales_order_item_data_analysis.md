# Sales Order Item Test-Data Analysis

Source: `sales order item list.csv`

This analysis decides the unit-test partitions before choosing any rows. The
test suite does not loop the full CSV. SQFT testing uses 55 analyzed scenarios:
one per distinct rule or observed boundary, with extra rows only where height,
width, quantity shape, polish, Rajasthan properties, or recalculation events
verify a different part of the calculation path.

## Dataset profile

| Measure | Count |
|---|---:|
| Data rows | 1,231 |
| Sales Orders | 459 |
| Distinct item names | 135 |
| Repeated input keys with the same expected result | 72 |
| Repeated input keys with conflicting expected results | 14 |
| Rows with positive SQFT but a non-positive height, width, or quantity | 40 |

Rows with incomplete calculation inputs are not used as normal calculation
examples. Conflicting duplicate inputs are also avoided because one input
cannot have two valid unit-test outputs. They remain in the source data for
separate data-quality review.

## Script ownership and calculation branches

| Partition | All rows | Rows with positive height, width, and quantity |
|---|---:|---:|
| Standard Kota | 388 | 387 |
| Rajasthan Kota | 138 | 138 |
| Kaddpa | 7 | 7 |
| PATI | 6 | 3 |
| Default granite/other sqft | 501 | 486 |
| Mould, mouldG, tiles, and job work | 183 | 170 |
| Other strict exclusions (`hole`, `farma`) | 8 | 0 |

These partitions map directly to the SQFT script's branch order: PATI,
Rajasthan Kota, standard Kota, Kaddpa, default granite, and strict exclusions.
Item rates and amounts are intentionally excluded because the script calculates
cut dimensions and SQFT, not pricing.

## Boundary analysis

The Kota logic has six observable width bands:

1. below 6
2. 6 to below 12
3. 12 to below 15
4. exactly 15
5. above 15 to below 18
6. 18 or more

Standard Kota has 42 positive-input rows below 24 inches high and 345 at least
24 inches high. Both height paths contain all six width bands. For height 24 or
more, quantity also splits into 178 single rows, 155 even rows, and 54 odd rows
greater than one. The chosen cases cover all width bands in both height paths,
the exact-multiple height rule, and single/even/odd quantity behavior.

Kaddpa has only seven rows and only three observed width bands: below 6,
exactly 15, and 18 or more. All seven rows are retained because this is a
small branch and the rows add exact-multiple, polish, quantity, and source cut
outcomes.

The default granite branch has 486 usable rows. Eight cases cover exact
multiples of three, dimensions requiring rounding, width regions, odd/even
quantities, and large dimensions where the CSV exposes a script/source
discrepancy.

## Item-property analysis

Standard Kota suffixes in the CSV are DP, RIV, UNC, FIN, LDR, MIR, and RUF.
The SQFT formula should recognize all of them as standard Kota without
changing the mathematical branch, so the SQFT matrix contains a named case
for every observed polish suffix.

Rajasthan SQFT cases explicitly name Gadela, Patala, Jada, Rough/Jada, Mirror,
Rough without Jada, alternate suffix ordering, and plain Rajasthan rows. These
options share the Rajasthan formula, but the named cases protect item-code
recognition so a future keyword change cannot silently send one property
combination through standard Kota.

Kaddpa includes plain, LDR, and ROU rows. The calculation does not interpret
the finish itself; the tests confirm that the suffix does not prevent the
Kaddpa branch from being selected.

## Event analysis

The script registers four entry points: `item_code`, `custom_height`,
`custom_width`, and `custom_quantity`. Branch and boundary tests exercise
`item_code`; three additional named tests verify that height, width, and
quantity edits rerun the same calculation.

## Mould analysis

Only two rounding factors exist:

- factor 6 for standard `MOULD`;
- factor 3 for `MOULDG`, tiles, and job work.

One standard mould, one mouldG, and one job-work row cover both factors and
the job-work all-sides default. Side flags are explicit test inputs because
the source CSV does not contain them.

## Final representative set

| Script area | Test groups | Row contracts |
|---|---:|---:|
| SQFT calculation | 8 | 55 |
| Select Item dialog | 4 | 16 |
| Mould running feet | 3 | 3 |
| **Total** | **15** | **74** |

Every SQFT row contract is exposed as its own named `unittest`; group prefixes
keep similar height, width, polish, Rajasthan, Kaddpa, default, PATI,
exclusion, and event cases together in test output. Fifty-five are retained
because each protects a distinct branch, observed boundary, option category,
or registered recalculation event. Additional repeated CSV rows are omitted.
