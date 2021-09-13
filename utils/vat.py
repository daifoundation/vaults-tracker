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

from connectors.chain import chain

vat_address = '0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B'
vat_abi = '''
            [{"constant":true,"inputs":[],"name":"debt",
            "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
            "payable":false,"stateMutability":"view","type":"function"},
            {"constant":true,"inputs":[],"name":"Line",
            "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
            "payable":false,"stateMutability":"view","type":"function"},
            {"constant":true,"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
            "name":"ilks","outputs":[{"internalType":"uint256","name":"Art","type":"uint256"},
            {"internalType":"uint256","name":"rate","type":"uint256"},
            {"internalType":"uint256","name":"spot","type":"uint256"},
            {"internalType":"uint256","name":"line","type":"uint256"},
            {"internalType":"uint256","name":"dust","type":"uint256"}],
            "payable":false,"stateMutability":"view","type":"function"},
            {"constant":true,"inputs":[{"name":"address","type":"address"}],
            "name":"dai","outputs":[{"name":"dai","type":"uint256"}],
            "payable":false,"stateMutability":"view","type":"function"},
            {"constant":true,"inputs":[{"name":"address","type":"address"}],
            "name":"sin","outputs":[{"name":"sin","type":"uint256"}],
            "payable":false,"stateMutability":"view","type":"function"}]
          '''


# read ilk parameters directly form the chain
def get_ilk_data(ilk):

    try:
        vat = chain.eth.contract(address=vat_address, abi=vat_abi)
        ilk_bytes = ('0x' + ilk.encode('utf-8').hex()).ljust(66, '0')
        Art, rate, _, line, _ = vat.functions.ilks(ilk_bytes).call()

    except Exception as e:
        print(e)
        Art = rate = line = 0

    return Art, rate, line


# read VAT parameters directly from the chain
def get_vat_data():

    try:
        vat = chain.eth.contract(address=vat_address, abi=vat_abi)
        Line = vat.functions.Line().call() / 10 ** 45

    except Exception as e:
        print(e)
        Line = 0

    return Line
