FROM python:3.10-slim

# install dependencies
RUN apt update && apt install -y \
    python3-dev libpq-dev \
    python3-setuptools gcc
RUN pip install poetry

# copy data
COPY /dev/prepare_db.pql /app/prepare_db.pql
COPY /dev/prepare_db_mssql.pql /app/prepare_db_mssql.pql
COPY /dev/prepare_db_bigquery.pql /app/prepare_db_bigquery.pql
COPY /dev/poetry.lock /dev/pyproject.toml /dev/prepdb.sh /app/
ADD src src

WORKDIR /app
RUN chmod +x prepdb.sh

# install package
RUN poetry install

ARG DB1_URI
ARG TABLE1_NAME
ARG DB2_URI
ARG TABLE2_NAME
ARG OPTIONS

ENV DB1_URI ${DB1_URI}
ENV TABLE1_NAME ${TABLE1_NAME}
ENV DB2_URI ${DB2_URI}
ENV TABLE2_NAME ${TABLE2_NAME}
ENV OPTIONS ${OPTIONS}

CMD poetry run xdiff ${DB1_URI} ${TABLE1_NAME} ${DB2_URI} ${TABLE2_NAME} ${OPTIONS}