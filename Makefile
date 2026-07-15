.PHONY: web-smoke build

web-smoke:
	./scripts/local_web_smoke.sh

build:
	docker system prune -f && docker builder prune -f
	docker compose up -d --build
