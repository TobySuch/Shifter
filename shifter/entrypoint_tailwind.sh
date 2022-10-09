#!/bin/sh

# Install Tailwind dependencies
python manage.py tailwind install

# Copy over flowbite
mkdir ./theme/static/js
mkdir ./theme/static/js/flowbite
cp ./theme/static_src/node_modules/flowbite/dist/* ./theme/static/js/flowbite

exec "$@"