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

from flask import render_template, request
from datetime import datetime
from decimal import Decimal

from utils.utils import async_queries, vault_check, get_last_refresh, get_next_price_from_chain, get_oracle_address
from connectors.sf import sf_connect
from utils.tables import link

from forms.forms import SearchForm
from utils.searchbar import run_search
from graphs.vault_history import vault_history_graph

from web3 import Web3

# endpoint serving data for the vault page
def vault_page_data(sf, vault_id):

    # SQL injection protection
    if not vault_check(vault_id):
        return dict(status='failure', data='Wrong vault id %s' % vault_id)

    # test snowflake connection and reconnect if necessary
    try:
        if sf.is_closed():
            sf = sf_connect()
        if sf.is_closed():
            raise Exception('Reconnection failed')

    except Exception as e:
        print(e)
        return dict(status='failure', data='Database connection error')

    try:

        # snowflake data ingestion
        main_queries = []

        operations_query = """
                SELECT
                    order_index,
                    block,
                    timestamp,
                    tx_hash,
                    ilk,
                    operation,
                    dcollateral,
                    dprincipal,
                    dfees,
                    mkt_price,
                    osm_price,
                    dart,
                    rate,
                    ratio
                FROM mcd_public.public.vaults
                WHERE vault = '%s'
                ORDER BY order_index; """ % vault_id

        current_query = """
                SELECT *
                FROM mcd_public.public.current_vaults
                WHERE vault = '%s'; """ % vault_id

        all_queries = [
            dict(query=operations_query, id='operations'),
            dict(query=current_query, id='current')
        ]

        # snowflake data ingestion

        sf_responses = async_queries(sf, all_queries)
        operations = sf_responses['operations']
        current = sf_responses['current']

        # data processing

        vault_operations = []
        ink = art = 0
        for record in operations:
            coll0 = 100 * Decimal((ink * record[10])) / (art * record[12] / 10 ** 45) if ink and art and record[10] and record[12] else None
            ink += record[6]
            art += record[11]
            coll1 = 100 * Decimal((ink * record[10])) / (art * record[12] / 10 ** 45) if ink and art and record[10] and record[12] else None
            operation = [
                record[2],
                link(record[5],
                'https://ethtx.info/%s' % record[3],
                '%s transaction' % record[5]) if record[5] else '',
                "{0:,.2f}".format(record[6]) if record[6] else '',
                "{0:,.2f}".format(record[7]) if record[7] else '',
                "{0:,.2f}".format(record[8]) if record[8] else '',
                "{0:,.2f}".format(record[9]) if record[9] else '',
                "{0:,.2f}".format(record[10]) if record[10] else '',
                "{0:,.2f}%".format(coll0) if coll0 else '',
                "{0:,.2f}%".format(coll1) if coll1 else '',
                record[0]]

            vault_operations.append(operation)

        vault_operations_output = []
        for i in vault_operations[::-1]:

            vault_operations_output.append(dict(
                TIME=i[0].strftime("%Y-%m-%d %H:%M:%S") + ' ' + str(i[9]),
                OPERATION=i[1],
                COLLATERAL_CHANGE=i[2],
                DEBT_CHANGE=i[3],
                PAID_FEES=i[4],
                MARKET_PRICE=i[5],
                ORACLE_PRICE=i[6],
                PRE_COLL=i[7],
                POST_COLL=i[8]
            ))

        operations_num = "{0:,d}".format(len(vault_operations))
        locked_collateral = "{0:,.2f}".format(current[0][2])
        osm_price = "{0:,.2f}".format(current[0][8]) if current[0][8] else ''
        mkt_price = "{0:,.2f}".format(current[0][9]) if current[0][9] else ''
        collateral_value = "{0:,.2f}".format(current[0][2] * current[0][8])
        available_collateral = "{0:,.2f}".format(current[0][13])
        collateral_ratio = 100 * (current[0][2] - current[0][13]) / current[0][2] if current[0][2] else 0
        debt = "{0:,.2f}".format(current[0][5])
        available_debt = "{0:,.2f}".format(current[0][12]) if current[0][12] else "0.00"
        debt_ratio = 100 * current[0][5] / (current[0][5] + current[0][12]) if current[0][12] is not None and (current[0][5] + current[0][12]) else 0
        principal = "{0:,.2f}".format(current[0][3])
        coin = operations[-1][4].split('-')[0]
        fees = "{0:,.2f}".format(current[0][6])
        paid_fees = "{0:,.2f}".format(current[0][4])
        collateralization = "{0:,.2f}%".format(current[0][7]) if current[0][7] else '-'
        liquidation_ratio = "{0:,.0f}%".format(current[0][10] * 100)
        coll_ratio = 10000 * current[0][10] / current[0][7] if current[0][7] and current[0][10] else 0
        liquidation_price = "{0:,.2f}".format(current[0][11]) if current[0][11] else '-'

        x = []
        y1 = []
        y2 = []
        y3 = []

        if operations:

            all_queries = []

            if len(operations[-1][4].split('-')) > 2:
                token = operations[-1][4].split('-')[1]
            else:
                token = operations[-1][4].split('-')[0]

            days_query = """
                    SELECT
                        r.date,
                        rate,
                        price
                    FROM
                        (SELECT
                            distinct date(timestamp) as date,
                            last_value(rate) over (partition by date(timestamp) order by timestamp) as rate
                            FROM mcd_public.internal.rates
                            WHERE ilk = '%s'
                            AND date(timestamp) between '%s' AND '%s') r
                    JOIN
                        (SELECT
                            distinct date(time) as date,
                            min(osm_price) over (partition by date(time)) as price
                        FROM mcd_public.internal.prices
                        WHERE
                            token = '%s'
                            AND date(time) between '%s' and '%s') p
                    ON r.date = p.date
                    ORDER BY r.date; """ % (operations[-1][4],
                                            operations[0][2].date(),
                                            datetime.now().date(),
                                            token,
                                            operations[0][2].date(),
                                            datetime.now().date())

            mats_query = """
                    SELECT
                        distinct date(timestamp) as date,
                        last_value(mat) over (partition by date(timestamp) order by timestamp) as mat
                    FROM mcd_public.internal.mats
                    WHERE ilk = '%s'
                    ORDER BY date; """ % operations[-1][4]

            all_queries = [
                dict(query=days_query, id='days'),
                dict(query=mats_query, id='mats')
            ]

            # snowflake data ingestion

            sf_responses = async_queries(sf, all_queries)
            days = sf_responses['days']
            mats = sf_responses['mats']

            # processing the data

            pointer = 0
            ink = art = 0

            for d, rate, price in days:
                dart = 0
                dink = 0
                while pointer < len(operations) and operations[pointer][2].date() == d:
                    dart += operations[pointer][11]
                    dink += operations[pointer][6]
                    pointer += 1
                x.append(d)
                art += dart
                ink += dink
                _debt = art * rate / 10 ** 45
                _locked = ink * price if price else 0
                _collateralization = Decimal(_locked) / _debt if _debt > 1e-10 else None

                _mat = 0
                for record in mats:
                    if record[0] <= d:
                        _mat = record[1]

                y1.append(float(_debt) if _debt else 0)
                y2.append(float(_collateralization) if _collateralization else None)
                y3.append(_mat)
        
        pip_oracle = sf.execute("""SELECT pip_oracle_address, type
                                    FROM mcd_public.internal.ilks
                                    WHERE split_part(ilk, '-', 1) = '{}';
                                    """.format(coin)).fetchone()

        if coin == 'SAI':
            nxt = "{0:,.2f}".format(1)
        else:
            nxt = "{0:,.2f}".format(get_next_price_from_chain(pip_oracle[0], pip_oracle[1])[1])

        plot = vault_history_graph(x, y1, y2, y3)

        return dict(status='success',
                    data=dict(coin=coin,
                              locked_collateral=locked_collateral,
                              available_collateral=available_collateral,
                              osm_price=osm_price,
                              mkt_price=mkt_price,
                              collateral_value=collateral_value,
                              debt=debt,
                              available_debt=available_debt,
                              principal=principal,
                              fees=fees,
                              paid_fees=paid_fees,
                              collateralization=collateralization,
                              liquidation_ratio=liquidation_ratio,
                              liquidation_price=liquidation_price,
                              collateral_ratio=collateral_ratio,
                              debt_ratio=debt_ratio,
                              coll_ratio=coll_ratio,
                              plot=plot,
                              operations=vault_operations_output,
                              operations_num=operations_num,
                              next_osm_price=nxt))

    except Exception as e:
        print(e)
        return dict(status='failure', data='Backend error: %s' % e)


