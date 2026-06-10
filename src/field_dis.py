from __future__ import annotations

import os
import io
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/grapemaster_mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/grapemaster_cache")

import geopandas as gpd
from matplotlib.lines import Line2D
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from PIL import Image
from pyproj import CRS, Transformer


ACCOUNT_INVENTORY_MD = ROOT / "note" / "user_account_inventory_from_dataset_csv.md"
FIELD_CSV = ROOT / "data" / "dataset_csv" / "public_field_field.csv"
CROP_SEASON_CSV = ROOT / "data" / "dataset_csv" / "public_crop_cropseason.csv"
DEFAULT_CACHE_CSV = ROOT / "data" / "grapemaster_test_site_locations.csv"
DEFAULT_OUTPUT = ROOT / "fig" / "grapemaster_test_site_distribution_map.png"
CHINA_SHP = ROOT / "data" / "shp" / "国家矢量.shp"
PROVINCE_SHP = ROOT / "data" / "shp" / "procince.shp"

WEB_MERCATOR_CRS = "EPSG:3857"
CHINA_OVERVIEW_LONLAT_BOUNDS = (73.0, 135.5, 17.0, 54.5)
SOUTH_CHINA_SEA_LONLAT_BOUNDS = (105.0, 125.0, 3.0, 25.0)
SOUTH_CHINA_SEA_INSET_POS = (0.832, 0.0, 0.17, 0.27)

PANEL_FACE_COLOR = "#f2f6f5"
LAND_FACE_COLOR = "#f8fbf8"
PROVINCE_EDGE_COLOR = "#4b5f6b"
POINT_COLOR = "#087f8c"
EXPERIMENT_SITE_COLOR = "#d7301f"
POINT_EDGE_COLOR = "white"
TIANDITU_ZOOM = 4
EXPERIMENTAL_SITES = (
    {"site": "Experimental site 1", "centroid_lat": 25.45, "centroid_lon": 110.80},
    {"site": "Experimental site 2", "centroid_lat": 23.83, "centroid_lon": 108.11},
    {"site": "Experimental site 3", "centroid_lat": 22.61, "centroid_lon": 108.23},
)


class Tile(NamedTuple):
    x: int
    y: int
    z: int


def get_tianditu_key() -> str:
    load_dotenv()
    key = os.getenv("tianditu_api_key")
    if not key:
        raise EnvironmentError("Missing tianditu_api_key in .env")
    return key


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat = min(max(lat, -85.05112878), 85.05112878)
    n = 2**zoom
    x = int(np.floor((lon + 180.0) / 360.0 * n))
    lat_rad = np.radians(lat)
    y = int(np.floor((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n))
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def web_mercator_tiles(west: float, south: float, east: float, north: float, zoom: int) -> list[Tile]:
    min_x, max_y = lonlat_to_tile(west, south, zoom)
    max_x, min_y = lonlat_to_tile(east, north, zoom)
    return [Tile(x, y, zoom) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)]


def tile_bounds(tile_x: int, tile_y: int, zoom: int) -> tuple[float, float, float, float]:
    n = 2**zoom
    west = tile_x / n * 360.0 - 180.0
    east = (tile_x + 1) / n * 360.0 - 180.0
    north = np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * tile_y / n))))
    south = np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * (tile_y + 1) / n))))
    return west, south, east, north


