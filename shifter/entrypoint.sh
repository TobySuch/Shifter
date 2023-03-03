#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
elif [ "$DATABASE" = "sqlite" ]
then
    echo "Using sqlite"
    # Create db folder
    mkdir -p "/app/db"
fi

# If debug mode, flush the data from the server
if [ "$DEBUG" = "1" ]
then
    python manage.py flush --no-input  
fi

python manage.py migrate --no-input

# If debug mode and env vars are set, create an admin user
if [ "$DEBUG" = "1" ]
then
    if [[ -z "$DJANGO_SUPERUSER_EMAIL" ]] || [[ -z "$DJANGO_SUPERUSER_PASSWORD" ]]
    then
        echo "DJANGO_SUPERUSER_EMAIL and/or DJANGO_SUPERUSER_PASSWORD not set. Skipping superuser creation."
    else
        python manage.py createsuperuser --no-input
    fi
else
    # If prod mode, build and collect static files
    python manage.py tailwind install
    python manage.py tailwind build
    # Copy over flowbite
    mkdir ./theme/static/js
    mkdir ./theme/static/js/flowbite
    cp ./theme/static_src/node_modules/flowbite/dist/* ./theme/static/js/flowbite
    python manage.py crontab add
    python manage.py collectstatic --no-input --clear
fi
exec "$@"