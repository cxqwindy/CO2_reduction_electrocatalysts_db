#!/usr/bin/env python3
"""Generate the reconstructed 228-positive/532-negative training set."""

from synthesis_paragraph_classifier.cli import main

raise SystemExit(main(["generate-data", *__import__("sys").argv[1:]]))
