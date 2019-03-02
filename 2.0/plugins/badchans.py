"""
badchans.py - Kills unopered users when they join specified channels and optionally reports them to DNSBLs.
"""

'''
Configuration example:

badchans:
    # Configurable list of hosts to exempt. Opers, configured ulines, and non-global addresses
    # (e.g. localhost, 10.x.x.x) are automatically exempt.
    exempt_hosts:
        - "*!*@some.host"
        - "*!*@1.2.3.4"

    # Specify API keys for DroneBL and DNSBL.im to automatically submit to them. If any of these are missing, submission
    # to that blacklist will be automatically disabled.
    dnsblim_key: "123456"
    dronebl_key: "abcdef"

    # The DNSBL submission comment to use. Defaults to the value in DEFAULT_DNSBL_REASON below.
    #dnsbl_reason: "You did the unspeakable!"

    # Max threads count for DNSBL submission (defaults to 5)
    #max_threads: 5

servers:
    net1:
        # When anyone joins a channel matching these, they will be killed and (optionally) reported to DNSBLs.
        # Note that this does not create any channels automatically (e.g. in /list), so you'll want to either
        # use a custom module to fake /list replies or create the channels yourself.

        # Alternatively, PyLink 2.0.2+ users can use PyLink to keep these channels open by adding them to
        # the "channels" config variable and enabling "join_empty_channels".
        # This config option is case insensitive and supports simple globs (?*).
        badchans: ["#spamtrap0*", "#somebadplace"]

        # Determines whether to use KLINE/GLINE instead of KILL on target users. Defaults to false if not set.
        badchans_use_kline: false
        # Ban duration, if use_kline is enabled. This uses a time duration in the form 1w2d3h4m5s, and defaults
        # to 24h (24 hours) if not set.
        badchans_kline_duration: 24h
'''

from pylinkirc import utils, conf, world
from pylinkirc.log import log

import concurrent.futures
import ipaddress
import json
import requests

MAX_THREADS = conf.conf.get('badchans', {}).get('max_threads', 10)
pool = None

def main(irc=None):
    global pool
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

def die(irc=None):
    if pool is not None:
        pool.shutdown(wait=False)

DEFAULT_DNSBL_REASON = "A user o" + "n this host" + " joined an IR" + "C spa" + "mtra" + "p channel."

DRONEBL_TYPE = 3  # IRC spam drone
def _submit_dronebl(irc, ip, apikey, nickuserhost=None):
    reason = irc.get_service_option('badchans', 'dnsbl_reason', DEFAULT_DNSBL_REASON)

    request = '<add ip="%s" type="%s" comment="%s" />' % (ip, DRONEBL_TYPE, reason)
    xml_data = '<?xml version="1.0"?><request key="%s">%s</request>' % (apikey, request)
    headers = {'Content-Type': 'text/xml'}

    log.debug('(%s) badchans: posting to dronebl: %s', irc.name, xml_data)

    # Expecting this to block
    r = requests.post('https://dronebl.org/RPC2', data=xml_data, headers=headers)

    dronebl_response = r.text

    log.debug('(%s) badchans: got response from dronebl: %s', irc.name, dronebl_response)
    if '<success' in dronebl_response:
        log.info('(%s) badchans: got success for DroneBL on %s (%s)', irc.name, ip, nickuserhost or 'some n!u@h')
    else:
        log.warning('(%s) badchans: dronebl submission error: %s', irc.name, dronebl_response)

DNSBLIM_TYPE = 5  # Abusive Hosts
def _submit_dnsblim(irc, ip, apikey, nickuserhost=None):
    reason = irc.get_service_option('badchans', 'dnsbl_reason', DEFAULT_DNSBL_REASON)

    request = {
       'key': apikey,
       'addresses': [{
           'ip': ip,
           'type': str(DNSBLIM_TYPE),
           'reason': reason,
       }],
    }
    headers = {'Content-Type': 'application/json'}

    log.debug('(%s) badchans: posting to dnsblim: %s', irc.name, request)

    # Expecting this to block
    r = requests.post('https://api.dnsbl.im/import', data=json.dumps(request), headers=headers)

    #log.debug('(%s) badchans: got response from dnsblim: %s', irc.name, r.text)

