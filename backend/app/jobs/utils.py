
from urllib.parse import urlparse, unquote
def parse_database_url(db_url: str):
    parsed = urlparse(db_url)

    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "dbname": parsed.path.lstrip("/"),
    }
