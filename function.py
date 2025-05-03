# https://stackoverflow.com/questions/77657489/using-python-to-connect-to-sharepoint-via-app-sign-in-client-id-secret-tenan

import geocoder
import sys
import json
import os
import requests
import requests_cache
# expire cache after around 1yr
requests_cache.install_cache('geocoder', backend='sqlite', expire_after=31536000)
import urllib3
import pynetbox

import os
from functools import wraps
from flask import Flask, request, jsonify

WEBHOOK_AUTH_KEY = os.environ["WEBHOOK_TOKEN"]

nb = pynetbox.api(url=os.environ['NETBOX_URL'], token=os.environ['NETBOX_TOKEN'])
nb.http_session.verify = False
urllib3.disable_warnings()

def geolookup(data):
    try:
        site = nb.dcim.sites.get(id=data['id'])
        if not site.physical_address:
          return {"message": f"not adding {site.name} because physical_address is blank."}, 200
        if not site.latitude or not site.longitude:
            g = geocoder.bing(site.physical_address, key=os.environ.get('BING_GEOCODER_KEY'))
            results = g.json
            site.latitude = round(results['lat'],6)
            site.longitude = round(results['lng'],6)
        if not site.time_zone:
            url = f"https://api.geotimezone.com/public/timezone?latitude={site.latitude}&longitude={site.longitude}"
            tz = requests.get(url)
            results = tz.json()
            site.time_zone = results['iana_timezone']
        site.save()
        return {"message": f"added lat/lng ({site.latitude}/{site.longitude}) ({site.time_zone}) for site {site.name}"}, 200
    except Exception as e:
        return {"message": str(e)}, 400

app = Flask(__name__)

def require_authorization(view_func):
    @wraps(view_func)
    def _require_authorization(*args, **kwargs):
        headers = request.headers
        auth = headers.get("Authorization")
        if auth != WEBHOOK_AUTH_KEY:
            return jsonify({"message": "ERROR: Unauthorized"}), 401
        return view_func(*args, **kwargs)

    return _require_authorization


@app.route("/webhook", methods=["POST"])
@require_authorization
def webhook():
    return jsonify(geolookup(request.json['data']))

if __name__ == "__main__":
    import sys
    data = { 'id': sys.argv[1] }
    with app.test_request_context():
           response = geolookup(data)
           print(response)
