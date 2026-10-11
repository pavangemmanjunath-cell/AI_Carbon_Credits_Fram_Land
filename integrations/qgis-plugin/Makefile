# CarbonCreditBuy QGIS plugin - developer shortcuts (run from this directory).
# SPDX-License-Identifier: GPL-2.0-or-later

PY ?= python
PLUGIN := carboncreditbuy_qgis
REPO_ROOT := ../..
QGIS_PLUGINS_DIR ?= $(HOME)/.local/share/QGIS/QGIS3/profiles/default/python/plugins

.DEFAULT_GOAL := help
.PHONY: help package test lint format link clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'

package: ## build dist/carboncreditbuy_qgis-<version>.zip for "Install from ZIP"
	$(PY) scripts/package.py

test: ## run the plugin tests (QGIS is not needed)
	cd $(REPO_ROOT) && $(PY) -m pytest integrations/qgis-plugin/tests -q

lint: ## ruff check and format check
	cd $(REPO_ROOT) && ruff check integrations/qgis-plugin && ruff format --check integrations/qgis-plugin

format: ## ruff format and safe fixes
	cd $(REPO_ROOT) && ruff format integrations/qgis-plugin && ruff check --fix integrations/qgis-plugin

link: ## symlink the plugin into a QGIS profile for development (set QGIS_PLUGINS_DIR to change it)
	mkdir -p "$(QGIS_PLUGINS_DIR)"
	ln -sfn "$(CURDIR)/$(PLUGIN)" "$(QGIS_PLUGINS_DIR)/$(PLUGIN)"
	@echo "Linked. Enable the plugin in QGIS (Plugins > Manage and Install Plugins > Installed)."

clean: ## remove build output and caches
	rm -rf dist .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
