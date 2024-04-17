#!/usr/bin/env bash

docker build . -f Dockerfile --target base -t local-python-base --no-cache
docker build . -f Dockerfile.requirements -t local-python-requirements --no-cache
id=$(docker create local-python-requirements)
docker cp $id:requirements.txt gen_requirements.txt
docker rm $id
docker image rm local-python-requirements local-python-base
cat < gen_requirements.txt > requirements.txt
rm gen_requirements.txt