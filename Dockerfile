# This Dockerfile is built from docker-compose.yml
FROM continuumio/miniconda3
MAINTAINER jimako1989

# Environment variables for alunir
#ENV KEY VAL

# Sharing files
ADD . /home

RUN pip install -r /home/requirements.txt
