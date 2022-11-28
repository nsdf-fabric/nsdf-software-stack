# Nice to have

Queries like:

- What is the most common file format (i.e. ext) in scientific repositories

```
select ext,SUM(tot_size) as tot_size from nsdf.aggregated_catalog GROUP BY(ext) ORDER BY tot_size DESC LIMIT 10;
```

- Growth curve of public scientific repos

```
# TODO: need to track the history, how to do that
```

- Most growing scientific repository in the world (time-window 30-60 days)

```
# TODO: will come for scraping done in different times
```

- What's the file size distribution world-wide. What's the file size in science?

```
# TODO: size in bucket with 10% percentile, median, 90% percentile
```

- What is the growing trends (material science vs astronony)

```
# TODO: how to perform freetext search? see `multiMatchAny`
```

- How many files tagged ML/FAIR in the last 60 days?

```
# TODO: enable tags
```

# Preliminary steps


Create an `.env` file with the content (change as needed):

```
AWS_ACCESS_KEY_ID=XXXXX
AWS_SECRET_ACCESS_KEY=YYYYY
CLICKHOUSE_HOST=ZZZZ
CLICKHOUSE_PORT=9440
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=KKKKK 
CLICKHOUSE_SECURE=True
```

Export `.env` variables to the current terminal:

```
set -o allexport
source ".env"
set +o allexport

# test aws credentials
aws s3 --profile wasabi ls s3://

# test clickhouse
alias cc="clickhouse-client --receive_timeout 9999999 --host ${CLICKHOUSE_HOST} --port ${CLICKHOUSE_PORT} --secure --user ${CLICKHOUSE_USER} --password ${CLICKHOUSE_PASSWORD}"
cc
```

# Instrutions

Check and modify the `docker-compose` as needed:

Serve panel application *locally*, for debugging purpouse:

```
python3 -m panel serve --autoreload --address='0.0.0.0' --allow-websocket-origin='*' --port ${PANEL_PORT} --autoreload run.py 
```

Serve using Docker 

```
# build the image
sudo docker build --tag nsdf/catalog:0.1 ./

# serve in foreground
sudo docker-compose --env-file .env up


# serve in daemon mode
sudo docker-compose --env-file .env up -d

# to shutdown
# sudo docker-compose down

# to inspect logs
# sudo docker compose logs 
```
