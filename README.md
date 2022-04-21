# Shifter

Simple Firefox Send replacement built using Django and Tailwind. Quickly and easily upload files and get a link you can share with others to download. All files have an expiry date after which they will be deleted. 

The project is currently in early development and not all features are implemented yet. Pretty much everything is subject to change at this point in time.

## Built using:
- [Django 4](https://github.com/django/django)
- [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) (With help from [Django-Tailwind](https://github.com/timonweb/django-tailwind))
- [Docker](https://github.com/docker)
- [FilePond](https://github.com/pqina/filepond)

## Installation Instructions (development):
1. Install docker and docker compose
2. Download/clone this repository
3. Make a copy of the `.env EXAMPLE` file called `.env.dev`. In your new copy make sure `DEBUG` is set to 1 and you should change anything that is set to `CHANGEME` to another value, although in dev this isn’t as important.
4. Build and start the development containers using the command:
```
docker-compose -f docker-compose.dev.yml up —-build
```
5. You should be able to access the site in your web browser at `127.0.0.1:8000`. By default there will be an admin user created with the email “admin@mydomain.com” and password “CHANGEME” unless you have changed these values in your environment file.
