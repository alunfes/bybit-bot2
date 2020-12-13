FROM python:3
#USER root

RUN apt-get update

RUN apt-get install -y vim
RUN pip install --upgrade pip