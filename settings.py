import json
import os

"""
Paramètres de l'application.
Les valeurs secrètes (token IPinfo, mot de passe PostgreSQL) sont dans config.json,
qui n'est PAS envoyé sur Git (voir .gitignore). Modèle : config.example.json
"""

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT_DIR, 'config.json')

DEFAULT_SETTINGS = {
    'ipinfo_token': '',
    'log_year': 2026,  # les lignes syslog n'ont pas d'année
    'database': {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'log_analysis',
        'user': 'postgres',
        'password': '',
    },
}


def load_settings(config_file: str = CONFIG_FILE):
    """Paramètres par défaut, complétés par config.json s'il existe."""
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # copie
    if not os.path.exists(config_file):
        return settings
    try:
        with open(config_file, encoding='utf-8') as f:
            user_settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return settings

    for key, value in user_settings.items():
        if key == 'database' and isinstance(value, dict):
            settings['database'].update(value)
        else:
            settings[key] = value
    return settings


SETTINGS = load_settings()
