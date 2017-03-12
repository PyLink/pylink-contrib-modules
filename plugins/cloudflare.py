"""
cloudflare.py: Manipulates DNS via CloudFlare's API.
"""

import pylinkirc
from pylinkirc import utils, world, conf
from pylinkirc.coremods import permissions
from pylinkirc.log import log

import CloudFlare
import json

def get_cf():
    """Fetches an API instance from python-cloudflare"""
    cf_conf = conf.conf.get("cloudflare", {})
    email = cf_conf.get("api_email", "")
    key = cf_conf.get("api_key", "")

    return CloudFlare.CloudFlare(email=email, token=key, raw=True)

rr_add = utils.IRCParser()
rr_add.add_argument("name")
rr_add.add_argument("content")
# TODO: autodetect the record type; it's simple enough to do...
rr_add.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"], required=True)
rr_add.add_argument("-l", "--ttl", type=int, default=1)
def cf_add(irc, source, args):
    """<subdomain> <address> --type <type> [--ttl <ttl>]

    Adds a record to a RR group of records. The following options are supported:

    -t / --type : Type of Record (A, AAAA, CNAME)

    -l / --ttl : 'time to live' of record (If not given, ttl is made automatic)
    """
    permissions.checkPermissions(irc, source, ['cloudflare.add'])
    cf = get_cf()
    zone = conf.conf.get("cloudflare", {}).get('target_zone')
    if not zone:
        irc.error("No target zone ID specified! Configure it via a 'cloudflare::target_zone' option.")
        return
    args = rr_add.parse_args(args)

    body = {
        "type":    args.type,
        "name":    args.name,
        "content": args.content,
        "ttl":     args.ttl
    }

    response = cf.zones.dns_records.post(zone, data=body)
    result = response.get("result", [])
    irc.reply("Record Added. %(name)s as %(content)s" % result, private=False)
    irc.reply("Record ID: %(id)s" % result, private=False)

utils.add_cmd(cf_add, "rr-add", featured=True)

rr_show = utils.IRCParser()
rr_show.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"])
rr_show.add_argument("-n", "--name")
rr_show.add_argument("-c", "--content")
rr_show.add_argument("-o", "--order", default="type")
def cf_show(irc, source, args):
    """[<options>]

    Searches CloudFlare DNS records. The following options are supported:

    -n / --name : Name / Subdomain

    -t / --type : Type of record

    -c / --content : Content of record / IP

    -o / --order : Order by ... (type, content, name)
    """
    permissions.checkPermissions(irc, source, ['cloudflare.show'])
    cf = get_cf()
    zone = conf.conf.get("cloudflare", {}).get('target_zone')
    if not zone:
        irc.error("No target zone ID specified! Configure it via a 'cloudflare::target_zone' option.")
        return

    args = rr_show.parse_args(args)

    body = {
        "order": args.order,
        "type":  args.type
    }

    if args.name:
        body["name"] = args.name
    if args.content:
        body["content"] = args.content

    response = cf.zones.dns_records.get(zone, params=body)

    count = response.get("result_info", {}).get("count", 0)
    result = response.get("result", [])
    irc.reply("Found %d records" % count, private=False)
    for res in result:
        irc.reply("\x02Name\x02: %(name)s \x02Content\x02: %(content)s" % res, private=False)
        irc.reply("\x02ID\x02: %(id)s" % res, private=False)
utils.add_cmd(cf_show, "rr-show", featured=True)

rr_rem = utils.IRCParser()
rr_rem.add_argument("id")
def cf_rem(irc, source, args):
    """<record id>

    Removes a record by its ID (Use the "rr-show" command to display a list of records).
    """
    permissions.checkPermissions(irc, source, ['cloudflare.rem'])
    zone = conf.conf.get("cloudflare", {}).get('target_zone')
    cf = get_cf()
    if not zone:
        irc.error("No target zone ID specified! Configure it via a 'cloudflare::target_zone' option.")
        return
    args = rr_rem.parse_args(args)

    response = cf.zones.dns_records.delete(zone, args.id)
    result = response["result"]
    irc.reply("Record Removed. ID: %(id)s" % result, private=False)
utils.add_cmd(cf_rem, "rr-rem", featured=True)
