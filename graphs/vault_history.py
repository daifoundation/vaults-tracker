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


# Vault history graph
def vault_history_graph(x, y1, y2, y3):

    data1 = [
            go.Scatter(
                x=x,
                y=y1,
                name='Debt (DAI)',
                line={'color': '#1aab9b'},
                fill='tozeroy',
                yaxis="y"
            ),
            go.Scatter(
                x=x,
                y=y2,
                name='Collateralization',
                line={'color': '#006699'},
                yaxis="y2"
            ),
            go.Scatter(
                x=x,
                y=y3,
                name='Liquidation ratio',
                line={'color': 'red'},
                yaxis="y2"
            )
        ]

    layout1 = go.Layout(title={'text': "Vault in time (UTC)", 'x': 0.5, 'xanchor': 'center'}, plot_bgcolor='#fcfcfc', paper_bgcolor='#fcfcfc',
                        height=275, margin={"b": 20, "l": 20, "r": 10, "t": 75, "pad": 10}, xaxis={'gridcolor': '#F0F0F0'},
                        yaxis={'gridcolor': '#F0F0F0'}, legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=.5),
                        yaxis2={'gridcolor': '#F0F0F0', 'side': 'right', 'tickformat': ',.0%', 'overlaying': 'y',
                                'range': [1, min(safe_max([y or 0 for y in y2]) * 1.1, 20)]},
                        hovermode="x unified", hoverlabel={'namelength': -1})

    figure1 = go.Figure(data=data1, layout=layout1)

    graph_json1 = json.dumps(figure1, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json1
