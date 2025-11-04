# Overview:

This is a webhook used for netbox which will perform a geolookup when a site
is created or updated.

# Notes:

The environment file for docker is a bit different than a file for shell.  If
you're testing this outside of docker you can convert the file to a bash
environment by running something like this:

    eval $(sed 's/^/export /;s/=\(.*\)$/="\1"/' geolookup.env)

# Installation

Copy the lines from the docker-compose.stub.yaml into your netbox project.

or

With docker-compose 2.20.0 and later, you can use includes:

```
include:
    - ../geolookup_webhook/docker-compose.stub.yml
```

Once this is done you'll need to restart docker and then activate the webhook
in netbox.

Under "Admin|Users"
Add a user for "webhooks_api" if you wish

Under "Admin|API Tokens"
Create an API token under the webhooks_api user (or whichever user you prefer)
then update geolookup.env to assign the token to NETBOX_TOKEN

Under "Operations|Event Rules|Webhooks"

Name: Geolookup Webhook
Payload URL: http://geolookup-webhook:5000/webhook
Secret: This should match your WEBHOOK_TOKEN in your geolookup.env file. You
can use "openssl rand -base64 32" to generate this.

Under "Operations|Event Rules|Add"

Name: Geolookup Webhook
Object Types: DCIM > Site
Event Types: Object created, Object updated
Action Type: Webhook
Webhook: Geolookup Webhook

# Note about WEBHOOK_USER

When you create the geolookup.env file you need to supply a NETBOX_TOKEN
value. This is created inside netbox and attached to a user. In my case I made
a special user called "webhooks_api" and gave it a token.

You will generally want this to be a role account because the token will be
making changes to netbox, like updating lattitude and longitude. When this
happens, netbox will fire another webhook because the site was updated. We
need to ignore these updates or there is a possibility of a loop.

Setting the WEBHOOK_USER allows us to watch for updates from that user and
ignore them.
