#!/usr/bin/env python3

from geopy.geocoders import Nominatim
import sys
import json
import os
import requests
import requests_cache
# expire cache after around 1yr
requests_cache.install_cache('geocoder', backend='sqlite', expire_after=31536000)
import urllib3
import pynetbox
import time

import os
from functools import wraps
from flask import Flask, request, jsonify

# I think this is pretty much pointless because we're running inside docker
# without an exposed port, but I've already implemented it so I'm leaving it.
WEBHOOK_AUTH_KEY = os.environ["WEBHOOK_TOKEN"]

# I need to rewrite this with a queue system to accept the lookup request,
# then later execute the job and post back to netbox.  This way I can rate
# limit the job requests so that we don't anger Nominatim

nb = pynetbox.api(url=os.environ['NETBOX_URL'], token=os.environ['NETBOX_TOKEN'])
nb.http_session.verify = False
urllib3.disable_warnings()

def geolookup(data):
    try:
        site = nb.dcim.sites.get(id=data['id'])
        print(site.latitude, site.longitude, site.time_zone)
        if not site.physical_address:
          return {"message": f"not changing {site.name} because physical_address is blank."}, 200
        modified = False
        if not site.latitude or not site.longitude:
            geolocator = Nominatim(user_agent="netbox_geolookup_webhook.py")
            results = geolocator.geocode(site.physical_address)
            site.latitude = round(results.latitude,6)
            site.longitude = round(results.longitude,6)
            modified = True
        if not site.time_zone:
            url = f"https://api.geotimezone.com/public/timezone?latitude={site.latitude}&longitude={site.longitude}"
            tz = requests.get(url)
            results = tz.json()
            site.time_zone = results['iana_timezone']
            modified = True
        if modified:
            site.save()
            time.sleep(10)
            return {"message": f"added lat/lng ({site.latitude}/{site.longitude}) ({site.time_zone}) for site {site.name} ({site.id})"}, 200
        else:
            return {"message": f"{site.name} ({site.id}) already has the information needed."}
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
