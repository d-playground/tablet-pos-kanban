#!/bin/bash
set -e

# Wait for MariaDB to be ready
echo "Waiting for MariaDB to be ready..."
python << END
import sys
import time
import mariadb

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = mariadb.connect(
            host="${DB_HOST}",
            user="${DB_USER}",
            password="${DB_PASSWORD}",
            database="${DB_NAME}"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM tables LIMIT 1")
        cursor.close()
        conn.close()
        print("MariaDB is up and initialized - starting Flask application")
        break
    except Exception as e:
        retry_count += 1
        if retry_count == max_retries:
            print(f"Failed to connect to MariaDB after {max_retries} attempts: {e}")
            sys.exit(1)
        print(f"MariaDB is unavailable - sleeping (attempt {retry_count}/{max_retries}): {e}")
        time.sleep(2)
END

# Start Flask application
exec python app.py 