PYTHON = .venv/bin/python
PIP = .venv/bin/pip
GUNICORN = .venv/bin/gunicorn
PORT ?= 8301

# ── Setup ─────────────────────────────────────────────

.PHONY: setup
setup: venv install migrate seed  ## Full local setup from scratch

.PHONY: venv
venv:  ## Create virtualenv
	python3 -m venv .venv

.PHONY: install
install:  ## Install dependencies
	$(PIP) install -r requirements.txt

# ── Database ──────────────────────────────────────────

.PHONY: migrate
migrate:  ## Run makemigrations + migrate
	$(PYTHON) manage.py makemigrations
	$(PYTHON) manage.py migrate

.PHONY: seed
seed:  ## Flush ifr_ tables and reload all fixtures
	$(PYTHON) manage.py seed

.PHONY: fixtures-load
fixtures-load:  ## Load all scenario fixtures (skip existing)
	$(PYTHON) manage.py load_all_scenarios

.PHONY: fixtures-update
fixtures-update:  ## Load all scenario fixtures (update existing)
	$(PYTHON) manage.py load_all_scenarios --update

.PHONY: flush
flush:  ## Flush all ifr_ tables (with confirmation)
	$(PYTHON) manage.py flush_ifr

.PHONY: flush-sessions
flush-sessions:  ## Flush only session data, keep scenarios
	$(PYTHON) manage.py flush_ifr --sessions-only --no-input

# ── Server ────────────────────────────────────────────

.PHONY: server
server:  ## Run gunicorn dev server on PORT (default 8301)
	$(GUNICORN) config.wsgi:application --bind 127.0.0.1:$(PORT) --workers 2 --access-logfile - --reload

.PHONY: server-otel
server-otel:  ## Run gunicorn with OTel export to local Alloy
	OTEL_ENABLED=true $(GUNICORN) config.wsgi:application --bind 127.0.0.1:$(PORT) --workers 2 --access-logfile - --reload

.PHONY: server-dev
server-dev:  ## Run Django runserver (no gunicorn, for debugging)
	$(PYTHON) manage.py runserver $(PORT)

.PHONY: shell
shell:  ## Django shell
	$(PYTHON) manage.py shell

.PHONY: admin
admin:  ## Create superuser (admin/admin)
	DJANGO_SUPERUSER_PASSWORD=admin $(PYTHON) manage.py createsuperuser --noinput --username admin --email admin@local.dev 2>/dev/null || echo "Superuser already exists"

# ── Testing ───────────────────────────────────────────

.PHONY: test
test:  ## Run all tests
	$(PYTHON) -m pytest tests/ -v

.PHONY: test-fast
test-fast:  ## Run tests without verbose output
	$(PYTHON) -m pytest tests/

.PHONY: check
check:  ## Django system checks
	$(PYTHON) manage.py check

# ── Heroku ────────────────────────────────────────────

.PHONY: heroku-seed
heroku-seed:  ## Seed fixtures on Heroku
	heroku run python manage.py seed -a cleared-direct

.PHONY: heroku-shell
heroku-shell:  ## Open Django shell on Heroku
	heroku run python manage.py shell -a cleared-direct

.PHONY: heroku-logs
heroku-logs:  ## Tail Heroku logs
	heroku logs --tail -a cleared-direct

.PHONY: heroku-migrate
heroku-migrate:  ## Run migrations on Heroku
	heroku run python manage.py migrate -a cleared-direct

# ── Help ──────────────────────────────────────────────

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
