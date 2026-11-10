import os
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from log_config import get_logger

"""
Dashboard matplotlib :
    - une ligne de chiffres clés (résumé statistique)
    - indicateur 1 : tentatives échouées par pays
    - indicateur 2 : connexions réussies par utilisateur
    - indicateur 3 : tentatives échouées avec utilisateur invalide
    - évolution dans le temps : échecs par jour et par heure
"""

logger = get_logger('serving')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
DASHBOARD_FILE = os.path.join(OUTPUT_DIR, 'dashboard.png')

TOP_COUNTRIES = 15
TOP_INVALID_USERS = 10

# Couleurs
BACKGROUND = '#eef0f3'
CARD = '#ffffff'
HEADER = '#151a22'
TEXT = '#1f2937'
MUTED = '#6b7280'
GRID = '#e5e7eb'
RED = '#b8360f'
GREEN = '#2e9d48'
BLUE = '#1f4e8c'
GREY = '#9ca3af'
ORANGE = '#e8710a'


def number(value):
    """65565 -> '65 565' (séparateur des milliers à la française)."""
    return f'{value:,}'.replace(',', ' ')


def draw_card(fig, x, y, width, height):
    """Fond blanc arrondi derrière un graphique ou un chiffre clé."""
    fig.patches.append(FancyBboxPatch((x, y), width, height, transform=fig.transFigure,
                                      boxstyle='round,pad=0,rounding_size=0.006',
                                      facecolor=CARD, edgecolor='#d9dde3', linewidth=0.8,
                                      zorder=-1))


def style_axes(ax, grid_axis='y'):
    """Style commun : pas de cadre, grille légère."""
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(CARD)


def add_title(fig, ax, title, subtitle):
    """Titre et sous-titre en haut à gauche de la carte du graphique."""
    box = ax.get_position()
    x = ax.card_x + 0.012  # bord gauche de la carte
    fig.text(x, box.y1 + 0.032, title, fontsize=13, fontweight='bold', color=TEXT)
    fig.text(x, box.y1 + 0.016, subtitle, fontsize=9, color=MUTED)


def draw_header(fig, statistics):
    fig.patches.append(Rectangle((0, 0.955), 1, 0.045, transform=fig.transFigure,
                                 facecolor=HEADER, zorder=0))
    fig.patches.append(Rectangle((0, 0.952), 1, 0.003, transform=fig.transFigure,
                                 facecolor=RED, zorder=0))
    fig.text(0.02, 0.975, 'SSH Log Analysis', fontsize=22, fontweight='bold', color='white')
    fig.text(0.02, 0.959, 'Successful and failed SSH logins  ·  auth.log files from data/  ·  '
             'countries located with IPinfo', fontsize=10, color='#c9cdd4')
    fig.text(0.98, 0.977, 'Log analysis pipeline', fontsize=13, fontweight='bold',
             color='white', ha='right')
    fig.text(0.98, 0.961, 'ESISA  ·  Python avancé', fontsize=10, color='#c9cdd4', ha='right')


def draw_kpis(fig, statistics):
    """Ligne de 6 chiffres clés avec une barre de couleur à gauche."""
    failed = statistics['failed_logins']
    invalid = statistics['invalid_user_attempts']
    countries = len(statistics['failures_by_country'])
    users = len(statistics['successes_by_user'])
    top_invalid = statistics['invalid_users'][0][0] if statistics['invalid_users'] else '-'
    share = round(100 * invalid / failed) if failed else 0

    kpis = [
        ('Lines analysed', statistics['total_lines'], 'events read from auth.log', TEXT),
        ('Successful logins', statistics['successful_logins'], f'{users} user(s)', GREEN),
        ('Failed logins', failed, f'from {countries} countries', RED),
        ('Invalid-user failures', invalid, f'{share} % of failed logins', RED),
        ('Distinct invalid users', statistics['distinct_invalid_users'], f'most tried: {top_invalid}', BLUE),
        ('Distinct IP addresses', statistics['distinct_ips'], 'seen in all events', BLUE),
    ]
    width, gap, x, y, height = 0.1507, 0.0112, 0.02, 0.865, 0.07
    for label, value, detail, color in kpis:
        draw_card(fig, x, y, width, height)
        fig.patches.append(Rectangle((x + 0.006, y + 0.012), 0.0025, height - 0.024,
                                     transform=fig.transFigure, facecolor=color, zorder=1))
        fig.text(x + 0.016, y + 0.05, label, fontsize=10, color=MUTED)
        fig.text(x + 0.016, y + 0.022, number(value), fontsize=21, fontweight='bold', color=TEXT)
        fig.text(x + 0.016, y + 0.009, detail, fontsize=8.5, color=MUTED)
        x += width + gap