# flask view for the vault page
def vault_page_view(sf, vault_id):

    # SQL injection prevention
    if not vault_check(vault_id):
        return render_template('unknown.html', object_name='vault', object_value=vault_id)

    # test snowflake connection and reconnect if necessary
    try:
        if sf.is_closed():
            sf = sf_connect()
        if sf.is_closed():
            raise Exception('Reconnection failed')

    except Exception as e:
        print(e)
        return dict(status='failure', data='Database connection error')

    try:

        block, last_time = get_last_refresh(sf)

        current = sf.execute("""
                            SELECT ilk, owner, block_created, time_created
                            FROM mcd_public.public.current_vaults
                            WHERE vault = '%s'; """ % vault_id).fetchone()

        if not current:
            return render_template('unknown.html', object_name='vault', object_value=vault_id)

        plot = vault_history_graph([], [], [], [])

        search = SearchForm(request.form)
        if request.method == 'POST':
            return run_search(search.data['search'])

        return render_template(
            'vault.html',
            vault_id=vault_id,
            collateral=current[0],
            owner=current[1],
            block_created="{0:,.0f}".format(current[2]) if current[2] else '-',
            time_created=current[3],
            plot=plot,
            refresh="{0:,.0f}".format(block) + ' / ' + str(last_time),
            form=search
        )

    except Exception as e:
        print(e)
        return render_template(
            'error.html',
            error_message=str(e)
        )
