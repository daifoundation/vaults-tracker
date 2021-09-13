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

from snowflake.connector.cursor import SnowflakeCursor
from connectors.sf import sf, sf_disconnect
import pandas as pd
from flask import request
from connectors.chain import chain
from web3 import Web3
import requests
import json


def safe_max(sequence):
    if sequence:
        return max(sequence)
    else:
        return 0


def vault_check(vault_id):
    return vault_id.isnumeric() or (len(vault_id) == 10 and vault_id[:2] == '0x') or vault_id == 'MIGRATION'


# asynchronous queries execution using Snowflake
def async_queries(sf, all_queries):

    started_queries = []
    for i in all_queries:
        sf.execute(i['query'])
        started_queries.append(dict(
            qid=sf.sfqid,
            id=i['id']
        ))

    all_results = {}
    limit = len(started_queries)
    control = 0

    while limit != control:

        for i in started_queries:

            if i['id'] not in all_results.keys():

                try:
                    check_results = sf.execute("""
                        SELECT *
                        FROM table(result_scan('%s'))
                        """ % i['qid'])

                    if isinstance(check_results, SnowflakeCursor):
                        df = check_results.fetch_pandas_all()
                        result = df.where(pd.notnull(df), None).values.tolist()
                        all_results[i['id']] = result

                except Exception as e:
                    print(str(e))

        control = len(all_results.keys())

    return all_results


def get_last_refresh(sf):

    query = """
        SELECT
            DISTINCT LAST_BLOCK, LAST_TIME
        FROM MCD_PUBLIC.PUBLIC.CURRENT_VAULTS"""
    

    results = sf.execute(query).fetchone()

    return results[0], results[1]


def get_oracle_address(ilk):

    # ilk transformation
    if ilk in ('PSM', 'USDC', 'TUSD', 'USDT', 'SAI', 'GUSD', 'PAXUSD'):
        return None

    source = 'https://changelog.makerdao.com/releases/mainnet/active/contracts.json'

    get_changelog = requests.get(source)
    changelog = json.loads(get_changelog.text)

    if 'PIP_' + ilk in  changelog.keys():
        return changelog['PIP_' + ilk]
    else:
        return None


def get_LPOracle_price(address):

    next_price = 0
    # abi = """[{"inputs":[],"name":"nxt","outputs":[{"internalType":"uint128","name":"val","type":"uint128"},{"internalType":"uint128","name":"has","type":"uint128"}],"stateMutability":"view","type":"function"},
    #     {"inputs":[],"name":"cur","outputs":[{"internalType":"uint128","name":"val","type":"uint128"},{"internalType":"uint128","name":"has","type":"uint128"}],"stateMutability":"view","type":"function"}]"""

    # pip_oracle = chain.eth.contract(address=Web3.toChecksumAddress(address), abi=abi)
    # next_price = pip_oracle.functions.nxt().call()[0] / 10 ** 18
    x = chain.eth.getStorageAt(account=Web3.toChecksumAddress(address), position=4).hex()
    next_price = int(x[2:][32:], 16) / 10 ** 18

    return next_price


def get_current_LPOracle_price(address):

    current_price = 0
    # abi = """[{"inputs":[],"name":"nxt","outputs":[{"internalType":"uint128","name":"val","type":"uint128"},{"internalType":"uint128","name":"has","type":"uint128"}],"stateMutability":"view","type":"function"},
    #     {"inputs":[],"name":"cur","outputs":[{"internalType":"uint128","name":"val","type":"uint128"},{"internalType":"uint128","name":"has","type":"uint128"}],"stateMutability":"view","type":"function"}]"""

    # pip_oracle = chain.eth.contract(address=Web3.toChecksumAddress(address), abi=abi)
    # current_price = pip_oracle.functions.cur().call()[0] / 10 ** 18
    x = chain.eth.getStorageAt(account=Web3.toChecksumAddress(address), position=3).hex()
    current_price = int(x[2:][32:], 16) / 10 ** 18

    return current_price


def get_DSValue_price(address):

    abi = """[{"constant":true,"inputs":[],"name":"read","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"}]"""
    
    pip_oracle = chain.eth.contract(address=Web3.toChecksumAddress(address), abi=abi)
    nxt = pip_oracle.functions.read().call()
    next_price = int.from_bytes(nxt, byteorder='big') / 10 ** 18

    return next_price


def get_current_DSValue_price(address):

    abi = """[{"constant":true,"inputs":[],"name":"read","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"}]"""
    
    pip_oracle = chain.eth.contract(address=Web3.toChecksumAddress(address), abi=abi)
    nxt = pip_oracle.functions.read().call()
    next_price = int.from_bytes(nxt, byteorder='big') / 10 ** 18

    return next_price


def get_OSM_price(address):

    nxt_price = chain.eth.getStorageAt(Web3.toChecksumAddress(address), 4).hex()
    next_price = int(nxt_price[34:], 16) / 10 ** 18

    return next_price


def get_current_OSM_price(address):

    cur_price = chain.eth.getStorageAt(Web3.toChecksumAddress(address), 3).hex()
    current_price = int(cur_price[34:], 16) / 10 ** 18

    return current_price


def get_next_price_from_chain(address, type):
    
    if type == 'coin':
        current_price = get_current_OSM_price(address)
        next_price = get_OSM_price(address)
    elif type == 'stablecoin':
        current_price = get_DSValue_price(address)
        next_price = get_DSValue_price(address)
    elif type == 'lp':
        current_price = get_current_LPOracle_price(address)
        next_price = get_LPOracle_price(address)
    else:
        current_price = 0
        next_price = 0

    return current_price, next_price