REASON = "You have si" + "nned..."  # XXX: config option
DEFAULT_BAN_DURATION = '24h'
def handle_join(irc, source, command, args):
    """
    killonjoin JOIN listener.
    """
    # Ignore our own clients and other Ulines
    if irc.is_privileged_service(source) or irc.is_internal_server(source):
        return

    badchans = irc.serverdata.get('badchans')
    if not badchans:
        return
    elif not isinstance(badchans, list):
        log.error("(%s) badchans: the 'badchans' option must be a list of strings, not a %s", irc.name, type(badchans))
        return

    use_kline = irc.get_service_option('badchans', 'use_kline', False)
    kline_duration = irc.get_service_option('badchans', 'kline_duration', DEFAULT_BAN_DURATION)
    try:
        kline_duration = utils.parse_duration(kline_duration)
    except ValueError:
        log.warning('(%s) badchans: invalid kline duration %s', irc.name, kline_duration, exc_info=True)
        kline_duration = DEFAULT_BAN_DURATION

    channel = args['channel']
    for badchan in badchans:
        if irc.match_text(badchan, channel):
            asm_uid = None
            # Try to kill from the antispam service if available
            if 'antispam' in world.services:
                asm_uid = world.services['antispam'].uids.get(irc.name)

            for user in args['users']:
                try:
                    ip = irc.users[user].ip
                    ipa = ipaddress.ip_address(ip)
                except (KeyError, ValueError):
                    log.error("(%s) badchans: could not obtain IP of user %s", irc.name, user)
                    continue
                nuh = irc.get_hostmask(user)

                exempt_hosts = set(conf.conf.get('badchans', {}).get('exempt_hosts', [])) | \
                             set(irc.serverdata.get('badchans_exempt_hosts', []))

                if not ipa.is_global:
                    irc.msg(user, "Warning: %s kills unopered users, but non-public addresses are exempt." % channel,
                            notice=True,
                            source=asm_uid or irc.pseudoclient.uid)
                    continue

                if exempt_hosts:
                    skip = False
                    for glob in exempt_hosts:
                        if irc.match_host(glob, user):
                            log.info("(%s) badchans: ignoring exempt user %s on %s (%s)", irc.name, nuh, channel, ip)
                            irc.msg(user, "Warning: %s kills unopered users, but your host is exempt." % channel,
                                    notice=True,
                                    source=asm_uid or irc.pseudoclient.uid)
                            skip = True
                            break
                    if skip:
                        continue

                if irc.is_oper(user):
                    irc.msg(user, "Warning: %s kills unopered users!" % channel,
                            notice=True,
                            source=asm_uid or irc.pseudoclient.uid)
                else:
                    log.info('(%s) badchans: punishing user %s (server: %s) for joining channel %s',
                             irc.name, nuh, irc.get_friendly_name(irc.get_server(user)), channel)
                    if use_kline:
                        irc.set_server_ban(asm_uid or irc.sid, kline_duration, host=ip, reason=REASON)
                    else:
                        irc.kill(asm_uid or irc.sid, user, REASON)

                    dronebl_key = irc.get_service_option('badchans', 'dronebl_key')
                    if dronebl_key:
                        log.info('(%s) badchans: submitting IP %s (%s) to DroneBL', irc.name, ip, nuh)
                        pool.submit(_submit_dronebl, irc, ip, dronebl_key, nuh)

                    dnsblim_key = irc.get_service_option('badchans', 'dnsblim_key')
                    if dnsblim_key:
                        log.info('(%s) badchans: submitting IP %s (%s) to DNSBL.im', irc.name, ip, nuh)
                        pool.submit(_submit_dnsblim, irc, ip, dnsblim_key, nuh)


utils.add_hook(handle_join, 'JOIN')
