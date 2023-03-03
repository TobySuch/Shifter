<p align="center">
  <a href="https://github.com/TobySuch/Shifter">
    <img alt="Shifter Logo" src="shifter/theme/static/img/logo.svg"/>
  </a>
</p>
<p align="center">
  <a href="https://github.com/TobySuch/Shifter/actions">
    <img alt="Test Status" src="https://github.com/TobySuch/Shifter/actions/workflows/main.yml/badge.svg?branch=main"/>
  </a>

  <a href="https://github.com/TobySuch/Shifter/blob/main/LICENSE">
    <img alt="MIT License" src="https://img.shields.io/github/license/TobySuch/Shifter.svg"/>
  </a>
  
  <a href="https://github.com/TobySuch/Shifter/releases">
    <img alt="Current Release" src="https://img.shields.io/github/release/TobySuch/Shifter.svg"/>
  </a>
</p>

---

Shifter is a simple self-hosted file-sharing web app built using Django and Tailwind. It allows you to quickly and easily upload files and share download links with others. All uploaded files have an expiration date after which they will be automatically deleted. Please note that the project is currently in early development and not all features are implemented yet, so everything is subject to change.

## Built using:
- [Django 4](https://github.com/django/django)
- [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) (With help from [Django-Tailwind](https://github.com/timonweb/django-tailwind))
- [Docker](https://github.com/docker)
- [FilePond](https://github.com/pqina/filepond) + [JSZip](https://github.com/Stuk/jszip)

## Running in production
This project is still in early development and should not be used in production yet. Many requirements and features are incomplete or non-existent. The instructions below are for documentation purposes only at this time. Please note that these instructions may not always be up to date or fully working in all configurations.

Before you begin, make sure you have installed Docker and Docker Compose on your system. If you're not sure how to do this, refer to the [Docker documentation](https://docs.docker.com/get-docker/) for instructions.

1. Download or clone this repository.
2. Make a copy of the `.env EXAMPLE` file and name it `.env`. In your new copy, make sure DEBUG is set to 0, and change any values that are set to `CHANGEME` to the appropriate values for your deployment.
3. In the .env file, update the DJANGO_ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS values to match your deployment.
4. Build and start the development containers using the following command:
```
docker-compose up --build
```
5. To create an admin user, run the following command and follow the prompts:
```
docker-compose exec web python manage.py createsuperuser
```
6. After creating the admin user, you will be able to log into the site using the credentials you entered.

## Installation Instructions (development):
These instructions are for setting up the project in development mode which may aid you in contributing. Before you begin, make sure you have installed Docker and Docker Compose on your system. If you're not sure how to do this, refer to the [Docker documentation](https://docs.docker.com/get-docker/) for instructions.

1. Download or clone this repository.
2. Make a copy of the `.env EXAMPLE` file and name it `.env.dev`. In your new copy, make sure `DEBUG` is set to 1, and change any values that are set to `CHANGEME` to the appropriate values for your development environment.
2. In the .env.dev file, add values for the following variables: `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`. These will be used to create an admin user when the containers are started. For example:
```
DJANGO_SUPERUSER_EMAIL=admin@mydomain.com
DJANGO_SUPERUSER_PASSWORD=CHANGEME
```
3. Build and start the development containers using the following command:
```
docker-compose -f docker-compose.dev.yml up --build
```
4. Once the containers are running, you should be able to access the site in your web browser at `127.0.0.1:8000`. By default, the admin user will automatically be created and you will be able to log in using the credentials you entered in the .env.dev file.
