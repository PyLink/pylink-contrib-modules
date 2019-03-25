"""
operlock.py: sets up persistent staff channels that kick deopered users and prevent opers from leaving.
"""

# Example config:
"""
servers:
    yournet:
        # <everything else>
        # A list of channels to enforce operlock on.
        operlock_channels: ["#staff", "#opers"]
        # A list of hosts / exttargets to enforce.
        operlock_exempt_hosts: ["*!*@your.host"]
"""

from pylinkirc import utils, world, conf
from pylinkirc.log import log
from pylinkirc.coremods import permissions

def _should_enforce(irc, source, args):
    exemptions = irc.get_service_option('operlock', 'exempt_hosts', default=None) or []
    if not irc.connected.is_set():
        # Don't act users until we've finished bursting.
        return False
    elif source not in irc.users:
        # Target isn't a user
        return False

    # Ignore exempt hosts
    for glob in exemptions:
        if irc.match_host(glob, source):
            log.debug("(%s) operlock: skipping exempt user %s", irc.name, irc.get_friendly_name(source))
            return False
    return True

def handle_part(irc, source, command, args):
    """Force joins users who try to leave a designated staff channel."""
    staffchans = irc.get_service_option('operlock', 'channels', default=None) or []
    if not staffchans:
        return
    elif not _should_enforce(irc, source, args):
        return

    for channel in args['channels']:
        if channel in staffchans and irc.is_oper(source):
            if irc.protoname in ('inspircd', 'unreal'):
                irc.msg(source, "Warning: You must deoper to leave %r." % channel, notice=True)
                irc._send_with_prefix(irc.sid, 'SAJOIN %s %s' % (source, channel))
            else:
                log.warning('(%s) Force join is not supported on this IRCd %r!', irc.name, irc.protoname)

utils.add_hook(handle_part, 'PART')

DEOPER_KICK_REASON = 'User has deopered'
def handle_mode(irc, source, command, args):
    """Kicks users who deoper from designated staff channels."""
    staffchans = irc.get_service_option('operlock', 'channels', default=None) or []
    if not staffchans:
        return
    elif not _should_enforce(irc, source, args):
        return

    if ('-o', None) in args['modes']:
        # User is deopering
        for channel in irc.users[source].channels:
            if channel in staffchans:
                if irc.protoname in ('inspircd', 'unreal'):
                    irc._send_with_prefix(irc.sid, 'SAPART %s %s :%s' % (source, channel, DEOPER_KICK_REASON))
                else:
                    irc.kick(irc.sid, source, channel, DEOPER_KICK_REASON)

utils.add_hook(handle_mode, 'MODE')
