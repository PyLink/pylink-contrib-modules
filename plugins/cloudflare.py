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

cf_add_parser = utils.IRCParser()
cf_add_parser.add_argument("name")
cf_add_parser.add_argument("content")
# TODO: autodetect the record type; it's simple enough to do...
cf_add_parser.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"], required=True)
cf_add_parser.add_argument("-l", "--ttl", type=int, default=1)
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
    args = cf_add_parser.parse_args(args)

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

utils.add_cmd(cf_add, "cf-add", featured=True)

cf_show_parser = utils.IRCParser()
cf_show_parser.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"])
cf_show_parser.add_argument("subdomain", nargs='?')
cf_show_parser.add_argument("-c", "--content")
cf_show_parser.add_argument("-o", "--order", default="type")
def cf_show(irc, source, args):
    """[<subdomain>] [--type <type>] [--content <record content>] [--order <sort order>]

    Searches CloudFlare DNS records. The following options are supported:

    -t / --type : Type of record

    -c / --content : Content of record / IP

    -o / --order : Order by ... (type, content, name)
    """
    permissions.checkPermissions(irc, source, ['cloudflare.cf-show'])
    cf = get_cf()
    zone = conf.conf.get("cloudflare", {}).get('target_zone')
    if not zone:
        irc.error("No target zone ID specified! Configure it via a 'cloudflare::target_zone' option.")
        return

    args = cf_show_parser.parse_args(args)

    body = {
        "order": args.order,
        "type":  args.type
    }

    if args.subdomain:
        # Add the domain to the lookup name so that less typing is needed.
        base_domain = cf.zones.get(zone)['result']['name']
        body["name"] = '%s.%s' % (args.subdomain, base_domain)
    if args.content:
        body["content"] = args.content

    response = cf.zones.dns_records.get(zone, params=body)

    count = response.get("result_info", {}).get("count", 0)
    result = response.get("result", [])
    irc.reply("Found %d records" % count, private=False)
    for res in result:
        irc.reply("\x02Name\x02: %(name)s \x02Content\x02: %(content)s" % res, private=False)
        irc.reply("\x02ID\x02: %(id)s" % res, private=False)
utils.add_cmd(cf_show, "cf-show", featured=True)

cf_rem_parser = utils.IRCParser()
cf_rem_parser.add_argument("id")
def cf_rem(irc, source, args):
    """<record id>

    Removes a record by its ID (Use the "rr-show" command to display a list of records).
    """
    permissions.checkPermissions(irc, source, ['cloudflare.cf-rem'])
    zone = conf.conf.get("cloudflare", {}).get('target_zone')
    cf = get_cf()
    if not zone:
        irc.error("No target zone ID specified! Configure it via a 'cloudflare::target_zone' option.")
        return
    args = cf_rem_parser.parse_args(args)

    response = cf.zones.dns_records.delete(zone, args.id)
    result = response["result"]
    irc.reply("Record Removed. ID: %(id)s" % result, private=False)
utils.add_cmd(cf_rem, "cf-rem", featured=True)
