# Dev workflow for the whole stack. Run `make` to list targets.
COMPOSE := docker compose -f docker/docker-compose.yml
export COMPOSE_BAKE := true

# Root CA of a TLS-inspecting proxy, trusted only while downloading during the image build (see `make ca`).
CA_NAME ?= Gateway CA - Cloudflare Managed
export EXTRA_CA_FILE := $(if $(wildcard docker/extra-ca.pem),$(abspath docker/extra-ca.pem),/dev/null)

.DEFAULT_GOAL := help
.PHONY: help up down logs ps migrate rebuild ca

help: ## Show this help
	@awk -F':.*## ' '/^[a-z]+:.*## /{printf "  make %-9s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

backend/.env:
	@cp backend/.env.example $@
	@echo "Created $@ from the example. Set DATABASE_URL in it, then re-run." >&2; exit 1

up: backend/.env ## Build and run backend (:7001) + frontend (:4001); auto sync/rebuild on change
	$(COMPOSE) up --build --watch --remove-orphans

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

ps: ## Show container status
	$(COMPOSE) ps

ca: ## macOS: export your network's TLS-inspection root CA so image builds can download (README: Troubleshooting)
	@security find-certificate -a -p -c "$(CA_NAME)" > docker/extra-ca.pem
	@test -s docker/extra-ca.pem || { rm -f docker/extra-ca.pem; echo "No certificate matching '$(CA_NAME)' in the keychain. Set CA_NAME=..." >&2; exit 1; }
	@echo "Wrote docker/extra-ca.pem ($$(grep -c BEGIN docker/extra-ca.pem) certificate); the next build trusts it."

migrate: backend/.env ## Run alembic upgrade head in the backend container
	$(COMPOSE) run --rm --no-deps backend alembic upgrade head

rebuild: backend/.env ## Clean rebuild (no cache), then run with watch
	$(COMPOSE) build --no-cache
	$(COMPOSE) up --watch --remove-orphans
