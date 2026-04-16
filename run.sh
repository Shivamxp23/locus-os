#!/bin/bash
set -a
source /opt/locus/.env
set +a
cd /opt/locus/backend
exec "$@"
