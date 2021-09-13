#  Copyright 2021 DAI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import json
import plotly
import plotly.graph_objs as go

from utils.utils import safe_max


# Collateralization graph for the main page
def main_collateralization_graph(stable, non_stable):

    x = []
    y = []
    v_sum = 0
    for c, v in non_stable:
        v_sum += v
        x.append(c / 100)
        y.append(v_sum)

    data1 = [
            go.Scatter(
                x=x,
                y=y,
                name='Non-Stable',
                line={'color': 'darkslategray'},
                fill='tozeroy',
                yaxis="y"
            )]

    x = []
    y = []
    v_sum = 0
    for c, v in stable:
        v_sum += v
        x.append(c / 100)
        y.append(v_sum)

    data1.append(
            go.Scatter(
                x=x,
                y=y,
                name='Stable',
                mode='lines',
                line={'color': '#1aab9b'},
                fill='tozeroy',
                yaxis="y"
            )
    )

    layout1 = go.Layout(title={'text': "Debt collateralization", 'x': 0.5, 'xanchor': 'center'}, plot_bgcolor='#fcfcfc',
                        paper_bgcolor='#fcfcfc', height=340, margin={"b": 20, "l": 20, "r": 10, "t": 75, "pad": 10},
                        xaxis={'gridcolor': '#F0F0F0', 'tickformat': ',.0%'},
                        yaxis={'gridcolor': '#F0F0F0'},
                        yaxis2={'overlaying': 'y', 'side': 'right'},
                        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=.5),
                        hovermode="x unified", hoverlabel={'namelength': -1})


    figure1 = go.Figure(data=data1, layout=layout1)
    figure1.update_traces(hovertemplate="%{y:,.2f}")

    graph_json1 = json.dumps(figure1, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json1


# Collateralization graph for other pages
def collateralization_graph(ilk, x, y, mat):

    data1 = [
            go.Scatter(
                x=x,
                y=y,
                name='Debt (DAI)',
                line={'color': '#1aab9b'},
                fill='tozeroy',
                yaxis="y"
            ),
            go.Scatter(
                x=[0],
                y=[-1],
                name='Liq. ratio',
                mode='lines',
                line={'color': 'red'},
                yaxis="y"
            )
            ]

    layout1 = go.Layout(title={'text': "%s debt collateralization" % ilk, 'x': 0.5, 'xanchor': 'center'}, plot_bgcolor='rgba(0,0,0,0)',
                        height=275, margin={"b": 20, "l": 20, "r": 10, "t": 75, "pad": 10},
                        xaxis={'gridcolor': '#F0F0F0', 'tickformat': ',.0%', 'range': [1, min(5, safe_max(x))]},
                        yaxis={'gridcolor': '#F0F0F0', 'range': [0, safe_max(y) * 1.05]},
                        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=.5),
                        hovermode="x unified", hoverlabel={'namelength': -1},
                        shapes=[dict(type="line", xref="x", yref="paper", x0=mat, y0=0, x1=mat, y1=0.95, line=dict(color="red", width=2))])

    figure1 = go.Figure(data=data1, layout=layout1)
    figure1.update_traces(hovertemplate="%{y:,.2f}")

    graph_json1 = json.dumps(figure1, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json1
