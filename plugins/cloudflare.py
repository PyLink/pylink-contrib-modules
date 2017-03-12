# dns.py: DNS for network
# -*- coding: utf-8 -*-
import pylinkirc
from pylinkirc import utils, world, conf
from pylinkirc.coremods import permissions
from pylinkirc.log import log

import CloudFlare
import json

cf_conf = conf.conf.get("cf", {})
def get_cf():
    
    email = cf_conf.get("email", "")
    key =   cf_conf.get("key", "")
    
    return CloudFlare.CloudFlare(email=email, token=key, raw=True)

rr_add = utils.IRCParser()
rr_add.set_defaults(zone=cf_conf.get("zone", ""))
rr_add.add_argument("name")
rr_add.add_argument("content")
rr_add.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"], required=True)
rr_add.add_argument("-l", "--ttl", type=int)
def cf_add(irc, source, args):
    """<name> <content> <args>
    -t / --type : Type of Record (A, AAAA, CNAME)
    
    -l / --ttl : 'time to live' of record (If not given, ttl is made automatic)
    
    
    Adds a record to a RR group of records
    """
    permissions.checkPermissions(irc, source, ['cloudflare.add'])
    cf = get_cf()
    args = rr_add.parse_args(args)

    body = {
        "type":    args.type,
        "name":    args.name,
        "content": args.content,
    }
    body["ttl"] = args.ttl if args.ttl else 1

    response = cf.zones.dns_records.post(args.zone, data = body)
    irc.reply("Record Added. %(name)s as %(content)s" % result, private=False)
    irc.reply("Record ID: %(id)s" % result, private=False)
utils.add_cmd(cf_add, "rr-add", featured=True)

rr_show = utils.IRCParser()
rr_show.set_defaults(zone=cf_conf.get("zone", "")) 
rr_show.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"])
rr_show.add_argument("-n", "--name")
rr_show.add_argument("-c", "--content")
rr_show.add_argument("-o", "--order", default="type")
def cf_show(irc, source, args):
    """<args>
    -n / --name : Name / Subdomain
    -t / --type : Type of record
    -c / --content : Content of record / IP
    -o / --order : Order by ... (type, content, name)
    —    Search records
    """
    permissions.checkPermissions(irc, source, ['cloudflare.show'])    
    cf = get_cf()
    args = rr_show.parse_args(args)

    body = {
        "order": args.order,
        "type":  args.type
    }

    if args.name:
        body["name"]    = args.name
    if args.content:
        body["content"] = args.content

    response = cf.zones.dns_records.get(args.zone, params = body)

    count = response.get("result_info", {}).get("count", 0)
    result = response.get("result", [])
    irc.reply("Found %d records" % count, private=False)
    for res in result:
        irc.reply("\x02Name\x02: %(name)s \x02Content\x02: %(content)s" % res, private=False)
        irc.reply("\x02ID\x02: %(id)s" % res, private=False)
utils.add_cmd(cf_show, "rr-show", featured=True)

rr_rem = utils.IRCParser()
rr_rem.set_defaults(zone=cf_conf.get("zone", ""))
rr_rem.add_argument("id")
def cf_rem(irc, source, args):
    """<record id>
    Removes a record.
    """
    permissions.checkPermissions(irc, source, ['cloudflare.rem'])
    cf = get_cf()
    args = rr_rem.parse_args(args)

    response = cf.zones.dns_records.delete(args.zone, args.id)
    result = response["result"]
    irc.reply("Record Removed. ID: %(id)s" % result, private=False)
utils.add_cmd(cf_rem, "rr-rem", featured=True)