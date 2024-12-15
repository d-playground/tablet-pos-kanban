#!/bin/bash

host="$1"
shift
cmd="$@"

until mysql -h"$host" -u"$DB_USER" -p"$DB_PASSWORD" -e '\q'; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "MySQL is up - executing command"
exec $cmd 