# base image
FROM python:3.6.4-alpine
ENV PYTHONUNBUFFERED 1

# set working directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN apk add --no-cache --virtual .build-deps gcc libc-dev git

RUN pip3 install --upgrade pip

# add requirements
COPY ./requirements.txt /usr/src/app/requirements.txt

# install requirements
RUN pip3 install -r requirements.txt

RUN apk del .build-deps gcc libc-dev git

# add app
COPY . /usr/src/app
