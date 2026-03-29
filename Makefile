# Genshin Manager — target operativi pipeline dati (nessuna dipendenza da make obbligatoria: solo convenzione).
.PHONY: help pipeline-starter pipeline-validate-seeds pipeline-inbox pipeline-inbox-dry pipeline-metrics user-export-help

PYTHON ?= python3
export PYTHONPATH := $(CURDIR)

help:
	@echo "Target pipeline:"
	@echo "  make pipeline-starter        — genera batch seed in data/pipeline_inbox/ e li valida"
	@echo "  make pipeline-validate-seeds — solo validazione dei tre batch_seed_*.json"
	@echo "  make pipeline-inbox          — ingest automatico file nuovi in inbox (manifest)"
	@echo "  make pipeline-inbox-dry      — anteprima ingest senza scrivere"
	@echo "  make pipeline-metrics        — report da data/pipeline_logs/ (volume, approve%, warning)"
	@echo "  make user-export-help        — comando bridge export utente → inbox (file-only)"

pipeline-starter:
	@$(PYTHON) tools/pipeline/export_from_catalog.py starter-pack
	@$(MAKE) pipeline-validate-seeds

pipeline-validate-seeds:
	@$(PYTHON) tools/pipeline/cli.py validate --batch data/pipeline_inbox/batch_seed_personaggi.json
	@$(PYTHON) tools/pipeline/cli.py validate --batch data/pipeline_inbox/batch_seed_armi.json
	@$(PYTHON) tools/pipeline/cli.py validate --batch data/pipeline_inbox/batch_seed_manufatti.json
	@echo "OK: batch seed validati."

pipeline-inbox:
	@$(PYTHON) tools/pipeline/inbox_runner.py

pipeline-inbox-dry:
	@$(PYTHON) tools/pipeline/inbox_runner.py --dry-run

pipeline-metrics:
	@$(PYTHON) tools/pipeline/metrics_report.py

user-export-help:
	@echo "Export utente (nessun token / nessuna rete):"
	@echo "  $(PYTHON) tools/user_export_bridge/convert_to_pipeline.py -i file.json --validate-only"
	@echo "  $(PYTHON) tools/user_export_bridge/convert_to_pipeline.py -i file.json -o data/pipeline_inbox/batch_user_export.json"
	@echo "Esempio input: tools/user_export_bridge/example_user_export.json"
