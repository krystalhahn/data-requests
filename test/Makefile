SHELL := bash
.ONESHELL:
# .SHELLFLAGS := -eu -o pipefail -c


# Define R and Python interpreters
R_SCRIPT = Rscript --vanilla

# Phony targets (i.e., do not produce files with these names)
.PHONY: all data

# Default target
all: data result.csv

data:
	mkdir -p $@

data/result.csv: get-data.r
	$(R_SCRIPT) $< $@
