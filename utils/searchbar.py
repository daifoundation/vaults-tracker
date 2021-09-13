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

from flask import redirect, request, render_template


def run_search(search_input):

    if search_input and search_input != '':
        return redirect(request.host_url + "vault/" + search_input)
    else:
        return render_template(
            'unknown.html',
            object_name='vault',
            object_value="""Please input a valid id""")
