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

# Token FLow connector for Blockchain node (tested with Parity)

from web3 import Web3
from config import NODE


# basic connection to the blockchain node
def connect_chain(http_hook=None):
    method = 'HTTP'
    provider = Web3.HTTPProvider
    hook = http_hook

    try:
        w3 = Web3(provider(hook, request_kwargs={'timeout': 60}))
        if w3.isConnected():
            print("Connected to %s: %s with latest block %d." % (method, hook, w3.eth.blockNumber))
            return w3
        else:
            print('%s connection to %s failed.' % (method, hook))
            return None
    except Exception as e:
        print("Error while connecting to chain.")
        print(e)


chain = connect_chain(NODE)
