# This Dockerfile is built from docker-compose.yml
ARG TEST_ENV
ARG DOCKER_DIST_DIR
ARG AWS_ACCOUNT_ID
ARG AWS_DEFAULT_REGION
ARG ECS_ENV
ARG JUPYTER_NOTEBOOK_PORT
ARG JUPYTER_NOTEBOOK_TOKEN
FROM ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/alunir-build:latest
MAINTAINER jimako1989

# Environment variables for laurel
#ENV KEY VAL

# Sharing files
ADD . /home
RUN rm -rf artifacts target target.zip **/__pychache__ .ecs_env */file::memory:?cache=shared* */shared-local-instance.db */nohup.out laurel/main/resources/laurel.db*
