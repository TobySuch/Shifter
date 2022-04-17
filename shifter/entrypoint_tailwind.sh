#!/bin/sh

# Install Tailwind dependencies
python manage.py tailwind install

exec "$@"