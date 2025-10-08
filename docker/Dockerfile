##################
# PYTHON BUILDER #
##################

FROM python:3.14.0-alpine AS builder

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk add --update postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY ./shifter/requirements_dev.txt .
RUN pip install -r requirements_dev.txt
COPY ./shifter/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

COPY ./shifter/ .
RUN ruff check .

################
# NODE BUILDER #
################
FROM node:24 AS nodebuilder
WORKDIR /app

RUN npm install -g npm
COPY ./shifter/package.json .
COPY ./shifter/package-lock.json .

RUN npm install

COPY ./shifter/webpack.config.js .
COPY ./shifter ./shifter

RUN npm run tailwind-build
RUN npm run js-build


#########
# FINAL #
#########
FROM python:3.14.0-alpine
ARG APP_VERSION="0.0.0"
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
RUN pip install --upgrade pip
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# copy project
COPY ./shifter/ $APP_HOME

# copy static files
COPY --from=nodebuilder /app/shifter/static/js $APP_HOME/static/js
COPY --from=nodebuilder /app/shifter/static/css $APP_HOME/static/css

# Labels
LABEL org.opencontainers.image.title=Shifter
LABEL org.opencontainers.image.source=https://github.com/TobySuch/Shifter
LABEL org.opencontainers.image.description="Shifter - A simple, self-hosted file-sharing web app, powered by Django"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.version=${APP_VERSION}
ENV APP_VERSION=${APP_VERSION}

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

ENTRYPOINT [ "/home/app/web/entrypoint.sh" ]
CMD [ "gunicorn", "shifter.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "600" ]
