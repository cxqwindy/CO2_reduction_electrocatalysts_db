# Paragraph classification data

`negative_examples.jsonl` contains exactly 532 deterministic weakly labelled non-synthesis paragraphs reconstructed from the local parsed-paper corpus used during this reproduction.

Each JSON object contains `id`, `doi`, `source_path`, `section_heading`, `text`, `label` (always `0`), and `selection_score`. These are reconstructed examples rather than the unavailable original human annotations described by the paper.
