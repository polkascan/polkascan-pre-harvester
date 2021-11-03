#! /usr/bin/env sh
LOG="$(date '+[%Y-%m-%d %T %z] [entrypoint] [INFO]')"

if [ -z $ENVIRONMENT ] || [ "$ENVIRONMENT" = "dev" ]; then
    ENVIRONMENT="dev"
fi

echo "$LOG ==========================="
echo "$LOG Environment: $ENVIRONMENT"
echo "$LOG ==========================="

if [ "$ENVIRONMENT" = "prod" ]; then
  echo "$LOG Wait for database..."
  # Let the DB start
  sleep 10;
fi

# Set path
export PYTHONPATH=$PYTHONPATH:$PWD:$PWD/py-substrate-interface/:$PWD/py-scale-codec/

echo "$LOG Running migrations..."

# Run migrations
alembic upgrade head

echo "$LOG Running gunicorn..."

if [ "$ENVIRONMENT" = "dev" ]; then
    gunicorn -b 0.0.0.0:8001 --workers=2 app.main:app --reload --timeout 600
fi

if [ "$ENVIRONMENT" = "prod" ]; then
    gunicorn -b 0.0.0.0:8000 --workers=5 app.main:app --worker-class="egg:meinheld#gunicorn_worker"
fi
