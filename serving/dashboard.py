import os
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

from log_config import get_logger

"""
Dashboard matplotlib (thème sombre) :
    - chiffres clés (résumé statistique)
    - indicateur 1 : tentatives échouées par pays
    - répartition des tentatives (anneau)
    - indicateur 2 : connexions réussies par utilisateur
    - indicateur 3 : tentatives échouées avec utilisateur invalide
    - temps : échecs par jour et carte jour de la semaine x heure
"""

logger = get_logger('serving')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
DASHBOARD_FILE = os.path.join(OUTPUT_DIR, 'dashboard.png')

TOP_COUNTRIES = 15
TOP_INVALID_USERS = 10
WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# Palette (thème sombre)
BACKGROUND = '#0b1120'
CARD = '#151e32'
BORDER = '#25304a'
TEXT = '#f1f5f9'
MUTED = '#8b9bb4'
GRID = '#24304a'
ROSE = '#fb7185'      # échecs
EMERALD = '#34d399'   # succès
VIOLET = '#a78bfa'    # utilisateurs invalides
SKY = '#38bdf8'       # adresses IP
AMBER = '#fbbf24'     # temps
SLATE = '#64748b'     # "Others"


def number(value):
    """65565 -> '65 565' (séparateur des milliers à la française)."""
    return f'{value:,}'.replace(',', ' ')


def draw_card(fig, x, y, width, height):
    """Fond arrondi derrière un graphique ou un chiffre clé."""
    fig.patches.append(FancyBboxPatch((x, y), width, height, transform=fig.transFigure,
                                      boxstyle='round,pad=0,rounding_size=0.008',
                                      facecolor=CARD, edgecolor=BORDER, linewidth=1, zorder=-1))


def card_axes(fig, x, y, width, height, title, subtitle, left=0.035, bottom=0.04, top=0.075):
    """Dessine une carte avec son titre et crée le graphique à l'intérieur."""
    draw_card(fig, x, y, width, height)
    fig.text(x + 0.014, y + height - 0.026, title, fontsize=14, fontweight='bold', color=TEXT)
    fig.text(x + 0.014, y + height - 0.043, subtitle, fontsize=9.5, color=MUTED)
    return fig.add_axes([x + left, y + bottom, width - left - 0.018, height - bottom - top])


def style_axes(ax, grid_axis='y'):
    """Style commun : pas de cadre, grille discrète."""
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9.5, length=0)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def no_data(ax):
    ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes,
            color=MUTED, fontsize=12)


# ---------- en-tête et chiffres clés ----------

def draw_header(fig):
    fig.text(0.02, 0.968, 'SSH Log Analysis', fontsize=26, fontweight='bold', color=TEXT)
    fig.text(0.02, 0.952, 'Who is trying to log in to the server, from where, and when',
             fontsize=11.5, color=MUTED)
    fig.text(0.98, 0.970, 'LOG ANALYSIS PIPELINE', fontsize=11, fontweight='bold',
             color=ROSE, ha='right')
    fig.text(0.98, 0.954, 'ESISA  ·  Python avancé', fontsize=10.5, color=MUTED, ha='right')


