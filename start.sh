#!/bin/bash

cd "$(dirname "$0")"

echo "$(pwd)"

source env/bin/activate

uvicorn app:app --host=0.0.0.0
