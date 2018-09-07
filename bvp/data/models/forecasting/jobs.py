from typing import Union
from datetime import timedelta

from humanize import naturaldelta

from bvp.data.config import db
from bvp.data.models.weather import WeatherSensor
from bvp.data.models.assets import Asset
from bvp.data.models.markets import Market


class ForecastingJob(db.Model):
    """Describing a forecasting job."""

    id = db.Column(db.Integer(), primary_key=True)
    timed_value_type = db.Column(db.String(30), nullable=False)
    asset_id = db.Column(db.Integer(), nullable=False)
    start = db.Column(db.DateTime(timezone=True), nullable=False)
    end = db.Column(db.DateTime(timezone=True), nullable=False)
    horizon = db.Column(db.Interval(), nullable=False)
    in_progress_since = db.Column(db.DateTime(timezone=True), nullable=True)

    def num_forecasts(self, resolution: timedelta) -> int:
        """Compute how many forecasts this job needs to make, given a resolution"""
        return ((self.end - resolution) - self.start) // resolution

    def get_asset(self) -> Union[Asset, Market, WeatherSensor]:
        """Get asset for this job. Maybe simpler once we redesign timed value classes (make a generic one)"""
        if self.timed_value_type not in ("Power", "Price", "Weather"):
            raise ("Cannot get asset for asset_type '%s'" % self.timed_value_type)
        asset = None
        if self.timed_value_type == "Power":
            asset = Asset.query.filter_by(id=self.asset_id).one_or_none()
        elif self.timed_value_type == "Price":
            asset = Market.query.filter_by(id=self.asset_id).one_or_none()
        elif self.timed_value_type == "Weather":
            asset = WeatherSensor.query.filter_by(id=self.asset_id).one_or_none()
        if asset is None:
            raise (
                "Cannot find asset for value type %s with id %d"
                % (self.timed_value_type, self.asset_id)
            )
        return asset

    def __repr__(self):
        horizon_str = "%s ahead" % naturaldelta(self.horizon)
        if self.horizon < timedelta(minutes=0):
            horizon_str = "%s ago (backwards forecasting)" % naturaldelta(-self.horizon)
        return (
            "<ForecastingJob for forecasts of %s for %s:%d for the period %s to %s.>"
            % (horizon_str, self.timed_value_type, self.asset_id, self.start, self.end)
        )
