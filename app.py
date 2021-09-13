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

from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPTokenAuth, HTTPBasicAuth
from datetime import datetime
import atexit
from werkzeug.security import generate_password_hash, check_password_hash

from connectors.sf import sf, sf_disconnect
from views.main_view import main_page_view, main_page_data
from views.vault_view import vault_page_view, vault_page_data
from views.collateral_view import collateral_page_view, collateral_page_data
from views.owner_view import owner_page_view, owner_page_data

from flask_talisman import Talisman

from config import API_TOKENS
import api

from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)
app.secret_key = 'YJJLM9W37V7A83OOC2VX'
app.config['JSON_SORT_KEYS'] = False
app.config['DEBUG'] = True
csrf = CSRFProtect(app)


SELF = "'self'"
UNSAFE_INLINE = "'unsafe-inline'"
UNSAFE_EVAL = "'unsafe-eval'"
talisman = Talisman(
    app,
    force_https=False,
    content_security_policy={
        'default-src': [
            SELF,
        ],
        'img-src': [
            '*',
            'data:'
        ],
        'script-src': [
            SELF,
            UNSAFE_EVAL,
            UNSAFE_INLINE,
            'https://cdn.plot.ly/',
            'https://cdn.datatables.net/',
            'https://cdnjs.cloudflare.com/',
            'https://code.jquery.com/'

        ],
        'style-src': [
            SELF,
            UNSAFE_INLINE,
            'https://cdnjs.cloudflare.com/',
        ],
        'font-src': [
            SELF,
            'https://cdnjs.cloudflare.com/'
        ]
    },
    content_security_policy_nonce_in=['script-src'],
    feature_policy={
        'geolocation': '\'none\'',
    }
)

login_auth = HTTPBasicAuth()
auth = HTTPTokenAuth(scheme='Bearer')

users = {
    "maker": generate_password_hash("DAO"),
    "beta": generate_password_hash("StableCoin")
}


# LOGIN authorization
@login_auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username


# API authorization
@auth.verify_token
def verify_token(token):
    if 'access_token' in request.args.to_dict().keys():
        if token in API_TOKENS or request.args.to_dict()['access_token'] in API_TOKENS:
            return True
    else:
        if token in API_TOKENS:
            return True


# API endpoints --------------------------------------------

@app.route("/api/last_block", methods=['GET'])
@auth.login_required
def api_get_last_block():
    return api.get_last_block()


@app.route("/api/last_time", methods=['GET'])
@auth.login_required
def api_get_last_time():
    return api.get_last_time()


@app.route("/api/vault_history/<vault>", methods=['GET'])
@auth.login_required
def api_get_vault_history(vault):
    return api.get_vault_history(vault, request)


@app.route("/api/vault_state/<vault>", methods=['GET'])
@auth.login_required
def api_get_vault_state(vault):
    return api.get_vault_state(vault)


@app.route("/api/vaults_list", methods=['GET'])
@auth.login_required
def api_get_filter_vaults():
    return api.get_filtered_vaults_list(request)


@app.route("/api/collaterals", methods=['GET'])
@auth.login_required
def api_get_collaterals():
    return api.get_ilks_state(request)


@app.route("/api/vault_state_for_block/<vault>/<block>", methods=['GET'])
@auth.login_required
def api_get_vault_state_for_block(vault, block):
    return api.get_vault_state_for_block(vault, block)


# HTML endpoints -------------------------------------------


@app.errorhandler(404)
def page_not_found(error):
   return render_template('404.html', title = '404'), 404


@app.errorhandler(500)
def page_not_found(error):
   return render_template('500.html', title = '500'), 500


@app.route('/', methods=['GET', 'POST'])
def main_page():
    return main_page_view(sf)


@app.route('/vault/<vault_id>', methods=['GET', 'POST'])
def vault_page(vault_id):
    return vault_page_view(sf, vault_id)


@app.route('/collateral/<collateral_id>',  methods=['GET', 'POST'])
def collateral_page(collateral_id):
    return collateral_page_view(sf, collateral_id.upper())


@app.route('/owner/<owner_id>',  methods=['GET', 'POST'])
def owner_page(owner_id):
    return owner_page_view(sf, owner_id.lower())


@app.route('/tos')
def tos_page():
    return render_template('tos.html', refresh=datetime.utcnow())


# DATA endpoints -------------------------------------------

@app.route("/data/main", methods=["GET"])
def get_main_page_data():
    dataset = main_page_data(sf)
    return jsonify(dataset)


@app.route("/data/vault/<vault_id>", methods=["GET"])
def get_vault_page_data(vault_id):
    dataset = vault_page_data(sf, vault_id)
    return jsonify(dataset)


@app.route("/data/collateral/<collateral_id>", methods=["GET"])
def get_collateral_page_data(collateral_id):
    dataset = collateral_page_data(sf, collateral_id)
    return jsonify(dataset)


@app.route("/data/owner/<owner_id>", methods=["GET"])
def get_owner_page_data(owner_id):
    dataset = owner_page_data(sf, owner_id)
    return jsonify(dataset)


# cleanup tasks

def cleanup_task():
    if not sf.is_closed():
        sf_disconnect(sf)
        print('SF connection closed.')


atexit.register(cleanup_task)


if __name__ == '__main__':
    app.run(debug=True)
