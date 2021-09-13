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

import snowflake.connector
from config import SNOWFLAKE_CONNECTION
from flask import jsonify, make_response
from flask.wrappers import Response

from utils.utils import vault_check

processing_error_message = 'Internal server error.'
snowflake_connection_error = dict(
    message='Connection with data source cannot be established.',
    status='failure')


def get_all_vaults(sf):

    vaults_check = "SELECT distinct vault FROM CURRENT_VAULTS; "

    try:
        vaults = sf.execute(vaults_check).fetchall()
    except:
        vaults = []
    
    vaults = [vault[0] for vault in vaults]

    return vaults


def operator_parser(op):

    if op.lower() == 'gte':
        operator = '>='
    elif op.lower() == 'gt':
        operator = '>'
    elif op.lower() == 'eq':
        operator = '='
    elif op.lower() == 'neq':
        operator = '!='
    elif op.lower() == 'lt':
        operator = '<'
    elif op.lower() == 'lte':
        operator = '<='
    elif op.lower() == 'in':
        operator = 'in'
    else:
        operator = None

    return operator


def get_last_block():

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)
    
    sf = connection.cursor()

    try:
        last_block = sf.execute('SELECT DISTINCT LAST_BLOCK FROM CURRENT_VAULTS;').fetchone()
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))
    finally:
        if not sf.is_closed():
            sf.connection.close()

    return jsonify(dict(
        message=dict(last_block=last_block[0]),
        status='success'))


def get_last_time():

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)

    sf = connection.cursor()

    try:
        last_time = sf.execute('SELECT DISTINCT LAST_TIME FROM CURRENT_VAULTS;').fetchone()
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))

    finally:
        if not sf.is_closed():
            sf.connection.close()

    return jsonify(dict(
        message=dict(last_time=last_time[0]),
        status='success'))


def get_vault_history(vault, request):

    if not vault_check(vault):
        return jsonify(dict(
            message='Vault {} does not exist.'.format(vault),
            status='failure'))

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)

    sf = connection.cursor()

    try:
        all_vaults = get_all_vaults(sf)
    
        if vault and vault in all_vaults:
    
            query = """
                SELECT
                    vault,
                    ilk,
                    block,
                    timestamp,
                    tx_hash,
                    operation,
                    dcollateral,
                    dprincipal,
                    dfees,
                    mkt_price,
                    osm_price,
                    dart,
                    rate,
                    ratio
                FROM VAULTS
                WHERE VAULT = '{}'
                ORDER BY order_index;""".format(vault)
    
            url_parameters = request.args.to_dict()
    
            if 'format' in url_parameters and url_parameters['format'] == 'csv':
        
                try:
                    vault_history = sf.execute(query).fetchall()
                except Exception as e:
                    return jsonify(dict(
                        message=str(e),
                        status='failure'))
    
                header_line = 'vault, ilk, block, timestamp, tx_hash, operation, collateral_delta, principal_delta, fees_paid, market_price, osm_price, art_delta, rate, ratio\n'
                content = ''
    
                for operation in vault_history:
                    content += ','.join([str(field) if field else '' for field in operation]) + '\n'
    
                try:
                    response = make_response(header_line + content)
                    response.headers['Content-Disposition'] = 'attachment; filename=' + str(vault) + '_history.csv'
                    response.mimetype = 'text/csv'
                except Exception as e:
                    return jsonify(dict(
                        message=str(e),
                        status='failure'))
    
                return response
    
            else:
    
                sf_dict = connection.cursor(snowflake.connector.DictCursor)
    
                try:
                    vault_history = sf_dict.execute(query).fetchall()
                    vault_history_json = [dict((k.lower(), v) for k, v in operation.items()) for operation in vault_history]

                except Exception as e:
                    return jsonify(dict(
                        message=str(e),
                        status='failure'))
            
                return jsonify(dict(
                        message=dict(vault_history=vault_history_json),
                        status='success'
                    ))
        
        else:
            return jsonify(dict(
                message='Vault {} does not exist.'.format(vault),
                status='failure'))
        
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))
    finally:
        if not sf.is_closed():
            sf.connection.close()


