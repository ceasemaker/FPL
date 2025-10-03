#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for Postgres to become available..."
until python - <<'PY'
import os
import psycopg2
from psycopg2 import OperationalError

try:
	conn = psycopg2.connect(
		host=os.getenv('POSTGRES_HOST', 'localhost'),
		port=int(os.getenv('POSTGRES_PORT', '5432')),
		dbname=os.getenv('POSTGRES_DB'),
		user=os.getenv('POSTGRES_USER'),
		password=os.getenv('POSTGRES_PASSWORD'),
		connect_timeout=3,
	)
except OperationalError:
	raise SystemExit(1)
else:
	conn.close()
	raise SystemExit(0)
PY
do
  echo "Postgres not ready yet. Retrying in 2s..."
  sleep 2
done

python manage.py migrate --no-input --fake-initial
exec "$@"
