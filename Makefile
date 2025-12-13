.PHONY: install init-db scrape analyze serve lint

install:
python -m venv .venv
. .venv/bin/activate && pip install -r requirements.txt

init-db:
. .venv/bin/activate && python -c "from workana.db import init_db; init_db()"

scrape:
. .venv/bin/activate && python -m workana.scraper

analyze:
. .venv/bin/activate && python -m workana.analyzer

serve:
. .venv/bin/activate && flask --app workana.app:APP run --host=0.0.0.0 --port=8000
