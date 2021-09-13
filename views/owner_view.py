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
from web3 import Web3

from config import ACTIVE_DUST_LIMIT
from connectors.sf import sf_connect
from utils.tables import link
from utils.utils import get_last_refresh

from forms.forms import SearchForm
from utils.searchbar import run_search
from graphs.collateralization import collateralization_graph


# endpoint serving data for the owner page
def owner_page_data(sf, owner_id):

    # SQL injection protection
    if not Web3.isAddress(owner_id):
        return dict(status='failure', data='Wrong owner address %s' % owner_id)

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
        vaults_query = """
                SELECT
                    vault,
                    ilk,
                    collateral,
                    debt,
                    collateralization,
                    liquidation_price,
                    available_debt,
                    available_collateral,
                    osm_price
                FROM mcd_public.public.current_vaults
                WHERE owner = '%s'; """ % owner_id

        # snowflake data ingestion

        vaults_records = sf.execute(vaults_query).fetchall()

        # data processing

        total_debt = available_debt = 0
        tokens = dict()
        vaults = list()
        coll_buckets = dict()
        active_num = 0

        for vault in vaults_records:

            # process vault data

            if vault[3] >= ACTIVE_DUST_LIMIT:
                active_num += 1

            if vault[4]:
                bucket = min(round(vault[4]), 1000)
                if bucket not in coll_buckets:
                    coll_buckets[bucket] = 0
                coll_buckets[bucket] += vault[3]

            vault = list(vault)
            token = vault[1].split('-')[0]

            vault[0] = link(vault[0], '/vault/%s' % vault[0], 'Vault %s history' % vault[0])
            if token not in tokens:
                tokens[token] = dict(locked_amount=0, locked_value=0, available_collateral=0)
            tokens[token]['locked_amount'] += vault[2]
            tokens[token]['locked_value'] += vault[2] * vault[8]
            tokens[token]['available_collateral'] += vault[7]
            vault[1] = link(vault[1], '/collateral/%s' % vault[1], 'Vaults using %s' % vault[1]) if vault[1] else ""
            vault[2] = "{0:,.2f}".format(vault[2])
            total_debt += vault[3]
            vault[3] = "{0:,.2f}".format(vault[3])
            vault[4] = "{0:,.2f}%".format(vault[4]) if vault[4] else "-"
            vault[5] = "{0:,.2f}".format(vault[5]) if vault[5] else "-"
            available_debt += vault[6]
            vault[6] = "{0:,.2f}".format(vault[6]) if vault[6] else "0.00"
            vault[7] = "{0:,.2f}".format(vault[7]) if vault[7] else "0.00"
            vaults.append(vault)

        vaults_output = []
        for i in vaults:
            vaults_output.append(dict(
                VAULT=i[0],
                COLLATERAL=i[1],
                LOCKED_AMOUNT=i[2],
                TOTAL_DEBT=i[3],
                COLLATERALIZATION=i[4],
                LIQUIDATION_PRICE=i[5],
                AVAILABLE_DEBT=i[6],
                AVAILABLE_COLLATERAL=i[7]
            ))

        # calculate the collateralization buckets
        coll_buckets = list(coll_buckets.items())
        coll_buckets.sort(key=lambda _c: _c[0])
        x = []
        y = []
        v_sum = 0
        for c, v in coll_buckets:
            v_sum += v
            x.append(c / 100)
            y.append(v_sum)

        # calculate total stats
        locked_value = sum(_v['locked_value'] for _v in tokens.values())
        collateralization = "{0:,.2f}%".format(100 * locked_value / total_debt) if locked_value and total_debt and total_debt > 1e-10 else '-'
        total_debt = "{0:,.2f}".format(total_debt)
        vaults_num = "{0:,d}".format(len(vaults_records))
        active_num = "{0:,d}".format(active_num) if active_num else "0"
        locked_value = "{0:,.2f}".format(locked_value) if locked_value else "0"
        available_debt = "{0:,.2f}".format(available_debt) if available_debt else "0"

        locked_amounts = sorted([(_t, _v['locked_amount']) for _t, _v in tokens.items()], key=lambda _i: _i[1], reverse=True)
        available_collaterals = sorted([(_t, _v['available_collateral']) for _t, _v in tokens.items()], key=lambda _i: _i[1], reverse=True)
        locked_amounts = [(token, "{0:,.2f}".format(amount)) for token, amount in locked_amounts if amount]
        available_collaterals = [(token, "{0:,.2f}".format(amount)) for token, amount in available_collaterals if amount]

        if len(x) > 1:
            plot = collateralization_graph(owner_id[:13] + '...', x, y, 1)
        else:
            plot = None

        return dict(status='success',
                    data=dict(owner_id=owner_id,
                              total_debt=total_debt,
                              vaults=vaults_output,
                              locked_amounts=locked_amounts,
                              locked_value=locked_value,
                              collateralization=collateralization,
                              available_collaterals=available_collaterals,
                              available_debt=available_debt,
                              vaults_num=vaults_num,
                              active_num=active_num,
                              plot=plot))

    except Exception as e:
        print(e)
        return dict(status='failure', data='Backend error: %s' % e)


# flask view for the owner page
def owner_page_view(sf, owner_id):

    if not Web3.isAddress(owner_id):
        return render_template('unknown.html', object_name='owner', object_value=owner_id)

    try:
        plot = collateralization_graph(owner_id, [], [], 1)

        block, last_time = get_last_refresh(sf)

        search = SearchForm(request.form)
        if request.method == 'POST':
            return run_search(search.data['search'])

        return render_template(
            'owner.html',
            owner_id=owner_id,
            refresh="{0:,.0f}".format(block) + ' / ' + str(last_time),
            plot=plot,
            form=search)

    except Exception as e:
        print(e)
        return render_template(
            'error.html',
            error_message=str(e)
        )
