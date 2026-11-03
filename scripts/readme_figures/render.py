"""README figures (docs/img/*.png), rendered from the published release package.

Usage:
    python scripts/readme_figures/render.py <unzipped release dir> docs/img <mx_states.geojson>

Extra dependencies (not needed by the pipeline): matplotlib, geopandas, duckdb.
State boundaries: https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json
Fonts: Inter / Inter Display if installed, DejaVu Sans otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
import brand as B  # noqa: E402

REL, OUT, STATES = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
B.setup()
con = duckdb.connect()
P = lambda t: f"'{REL / 'tabular' / (t + '.parquet')}'"  # noqa: E731
q = lambda s: con.execute(s).df()  # noqa: E731

# Canonical quarterly cuts = the snapshots used by the chronological models.
con.execute(f"""
create view canon as select distinct snapshot_id from (
  select snapshot_id from {P('fct_ppi_delta')}
  union select snapshot_id_inicio from {P('fct_ppi_ciclo_vida')}
  union select snapshot_id_fin from {P('fct_ppi_ciclo_vida')})
""")
con.execute(f"create view obs as select o.* from {P('fct_ppi_observacion')} o join canon using (snapshot_id)")

states = gpd.read_file(STATES)

N_PROJECTS = int(q(f"select count(*) n from {P('fct_ppi_ciclo_vida')}").n[0])
N_OBS = int(q(f"select count(*) n from {P('fct_ppi_observacion')}").n[0])
N_VERSIONS = int(q(f"select count(*) n from {P('dim_ppi')}").n[0])


def fmt_int(n):
    return f"{n:,.0f}"


# ---------------------------------------------------------------- map data
pts = q("""
with last as (
  select cve_cartera, latitud, longitud, descripcion_ramo,
         row_number() over (partition by cve_cartera order by snapshot_id desc) rn
  from obs where latitud between 14.3 and 32.8 and longitud between -118.5 and -86.5),