def get_vault_state(vault):

    if not vault_check(vault):
        return jsonify(dict(
            message='Vault {} does not exist.'.format(vault),
            status='failure'))

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)
    
    sf = connection.cursor()
    
    try:
        all_vaults = get_all_vaults(connection.cursor())
    
        if vault and vault in all_vaults:
                
            query = """
                SELECT
                    vault,
                    urn,
                    ilk,
                    collateral,
                    principal,
                    paid_fees,
                    art,
                    debt,
                    accrued_fees,
                    collateralization,
                    osm_price,
                    mkt_price,
                    ratio,
                    liquidation_price,
                    available_debt,
                    available_collateral,
                    owner,
                    block_created
                FROM CURRENT_VAULTS
                WHERE VAULT = '{}'
                ORDER BY vault;""".format(vault)
            
            sf_dict = connection.cursor(snowflake.connector.DictCursor)
    
            try:
                vault_status = sf_dict.execute(query).fetchone()
                vault_status_response = dict((k.lower(), v) for k, v in vault_status.items())

            except Exception as e:
                return jsonify(dict(
                    message=dict(vault_state=str(e)),
                    status='failure'))
            
            return jsonify(dict(
                    message=dict(vault_state=vault_status_response),
                    status='success'
                ))
        
        else:

            return jsonify(dict(
                message='Vault {} does not exist.'.format(vault),
                status='failure'))
        
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))
    finally:
        if not sf.is_closed():
            sf.connection.close()


def get_filtered_vaults_list(request):

    available_columns = [
        'vault',
        'urn',
        'ilk',
        'collateral',
        'principal',
        'paid_fees',
        'art',
        'debt',
        'accrued_fees',
        'collateralization',
        'osm_price',
        'mkt_price',
        'ratio',
        'liquidation_price',
        'available_debt',
        'available_collateral',
        'owner',
        'block_created'
    ]

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)

    sf = connection.cursor()

    try:
        args_to_parse = request.args.to_dict(flat=False)
    
        filters = 'True'
        for key, values in args_to_parse.items():
    
            if key in ('format', 'access_token'):
                continue
    
            params = key.split('[')
            column = params[0]
    
            # checking if all Query Params matching available columns
            if column not in available_columns:
                return jsonify(dict(
                    message='Unknown column: {}.'.format(column),
                    status='failure'))
    
            operator = params[1][:-1]
            decoded_operator = operator_parser(operator)
            decoded_values = values[0].split(',')
    
            # checking if there's any suspicious ; in params values
            for dv in decoded_values:
                if ';' in dv:
                    return jsonify(dict(
                        message='Bad request.',
                        status='failure'))
    
            if decoded_operator:
                if decoded_operator == 'in':
                    values_str = ','.join(["'%s'" % value for value in decoded_values])
                    filters += " AND %s in (%s)" % (column, values_str)
                else:
                    if column == 'vault' or not values[0].replace('.', '', 1).isdigit():
                        filters += " AND %s%s'%s'" % (column, decoded_operator, decoded_values[0])
                    else:
                        filters += " AND %s%s%s" % (column, decoded_operator, decoded_values[0])
    
            # if operator is not supported, we break the flow
            else:
                return jsonify(dict(
                    message='Unknown operator: {}.'.format(operator),
                    status='failure'))
    
        query = """
            SELECT
                vault,
                urn,
                ilk,
                collateral,
                principal,
                paid_fees,
                art,
                debt,
                accrued_fees,
                collateralization,
                osm_price,
                mkt_price,
                ratio,
                liquidation_price,
                available_debt,
                available_collateral,
                owner,
                block_created
            FROM CURRENT_VAULTS
            WHERE {}
            ORDER BY debt DESC;""".format(filters)
    
        if 'format' in args_to_parse and args_to_parse['format'] == ['csv']:
    
            try:
                vaults = sf.execute(query).fetchall()
            except Exception as e:
                return jsonify(dict(
                    message=str(e),
                    status='failure'))
          
            header_line = 'vault, urn, ilk, collateral, principal, paid_fees, art, debt, accrued_fees, collateralization, ' \
                          'osm_price, mkt_price, ratio, liquidation_price, available_debt, available_collateral, owner, block_created\n'
            content = ''
    
            for vault in vaults:
                content += ','.join([str(field) if field else '' for field in vault]) + '\n'
    
            try:
                response = make_response(header_line + content)
                response.headers['Content-Disposition'] = 'attachment; filename=vaults.csv'
                response.mimetype = 'text/csv'

            except Exception as e:
                return jsonify(dict(
                    message=str(e),
                    status='failure'))
    
            return response
    
        else:
    
            sf_dict = connection.cursor(snowflake.connector.DictCursor)
    
            try:
                vaults = sf_dict.execute(query).fetchall()
                vaults_json = [dict((k.lower(), v) for k, v in vault.items()) for vault in vaults]

            except Exception as e:
                return jsonify(dict(
                    message=str(e),
                    status='failure'))

            return jsonify(dict(
                message=dict(vaults=vaults_json),
                status='success'))
        
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))

    finally:
        if not sf.is_closed():
            sf.connection.close()
        

