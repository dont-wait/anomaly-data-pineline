SHELL := /bin/sh

CONFIG ?= configs/base.yaml
OUTPUT ?= data/generated
REPORT_DIR ?= reports
SEED ?=
CUSTOMERS ?=

.PHONY: help setup shell generate report pipeline clean ui-install ui-dev ui-build

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "%-12s %s\n", $$1, $$2}'

setup: ## Resolve and install locked Python dependencies with Nix and uv
	uv sync

shell: ## Enter the Nix development shell
	nix develop

generate: ## Generate JSONL entities and chronological events (CONFIG, OUTPUT, SEED, CUSTOMERS overridable)
	uv run anomaly-data generate-data --config "$(CONFIG)" $(if $(SEED),--seed $(SEED)) $(if $(CUSTOMERS),--customers $(CUSTOMERS)) --output "$(OUTPUT)"

report: ## Analyze generated data into Markdown and CSV (OUTPUT, REPORT_DIR overridable)
	uv run anomaly-data report --data "$(OUTPUT)" --output "$(REPORT_DIR)"
	mkdir -p client/public
	cp "$(REPORT_DIR)/dashboard.json" client/public/dashboard.json
	cp "$(REPORT_DIR)/monthly-traffic.csv" client/public/monthly-traffic.csv

ui-install: ## Install React dashboard dependencies from its lockfile
	cd client && npm ci

ui-dev: ## Start the React dashboard dev server
	cd client && npm run dev -- --host 127.0.0.1

ui-build: ## Build the React dashboard for static hosting
	cd client && npm run build

pipeline: ## Generate data, then write the statistical report
	$(MAKE) generate
	$(MAKE) report

clean: ## Remove generated data and reports
	rm -rf -- "$(OUTPUT)" "$(REPORT_DIR)"
	rm -f -- client/public/dashboard.json client/public/monthly-traffic.csv