def load_v1_accounts() -> set[str]:
    if not ACCOUNT_INVENTORY_MD.exists():
        raise FileNotFoundError(f"Account inventory not found: {ACCOUNT_INVENTORY_MD}")

    lines = ACCOUNT_INVENTORY_MD.read_text(encoding="utf-8").splitlines()
    in_section = False
    accounts = set()
    for line in lines:
        if line.startswith("## v1 账户列表"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|") or line.startswith("| ---"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "用户ID":
            continue
        if len(cells) < 2:
            continue
        account = cells[1]
        if account:
            accounts.add(account)

    if not accounts:
        raise ValueError("No accounts found in the v1 account inventory section.")
    return accounts


def get_fields_data() -> pd.DataFrame:
    v1_accounts = load_v1_accounts()
    fields = pd.read_csv(FIELD_CSV, encoding="utf-8-sig")
    crop_seasons = pd.read_csv(CROP_SEASON_CSV, encoding="utf-8-sig")

    required_field_cols = {"uuid", "name", "centroid_lon", "centroid_lat", "user_id_id", "region"}
    missing_field_cols = required_field_cols.difference(fields.columns)
    if missing_field_cols:
        raise ValueError(f"Missing required field columns: {', '.join(sorted(missing_field_cols))}")
    if "field_uuid_id" not in crop_seasons.columns:
        raise ValueError("Missing required crop-season column: field_uuid_id")

    fields["uuid"] = fields["uuid"].astype(str)
    fields["user_id_id"] = fields["user_id_id"].astype(str)
    crop_seasons["field_uuid_id"] = crop_seasons["field_uuid_id"].astype(str)
    crop_season_counts = crop_seasons.groupby("field_uuid_id").size().rename("crop_season_count")

    real_df = fields[
        fields["user_id_id"].isin(v1_accounts) & fields["uuid"].isin(crop_season_counts.index)
    ].copy()
    real_df = real_df.join(crop_season_counts, on="uuid")
    real_df = real_df.dropna(subset=["centroid_lon", "centroid_lat", "name"]).reset_index(drop=True)
    real_df["centroid_lon"] = pd.to_numeric(real_df["centroid_lon"], errors="coerce")
    real_df["centroid_lat"] = pd.to_numeric(real_df["centroid_lat"], errors="coerce")
    real_df = real_df.dropna(subset=["centroid_lon", "centroid_lat"])
    real_df = real_df[
        real_df["centroid_lon"].between(73, 136) & real_df["centroid_lat"].between(3, 54)
    ].copy()

    DEFAULT_CACHE_CSV.parent.mkdir(parents=True, exist_ok=True)
    real_df.to_csv(DEFAULT_CACHE_CSV, index=False, encoding="utf-8-sig")

    return real_df


def get_experimental_sites_data() -> pd.DataFrame:
    sites = pd.DataFrame(EXPERIMENTAL_SITES)
    sites["centroid_lon"] = pd.to_numeric(sites["centroid_lon"], errors="coerce")
    sites["centroid_lat"] = pd.to_numeric(sites["centroid_lat"], errors="coerce")
    return sites.dropna(subset=["centroid_lon", "centroid_lat"])


def infer_or_set_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is not None:
        return gdf

    minx, miny, maxx, maxy = gdf.total_bounds
    looks_like_lonlat = -180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90
    if looks_like_lonlat:
        return gdf.set_crs("EPSG:4326")

    return gdf.set_crs(
        CRS.from_proj4(
            "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 "
            "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        )
    )


def load_boundary(shp_path: Path) -> gpd.GeoDataFrame:
    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shp_path}")

    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise ValueError(f"Shapefile is empty: {shp_path}")
    return infer_or_set_crs(gdf).to_crs(WEB_MERCATOR_CRS)


def make_points_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["centroid_lon"], df["centroid_lat"]),
        crs="EPSG:4326",
    )
    return gdf.to_crs(WEB_MERCATOR_CRS)


def lonlat_bounds_to_3857(bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, east, south, north = bounds
    transformer = Transformer.from_crs("EPSG:4326", WEB_MERCATOR_CRS, always_xy=True)
    minx, miny = transformer.transform(west, south)
    maxx, maxy = transformer.transform(east, north)
    return minx, maxx, miny, maxy


def tianditu_url(layer: str, key: str) -> str:
    return (
        f"https://t0.tianditu.gov.cn/{layer}_w/wmts?"
        "SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
        f"&LAYER={layer}&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles"
        "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
        f"&tk={key}"
    )


def make_clip_patch(ax: plt.Axes, gdf: gpd.GeoDataFrame) -> patches.PathPatch:
    geometry = gdf.geometry.union_all() if hasattr(gdf.geometry, "union_all") else gdf.unary_union
    geometries = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
    vertices = []
    codes = []

    for geom in geometries:
        if geom.geom_type != "Polygon":
            continue
        for ring in [geom.exterior, *geom.interiors]:
            coords = list(ring.coords)
            if len(coords) < 3:
                continue
            vertices.extend(coords)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY])

    return patches.PathPatch(MplPath(vertices, codes), transform=ax.transData)


