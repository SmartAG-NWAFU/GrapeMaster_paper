from __future__ import annotations

import os
import io
from pathlib import Path

import geopandas as gpd
import mercantile
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from PIL import Image
from pyproj import CRS, Transformer
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRIAL_CSV = ROOT / "data" / "Grapemater_fields.csv"
DEFAULT_CACHE_CSV = ROOT / "data" / "grape_trial_locations.csv"
DEFAULT_OUTPUT = ROOT / "fig" / "grape_trial_distribution_china.png"
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
POINT_EDGE_COLOR = "white"
TIANDITU_ZOOM = 4


def build_database_url() -> str:
    load_dotenv()
    db_user = os.getenv("user")
    db_password = os.getenv("password")
    db_host = os.getenv("host")
    db_port = os.getenv("port")
    db_name = os.getenv("name")
    missing = [
        key
        for key, value in {
            "user": db_user,
            "password": db_password,
            "host": db_host,
            "port": db_port,
            "name": db_name,
        }.items()
        if not value
    ]
    if missing:
        raise EnvironmentError(f"Missing database environment variables: {', '.join(missing)}")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_tianditu_key() -> str:
    load_dotenv()
    key = os.getenv("tianditu_api_key")
    if not key:
        raise EnvironmentError("Missing tianditu_api_key in .env")
    return key


def get_fields_data() -> pd.DataFrame:
    engine = create_engine(build_database_url())
    sql = """
        SELECT
            ff.uuid,
            ff.centroid_lon,
            ff.centroid_lat,
            ff.region
        FROM field_field ff
    """
    fields = pd.read_sql(sql, engine)
    fields["uuid"] = fields["uuid"].astype(str)

    trials = pd.read_csv(DEFAULT_TRIAL_CSV)
    if "uuid" not in trials.columns:
        raise ValueError(f"Missing required column in trial CSV: uuid")
    trials["uuid"] = trials["uuid"].astype(str)

    real_df = (
        fields.merge(trials, on="uuid", how="inner")
        .dropna(subset=["centroid_lon", "centroid_lat", "name"])
        .reset_index(drop=True)
    )
    real_df["centroid_lon"] = pd.to_numeric(real_df["centroid_lon"], errors="coerce")
    real_df["centroid_lat"] = pd.to_numeric(real_df["centroid_lat"], errors="coerce")
    real_df = real_df.dropna(subset=["centroid_lon", "centroid_lat"])
    real_df = real_df[
        real_df["centroid_lon"].between(73, 136) & real_df["centroid_lat"].between(3, 54)
    ].copy()

    DEFAULT_CACHE_CSV.parent.mkdir(parents=True, exist_ok=True)
    real_df.to_csv(DEFAULT_CACHE_CSV, index=False, encoding="utf-8-sig")

    return real_df


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
) -> None:
    minx, maxx, miny, maxy = bounds_3857
    to_lonlat = Transformer.from_crs(WEB_MERCATOR_CRS, "EPSG:4326", always_xy=True)
    to_mercator = Transformer.from_crs("EPSG:4326", WEB_MERCATOR_CRS, always_xy=True)
    west, south = to_lonlat.transform(minx, miny)
    east, north = to_lonlat.transform(maxx, maxy)
    tiles = list(mercantile.tiles(west, south, east, north, [TIANDITU_ZOOM]))
    xs = sorted({tile.x for tile in tiles})
    ys = sorted({tile.y for tile in tiles})
    key = get_tianditu_key()
    mosaics = []

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

    west_all, south_all, _, _ = mercantile.bounds(xs[0], ys[-1], TIANDITU_ZOOM)
    _, _, east_all, north_all = mercantile.bounds(xs[-1], ys[0], TIANDITU_ZOOM)
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


def plot_distribution(points: gpd.GeoDataFrame) -> None:
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

    add_tianditu_basemap(ax, bounds_3857, china)
    china.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.9, zorder=2)
    if provinces is not None:
        provinces.boundary.plot(ax=ax, color=PROVINCE_EDGE_COLOR, linewidth=0.85, alpha=0.95, zorder=3)
    china.boundary.plot(ax=ax, color="black", linewidth=1.25, zorder=4)

    points.plot(ax=ax, markersize=82, color="black", edgecolor="none", alpha=0.82, zorder=5)
    points.plot(
        ax=ax,
        markersize=48,
        color=POINT_COLOR,
        edgecolor=POINT_EDGE_COLOR,
        linewidth=1.05,
        alpha=0.96,
        zorder=6,
    )
    add_south_china_sea_inset(ax, china)
    add_overview_ticks(ax, bounds_3857)
    add_north_arrow(ax, bounds_3857)
    add_scale_bar(ax, bounds_3857)

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
    points = make_points_gdf(df)
    if points.empty:
        raise ValueError("No valid trial points found for plotting.")

    plot_distribution(points)
    print(f"Saved grape trial distribution map to: {DEFAULT_OUTPUT}")
    print(f"Saved merged point table to: {DEFAULT_CACHE_CSV}")


if __name__ == "__main__":
    main()
