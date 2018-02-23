"""
Utils for accessing data.
"""

from typing import List, Dict, Union
import json
import os
import datetime

from flask import session, current_app
from werkzeug.exceptions import BadRequest
import pandas as pd

from models import Asset, Market, resolutions
from utils import time_utils


# global, lazily loaded asset description
ASSETS = []
# global, lazily loaded market description
MARKETS = []
# global, lazily loaded data source, will be replaced by DB connection probably
DATA = {}


def get_assets() -> List[Asset]:
    """Return a list of all models.Asset objects that are mentioned in assets.json and have data.
    The asset list is constructed lazily (only once per app start)."""
    global ASSETS
    if len(ASSETS) == 0:
        with open("data/assets.json", "r") as assets_json:
            dict_assets = json.loads(assets_json.read())
        ASSETS = []
        for dict_asset in dict_assets:
            has_data = True
            for res in resolutions:
                if not os.path.exists("data/pickles/df_%s_res%s.pickle" % (dict_asset["name"], res)):
                    has_data = False
                    break
            if has_data:
                ASSETS.append(Asset(**dict_asset))
    return ASSETS


def get_markets() -> List[Market]:
    """Return markets. Markets are loaded lazily from file."""
    global MARKETS
    if len(MARKETS) == 0:
        with open("data/markets.json", "r") as markets_json:
            dict_markets = json.loads(markets_json.read())
        MARKETS = [Market(**a) for a in dict_markets]
    return MARKETS


def get_data_for_assets(asset_names: List[str], start: datetime=None, end: datetime=None, resolution: str=None,
                        sum_multiple=True) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Get data for one or more assets (also markets).
    We (lazily) look up by pickle, so we require a list of asset or market names.
    If the time range parameters are None, they will be gotten from the session.
    Response is a 2D data frame with the usual columns (y, yhat, ...).
    If data from multiple assets is retrieved, the results are being summed.
    If sum_multiple is False, the response will be a dictionary with asset names as keys and data frames as values.
    Response might be None if no data exists for these assets in this time range."""
    data_as_dict: Dict[str, pd.DataFrame] = None
    data_as_df: pd.DataFrame = None
    if start is None or end is None or resolution is None and "resolution" not in session:
        time_utils.set_time_range_for_session()
    if start is None:
        start = session["start_time"]
    if end is None:
        end = session["end_time"]
    if resolution is None:
        resolution = session["resolution"]
    for asset_name in asset_names:
        data_label = "%s_res%s" % (asset_name, resolution)
        global DATA
        if data_label not in DATA:
            current_app.logger.info("Loading %s data from disk ..." % data_label)
            try:
                DATA[data_label] = pd.read_pickle("data/pickles/df_%s.pickle" % data_label)
            except FileNotFoundError:
                raise BadRequest("Sorry, we cannot find any data for the resource \"%s\" ..." % data_label)
        date_mask = (DATA[data_label].index >= start) & (DATA[data_label].index <= end)

        if sum_multiple is True:  # Here we only build one data frame, summed up if necessary.
            if data_as_df is None:
                data_as_df = DATA[data_label].loc[date_mask]
            else:
                data_as_df = data_as_df.add(DATA[data_label].loc[date_mask])
        else:                     # Here we build a dict with data frames.
            if data_as_dict is None:
                data_as_dict = {asset_name: DATA[data_label].loc[date_mask]}
            else:
                data_as_dict[asset_name] = DATA[data_label].loc[date_mask]
    if sum_multiple is True:
        return data_as_df
    else:
        return data_as_dict


def extract_forecasts(df: pd.DataFrame) -> pd.DataFrame:
    """Extract forecast columns (given the chosen horizon) and give them the standard naming"""
    forecast_columns = ["yhat", "yhat_upper", "yhat_lower"]  # this is what the plotter expects
    horizon = session["forecast_horizon"]
    forecast_renaming = {"yhat_%s" % horizon: "yhat",
                         "yhat_%s_upper" % horizon: "yhat_upper",
                         "yhat_%s_lower" % horizon:  "yhat_lower"}
    return df.rename(forecast_renaming, axis="columns")[forecast_columns]