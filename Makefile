.PHONY: data install analysis clean

DATA_URL := https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv
DATA_FILE := data/raw/telco_customer_churn.csv

data: $(DATA_FILE)

$(DATA_FILE):
	@mkdir -p data/raw
	curl -fsSL $(DATA_URL) -o $@
	@echo "fetched $$(wc -l < $@) lines"

install:
	pip install -r requirements.txt

analysis: $(DATA_FILE)
	python -m src.run_analysis

clean:
	rm -rf outputs/figures/*.png outputs/tables/*.csv outputs/metrics.json data/processed/*
