###########
# BUILDER #
###########

FROM python:3.9-alpine as builder

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
RUN flake8 . --ignore=E501

#########
# FINAL #
#########
FROM python:3.9-alpine

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
RUN apk add  --update libpq
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

COPY ./shifter/entrypoint.sh $APP_HOME

# copy project
COPY ./shifter/ $APP_HOME

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

ENTRYPOINT ["/home/app/web/entrypoint.sh"]