def draw_kpis(fig, statistics):
    """6 chiffres clés : une couleur par famille d'information."""
    failed = statistics['failed_logins']
    invalid = statistics['invalid_user_attempts']
    countries = len(statistics['failures_by_country'])
    users = len(statistics['successes_by_user'])
    top_invalid = statistics['invalid_users'][0][0] if statistics['invalid_users'] else '-'
    share = round(100 * invalid / failed) if failed else 0

    kpis = [
        ('LINES ANALYSED', statistics['total_lines'], 'from the auth.log files', TEXT),
        ('SUCCESSFUL LOGINS', statistics['successful_logins'], f'{users} user(s)', EMERALD),
        ('FAILED LOGINS', failed, f'from {countries} countries', ROSE),
        ('INVALID-USER FAILURES', invalid, f'{share} % of all failures', VIOLET),
        ('DISTINCT INVALID USERS', statistics['distinct_invalid_users'], f'most tried: "{top_invalid}"', VIOLET),
        ('DISTINCT IP ADDRESSES', statistics['distinct_ips'], 'seen in all events', SKY),
    ]
    gap = 0.010
    width = (0.96 - 5 * gap) / 6
    x, y, height = 0.02, 0.85, 0.083
    for label, value, detail, color in kpis:
        draw_card(fig, x, y, width, height)
        fig.patches.append(FancyBboxPatch((x, y + height - 0.005), width, 0.005,
                                          transform=fig.transFigure, facecolor=color,
                                          boxstyle='round,pad=0,rounding_size=0.002', zorder=0))
        fig.text(x + 0.013, y + height - 0.025, label, fontsize=9, fontweight='bold', color=MUTED)
        fig.text(x + 0.013, y + 0.026, number(value), fontsize=26, fontweight='bold', color=color)
        fig.text(x + 0.013, y + 0.011, detail, fontsize=9, color=MUTED)
        x += width + gap


# ---------- indicateur 1 : pays ----------

def draw_countries(ax, statistics):
    """Échecs par pays (ordre décroissant), les petits pays regroupés dans 'Others'."""
    style_axes(ax)
    items = statistics['failures_by_country']
    if not items:
        no_data(ax)
        return
    top = items[:TOP_COUNTRIES]
    others = items[TOP_COUNTRIES:]
    labels = [country for country, _ in top]
    values = [count for _, count in top]
    colors = [ROSE] * min(3, len(top)) + ['#be5b6e'] * max(0, len(top) - 3)
    if others:
        labels.append(f'Others ({len(others)})')
        values.append(sum(count for _, count in others))
        colors.append(SLATE)

    bars = ax.bar(labels, values, color=colors, width=0.68)
    total = statistics['failed_logins'] or 1
    for rank, bar in enumerate(bars):
        value = int(bar.get_height())
        text = number(value)
        if rank < 3:
            text += f'\n{round(100 * value / total)} %'
        ax.annotate(text, (bar.get_x() + bar.get_width() / 2, value), xytext=(0, 4),
                    textcoords='offset points', ha='center', va='bottom', fontsize=9.5,
                    color=TEXT, fontweight='bold' if rank < 3 else 'normal')
    ax.tick_params(axis='x', colors=TEXT, labelsize=10)
    ax.yaxis.set_major_formatter(lambda value, _: number(int(value)))
    ax.set_ylabel('Failed attempts', color=MUTED, fontsize=9.5)
    ax.margins(x=0.01, y=0.22)


# ---------- répartition des tentatives ----------

def draw_breakdown(ax, statistics):
    """Anneau : succès / échecs utilisateur existant / échecs utilisateur invalide."""
    invalid = statistics['invalid_user_attempts']
    existing = statistics['failed_logins'] - invalid
    success = statistics['successful_logins']
    total = invalid + existing + success
    if not total:
        no_data(ax)
        return
    ax.pie([existing, invalid, success], colors=[ROSE, VIOLET, EMERALD], startangle=90,
           counterclock=False, wedgeprops={'width': 0.32, 'edgecolor': CARD, 'linewidth': 3})
    ax.text(0, 0.1, number(total), ha='center', va='center', fontsize=22, fontweight='bold', color=TEXT)
    ax.text(0, -0.17, 'login attempts', ha='center', va='center', fontsize=10, color=MUTED)
    ax.set_aspect('equal')

    legend = [('Wrong password', existing, ROSE),
              ('Invalid user', invalid, VIOLET),
              ('Successful', success, EMERALD)]
    for row, (label, value, color) in enumerate(legend):
        y = -1.38 - row * 0.27
        ax.scatter([-1.25], [y], s=90, color=color, clip_on=False)
        ax.text(-1.1, y, label, va='center', fontsize=10, color=TEXT)
        percent = 100 * value / total
        percent_text = f'{percent:.1f} %' if percent >= 0.1 else '< 0.1 %'
        ax.text(1.45, y, f'{number(value)}  ·  {percent_text}', va='center', ha='right',
                fontsize=10, color=MUTED)
    ax.set_xlim(-1.3, 1.5)
    ax.set_ylim(-2.05, 1.1)
    ax.axis('off')


