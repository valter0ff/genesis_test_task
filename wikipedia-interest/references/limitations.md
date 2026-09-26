# Known Limitations

- **No topic-to-article resolution.** The `topic` field in `spec.json` is used *literally* as the Wikipedia article title in every requested language. There is no Wikidata lookup or translation step. If you ask for `"topic": "astronomy"` on `uk.wikipedia`, it will fail, because the Ukrainian article is titled `Астрономія`. **You must supply the exact article title for each language yourself** (open `https://<lang>.wikipedia.org/wiki/<Title>` to check).

- **Report language is hardcoded to Ukrainian** in the current build (both the `analyze` command and `run` pass `lang="uk"` unconditionally). English report text is not currently reachable through the CLI, even for an English-language topic. Localizing this properly (via a `--lang` flag or a `report_lang` field in `spec.json`) is the top item for the next iteration.

- **Only single-article topics are tested end-to-end.** Multi-article "baskets" (a topic covered by more than one article) are implemented and unit-tested in `metrics.py`, but not exercised through the CLI in a live run.

- Wikipedia interest measures attention, not willingness to pay or product demand.

- Normalization uses total monthly project views (`agent=user`) to remove platform-wide traffic trends; it does not control for differences in editor or reader demographics between language editions.

- A trend/YoY figure requires at least 24 full calendar months of data; shorter windows return `null` for those fields and a `low` confidence rating.