def country_colors(count):
    """Rouge foncé pour les premiers pays, puis de plus en plus clair."""
    colors = []
    for rank in range(count):
        ratio = rank / max(count - 1, 1)
        colors.append((0.62 + 0.30 * ratio, 0.18 + 0.30 * ratio, 0.06 + 0.10 * ratio))
    return colors


def draw_countries(fig, ax, statistics):
    """Indicateur 1 : échecs par pays, top 15 + les autres regroupés dans 'Others'."""
    items = statistics['failures_by_country']
    top = items[:TOP_COUNTRIES]
    others = items[TOP_COUNTRIES:]
    labels = [country for country, _ in top]
    values = [count for _, count in top]
    colors = country_colors(len(top))
    if others:
        labels.append(f'Others\n({len(others)})')
        values.append(sum(count for _, count in others))
        colors.append(GREY)

    style_axes(ax)
    bars = ax.bar(labels, values, color=colors, width=0.7)
    for rank, bar in enumerate(bars):
        ax.annotate(number(int(bar.get_height())), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9,
                    fontweight='bold' if rank < 3 else 'normal', color=TEXT)
    ax.set_ylabel('Failed attempts', color=MUTED, fontsize=9)
    ax.set_xlabel('Country (ISO code)', color=MUTED, fontsize=9)
    ax.yaxis.set_major_formatter(lambda value, _: number(int(value)))
    ax.margins(y=0.15)

    total = statistics['failed_logins'] or 1
    top3 = round(100 * sum(values[:3]) / total) if top else 0
    subtitle = f'{len(items)} countries  ·  the top 3 send {top3} % of all failures'
    if others:
        subtitle += f'  ·  the {len(others)} smallest are grouped in "Others"'
    add_title(fig, ax, 'Failed logins by country', subtitle)


def draw_horizontal_bars(fig, ax, items, color, title, subtitle, xlabel):
    """Barres horizontales triées (la plus grande en haut) avec la valeur au bout."""
    style_axes(ax, grid_axis='x')
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(True)
    ax.spines['left'].set_color(GRID)
    labels = [label for label, _ in items][::-1]
    values = [value for _, value in items][::-1]
    bars = ax.barh(labels, values, color=color, height=0.6)
    for bar in bars:
        ax.annotate(number(int(bar.get_width())), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords='offset points', va='center', fontsize=9, color=TEXT)
    ax.tick_params(axis='y', labelsize=9.5, colors=TEXT)
    # au moins 6 emplacements : une seule barre ne remplit pas tout le graphique
    rows = max(len(items), 6)
    ax.set_ylim(len(items) - rows - 0.5, len(items) - 0.5)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.margins(x=0.1)
    ax.xaxis.get_major_locator().set_params(integer=True)
    if not items:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes, color=MUTED)
    add_title(fig, ax, title, subtitle)


def draw_timeline(fig, ax, statistics):
    """Évolution des tentatives échouées jour par jour."""
    days = statistics['failures_by_date']
    style_axes(ax)
    if not days:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes, color=MUTED)
        add_title(fig, ax, 'Failed logins over time', 'no dated event')
        return

    dates = [datetime.strptime(day, '%Y-%m-%d') for day, _, _ in days]
    failures = [total for _, total, _ in days]
    invalid = [count for _, _, count in days]
    ax.fill_between(dates, failures, color=RED, alpha=0.12)
    ax.plot(dates, failures, color=RED, linewidth=2, marker='o', markersize=3.5, label='All failed logins')
    ax.plot(dates, invalid, color=BLUE, linewidth=1.8, marker='o', markersize=3, label='Invalid user')

    peak = failures.index(max(failures))
    ax.annotate(f'peak: {number(failures[peak])}', (dates[peak], failures[peak]), xytext=(0, 8),
                textcoords='offset points', ha='center', fontsize=9, fontweight='bold', color=RED)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
    ax.yaxis.set_major_formatter(lambda value, _: number(int(value)))
    ax.set_ylabel('Failed attempts', color=MUTED, fontsize=9)
    ax.set_ylim(bottom=0)
    ax.margins(y=0.18)
    ax.legend(frameon=False, fontsize=9, loc='upper right', ncols=2)
    average = round(sum(failures) / len(failures))
    add_title(fig, ax, 'Failed logins over time',
              f'{days[0][0]} to {days[-1][0]}  ·  {len(days)} days  ·  {number(average)} failures per day on average')


