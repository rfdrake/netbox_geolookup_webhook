# Overview:

This is a webhook used for netbox which will perform a geolookup when a site
is created or updated.

# Notes:

The environment file for docker is a bit different than a file for shell.  If
you're testing this outside of docker you can convert the file to a bash
environment by running something like this:

    eval $(sed 's/^/export /;s/=\(.*\)$/="\1"/' geolookup.env)

# Installation

Copy the lines from the docker-compose.stub.yaml into your netbox project's
docker-compose.override.yml.

or

With docker-compose 2.20.0 and later, you can use includes:

```
include:
    - ../geolookup_webhook/docker-compose.stub.yml
```

# Setting up Netbox with the Webhook

Under "Admin|Users"
Add a user for "webhooks_api" if you wish, you can pick another name that
suits your purpose.

Under "Admin|API Tokens"
Create an API token under the webhooks_api user (or whichever user you prefer)
then update geolookup.env to assign the token to NETBOX_TOKEN

Under "Operations|Event Rules|Webhooks"

Name: Geolookup Webhook
Payload URL: http://geolookup-webhook:5000/webhook
Secret: This should match your WEBHOOK_SECRET in your geolookup.env file. You
can use "openssl rand -base64 32" to generate this.

Under "Operations|Event Rules|Add"

Name: Geolookup Webhook
Object Types: DCIM > Site
Event Types: Object created, Object updated
Action Type: Webhook
Webhook: Geolookup Webhook

# Running install.py instead of the above

If you have installed pynetbox, you can run the install.py script to edit
netbox and create the needed webhook, users and permissions.

Because this script directly writes to netbox as an admin user, I advise you to check it before
running it.

```
python3 -m venv geolookup_webhook_install
source geolookup_webhook_install/bin/activate
pip install pynetbox
./install.py --netbox-url http://localhost:8080 --netbox-token xxxx
```

# Note about the webhook token's user:

You will generally want this to be a role account because the token will be
making changes to netbox, like updating lattitude and longitude. When this
happens, netbox will fire another webhook because the site was updated. We
need to ignore these updates or there is a possibility of a loop.

There has been talk about making a better method to avoid loops in netbox, but
currently I don't think there is a way to avoid the second webhook call right
now.

Setting the WEBHOOK_USER allows us to watch for updates from that user and
ignore them. You can either set this as an environment variable in
geolookup.env, or let the script figure it out by querying netbox.
