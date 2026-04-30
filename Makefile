up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend:
	docker compose exec backend bash

test-backend:
	cd backend && pytest
