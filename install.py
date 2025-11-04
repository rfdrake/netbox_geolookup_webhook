#!/usr/bin/env python3
import pynetbox
import click
import binascii
import os

# This script needs high level permissions in order to create users, tokens
# and permissions. You can use your "admin" account or another superuser to
# run this if you wish, or you can create all of this yourself rather than
# trusting a script you haven't audited.

# This script isn't idempotent but it probably should be. Running it a second
# time should just change the webhook_secret and new_token values then update
# the existing objects.

@click.command()
@click.option("--netbox-url", envvar="NETBOX_URL", required=True)
@click.option("--netbox-user", type=str)
@click.option("--netbox-password", type=str)
@click.option("--netbox-token", envvar="NETBOX_TOKEN")
@click.option("--verify-ssl", envvar="NETBOX_VERIFY_SSL", is_flag=True, default=True)
@click.option("--webhook-user", envvar="WEBHOOK_USER", default="webhooks_api")
def main(
    netbox_url: str,
    netbox_user: str,
    netbox_password: str,
    netbox_token: str,
    verify_ssl: bool,
    webhook_user: str,
) -> None:

    if not (netbox_token or (netbox_user and netbox_password)):
        raise click.UsageError('Must specify --netbox-token or both --netbox-user and --netbox-password')

    if netbox_token:
        nb = pynetbox.api(url=netbox_url, token=netbox_token)
    else:
        nb = pynetbox.api(url=netbox_url, username=netbox_user, password=netbox_password)

    if not verify:
        nb.http_session.verify = False
        urllib3.disable_warnings()

    # generate the random keys we will need
    new_token = binascii.hexlify(os.urandom(20)).decode()
    webhook_secret = binascii.hexlify(os.urandom(20)).decode()

    # create user
    user = nb.users.users.get(username=webhook_user)
    if not user:
        user = nb.users.users.create({ 'username': webhook_user, 'is_active': True, 'is_staff' False, 'is_superuser': False })

    # create permissions
    # "Webhook Can view users"
    nb.users.permissions.create(name='Webhook can view users', object_types=[ "users.user" ], actions=['view'], users=[ user.id ])
    # "Webhook Can edit sites"
    nb.users.permissions.create(name='Webhook can edit sites', object_types=[ "dcim.site" ], actions=['view','change'], users=[ user.id ])
    # create token for user
    token = nb.users.tokens.create(description='Used by triggered webhooks to post data back to netbox', user=user.id,key=new_token)
    # create webhook
    webhook = nb.extras.webhooks.create(name='Geolookup webhook', secret=webhook_secret, payload_url='http://geolookup-webhook:5000/webhook')
    # create event rule
    nb.extras.event_rules.create(name='Geolookup webhook', object_types=[ "dcim.site" ], event_types=[ "object_created", "object_updated"], action_type="webhook", action_object_type="extras.webhook", action_object_id=webhook.id)

    print("If nothing errored then things should be setup.")
    print("Edit your geolookup.env to look like this:")
    print( dedent(f"""
            NETBOX_TOKEN={new_token}
            WEBHOOK_SECRET={webhook_secret}
            NETBOX_URL=http://netbox:8080
    """))

if __name__ == "__main__":
    main()
