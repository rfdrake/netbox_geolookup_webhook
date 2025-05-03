Notes:

The environment file for docker is a bit different than a file for shell.  If
you're testing this outside of docker you can convert the file to a bash
environment by running something like this:

    sed 's/^/export /;s/=\(.*\)$/="\1"/' geolookup.env > /tmp/f
    source /tmp/f

# Installation

Copy the lines from the docker-compose.stub.yaml into your netbox project.

# TODO

Bing geocoder is going away soon.   We could switch to nominatim
(openstreetmaps), but we need
something that is frequently updated, because we might have a brand new
building with an address they haven't seen yet.

We could directly implement a lookup using Azure maps API (which I haven't
found a library that supports it yet), but it means we're stuck with azure.

Maybe we should just do our best with an offline db, or with openstreetmap?

# other python modules

The geocoder python module is unmaintained.  Geopy is undermaintained and not
ideal (no first party caching support like requests-cache).  "whereabouts"
uses an offline db.

For nominatim we need to implement a rate limit.  I'm thinking of doing that
with RQ.