def add_tianditu_basemap(
    ax: plt.Axes,
    bounds_3857: tuple[float, float, float, float],
    clip_gdf: gpd.GeoDataFrame,
) -> bool:
    minx, maxx, miny, maxy = bounds_3857
    to_lonlat = Transformer.from_crs(WEB_MERCATOR_CRS, "EPSG:4326", always_xy=True)
    to_mercator = Transformer.from_crs("EPSG:4326", WEB_MERCATOR_CRS, always_xy=True)
    west, south = to_lonlat.transform(minx, miny)
    east, north = to_lonlat.transform(maxx, maxy)
    tiles = web_mercator_tiles(west, south, east, north, TIANDITU_ZOOM)
    xs = sorted({tile.x for tile in tiles})
    ys = sorted({tile.y for tile in tiles})
    try:
        key = get_tianditu_key()
    except EnvironmentError as exc:
        print(f"Skipping Tianditu basemap: {exc}")
        return False
    mosaics = []

    try:
        with requests.Session() as session:
            for layer in ("ter",):
                mosaic = Image.new("RGBA", (256 * len(xs), 256 * len(ys)))
                url = tianditu_url(layer, key)
                for tile in tiles:
                    response = session.get(url.format(x=tile.x, y=tile.y, z=tile.z), timeout=20)
                    response.raise_for_status()
                    image = Image.open(io.BytesIO(response.content)).convert("RGBA")
                    mosaic.paste(image, (xs.index(tile.x) * 256, ys.index(tile.y) * 256))
                mosaics.append(mosaic)
    except requests.RequestException as exc:
        print(f"Skipping Tianditu basemap: {exc}")
        return False

    west_all, south_all, _, _ = tile_bounds(xs[0], ys[-1], TIANDITU_ZOOM)
    _, _, east_all, north_all = tile_bounds(xs[-1], ys[0], TIANDITU_ZOOM)
    left, bottom = to_mercator.transform(west_all, south_all)
    right, top = to_mercator.transform(east_all, north_all)
    clip_patch = make_clip_patch(ax, clip_gdf)
    for zorder, mosaic in zip((1, 1.2), mosaics):
        basemap = ax.imshow(mosaic, extent=[left, right, bottom, top], interpolation="bilinear", zorder=zorder)
        basemap.set_clip_path(clip_patch)

    mask = patches.Rectangle(
        (minx, miny),
        maxx - minx,
        maxy - miny,
        facecolor="white",
        edgecolor="none",
        alpha=0.32,
        zorder=1.5,
    )
    mask.set_clip_path(clip_patch)
    ax.add_patch(mask)
    return True


def format_lon_label(value: float) -> str:
    return f"{value:.0f} °E"


def format_lat_label(value: float) -> str:
    return f"{value:.0f} °N"


