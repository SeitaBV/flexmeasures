"""CLI tasks tasks to collect third-party data."""

import os

from flask import current_app as app
import click
import pytz
import pandas as pd


@app.cli.command()
def initialise_ts_pickles():
    """Import and clean data from CSV/Excel sheets into pickles"""
    from bvp.data.scripts.init_timeseries_data import initialise_all

    with app.app_context():
        initialise_all()


@app.cli.command()
def localize_ts_pickles():
    """Set the tz of all datetime indexes to Asia/Seoul"""
    for pickle in [p for p in os.listdir("raw_data/pickles") if p.endswith(".pickle")]:
        print(
            "Localising index of %s to %s ..."
            % (pickle, app.config.get("BVP_TIMEZONE"))
        )
        df = pd.read_pickle("raw_data/pickles/%s" % pickle)
        df.index = df.index.tz_localize(
            tz=pytz.timezone(app.config.get("BVP_TIMEZONE"))
        )
        df.to_pickle("raw_data/pickles/%s" % pickle)


@app.cli.command()
@click.option(
    "--region",
    type=str,
    default="",
    help="Name of the region (will create sub-folder, should later tag the forecast in the DB, probably).",
)
@click.option(
    "--location",
    type=str,
    required=True,
    help='Measurement location(s). "latitude,longitude" or "top-left-latitude,top-left-longitude:'
    'bottom-right-latitude,bottom-right-longitude." The first format defines one location to measure.'
    " The second format defines a region of interest with several (>=4) locations"
    ' (see also the "method" and "num_cells" parameters for this feature).',
)
@click.option(
    "--num_cells",
    type=int,
    default=1,
    help="Number of cells on the grid. Only used if a region of interest has been mapped in the location parameter.",
)
@click.option(
    "--method",
    default="hex",
    type=click.Choice(["hex", "square"]),
    help="Grid creation method. Only used if a region of interest has been mapped in the location parameter.",
)
@click.option(
    "--store-in-db/--store-as-json-files",
    default=False,
    help="Store forecasts in the database, or simply save as json files.",
)
def collect_weather_data(region, location, num_cells, method, store_in_db):
    """Collect weather data for a grid. Leave bottom right empty for only one location (top left)."""
    from bvp.data.scripts.grid_weather import get_weather_forecasts

    get_weather_forecasts(app, region, location, num_cells, method, store_in_db)