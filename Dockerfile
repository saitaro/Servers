FROM python:3.7-alpine
LABEL maintainer="Victor B"

ENV PYTHONUNBUFFERED 1

RUN mkdir /server
WORKDIR /server
COPY . /server

RUN adduser -D user
RUN chown -R user:user /server
RUN chmod -R 755 /server
USER user
