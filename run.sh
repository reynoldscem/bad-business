#!/bin/bash

python bad_business.py > output.md && \
  pandoc output.md -o output.pdf
