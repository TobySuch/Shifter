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

python manage.py createsettings

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
    # If not debug mode or test mode, set up cron.
    if [[ -z "$TEST_MODE" ]]
    then
        echo "Setting up cron."
        env >> /etc/environment  # Export environment variables for cron
        python manage.py crontab add
        crond -b
    else
        echo "In testing mode - not setting up con."
    fi
    python manage.py collectstatic --no-input --clear
fi
exec "$@"