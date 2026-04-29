#!/bin/sh
set -eu

alembic -c alembic.ini upgrade head
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000
