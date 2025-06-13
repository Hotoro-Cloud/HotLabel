#!/bin/bash

# Stop the services
cd /Users/faidhfeisal/hotlabel/hotlabel-infra
docker-compose -f docker-compose-local.yml stop tasks qa

# Run migrations for tasks service
echo "Running migrations for tasks service..."
cd /Users/faidhfeisal/hotlabel/hotlabel-tasks
docker-compose -f ../hotlabel-infra/docker-compose-local.yml run --rm tasks alembic upgrade head

# Run migrations for qa service
echo "Running migrations for qa service..."
cd /Users/faidhfeisal/hotlabel/hotlabel-qa
docker-compose -f ../hotlabel-infra/docker-compose-local.yml run --rm qa alembic upgrade head

# Restart the services
cd /Users/faidhfeisal/hotlabel/hotlabel-infra
docker-compose -f docker-compose-local.yml up -d tasks qa

echo "Migrations completed. Services restarted." 