def draw_hours(fig, ax, statistics):
    """Tentatives échouées selon l'heure de la journée."""
    hours = statistics['failures_by_hour']
    style_axes(ax)
    values = [count for _, count in hours]
    top = max(values) if values else 0
    colors = [RED if value == top and top else ORANGE for value in values]
    ax.bar([hour for hour, _ in hours], values, color=colors, width=0.75)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f'{hour}h' for hour in range(0, 24, 2)])
    ax.yaxis.set_major_formatter(lambda value, _: number(int(value)))
    ax.set_xlabel('Hour of the day', color=MUTED, fontsize=9)
    peak = values.index(top) if top else 0
    add_title(fig, ax, 'Failed logins by hour', f'busiest hour: {peak}h ({number(top)} failures)')


def draw_footer(fig, statistics):
    storage = statistics.get('storage', 'CSV / JSON')
    now = datetime.now().strftime('%d/%m/%Y at %H:%M')
    fig.text(0.02, 0.008, f'Sources: auth.log files (data/)  ·  countries: IPinfo  ·  '
             f'storage: {storage}  ·  generated on {now}', fontsize=9, color=MUTED)


def card_axes(fig, x, y, width, height, left_margin=0.035):
    """Dessine une carte et crée le graphique à l'intérieur."""
    draw_card(fig, x, y, width, height)
    ax = fig.add_axes([x + left_margin, y + 0.035, width - left_margin - 0.015, height - 0.09])
    ax.card_x = x
    return ax


def create_figure(statistics: dict):
    """Construit toute la figure du dashboard."""
    fig = plt.figure(figsize=(20, 15), facecolor=BACKGROUND)
    draw_header(fig, statistics)
    draw_kpis(fig, statistics)

    # Indicateur 1 (toute la largeur)
    draw_countries(fig, card_axes(fig, 0.02, 0.59, 0.96, 0.26), statistics)

    # Indicateurs 2 et 3
    by_user = statistics['successes_by_user']
    draw_horizontal_bars(fig, card_axes(fig, 0.02, 0.315, 0.36, 0.26, 0.09), by_user, GREEN,
                         'Successful logins by user',
                         f"{statistics['successful_logins']} successful login(s) for {len(by_user)} user(s)",
                         'Successful logins')

    invalid = statistics['invalid_users']
    draw_horizontal_bars(fig, card_axes(fig, 0.39, 0.315, 0.59, 0.26, 0.08), invalid[:TOP_INVALID_USERS], BLUE,
                         f"Failed logins with invalid user: {number(statistics['invalid_user_attempts'])}",
                         f'Top {TOP_INVALID_USERS} of {number(len(invalid))} usernames that do not exist on the server',
                         'Failed attempts')

    # Évolution dans le temps
    draw_timeline(fig, card_axes(fig, 0.02, 0.035, 0.62, 0.265), statistics)
    draw_hours(fig, card_axes(fig, 0.65, 0.035, 0.33, 0.265), statistics)

    draw_footer(fig, statistics)
    return fig


def build_dashboard(statistics: dict, output_file: str = DASHBOARD_FILE, show: bool = True):
    """Crée la figure, l'enregistre en PNG et l'affiche si `show` est vrai.
    Retourne le chemin de l'image, ou None en cas d'erreur."""
    try:
        fig = create_figure(statistics)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        fig.savefig(output_file, dpi=100, facecolor=BACKGROUND)
        logger.info(f"Dashboard saved in {output_file}")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.error(f"Dashboard generation error: {e}")
        plt.close('all')
        return None

    if show:
        plt.show()
    plt.close(fig)
    return output_file