# ---------- indicateurs 2 et 3 : barres horizontales ----------

def draw_success_details(ax, statistics):
    """Sous le graphique : le détail des connexions réussies (5 au maximum)."""
    details = statistics.get('successful_logins_detail', [])[:5]
    lines = [f'{user}  ·  from {ip}  ·  {day} {time}' for user, ip, day, time in details]
    if lines:
        ax.text(0, -0.2, '\n'.join(lines), transform=ax.transAxes, va='top', fontsize=10,
                color=MUTED, linespacing=1.6)


def draw_ranking(ax, items, color):
    """Classement horizontal (le plus grand en haut) avec la valeur au bout de la barre."""
    style_axes(ax, grid_axis='x')
    if not items:
        no_data(ax)
        return
    labels = [label for label, _ in items][::-1]
    values = [value for _, value in items][::-1]
    top = max(values)
    bars = ax.barh(labels, values, color=color, height=0.62)
    for bar, value in zip(bars, values):
        # La barre la plus grande est pleine, les autres un peu transparentes
        bar.set_alpha(1.0 if value == top else 0.75)
        ax.annotate(number(int(bar.get_width())), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0), textcoords='offset points', va='center', fontsize=10,
                    fontweight='bold', color=TEXT)
    ax.tick_params(axis='y', labelsize=10.5, colors=TEXT)
    ax.xaxis.get_major_locator().set_params(integer=True)
    rows = max(len(items), 4)  # une seule barre ne remplit pas tout le graphique
    ax.set_ylim(len(items) - rows - 0.5, len(items) - 0.5)
    ax.margins(x=0.12)


# ---------- temps ----------

def draw_timeline(ax, statistics):
    """Tentatives échouées jour par jour (toutes et utilisateur invalide)."""
    style_axes(ax)
    days = statistics['failures_by_date']
    if not days:
        no_data(ax)
        return
    dates = [datetime.strptime(day, '%Y-%m-%d') for day, _, _ in days]
    failures = [total for _, total, _ in days]
    invalid = [count for _, _, count in days]

    ax.fill_between(dates, failures, color=ROSE, alpha=0.18)
    ax.plot(dates, failures, color=ROSE, linewidth=2.4, label='All failed logins')
    ax.fill_between(dates, invalid, color=VIOLET, alpha=0.25)
    ax.plot(dates, invalid, color=VIOLET, linewidth=2, label='Invalid user')

    average = sum(failures) / len(failures)
    ax.axhline(average, color=MUTED, linewidth=1, linestyle='--')
    ax.text(dates[0], average, f' average {number(round(average))}/day', color=MUTED,
            fontsize=9, va='bottom')

    peak = failures.index(max(failures))
    ax.scatter([dates[peak]], [failures[peak]], s=60, color=ROSE, edgecolor=TEXT, zorder=3)
    ax.annotate(f'peak {number(failures[peak])}\n{dates[peak]:%d %b}', (dates[peak], failures[peak]),
                xytext=(0, 10), textcoords='offset points', ha='center', fontsize=9.5,
                fontweight='bold', color=TEXT)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.yaxis.set_major_formatter(lambda value, _: number(int(value)))
    ax.set_ylim(0, max(failures) * 1.3)
    ax.set_xlim(dates[0], dates[-1])
    legend = ax.legend(frameon=False, fontsize=9.5, loc='upper right', ncols=2)
    for text in legend.get_texts():
        text.set_color(TEXT)


