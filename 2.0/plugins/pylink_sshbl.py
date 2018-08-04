"""SSHBL scanner for PyLink IRC Services."""

# Config roughly looks like this:
'''
sshbl:
    # Defaults to 0. -5 is safer, -10 will only block really old hosts like dropbear 0.5x
    threshold: 0
    reason: "specify a kill reason"
    exempt_hosts:
        # E.g. to exempt SASL users
        - $account
        - *!*@*.some.good.isp.net
'''

try:
    from sshbl import sshbl
except ImportError:
    raise ImportError("sshbl is not installed - get it at https://github.com/jlu5/sshbl")
import concurrent.futures
import ipaddress

from pylinkirc.log import log
from pylinkirc import utils, conf

MAX_THREADS = conf.conf.get('sshbl', {}).get('max_threads', 10)
pool = None

def main(irc=None):
    global pool
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

def die(irc=None):
    if pool is not None:
        pool.shutdown(wait=False)

def _check_connection(irc, args):
    ip = args['ip']
    try:
        result = sshbl.scan(ip)
    except:
        log.exception("SSHBL scan errored:")
        return

    threshold = irc.get_service_option('sshbl', 'threshold', default=0)
    reason = irc.get_service_option('sshbl', 'reason',
        "Your host runs an SSH daemon commonly used by spammer IPs. Consider upgrading your machines "
        "or contacting network staff for an exemption.")

    if result:
        _, port, blacklisted, score = result
        if not blacklisted:
            return
        log.info("sshbl: caught IP %s:%s (%s/%s) with score %s", ip, port, irc.name, args['nick'], score)
        if args['uid'] in irc.users:
            irc.kill(irc.pseudoclient.uid, args['uid'], reason)

def handle_uid(irc, source, command, args):
    """Checks incoming connections against SSHBL."""
    ip = args['ip']
    exemptions = irc.get_service_option('sshbl', 'exempt_hosts', default=None) or []
    if not irc.connected.is_set():
        # Don't scan users until we've finished bursting.
        return
    elif not ipaddress.ip_address(ip).is_global:
        log.debug("sshbl: skipping scanning local address %s", ip)
        return
    elif args['uid'] in irc.users and exemptions:
        for glob in exemptions:
            if irc.match_host(glob, args['uid']):
                log.debug("sshbl: skipping scanning exempt address %s (%s/%s)", ip, irc.name, args['nick'])
                return
    pool.submit(_check_connection, irc, args)

utils.add_hook(handle_uid, 'UID')
