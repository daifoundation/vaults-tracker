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
import requests
import json

from config import ACTIVE_DUST_LIMIT
from connectors.sf import sf_connect
from utils.tables import link
from utils.vat import get_ilk_data
from utils.utils import get_last_refresh, get_next_price_from_chain, get_current_OSM_price

from forms.forms import SearchForm
from utils.searchbar import run_search
from graphs.collateralization import collateralization_graph


# endpoint serving data for the collateral page
def collateral_page_data(sf, collateral_id):

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

        # SQL injection protection
        collaterals = sf.execute("SELECT distinct ilk FROM mcd_public.internal.ilks; ").fetchall()

        collaterals = [c[0] for c in collaterals]
        if collateral_id not in collaterals:
            return dict(status='failure', data='Unknown collateral %s' % collateral_id)

        vaults_query = """
                SELECT
                    vault,
                    owner,
                    collateral,
                    debt,
                    collateralization,
                    liquidation_price,
                    available_debt,
                    available_collateral,
                    osm_price,
                    ratio
                FROM mcd_public.public.current_vaults
                WHERE ilk = '%s'; """ % collateral_id

        # snowflake data ingestion

        vaults_records = sf.execute(vaults_query).fetchall()

        # data processing

        Art, rate, line = get_ilk_data(collateral_id)

        total_debt = locked_amount = available_collateral = available_debt = 0
        current_vaults = []
        vaults_output = []
        coll_buckets = {}
        active_num = 0
        price = mat = 0

        for vault in vaults_records:

            # process vault data

            if vault[8]:
                price = vault[8]
            if vault[9]:
                mat = vault[9]

            if vault[3] >= ACTIVE_DUST_LIMIT:
                active_num += 1

            if vault[4]:
                bucket = min(round(vault[4]), 1000)
                if bucket not in coll_buckets:
                    coll_buckets[bucket] = 0
                coll_buckets[bucket] += vault[3]

            vault = list(vault)
            locked_amount += vault[2] or 0
            total_debt += vault[3] or 0
            available_debt += vault[6] or 0
            available_collateral += vault[7] or 0

            if vault[3] and vault[3] >= ACTIVE_DUST_LIMIT:
                vaults_output.append(dict(
                    VAULT=link(vault[0], '/vault/%s' % vault[0], 'Vault %s history' % vault[0]),
                    OWNER=link(vault[1], '/owner/%s' % vault[1], 'Vaults owned by %s...' % vault[1][:16]) if vault[1] else "",
                    COLLATERAL="{0:,.2f}".format(vault[2]),
                    DEBT="{0:,.2f}".format(vault[3]),
                    COLLATERALIZATION="{0:,.2f}%".format(vault[4]) if vault[4] else "",
                    LIQUIDATION_PRICE="{0:,.2f}".format(vault[5]) if vault[5] else "",
                    AVAILABLE_DEBT="{0:,.2f}".format(vault[6]) if vault[6] else "",
                    AVAILABLE_COLLATERAL="{0:,.2f}".format(vault[7]) if vault[7] else ""
                ))

        # calculate the collateralization buckets
        coll_buckets = list(coll_buckets.items())
        coll_buckets.sort(key=lambda c: c[0])
        x = []
        y = []
        v_sum = 0
        for c, v in coll_buckets:
            v_sum += v
            x.append(c / 100)
            y.append(v_sum)

        # calculate total stats
        token = collateral_id.split('-')[0]
        locked_value = locked_amount * price if price else None
        collateralization = "{0:,.2f}%".format(100 * locked_value / total_debt) if locked_value and total_debt and total_debt > 1e-10 else "-"
        debt_ceiling = "{0:,.0f}".format(line / 10 ** 45) if line else "-"
        debt_utilization = "{0:,.2f}%".format(100 * total_debt / (line / 10 ** 45)) if line else "-"
        total_debt = "{0:,.2f}".format(total_debt)
        vaults_num = "{0:,d}".format(len(vaults_records))
        active_num = "{0:,d}".format(active_num) if active_num else "0"
        listed_num = "{0:,d}".format(len(current_vaults) - 1)
        locked_amount = "{0:,.2f}".format(locked_amount) if locked_amount else "0"
        locked_value = "{0:,.2f}".format(locked_value) if locked_value else "0"
        liquidation_ratio = "{0:,.0f}%".format(mat * 100) if mat else "-"
        available_collateral = "{0:,.2f}".format(available_collateral) if available_collateral else "0"
        available_debt = "{0:,.2f}".format(available_debt) if available_debt else "0"

        pip_oracle = sf.execute("""SELECT pip_oracle_address, type
                                    FROM mcd_public.internal.ilks
                                    WHERE split_part(ilk, '-', 1) = '{}';
                                    """.format(token)).fetchone()

        if token == 'SAI':
            cur = "{0:,.2f}".format(1)
            nxt = "{0:,.2f}".format(1)
        else:
            cur = "{0:,.2f}".format(get_next_price_from_chain(pip_oracle[0], pip_oracle[1])[0])
            nxt = "{0:,.2f}".format(get_next_price_from_chain(pip_oracle[0], pip_oracle[1])[1])
        
        r = requests.get('https://api.coinbase.com/v2/prices/{}-USD/spot?date={}'.format(token, datetime.utcnow().date()))
        market_price = None
        if r.status_code == 200:
            coinbase_response = json.loads(r.text)
            market_price = coinbase_response['data']['amount']

        plot = collateralization_graph(collateral_id, x, y, mat)

        return dict(status='success',
                    data=dict(vaults=vaults_output,
                              listed_num=listed_num,
                              collateral_id=collateral_id,
                              total_debt=total_debt,
                              debt_ceiling=debt_ceiling,
                              debt_utilization=debt_utilization,
                              locked_amount=locked_amount,
                              locked_value=locked_value,
                              token=token,
                              liquidation_ratio=liquidation_ratio,
                              collateralization=collateralization,
                              available_collateral=available_collateral,
                              available_debt=available_debt,
                              vaults_num=vaults_num,
                              active_num=active_num,
                              plot=plot,
                              current_osm_price=cur,
                              next_osm_price=nxt,
                              market_price=market_price))

    except Exception as e:
        print(e)
        return dict(status='failure', data='Backend error: %s' % e)


# flask view for the collateral page
def collateral_page_view(sf, collateral_id):

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
        collaterals = sf.execute("""
            SELECT
                ilk,
                block,
                timestamp
            FROM mcd_public.internal.ilks; """).fetchall()

        created_block = created_time = None
        for collateral in collaterals:
            if collateral[0] == collateral_id:
                created_block = "{0:,.0f}".format(collateral[1])
                created_time = collateral[2]
                break

        # SQL injection protection
        if not created_block:
            return render_template('unknown.html', object_name='collateral', object_value=collateral_id)

        plot = collateralization_graph(collateral_id, [], [], 0)

        block, last_time = get_last_refresh(sf)

        search = SearchForm(request.form)
        if request.method == 'POST':
            return run_search(search.data['search'])

        return render_template(
            'collateral.html',
            collateral_id=collateral_id,
            created_block=created_block,
            created_time=created_time,
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