def draw_heatmap(fig, ax, statistics):
    """Carte de chaleur : jour de la semaine x heure de la journée."""
    grid = statistics['failures_by_weekday_hour']
    colormap = LinearSegmentedColormap.from_list('heat', [CARD, '#3b2a4f', '#9d3b5a', ROSE, AMBER])
    image = ax.imshow(grid, cmap=colormap, aspect='auto', interpolation='nearest')
    ax.set_yticks(range(7))
    ax.set_yticklabels(WEEKDAYS)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f'{hour}h' for hour in range(0, 24, 3)])
    ax.tick_params(colors=MUTED, labelsize=9.5, length=0)
    ax.tick_params(axis='y', colors=TEXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    # fines lignes pour séparer les cases
    ax.set_xticks([x - 0.5 for x in range(1, 24)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, 7)], minor=True)
    ax.grid(which='minor', color=CARD, linewidth=1.5)
    ax.tick_params(which='minor', length=0)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(colors=MUTED, labelsize=8.5, length=0)


def busiest_slot(statistics):
    """(nombre, jour, heure) de la case la plus chargée de la carte de chaleur."""
    grid = statistics['failures_by_weekday_hour']
    best = (0, 0, 0)
    for day in range(7):
        for hour in range(24):
            if grid[day][hour] > best[0]:
                best = (grid[day][hour], day, hour)
    return best


# ---------- assemblage ----------

def draw_footer(fig, statistics):
    storage = statistics.get('storage', 'CSV / JSON')
    now = datetime.now().strftime('%d/%m/%Y at %H:%M')
    fig.text(0.02, 0.008, f'Data: auth.log files (data/)   ·   countries: IPinfo   ·   '
             f'storage: {storage}   ·   generated on {now}', fontsize=9.5, color=MUTED)


def create_figure(statistics: dict):
    """Construit toute la figure du dashboard."""
    fig = plt.figure(figsize=(20, 16), facecolor=BACKGROUND)
    draw_header(fig)
    draw_kpis(fig, statistics)

    # Ligne 2 : indicateur 1 + répartition
    countries = statistics['failures_by_country']
    total = statistics['failed_logins'] or 1
    top3 = round(100 * sum(count for _, count in countries[:3]) / total)
    subtitle = f'{len(countries)} countries, sorted from most to least  ·  the top 3 send {top3} % of all failures'
    draw_countries(card_axes(fig, 0.02, 0.575, 0.665, 0.26, 'Failed logins by country', subtitle,
                             left=0.05, bottom=0.03, top=0.065), statistics)
    draw_breakdown(card_axes(fig, 0.695, 0.575, 0.285, 0.26, 'Where do attempts end up?',
                             'every login attempt, by result', left=0.02, bottom=0.01, top=0.055),
                   statistics)

    # Ligne 3 : indicateurs 2 et 3
    by_user = statistics['successes_by_user']
    success_ax = card_axes(fig, 0.02, 0.305, 0.33, 0.255, 'Successful logins by user',
                           f"{statistics['successful_logins']} successful login(s) for {len(by_user)} user(s)",
                           left=0.085, bottom=0.085)
    draw_ranking(success_ax, by_user, EMERALD)
    draw_success_details(success_ax, statistics)
    invalid = statistics['invalid_users']
    draw_ranking(card_axes(fig, 0.36, 0.305, 0.62, 0.255,
                           f"Failed logins with an invalid user: {number(statistics['invalid_user_attempts'])}",
                           f'top {TOP_INVALID_USERS} of {number(len(invalid))} usernames that do not exist on the server',
                           left=0.075), invalid[:TOP_INVALID_USERS], VIOLET)

    # Ligne 4 : le temps
    days = statistics['failures_by_date']
    period = f'{days[0][0]} to {days[-1][0]}  ·  {len(days)} days' if days else 'no dated event'
    draw_timeline(card_axes(fig, 0.02, 0.03, 0.555, 0.26, 'Failed logins over time', period,
                            left=0.045), statistics)
    count, day, hour = busiest_slot(statistics)
    draw_heatmap(fig, card_axes(fig, 0.585, 0.03, 0.395, 0.26, 'When do attacks happen?',
                                f'failed logins by weekday and hour  ·  busiest: {WEEKDAYS[day]} {hour}h '
                                f'({number(count)})', left=0.04), statistics)

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
