# horse-model

Handicapping models, PP parsers, and pace/speed analysis for thoroughbred racing.

## Layout

```
data/
  raw/        # source PP files (PDF, DRF, BRIS, HTML)
  parsed/     # normalized DataFrames / CSVs
notebooks/    # exploratory analysis
src/          # parsers, ratings, modeling
```

## Approach

Speed (Beyer) + Pace (E1/E2/LP) + Class + Form cycle → fair odds → bet only on overlays.
