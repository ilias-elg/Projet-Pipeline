import psycopg2
from psycopg2.extras import execute_values

from log_config import get_logger
from settings import SETTINGS

"""
Stockage des événements dans PostgreSQL (psycopg2).

Tables :
    events       un événement par ligne de log
    geolocation  cache ip -> pays

Si la base n'est pas joignable, le pipeline continue avec les fichiers CSV/JSON.
"""

logger = get_logger('storage')

CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id           SERIAL PRIMARY KEY,
    event_date   DATE,
    month        VARCHAR(3),
    day          VARCHAR(2),
    time         VARCHAR(8),
    host         VARCHAR(100),
    process      VARCHAR(100),
    pid          VARCHAR(20),
    event_type   VARCHAR(30),
    status       VARCHAR(10),
    username     VARCHAR(255),
    ip           VARCHAR(15),
    port         VARCHAR(10),
    method       VARCHAR(50),
    invalid_user BOOLEAN,
    reason       VARCHAR(100),
    count        INTEGER,
    country      VARCHAR(20)
)"""

CREATE_GEOLOCATION = """
CREATE TABLE IF NOT EXISTS geolocation (
    ip      VARCHAR(15) PRIMARY KEY,
    country VARCHAR(20)
)"""

# Colonnes de la table events, dans le même ordre que les valeurs insérées
EVENT_COLUMNS = ['event_date', 'month', 'day', 'time', 'host', 'process', 'pid', 'event_type',
                 'status', 'username', 'ip', 'port', 'method', 'invalid_user', 'reason', 'count',
                 'country']


def connect(database: dict = None):
    """Ouvre une connexion PostgreSQL. Retourne None si la base est injoignable."""
    params = database or SETTINGS['database']
    try:
        connection = psycopg2.connect(host=params['host'], port=params['port'],
                                      dbname=params['dbname'], user=params['user'],
                                      password=params['password'], connect_timeout=5)
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL connection error: {e}")
        return None
    logger.info(f"Connected to PostgreSQL database {params['dbname']}")
    return connection


def create_tables(connection):
    with connection.cursor() as cursor:
        cursor.execute(CREATE_EVENTS)
        cursor.execute(CREATE_GEOLOCATION)
    connection.commit()


def event_to_row(event: dict):
    """Transforme un événement (dictionnaire) en tuple pour l'insertion SQL."""
    return (event['date'] or None, event['month'], event['day'], event['time'], event['host'],
            event['process'], event['pid'], event['event_type'], event['status'], event['user'],
            event['ip'], event['port'], event['method'], event['invalid_user'], event['reason'],
            event['count'], event['country'])


def row_to_event(row: tuple):
    """Transforme une ligne SQL en événement (mêmes clés que le processing)."""
    values = dict(zip(EVENT_COLUMNS, row))
    values['date'] = values.pop('event_date').isoformat() if values['event_date'] else ''
    values['user'] = values.pop('username')
    return values


def save_events(events: list, connection=None):
    """Remplace le contenu de la table events. Retourne True si la sauvegarde a réussi."""
    own_connection = connection is None
    connection = connection or connect()
    if connection is None:
        return False
    try:
        create_tables(connection)
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE events RESTART IDENTITY")
            execute_values(cursor,
                           "INSERT INTO events (" + ", ".join(EVENT_COLUMNS) + ") VALUES %s",
                           [event_to_row(event) for event in events], page_size=5000)
        connection.commit()
    except psycopg2.Error as e:
        connection.rollback()
        logger.error(f"PostgreSQL save error: {e}")
        return False
    finally:
        if own_connection:
            connection.close()
    logger.info(f"{len(events)} events saved in PostgreSQL")
    return True


def load_events(connection=None):
    """Relit tous les événements de la table events (liste vide en cas d'erreur)."""
    own_connection = connection is None
    connection = connection or connect()
    if connection is None:
        return []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT " + ", ".join(EVENT_COLUMNS) + " FROM events ORDER BY id")
            events = [row_to_event(row) for row in cursor.fetchall()]
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL read error: {e}")
        return []
    finally:
        if own_connection:
            connection.close()
    logger.info(f"{len(events)} events loaded from PostgreSQL")
    return events


def save_geolocation(cache: dict, connection=None):
    """Enregistre (ou met à jour) le pays de chaque IP."""
    own_connection = connection is None
    connection = connection or connect()
    if connection is None:
        return False
    try:
        create_tables(connection)
        with connection.cursor() as cursor:
            execute_values(cursor,
                           "INSERT INTO geolocation (ip, country) VALUES %s "
                           "ON CONFLICT (ip) DO UPDATE SET country = EXCLUDED.country",
                           list(cache.items()))
        connection.commit()
    except psycopg2.Error as e:
        connection.rollback()
        logger.error(f"PostgreSQL geolocation save error: {e}")
        return False
    finally:
        if own_connection:
            connection.close()
    logger.info(f"{len(cache)} IP countries saved in PostgreSQL")
    return True