def add_overview_ticks(ax: plt.Axes, bounds_3857: tuple[float, float, float, float]) -> None:
    minx, maxx, miny, maxy = bounds_3857
    to_lonlat = Transformer.from_crs(WEB_MERCATOR_CRS, "EPSG:4326", always_xy=True)
    to_mercator = Transformer.from_crs("EPSG:4326", WEB_MERCATOR_CRS, always_xy=True)
    west, south = to_lonlat.transform(minx, miny)
    east, north = to_lonlat.transform(maxx, maxy)

    lon_ticks = np.arange(np.ceil(west / 10) * 10, np.floor(east / 10) * 10 + 0.5, 10)
    lat_ticks = np.arange(np.ceil(south / 10) * 10, np.floor(north / 10) * 10 + 0.5, 10)
    ax.set_xticks([to_mercator.transform(lon, south)[0] for lon in lon_ticks])
    ax.set_yticks([to_mercator.transform(west, lat)[1] for lat in lat_ticks])
    ax.set_xticklabels([format_lon_label(lon) for lon in lon_ticks], fontsize=15)
    ax.set_yticklabels([format_lat_label(lat) for lat in lat_ticks], fontsize=15)
    ax.tick_params(
        axis="both",
        which="major",
        top=True,
        bottom=True,
        left=True,
        right=True,
        labeltop=True,
        labelbottom=True,
        labelleft=True,
        labelright=True,
        direction="out",
        length=7,
        width=1.2,
        colors="black",
        pad=5,
    )


def choose_scale_length(width_m: float) -> int:
    candidates = [50000, 100000, 200000, 500000, 1000000, 1500000, 2000000]
    target = width_m * 0.16
    valid = [value for value in candidates if value <= target]
    return valid[-1] if valid else candidates[0]


def add_scale_bar(ax: plt.Axes, bounds_3857: tuple[float, float, float, float]) -> None:
    minx, maxx, miny, maxy = bounds_3857
    width_m = maxx - minx
    height_m = maxy - miny
    scale_length = choose_scale_length(width_m)
    half_length = scale_length / 2
    x0 = minx + width_m * 0.06
    y0 = miny + height_m * 0.075
    bar_height = height_m * 0.012

    ax.add_patch(plt.Rectangle((x0, y0), half_length, bar_height, facecolor="black", edgecolor="black", zorder=8))
    ax.add_patch(
        plt.Rectangle((x0 + half_length, y0), half_length, bar_height, facecolor="white", edgecolor="black", zorder=8)
    )
    for xpos in (x0, x0 + half_length, x0 + scale_length):
        ax.plot([xpos, xpos], [y0, y0 + bar_height], color="black", linewidth=1.2, zorder=9)

    labels = ["0", f"{half_length / 1000:g}", f"{scale_length / 1000:g} km"]
    for xpos, label in zip((x0, x0 + half_length, x0 + scale_length), labels):
        ax.text(xpos, y0 - bar_height * 1.25, label, ha="center", va="top", fontsize=15, color="black", zorder=9)


def add_north_arrow(ax: plt.Axes, bounds_3857: tuple[float, float, float, float]) -> None:
    minx, maxx, miny, maxy = bounds_3857
    width = maxx - minx
    height = maxy - miny
    x = maxx - width * 0.055
    y = maxy - height * 0.18
    h = height * 0.10
    w = width * 0.016
    tip = (x, y + h)
    left = (x - w, y)
    right = (x + w, y)
    inner = (x, y + h * 0.43)

    ax.add_patch(patches.Polygon([left, inner, tip], closed=True, facecolor="black", edgecolor="black", linewidth=1.0, zorder=8))
    ax.add_patch(patches.Polygon([inner, right, tip], closed=True, facecolor="white", edgecolor="black", linewidth=1.0, zorder=9))
    ax.text(x, y + h * 1.08, "N", ha="center", va="bottom", fontsize=16, fontweight="bold", color="black", zorder=10)


def add_south_china_sea_inset(ax: plt.Axes, china: gpd.GeoDataFrame) -> None:
    inset = ax.inset_axes(SOUTH_CHINA_SEA_INSET_POS, transform=ax.transAxes)
    minx, maxx, miny, maxy = lonlat_bounds_to_3857(SOUTH_CHINA_SEA_LONLAT_BOUNDS)
    inset.set_xlim(minx, maxx)
    inset.set_ylim(miny, maxy)
    inset.set_facecolor(PANEL_FACE_COLOR)
    china.plot(ax=inset, facecolor=LAND_FACE_COLOR, edgecolor="black", linewidth=0.55, zorder=3)
    china.boundary.plot(ax=inset, color="black", linewidth=0.45, zorder=4)
    inset.set_xticks([])
    inset.set_yticks([])
    inset.set_aspect("equal")
    for spine in inset.spines.values():
        spine.set_linewidth(0.9)
        spine.set_color("black")


