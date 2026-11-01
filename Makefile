# Pintasan perintah. Di Windows, jalankan lewat Git Bash/WSL atau salin perintahnya manual.
.PHONY: up down logs ps etl import-data dev-data import-dev psql reset-db test test-go test-ml test-front

up:            ## bangun dan jalankan semua layanan (web di http://localhost:3000)
	docker compose up --build -d

down:          ## hentikan semua layanan (data database tetap ada)
	docker compose down

reset-db:      ## hentikan dan HAPUS volume database
	docker compose down -v

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

etl:           ## ubah data mentah SIMPANG (data/raw/simpang/) menjadi CSV 6 kolom (data/processed/)
	python3 scripts/etl_simpang.py data/raw/simpang/data_harian_simpang_medan.csv

import-data:    ## impor data SIMPANG hasil ETL lewat API (aman diulang, tidak membuat duplikat)
	python3 scripts/impor_csv.py data/processed/harga_harian_simpang.csv

dev-data:      ## bangkitkan data sintetis (sumber DEV) ke data/dev/harga_dev.csv
	python3 scripts/gen_data_dev.py

import-dev:    ## impor data sintetis lewat API (jalur yang sama dengan impor CSV asli)
	python3 scripts/impor_csv.py data/dev/harga_dev.csv

psql:
	docker compose exec db psql -U $${POSTGRES_USER:-pangan} -d $${POSTGRES_DB:-harga_pangan}

test: test-go test-ml test-front

test-go:
	cd backend && go test ./...

test-ml:
	cd ml && python3 -m pytest -q

test-front:
	cd frontend && npm test
