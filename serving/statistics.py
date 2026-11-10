from collections import Counter
from datetime import date

from log_config import get_logger

"""
Calcul des statistiques du dashboard à partir des événements.
Chaque événement compte `count` fois (lignes "message repeated N times").
"""

logger = get_logger('serving')


def sort_counter(counter: Counter):
    """Liste de (clé, valeur) triée par valeur décroissante puis par clé."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def failures_by_country(events: list):
    """Indicateur 1 : tentatives échouées par pays."""
    counter = Counter()
    for event in events:
        if event['status'] == 'failure':
            counter[event['country'] or 'Unknown'] += event['count']
    return sort_counter(counter)


def successes_by_user(events: list):
    """Indicateur 2 : connexions réussies par utilisateur."""
    counter = Counter()
    for event in events:
        if event['event_type'] == 'accepted':
            counter[event['user']] += event['count']
    return sort_counter(counter)


def invalid_user_failures(events: list):
    """Indicateur 3 : tentatives échouées avec utilisateur invalide, par nom d'utilisateur.
    Seules les lignes "Failed ... for invalid user" sont comptées : la ligne
    "Invalid user ..." qui les précède décrit la même tentative."""
    counter = Counter()
    for event in events:
        if event['event_type'] == 'failed_invalid_user':
            counter[event['user'] or '(empty)'] += event['count']
    return sort_counter(counter)


def failures_by_date(events: list):
    """Indicateur temporel : tentatives échouées par jour (toutes / utilisateur invalide)."""
    all_failures = Counter()
    invalid_failures = Counter()
    for event in events:
        if event['status'] == 'failure' and event['date']:
            all_failures[event['date']] += event['count']
            if event['event_type'] == 'failed_invalid_user':
                invalid_failures[event['date']] += event['count']
    # tri chronologique (les dates ISO se trient comme du texte)
    return [(day, all_failures[day], invalid_failures[day]) for day in sorted(all_failures)]


def failures_by_hour(events: list):
    """Tentatives échouées selon l'heure de la journée (0 à 23 h)."""
    counter = Counter()
    for event in events:
        if event['status'] == 'failure' and event['time']:
            counter[int(event['time'][:2])] += event['count']
    return [(hour, counter[hour]) for hour in range(24)]


def failures_by_weekday_hour(events: list):
    """Grille 7 x 24 : tentatives échouées par jour de la semaine (lundi = 0) et par heure."""
    grid = [[0] * 24 for _ in range(7)]
    for event in events:
        if event['status'] == 'failure' and event['date'] and event['time']:
            weekday = date.fromisoformat(event['date']).weekday()
            grid[weekday][int(event['time'][:2])] += event['count']
    return grid


def compute_statistics(events: list):
    """Toutes les statistiques nécessaires au dashboard."""
    by_country = failures_by_country(events)
    by_user = successes_by_user(events)
    invalid = invalid_user_failures(events)

    statistics = {
        'total_lines': len(events),
        'successful_logins': sum(count for _, count in by_user),
        'failed_logins': sum(count for _, count in by_country),
        'invalid_user_attempts': sum(count for _, count in invalid),
        'distinct_invalid_users': len(invalid),
        'distinct_ips': len({event['ip'] for event in events if event['ip']}),
        'failures_by_country': by_country,
        'successes_by_user': by_user,
        'invalid_users': invalid,
        'failures_by_date': failures_by_date(events),
        'failures_by_hour': failures_by_hour(events),
        'failures_by_weekday_hour': failures_by_weekday_hour(events),
    }
    logger.info(f"Statistics computed: {statistics['failed_logins']} failures, "
                f"{statistics['successful_logins']} successes")
    return statistics