def plot_point_layer(ax: plt.Axes, points: gpd.GeoDataFrame, color: str, zorder: int) -> None:
    points.plot(ax=ax, markersize=82, color="black", edgecolor="none", alpha=0.82, zorder=zorder)
    points.plot(
        ax=ax,
        markersize=48,
        color=color,
        edgecolor=POINT_EDGE_COLOR,
        linewidth=1.05,
        alpha=0.96,
        zorder=zorder + 1,
    )


def add_site_legend(ax: plt.Axes) -> None:
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=POINT_COLOR,
            markeredgecolor=POINT_EDGE_COLOR,
            markeredgewidth=1.05,
            markersize=8,
            label="Test-account fields",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=EXPERIMENT_SITE_COLOR,
            markeredgecolor=POINT_EDGE_COLOR,
            markeredgewidth=1.05,
            markersize=8,
            label="Experimental data sites",
        ),
    ]
    legend = ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.035, 0.965),
        frameon=True,
        framealpha=0.92,
        facecolor="white",
        edgecolor="#6c757d",
        fontsize=10.5,
    )
    legend.get_frame().set_linewidth(0.8)


def plot_distribution(account_points: gpd.GeoDataFrame, experimental_points: gpd.GeoDataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "axes.unicode_minus": False,
            "savefig.bbox": "tight",
        }
    )

    china = load_boundary(CHINA_SHP)
    provinces = load_boundary(PROVINCE_SHP) if PROVINCE_SHP.exists() else None
    bounds_3857 = lonlat_bounds_to_3857(CHINA_OVERVIEW_LONLAT_BOUNDS)

    fig, ax = plt.subplots(figsize=(10.2, 7.2), dpi=300)
    ax.set_xlim(bounds_3857[0], bounds_3857[1])
    ax.set_ylim(bounds_3857[2], bounds_3857[3])
    ax.set_facecolor(PANEL_FACE_COLOR)

    basemap_added = add_tianditu_basemap(ax, bounds_3857, china)
    china.plot(
        ax=ax,
        facecolor="none" if basemap_added else LAND_FACE_COLOR,
        edgecolor="black",
        linewidth=0.9,
        zorder=2,
    )
    if provinces is not None:
        provinces.boundary.plot(ax=ax, color=PROVINCE_EDGE_COLOR, linewidth=0.85, alpha=0.95, zorder=3)
    china.boundary.plot(ax=ax, color="black", linewidth=1.25, zorder=4)

    plot_point_layer(ax, account_points, POINT_COLOR, zorder=5)
    plot_point_layer(ax, experimental_points, EXPERIMENT_SITE_COLOR, zorder=7)
    add_south_china_sea_inset(ax, china)
    add_overview_ticks(ax, bounds_3857)
    add_north_arrow(ax, bounds_3857)
    add_scale_bar(ax, bounds_3857)
    add_site_legend(ax)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_aspect("auto")
    for spine in ax.spines.values():
        spine.set_linewidth(1.1)
        spine.set_color("black")

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(DEFAULT_OUTPUT, dpi=300)
    plt.close(fig)


def main() -> None:
    df = get_fields_data()
    account_points = make_points_gdf(df)
    experimental_points = make_points_gdf(get_experimental_sites_data())
    if account_points.empty:
        raise ValueError("No valid test-account vineyard points found for plotting.")
    if experimental_points.empty:
        raise ValueError("No valid experimental sites found for plotting.")

    plot_distribution(account_points, experimental_points)
    print(f"Saved GrapeMaster site distribution map to: {DEFAULT_OUTPUT}")
    print(f"Saved merged point table to: {DEFAULT_CACHE_CSV}")


if __name__ == "__main__":
    main()
