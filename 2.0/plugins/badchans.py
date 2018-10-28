"""
badchans.py - Kills unopered users when they join specified channels.
"""

from pylinkirc import utils, conf, world
from pylinkirc.log import log

REASON = "You have si" + "nned..."  # XXX: config option
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

    channel = args['channel']
    for badchan in badchans:
        if irc.match_text(badchan, channel):
            asm_uid = None
            # Try to kill from the antispam service if available
            if 'antispam' in world.services:
                asm_uid = world.services['antispam'].uids.get(irc.name)

            for user in args['users']:
                if irc.is_oper(user):
                    irc.msg(user, "Warning: %s kills unopered users!" % channel,
                            notice=True,
                            source=asm_uid or irc.pseudoclient.uid)
                else:
                    log.info('(%s) badchans: killing user %s for joining channel %s',
                             irc.name, irc.get_hostmask(user), channel)
                    irc.kill(asm_uid or irc.sid, user, REASON)

utils.add_hook(handle_join, 'JOIN')
