# Methodology Overview

## Normalization
Views are normalized as views per million project views (basket_views / project_total_views * 1e6) to remove platform-wide traffic trends and enable cross-language comparison.

## Year-over-Year (YoY) Growth
YoY growth compares the last 12 months to the previous 12 months (last_12m / prev_12m - 1). Calculated for both raw and normalized views to distinguish topic-specific trends from platform-wide trends.

## Theil-Sen Trend
Theil-Sen slope computes the median slope between all pairs of points in the monthly normalized series, providing a robust linear trend estimate. Expressed as % change per year relative to the series median.

## Spike Detection
Spikes are identified using robust z-scores: z = (x - median) / (1.4826 * MAD), where MAD is the median absolute deviation. Days with z > 4 are considered spikes. Spike share represents the fraction of total views attributable to spike days.