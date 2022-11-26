![Shifter Logo](shifter/theme/static/img/logo.svg)

![Test Status](https://github.com/TobySuch/Shifter/actions/workflows/main.yml/badge.svg?branch=main)

---

Simple Firefox Send replacement built using Django and Tailwind. Quickly and easily upload files and get a link you can share with others to download. All files have an expiry date after which they will be deleted. 

The project is currently in early development and not all features are implemented yet. Pretty much everything is subject to change at this point in time.

## Built using:
- [Django 4](https://github.com/django/django)
- [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) (With help from [Django-Tailwind](https://github.com/timonweb/django-tailwind))
- [Docker](https://github.com/docker)
- [FilePond](https://github.com/pqina/filepond)

## Running in production
This project is still in early development and **should not** be used in production yet. Many requirements/features are incomplete or non existant. Instuctions below are for documentation reasons only right now. Also please note that these instructions may not always be up to date or fully working in all configurations currently.
1. Install docker and docker compose
2. Download/clone this repository
3. Make a copy of the `.env EXAMPLE` file called `.env`. In your new copy make sure `DEBUG` is set to 0 and you should change anything that is set to `CHANGEME` to another value.
4. `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` need to be changed to appropriate values for your deployment.
5. Build and start the development containers using the command:
```
docker-compose up --build
```
5. Create an admin user using by running the following command, and filling out the prompts that come up:
```
docker-compose exec web python manage.py createsuperuser
```
6. You will now be able to log into the site with the credentials entered when creating the admin user.

## Installation Instructions (development):
1. Install docker and docker compose
2. Download/clone this repository
3. Make a copy of the `.env EXAMPLE` file called `.env.dev`. In your new copy make sure `DEBUG` is set to 1 and you should change anything that is set to `CHANGEME` to another value, although in dev this isn’t as important.
4. Build and start the development containers using the command:
```
docker-compose -f docker-compose.dev.yml up --build
```
5. You should be able to access the site in your web browser at `127.0.0.1:8000`. By default there will be an admin user created with the email “admin@mydomain.com” and password “CHANGEME” unless you have changed these values in your environment file.
