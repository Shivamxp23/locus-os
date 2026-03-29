#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/tmp/locus-backup-$DATE
mkdir -p $BACKUP_DIR

docker exec locus-postgres pg_dump -U locus locus | gzip > $BACKUP_DIR/postgres.sql.gz
docker exec locus-neo4j neo4j-admin database dump neo4j --to-path=/tmp 2>/dev/null
docker cp locus-neo4j:/tmp/neo4j.dump $BACKUP_DIR/neo4j.dump 2>/dev/null || true

rclone copy $BACKUP_DIR gdrive:locus-backups/$DATE
rm -rf $BACKUP_DIR
rclone delete gdrive:locus-backups --min-age 30d