amount as (select cve_cartera, max(monto_total_inversion) monto from obs group by 1)
select l.cve_cartera, l.latitud, l.longitud, l.descripcion_ramo, a.monto
from last l join amount a using (cve_cartera) where rn = 1
""")
pts = pts[pts.monto.fillna(0) > 0].sort_values("monto", ascending=False)
N_MAPPED = len(pts)


def draw_mexico(ax, face, edge, lw=0.5):
    states.plot(ax=ax, color=face, edgecolor=edge, linewidth=lw, zorder=1)
    ax.set_xlim(-118.6, -86.4)
    ax.set_ylim(14.2, 33.0)
    ax.set_aspect(1.08)
    ax.axis("off")


def draw_points(ax, scale=1.0, color=B.AMBER):
    s = np.clip(np.sqrt(pts.monto / 1e6), 0.5, 140) * 0.9 * scale
    ax.scatter(pts.longitud, pts.latitud, s=s * 6, color=color, alpha=0.05, linewidths=0, zorder=2)
    ax.scatter(pts.longitud, pts.latitud, s=s, color=color, alpha=0.55, linewidths=0, zorder=3)
    ax.scatter(pts.longitud, pts.latitud, s=np.clip(s * 0.12, 0.3, 6), color="#FFF3D6", alpha=0.9,
               linewidths=0, zorder=4)


# ---------------------------------------------------------------- 0. hero banner
def hero():
    fig = plt.figure(figsize=(12, 4.6), facecolor=B.NAVY)
    bg = fig.add_axes([0, 0, 1, 1])
    grad = np.linspace(0, 1, 256)[None, :]
    bg.imshow(grad, aspect="auto", cmap=LinearSegmentedColormap.from_list("g", [B.NAVY, "#0E2A4A"]),
              extent=[0, 1, 0, 1])
    bg.axis("off")
    df = B.display_font()
    fig.text(0.045, 0.83, "OPEN DATA  ·  PUBLIC INVESTMENT  ·  MEXICO", color=B.AMBER, fontsize=10.5,
             fontweight="bold", family=df)
    fig.text(0.045, 0.75, "Federal Public Investment Panel", color="white", fontsize=30,
             fontweight="semibold", family=df, va="top")
    fig.text(0.045, 0.585, "Eleven years of quarterly snapshots that the official source overwrites,\n"
             "reconstructed into one longitudinal panel per investment project.",
             color="#B8C4D6", fontsize=12.5, va="top", linespacing=1.5)
    kpis = [(fmt_int(N_PROJECTS), "investment projects"), (fmt_int(N_OBS), "project × quarter records"),
            ("2015–2026", "eleven fiscal years"), ("98.9%", "rows pass the data contract")]
    for i, (val, lab) in enumerate(kpis):
        x = 0.045 + i * 0.148
        fig.text(x, 0.30, val, color="white", fontsize=20, fontweight="semibold", family=df)
        fig.text(x, 0.23, lab, color="#8FA3BF", fontsize=9.5)
    fig.text(0.045, 0.08, "Source: SHCP · Obra Pública Abierta  ·  Python · dbt · DuckDB · Pandera",
             color="#5E7393", fontsize=9.5)
    ax = fig.add_axes([0.615, 0.05, 0.37, 0.90])
    draw_mexico(ax, "#132F52", "#1E4270", 0.4)
    draw_points(ax, 0.55)
    B.save(fig, OUT / "hero.png")


# ---------------------------------------------------------------- 1. map
def mapa():
    fig = plt.figure(figsize=(12, 7.6), facecolor="none")
    fig.patches.append(FancyBboxPatch((0.004, 0.005), 0.992, 0.99, boxstyle="round,pad=0,rounding_size=0.015",
                                      transform=fig.transFigure, facecolor=B.NAVY, edgecolor=B.NAVY_3,
                                      linewidth=1.2, zorder=-10))
    B.heading(fig, "Where federal investment lands",
              f"{fmt_int(N_MAPPED)} geolocated projects. Dot size = total investment amount (nominal MXN).",
              kicker="Geography", color="white", sub_color="#9FB0C8")
    ax = fig.add_axes([0.05, 0.06, 0.90, 1 - 1.75 / 7.6 - 0.07])
    draw_mexico(ax, "#132F52", "#24497A", 0.5)
    draw_points(ax, 1.0)
    # legend of sizes
    lx = -116.5
    for i, (val, lab) in enumerate([(1e8, "MXN 100 M"), (1e9, "MXN 1 B"), (1e10, "MXN 10 B")]):
        s = np.clip(np.sqrt(val / 1e6), 0.5, 140) * 0.9
        y = 17.6 - i * 1.25
        ax.scatter([lx], [y], s=s, color=B.AMBER, alpha=0.6, linewidths=0, zorder=5)
        ax.text(lx + 1.1, y, lab, color="#B8C4D6", fontsize=9.5, va="center", zorder=5)
    B.source(fig, "Coordinates as published by SHCP; projects without valid coordinates are not drawn. "
                  "Amounts in current pesos, not deflated.", color="#6F84A3")
    B.save(fig, OUT / "map.png")


# ---------------------------------------------------------------- 2. coverage
def coverage():
    canon = q("select snapshot_id from canon").snapshot_id
    real = {(int(s[:4]), int(s[5])) for s in canon if s[4] == "Q"}
    corrupt = {(2024, 1)}
    # Cuts where only Seguimiento/Concluido exist (not the full Consolidado universe),
    # as flagged by int_snapshot_canonico.cobertura_parcial_del_universo in the gold build.
    partial = {(2016, 3), (2017, 1), (2017, 2), (2017, 3), (2018, 3), (2019, 1), (2019, 2), (2019, 3),
               (2019, 4), (2020, 1), (2020, 2), (2020, 3), (2020, 4), (2021, 1)}
    years = list(range(2016, 2027))
    fig, ax = B.card((12, 5.6), bottom=0.16, left=0.08, right=0.97)
    B.heading(fig, "29 of 36 quarters recovered for 2016–2024",
              "Each tile is one quarterly snapshot. The source keeps only the latest one online.",
              kicker="Coverage")
    ax.grid(False)
    colors = {"full": B.NAVY_3, "partial": "#6C8EBF", "corrupt": B.CORAL, "gap": "#EEF1F5", "future": "white"}
    for xi, y in enumerate(years):
        for t in range(1, 5):
            if (y, t) in corrupt:
                k = "corrupt"
            elif (y, t) in real:
                k = "partial" if (y, t) in partial else "full"
            elif y == 2026 and t > 1:
                k = "future"
            else:
                k = "gap"
            ax.add_patch(FancyBboxPatch((xi + 0.06, (4 - t) + 0.08), 0.88, 0.84,
                                        boxstyle="round,pad=0,rounding_size=0.08", facecolor=colors[k],
                                        edgecolor="#E3E8EF" if k in ("gap", "future") else "none",
                                        linewidth=1, linestyle="--" if k == "future" else "-"))
    ax.set_xlim(0, len(years))
    ax.set_ylim(0, 4)
    ax.set_xticks(np.arange(len(years)) + 0.5, years)
    ax.set_yticks(np.arange(4) + 0.5, ["Q4", "Q3", "Q2", "Q1"])
    ax.tick_params(length=0, labelsize=10.5)
    for s in ax.spines.values():
        s.set_visible(False)
    items = [("full", "Full universe"), ("partial", "Partial product (Seguimiento / Concluido)"),
             ("corrupt", "Corrupt at source"), ("gap", "No known source")]
    x = 0.08
    for k, lab in items:
        fig.patches.append(FancyBboxPatch((x, 0.055), 0.014, 0.03, boxstyle="round,pad=0,rounding_size=0.004",
                                          transform=fig.transFigure, facecolor=colors[k],
                                          edgecolor="#D5DCE5" if k == "gap" else "none"))
        fig.text(x + 0.02, 0.07, lab, fontsize=10, color=B.TEXT, va="center")
        x += 0.07 + len(lab) * 0.0068
    B.save(fig, OUT / "coverage.png")


# ---------------------------------------------------------------- 3. universe per cut
def universe():
    d = q("select snapshot_id, count(distinct cve_cartera) n from obs group by 1 order by 1")
    d = d[d.snapshot_id.str[4] == "Q"].copy()
    d["y"] = d.snapshot_id.str[:4].astype(int)
    d["t"] = d.snapshot_id.str[5].astype(int)
    d = d.drop_duplicates(["y", "t"]).sort_values(["y", "t"])
    d["x"] = d.y + (d.t - 1) / 4
    # From 2021 Q2 on, every cut is the full Consolidado universe (earlier cuts are partial products).
    d = d[d.x >= 2021.25]
    fig, ax = B.card((12, 5.8), bottom=0.13, left=0.07, right=0.96)
    B.heading(fig, "Every first quarter, 15–29% of the registry drops out",
              "Projects per quarterly snapshot, 2021–2026. The Q1 dip is the yearly re-registration of "
              "multi-year projects, not a load error.", kicker="Seasonality")
    seg = [d[d.x < 2024], d[d.x > 2024.1]]
    for part in seg:
        ax.fill_between(part.x, part.n, color=B.BLUE, alpha=0.08, zorder=1, linewidth=0)
        ax.plot(part.x, part.n, color=B.NAVY_3, lw=2.6, zorder=3, solid_capstyle="round")
    a, b = seg[0].iloc[-1], seg[1].iloc[0]
    ax.plot([a.x, b.x], [a.n, b.n], color=B.SOFT, lw=1.8, ls=(0, (3, 3)), zorder=2)
    ax.axvspan(2024.0, 2024.25 - 0.001, color="#F1F4F8", zorder=0)
    ax.text(2024.125, d.n.max() * 1.10, "2024 Q1\ncorrupt at\nsource", ha="center", va="top", fontsize=9,
            color=B.MUTED, linespacing=1.25)
    ax.scatter(d.x, d.n, s=26, color="white", edgecolor=B.NAVY_3, linewidth=1.8, zorder=4)
    q1 = d[d.t == 1]
    ax.scatter(q1.x, q1.n, s=90, color=B.CORAL, edgecolor="white", linewidth=1.5, zorder=5)
    for _, r in q1.iterrows():
        prev = d[(d.x < r.x)].tail(1)
        if len(prev):
            drop = (r.n / prev.n.iloc[0] - 1) * 100
            ax.annotate(f"{drop:.0f}%", (r.x, r.n), xytext=(0, -22), textcoords="offset points",
                        ha="center", fontsize=10.5, fontweight="bold", color=B.CORAL)
    ax.set_ylim(0, d.n.max() * 1.18)
    ax.set_xticks(range(2022, 2027), [f"Q1 {y}" for y in range(2022, 2027)])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlim(d.x.min() - 0.15, d.x.max() + 0.15)
    B.source(fig, "Canonical snapshot per quarter (full Consolidado universe). Percentages vs. the previous "
                  "quarter.")
    B.save(fig, OUT / "seasonality.png")


# ---------------------------------------------------------------- 4. by sector
SHORT = {
    "Infraestructura, Comunicaciones y Transportes": "Infrastructure & Transport",
    "Petróleos Mexicanos": "Pemex",
    "Medio Ambiente y Recursos Naturales": "Environment & Water",
    "Instituto Mexicano del Seguro Social": "IMSS (social security)",
    "Educación Pública": "Public Education",
    "Instituto de Seguridad y Servicios Sociales de los Trabajadores del Estado": "ISSSTE",
    "Energía": "Energy",
    "Hacienda y Crédito Público": "Finance (SHCP)",
    "Economía": "Economy",
    "Salud": "Health",
    "Comisión Federal de Electricidad": "CFE (electricity)",
    "Defensa Nacional": "Defense",
    "Marina": "Navy",
}


def sectors():
    last = q("select max(snapshot_id) s from obs where substr(snapshot_id,5,1)='Q'").s[0]
    d = q(f"""select descripcion_ramo r, sum(modificado)/1e9 v, count(*) n from obs
              where snapshot_id='{last}' and modificado > 0 group by 1 order by 2 desc""")
    top = d.head(9).copy()
    other = d.iloc[9:]
    top.loc[len(top)] = ["All other sectors", other.v.sum(), other.n.sum()]
    top["label"] = top.r.map(lambda r: SHORT.get(r, r))
    top = top.iloc[::-1]
    total = d.v.sum()
    fig, ax = B.card((12, 6.4), bottom=0.10, left=0.25, right=0.93)
    yr, qt = last[:4], last[5]
    B.heading(fig, "Transport takes 42% of this year's investment budget",
              f"Modified budget by sector, {yr} Q{qt} snapshot · MXN billions (nominal) · "
              f"total MXN {total:,.0f} B across {int(d.n.sum()):,} projects", kicker="Sectors")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    cols = [B.SLATE if lbl == "All other sectors" else B.NAVY_3 for lbl in top.label]
    cols[-1] = B.AMBER
    bars = ax.barh(top.label, top.v, color=cols, height=0.62, zorder=3)
    for b, v in zip(bars, top.v, strict=True):
        ax.text(b.get_width() + total * 0.006, b.get_y() + b.get_height() / 2,
                f"{v:,.1f}  ·  {v / total:.0%}", va="center", fontsize=10.5, color=B.TEXT, fontweight="medium")
    ax.tick_params(axis="y", labelsize=11, labelcolor=B.TEXT)
    ax.set_xlim(0, top.v.max() * 1.22)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    B.save(fig, OUT / "sectors.png")


# ---------------------------------------------------------------- 5. lifecycle outcome
def outcomes():
    d = q(f"select estatus_terminal_inferido k, count(*) n from {P('fct_ppi_ciclo_vida')} group by 1")
    lab = {"terminado_probable": ("Likely completed", B.TEAL),
           "vigente_ultimo_corte_disponible": ("Still active in latest snapshot", B.BLUE),
           "salida_no_explicada": ("Left the registry unexplained", B.CORAL)}
    order = ["terminado_probable", "vigente_ultimo_corte_disponible", "salida_no_explicada"]
    d = d.set_index("k").loc[order]
    tot = d.n.sum()
    fig, ax = B.card((12, 4.8), bottom=0.36, left=0.035, right=0.965)
    B.heading(fig, "62% of projects leave the registry before reaching 95% progress",
              f"Inferred end state of the {tot:,} projects in the panel", kicker="Project lifecycle")
    ax.grid(False)
    left = 0
    for k in order:
        n = d.loc[k, "n"]
        _, c = lab[k]
        ax.barh([0], [n], left=left, color=c, height=1, edgecolor="white", linewidth=3)
        ax.text(left + n / 2, 0, f"{n / tot:.0%}", ha="center", va="center", color="white",
                fontsize=17, fontweight="semibold")
        left += n
    ax.set_xlim(0, tot)
    ax.set_ylim(-0.5, 0.5)
    ax.axis("off")
    x = 0.035
    for k in order:
        name, c = lab[k]
        n = d.loc[k, "n"]
        fig.patches.append(FancyBboxPatch((x, 0.215), 0.012, 0.045, boxstyle="round,pad=0,rounding_size=0.003",
                                          transform=fig.transFigure, facecolor=c))
        fig.text(x + 0.018, 0.255, name, fontsize=10.5, color=B.TEXT, fontweight="medium", va="top")
        fig.text(x + 0.018, 0.205, f"{n:,} projects", fontsize=9.5, color=B.MUTED, va="top")
        x += 0.30
    B.source(fig, "“Unexplained” may be a real cancellation or a project that fell into one of the 7 "
                  "unrecoverable quarters — open data cannot tell them apart.")
    B.save(fig, OUT / "lifecycle.png")


# ---------------------------------------------------------------- 6. cost changes
def cost_change():
    d = q(f"select sobrecosto_pct v from {P('fct_ppi_ciclo_vida')} where sobrecosto_pct is not null")
    bins = [(-1e9, -99.5, "Cut to zero"), (-99.5, -25, "Cut > 25%"), (-25, -5, "Cut 5–25%"),
            (-5, 5, "Within ±5%"), (5, 25, "Up 5–25%"), (25, 100, "Up 25–100%"), (100, 1e9, "More than doubled")]
    rows = [(lab, int(((d.v > lo) & (d.v <= hi)).sum())) for lo, hi, lab in bins]
    rows[0] = (rows[0][0], int((d.v <= -99.5).sum()))
    tot = len(d)
    cols = ["#9F2D2D", B.CORAL, "#F4A3A3", B.SLATE, "#9CC3F5", B.BLUE, B.NAVY_3]
    fig, ax = B.card((12, 5.8), bottom=0.14, left=0.07, right=0.97)
    B.heading(fig, "42% of projects close within ±5% of their initial amount",
              f"{tot:,} projects with both amounts observed · nominal pesos (overstates real overruns on "
              "long projects)", kicker="Cost changes")
    x = np.arange(len(rows))
    bars = ax.bar(x, [r[1] for r in rows], color=cols, width=0.68, zorder=3)
    for b, (_, n) in zip(bars, rows, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + tot * 0.006, f"{n:,}  ·  {n / tot:.0%}",
                ha="center", va="bottom", fontsize=10.5, color=B.TEXT, fontweight="medium")
    ax.set_xticks(x, [r[0] for r in rows])
    ax.tick_params(axis="x", labelsize=10.5, labelcolor=B.TEXT)
    ax.set_ylim(0, max(r[1] for r in rows) * 1.12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    B.source(fig, "“Cut to zero”: final reported amount is 0 — typically a cancelled or deregistered project.")
    B.save(fig, OUT / "cost_change.png")


for f in (hero, mapa, coverage, universe, sectors, outcomes, cost_change):
    f()
    print("ok", f.__name__)
print({"projects": N_PROJECTS, "obs": N_OBS, "versions": N_VERSIONS, "mapped": N_MAPPED})
