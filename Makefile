
.PHONY: ingest run quality test
ingest:
	python3 build_project.py
run: ingest quality
quality:
	python3 -c "import json; print(json.load(open('quality/dq_results.json')));"
test:
	pytest -q
