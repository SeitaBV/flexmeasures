import datetime

from flask import Flask, render_template, request, redirect
import pandas as pd
from bokeh.models import HoverTool, Plot, Range1d
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.util.string import encode_utf8
#from bokeh.models.sources import ColumnDataSource

APP = Flask(__name__)

PV_DATA = None
SOLAR_ASSET = "EJJ PV (MW)"


@APP.route('/')
def index():
    req_month = request.args.get("month", type=int, default=1)
    req_day = request.args.get("day", type=int, default=1)
    return redirect("/%d/%d" % (req_month, req_day))


@APP.route("/<int:month>/<int:day>/")
def chart(month, day):
    try:
        datetime.datetime(year=2016, month=month, day=day)
    except ValueError:
        # TODO: raise this error to the UI
        print("Day %d is out of range for month %d" % (day, month))
        raise

    data = get_data(month, day)
    hover = create_hover_tool()
    
    fig = create_figure(data, "Solar radiation per day on %s" % SOLAR_ASSET, "15min", "MW", hover)

    script, div = components(fig)
    html = render_template("pv.html", month=month, day=day,
                           all_months=range(1, 13),
                           all_days=range(1, 32),
                           the_div=div, the_script=script,
                           js_resources=CDN.render_js(),
                           css_resources=CDN.render_css())
    return encode_utf8(html)


def get_data(month:int, day:int):
    global PV_DATA
    if PV_DATA is None:
        df = pd.read_csv("data/pv.csv")
        # TODO: We will want a clean datetime index here, where the Time column is a bit difficult to compute
        #       Maybe it's easiest if we use only it, actually
        #df['datetime'] = pd.to_datetime('2017-' + df.Month + '-' + df.Day + ' ' + df['Time'])
        #df = df.set_index('datetime').drop(['Month', 'Day'], axis=1)
        PV_DATA = df
    return PV_DATA.loc[PV_DATA.Month==month][PV_DATA.Day==day][SOLAR_ASSET]


def create_hover_tool():
    """we can return html for hover tooltips"""
    # return HoverTool(tooltips=hover_html)
    return None


def create_figure(series, title, x_label, y_label, hover_tool=None,
                  width=1200, height=300):
    #source = ColumnDataSource(series)
    xdr = Range1d(start=min(series.index), end=max(series.index))
    ydr = Range1d(start=0, end=max(series)*1.5)

    tools = []
    if hover_tool:
        tools = [hover_tool,]

    fig = figure(title=title, x_range=xdr, y_range=ydr, plot_width=width,
                 plot_height=height, h_symmetry=False, v_symmetry=False,
                 min_border=0, toolbar_location="above", tools=tools,
                 sizing_mode='scale_width', outline_line_color="#666666")

    fig.circle(series.index, series.values, color="navy", alpha=0.5)

    fig.toolbar.logo = None
    fig.yaxis.axis_label = y_label
    fig.ygrid.grid_line_alpha = 0.5
    fig.xaxis.axis_label = x_label
    fig.xgrid.grid_line_alpha = 0.5

    return fig


if __name__ == '__main__':
    APP.run(debug=True)
