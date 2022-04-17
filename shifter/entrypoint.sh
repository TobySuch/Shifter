#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# If debug mode, flush the data from the server
if [ "$DEBUG" = "1" ]
then
  python manage.py flush --no-input  
fi

python manage.py migrate --no-input

# If debug mode, create an admin user
if [ "$DEBUG" = "1" ]
then
  python manage.py createsuperuser --no-input --email "admin@example.com"
else
  python manage.py tailwind install
  python manage.py tailwind build
  python manage.py collectstatic --no-input --clear
fi
exec "$@"