def get_ilks_state(request):

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)

    sf = connection.cursor()

    try:
        vaults_query = """
            SELECT
                vault,
                ilk,
                collateral,
                debt,
                available_debt,
                available_collateral,
                owner,
                collateralization
            FROM mcd_public.public.current_vaults
            ORDER BY principal + accrued_fees DESC;"""

        vaults = sf.execute(vaults_query).fetchall()

        mats_records_query = """
            SELECT
                distinct ilk,
                last_value(mat) over (partition by ilk order by timestamp) as mat
            FROM mcd_public.internal.mats;"""

        mats_records = sf.execute(mats_records_query).fetchall()

        collaterals = dict()
        for m in mats_records:
            collaterals[m[0]] = dict(mat=100 * m[1])

        prices_records_query = """
            SELECT
                distinct token,
                last_value(osm_price) over (partition by token order by time) as price
            FROM mcd_public.internal.prices;"""

        prices_records = sf.execute(prices_records_query).fetchall()

        prices = dict()
    
        for p in prices_records:
            prices[p[0]] = p[1]
    
        for c in collaterals:
            collaterals[c]['debt'] = 0
            collaterals[c]['locked_amount'] = 0
            collaterals[c]['available_debt'] = 0
            collaterals[c]['available_collateral'] = 0
            collaterals[c]['vaults_num'] = 0
            collaterals[c]['active_num'] = 0
    
        for vault in vaults:
            collaterals[vault[1]]['vaults_num'] += 1
            collaterals[vault[1]]['active_num'] += 1 if vault[3] > 20 else 0
            collaterals[vault[1]]['locked_amount'] += vault[2]
            collaterals[vault[1]]['debt'] += vault[3]
            collaterals[vault[1]]['available_debt'] += vault[4] or 0
            collaterals[vault[1]]['available_collateral'] += vault[5]

        if 'RWA' == c[:3]:
            rwa_fake_price = 0
        else:
            rwa_fake_price = prices[c.split('-')[0]] if c.split('-')[0] in prices else 0
        for c in collaterals:
            collaterals[c]['locked_value'] = collaterals[c]['locked_amount'] * rwa_fake_price
            collaterals[c]['collateralization'] = (collaterals[c]['locked_value'] / collaterals[c]['debt']) \
                if collaterals[c]['locked_value'] and collaterals[c]['debt'] and collaterals[c]['debt'] > 1e-10 else None
    
        url_parameters = request.args.to_dict()
    
        if 'format' in url_parameters and url_parameters['format'] == 'csv':
    
            header_line = 'collateral,active_vaults,total_vaults,locked_value,total_debt,available_debt,available_collateral,collateralization\n'
            content = ''
    
            for collateral, state in collaterals.items():
                content += ','.join([collateral, str(state['active_num']), str(state['vaults_num']), str(state['locked_value']),
                                     str(state['debt']), str(state['available_debt']), str(state['available_collateral']),
                                     str(state['collateralization']) if state['collateralization'] else '']) + '\n'
            try:    
                response = make_response(header_line + content)
                response.headers['Content-Disposition'] = 'attachment; filename=collaterals.csv'
                response.mimetype = 'text/csv'

            except Exception as e:
                return jsonify(dict(
                    message=str(e),
                    status='failure'))
        
            return response
    
        else:
            collaterals_state_json = []
            for collateral, state in collaterals.items():
                collaterals_state_json.append(dict(
                    collateral=collateral,
                    active_vaults=state['active_num'],
                    total_vaults=state['vaults_num'],
                    locked_value=state['locked_value'],
                    total_debt=state['debt'],
                    available_debt=state['available_debt'],
                    available_collateral=state['available_collateral'],
                    collateralization=state['collateralization']))
    
            return jsonify(dict(
                message=dict(collaterals=collaterals_state_json),
                status='success'))
        
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))
    finally:
        if not sf.is_closed():
            sf.connection.close()


