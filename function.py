#!/usr/bin/env python3

from geopy.geocoders import Nominatim
import sys
import json
import os
import hmac
import hashlib
import requests
import pynetbox
import time
import threading
import logging
from flask import Flask, request, abort
from functools import wraps

app = Flask(__name__)

logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get('LOGLEVEL','INFO').upper(),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

USER_AGENT = "Netbox Geolookup Webhook v1.2"

geolocator = Nominatim(user_agent=USER_AGENT)

# lock needed for the rate limiter
lock = threading.Lock()
last_request_time = 0

# Changed this to use X-Hook-Signature from netbox
WEBHOOK_AUTH_KEY = os.environ["WEBHOOK_TOKEN"].encode('utf-8')

# this is the user that the NETBOX_TOKEN was created as.  Which means we want
# to ignore any webhooks that were fired by that user because they might be
# because of an update from a webhook.  This is to prevent loops when we run
# site.save()
WEBHOOK_USER = os.environ["WEBHOOK_USER"]

nb = pynetbox.api(url=os.environ['NETBOX_URL'], token=os.environ['NETBOX_TOKEN'])
if os.environ.get('NETBOX_DISABLE_SSL_WARNINGS', False):
    import urllib3
    nb.http_session.verify = False
    urllib3.disable_warnings()

# This is a really stupid way to go about this, and requires that we run
# "gunicorn -w 1" in order to only have 1 worker.  But considering the amount
# of webhooks that will (probably) fire, these should be fine constraints.  If
# it gets worse later we can rewrite this with a redis queue and a worker.
#
# I've also set the rate limit to every 2 seconds because 1/s is too tight
# final note: The request_cache caches the lookup, but the rate limit is still
# used.  We should make it so the rate limit only applies if a lookup was not
# cached.
def rate_limit_lookup(address):
    global last_request_time
    with lock:
        now = time.monotonic()
        wait = max(0, 2 - (now - last_request_time))
        if wait > 0:
            logger.debug(f"Rate limit applied for {wait}")
            time.sleep(wait)
        last_request_time = time.monotonic()

        logger.info(f"Address is {address}")
        return geolocator.geocode(address, timeout=10)

# this returns nothing because no error changes things. If we needed netbox to
# retry a queue then we might trap and return errors from here.
def geolookup(data):
    try:
        # do these two if checks with the provided data rather than doing a lookup.
        if data['latitude'] and data['longitude'] and data['time_zone']:
            logger.info(f"{data['name']} ({data['id']}) already has the information needed.")
            return

        if not data['physical_address']:
            logger.warning(f"not changing {data['name']} because physical_address is blank.")
            return

        site = nb.dcim.sites.get(id=data['id'])
        logger.info(f"Existing {site} ({site.id}): lat {site.latitude}, lng {site.longitude}, tz {site.time_zone}")
        modified = False
        if not site.latitude or not site.longitude:
            results = rate_limit_lookup(site.physical_address)
            site.latitude = round(results.latitude,6)
            site.longitude = round(results.longitude,6)
            logger.info(f"Updated lat {site.latitude}, lng {site.longitude}")
            modified = True
        if not site.time_zone:
            url = f"https://api.geotimezone.com/public/timezone?latitude={site.latitude}&longitude={site.longitude}"
            tz = requests.get(url)
            results = tz.json()
            site.time_zone = results['iana_timezone']
            logger.info(f"Updated tz: {site.time_zone}")
            modified = True
        if modified:
            site.save()
            logger.info(f"added lat/lng ({site.latitude}/{site.longitude}) ({site.time_zone}) for site {site.name} ({site.id})")
    except Exception as e:
        logger.warning(f"Exception in geolookup {str(e)}")

def require_authorization(view_func):
    @wraps(view_func)
    def _require_authorization(*args, **kwargs):
        headers = request.headers
        hmac_header = headers.get("X-Hook-Signature").encode('utf-8')
        request_data = request.data
        digest = hmac.new(WEBHOOK_AUTH_KEY, request_data, hashlib.sha512)
        computed_hmac = digest.hexdigest().encode('utf-8')

        if not hmac.compare_digest(computed_hmac, hmac_header):
            return abort(401)
        logger.debug("Webhook signature validation succeeded.")
        return view_func(*args, **kwargs)

    return _require_authorization


@app.route("/webhook", methods=["POST"])
@require_authorization
def webhook():
    logger.debug(f"request username = {request.json['username']}")
    if request.json['username'] == WEBHOOK_USER:
        logger.warning(f"Not running webhook because it was triggered by a WEBHOOK user (possible update loop).")
    else:
        geolookup(request.json['data'])
    return {}, 200

if __name__ == "__main__":
    import sys
    for id in sys.argv[1:]:
        with app.test_request_context():
               geolookup({ 'id': id })
