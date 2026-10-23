#!/usr/bin/env python3
"""Train and save the sentence LDA and synthesis paragraph classifier."""

from synthesis_paragraph_classifier.cli import main

raise SystemExit(main(["train", *__import__("sys").argv[1:]]))
