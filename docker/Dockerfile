###########
# BUILDER #
###########

FROM python:3.10-alpine as builder

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk add --update postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
RUN pip install flake8
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

COPY ./shifter/ .
RUN flake8 . --exclude=migrations

#########
# FINAL #
#########
FROM python:3.10-alpine

# create directory for the app user
RUN mkdir -p /home/app

# create the app user
RUN addgroup -S app && adduser -S app -G app

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/static
WORKDIR $APP_HOME

# install dependencies
RUN apk add --update libpq nodejs npm
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# copy project
COPY ./shifter/ $APP_HOME

# Labels
LABEL org.opencontainers.image.source https://github.com/TobySuch/Shifter
LABEL org.opencontainers.image.description="Shifter - A simple, self-hosted file-sharing web app, powered by Django"
LABEL org.opencontainers.image.licenses=MIT

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

ENTRYPOINT [ "/home/app/web/entrypoint.sh" ]
CMD [ "gunicorn", "shifter.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "600" ]