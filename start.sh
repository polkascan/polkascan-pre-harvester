#! /usr/bin/env sh

if [ -z $ENVIRONMENT ] || [ "$ENVIRONMENT" = "dev" ]; then
    ENVIRONMENT="dev"
fi

echo "==========================="
echo "Environment: $ENVIRONMENT"
echo "==========================="

if [ "$ENVIRONMENT" = "prod" ]; then
  echo "Wait for database..."
  # Let the DB start
  sleep 10;
fi

echo "Running migrations..."

# Run migrations
alembic upgrade head

echo "Running gunicorn..."

if [ "$ENVIRONMENT" = "dev" ]; then
    # Set path
    export PYTHONPATH=$PYTHONPATH:./py-substrate-interface/:./py-scale-codec/
    gunicorn -b 0.0.0.0:8001 --workers=2 app.main:app --reload
fi

if [ "$ENVIRONMENT" = "prod" ]; then
    gunicorn -b 0.0.0.0:8000 --workers=5 app.main:app --worker-class="egg:meinheld#gunicorn_worker"
fi