def get_vault_state_for_block(vault, block):

    if not vault_check(vault):
        return jsonify(dict(
            message='Vault {} does not exist.'.format(vault),
            status='failure'))

    try:
        connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION)
    except:
        return jsonify(snowflake_connection_error)
    
    sf = connection.cursor()
    
    try:
        all_vaults = get_all_vaults(connection.cursor())
    
        if vault and vault in all_vaults:
                
            query = f"""
                select v.vault, v.ilk, round(v.collateral, 4) as collateral, round(v.principal, 4) as principal, v.paid_fees, round(v.art / power(10, 18) * r.rate / power(10, 27), 6) as debt, 
                    round(debt - v.principal, 4) as accrued_fees,
                    case when debt = 0 then null else round(100 * v.collateral * p.osm_price / debt, 4) end as collateralization, p.osm_price, p.mkt_price,
                    m.ratio, 
                    case when collateral = 0 then null else round(ratio * debt / collateral, 4) end as liquidation_price,
                    case when ratio = 0 then null else round(greatest(collateral * osm_price / ratio - debt, 0), 4) end as available_debt,
                    case when osm_price = 0 then null else round(greatest(collateral - ratio * debt / osm_price, 0), 4) end as available_collateral, 
                    v.urn, v.block_created, to_varchar(v.time_created, 'YYYY-MM-DD HH:MI:SS') as time_created
                from
                (select vault, ilk, urn, sum(dart) as art,
                    round(sum(dcollateral), 6) as collateral, 
                    round(sum(dprincipal), 6) as principal, 
                    round(sum(dfees), 6) as paid_fees,
                    min(block) as block_created, min(timestamp) as time_created
                from mcd_public.public.vaults
                where vault = '{vault}' and block <= {block}
                group by vault, ilk, urn) v join
                (select distinct ilk, last_value(rate) over (partition by ilk order by block) as rate
                from mcd_public.internal.rates
                where block <= {block}) r on v.ilk = r.ilk join
                (select distinct token, coalesce(last_value(osm_price) over (partition by token order by block), 1) as osm_price, 
                                last_value(mkt_price) over (partition by token order by block) as mkt_price
                from mcd_public.internal.prices
                where block <= {block}) p on (split(v.ilk, '-')[0] = p.token or split(v.ilk, '-')[1] = p.token) join
                (select distinct ilk, last_value(mat) over (partition by ilk order by block) as ratio 
                from mcd_public.internal.mats
                where block <= {block}) m on v.ilk = m.ilk;"""
            
            sf_dict = connection.cursor(snowflake.connector.DictCursor)
    
            try:
                vault_status = sf_dict.execute(query).fetchone()
                if vault_status:
                    vault_status_response = dict((k.lower(), v) for k, v in vault_status.items())
                    vault_status_response['block'] = block
                else:
                    vault_status_response = f"""Vault {vault} was created later than block {block}"""

            except Exception as e:
                return jsonify(dict(
                    message=dict(vault_state_for_block=str(e)),
                    status='failure'))
            
            return jsonify(dict(
                    message=dict(vault_state_for_block=vault_status_response),
                    status='success'
                ))
        
        else:

            return jsonify(dict(
                message='Vault {} does not exist.'.format(vault),
                status='failure'))
        
    except Exception as e:
        return jsonify(dict(
            message=str(e),
            status='failure'))
    finally:
        if not sf.is_closed():
            sf.connection.close()