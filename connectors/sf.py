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

# Token FLow connector for SnowFlake

import snowflake.connector
from config import SNOWFLAKE_CONNECTION


def sf_connect():
    connection = snowflake.connector.connect(**SNOWFLAKE_CONNECTION, client_session_keep_alive=True)
    cursor = connection.cursor()
    return cursor


def sf_disconnect(cursor):
    cursor.connection.close()


sf = sf_connect()
