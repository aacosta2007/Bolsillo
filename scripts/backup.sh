#!/bin/sh
# Backup diario de MariaDB con rotación. Corre dentro del contenedor `backup`.
set -eu
KEEP="${BACKUP_KEEP_DAYS:-14}"

run_backup() {
  file="/backups/bolsillo_$(date +%Y%m%d_%H%M%S).sql.gz"
  if mariadb-dump -h "$DB_HOST" -u "$DB_USER" --single-transaction "$DB_NAME" | gzip > "$file.tmp"; then
    mv "$file.tmp" "$file"
    echo "[backup] OK $file"
  else
    rm -f "$file.tmp"
    echo "[backup] ERROR al generar backup" >&2
  fi
  find /backups -name 'bolsillo_*.sql.gz' -mtime +"$KEEP" -delete
}

run_backup
while true; do
  # Siguiente ejecución a las 03:00
  now=$(date +%s)
  next=$(date -d "$(date +%Y-%m-%d) 03:00" +%s 2>/dev/null || echo $((now + 86400)))
  [ "$next" -le "$now" ] && next=$((next + 86400))
  sleep $((next - now))
  run_backup
done
