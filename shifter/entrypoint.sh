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

# Copy over flowbite
mkdir ./theme/static/js
mkdir ./theme/static/js/flowbite
cp ./theme/static_src/node_modules/flowbite/dist/* ./theme/static/js/flowbite

# If debug mode, create an admin user
if [ "$DEBUG" = "1" ]
then
  python manage.py createsuperuser --no-input
else
# If prod mode, build and collect static files
  python manage.py tailwind install
  python manage.py tailwind build
  python manage.py crontab add
  python manage.py collectstatic --no-input --clear
fi
exec "$@"