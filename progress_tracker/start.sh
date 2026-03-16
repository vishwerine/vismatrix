#!/bin/bash

echo "Installing dependencies..."
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Running migrations..."
python3 manage.py migrate --noinput

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Starting server..."
gunicorn progress_tracker.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120