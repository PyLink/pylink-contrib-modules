"""
mimic.py: Echoes ZNC (energymech)-format chatlogs to channels by spawning fake users and talking
as them. Useful for training AI bots and the like.
"""

__authors__ = [('James Lu', 'james@overdrivenetworks.com')]
__version__ = '0.1'

import re
import glob
import time
import threading
import os.path
import string

from pylinkirc import utils, conf
from pylinkirc.log import log

CHAT_REGEX = re.compile(r"^\[(?:[0-9]{2}\:){2}[0-9]{2}\] <(.+?)> (.*)$")
ACTION_REGEX = re.compile(r"^\[(?:[0-9]{2}\:){2}[0-9]{2}\] \* (\S+?) (.*)$")
# Hostname and server name used by clients.
HOSTNAME = 'mimic.int'
# Sets the delay between speaking lines, in order to prevent excess flood.
LINEDELAY = 0.15
# Suffix appended to nicks if a nick in the chatlogs is taken.
MIMICSUFFIX = '|mimic'

def _sayit(irc, sid, userdict, channel, nick, text, action=False):
    """Mimic core function."""

    # Fix imperfections in the REGEX matching.
    nick = nick.strip(('\x03\x02\x01'))

    lowernick = irc.toLower(nick)
    uid = userdict.get(lowernick)
    log.debug('(%s) mimic: got UID %s for nick %s', irc.name, uid, nick)
    if not uid:  # Nick doesn't exist; make a new client for it.
        ircnick = nick
        ircnick = ircnick.replace('/', '|')
        if irc.nickToUid(nick):
            # Nick exists, but is not one of our temp users. Tag it with |mimic
            ircnick += MIMICSUFFIX

        if nick.startswith(tuple(string.digits)):
            ircnick = '_' + ircnick

        if not utils.isNick(ircnick):
            log.warning('(%s) mimic: Bad nick %s, ignoring text: <%s> %s', irc.name, ircnick, nick, text)
            return userdict

        userdict[lowernick] = uid = irc.proto.spawnClient(ircnick, 'mimic', HOSTNAME, server=sid).uid
        log.debug('(%s) mimic: spawning client %s for nick %s (really %s)', irc.name, uid, ircnick, nick)
        irc.proto.join(uid, channel)

    if action:  # Format CTCP action
        text = '\x01ACTION %s\x01' % text

    irc.proto.message(uid, channel, text)
    return userdict

@utils.add_cmd
def mimic(irc, source, args):
    """<channel> <log glob>

    Echoes chatlogs matching the log glob to the given channel. Home folders ("~") and environment variables ($HOME, etc.) are expanded in THAT order."""
    irc.checkAuthenticated(source, allowOper=False)
    try:
        channel, logs = args[:2]
    except ValueError:
        irc.reply("Error: Not enough arguments. Needs 2: channel, log glob.")
        return
    else:
        assert utils.isChannel(channel), "Invalid channel %s" % channel
        channel = irc.toLower(channel)

        # Expand variables in the path glob
        logs = os.path.expandvars(os.path.expanduser(logs))

    mysid = irc.proto.spawnServer(HOSTNAME)
    logs = sorted(glob.glob(logs))

    def talk():
        userdict = {}
        for item in logs:
            irc.proto.notice(irc.pseudoclient.uid, channel, 'Beginning mimic of log file %s' % item)
            with open(item, errors='replace') as f:  # errors='replace' ignores UnicodeDecodeError
                for line in f.readlines():
                    action = False  # Marks whether line is an action
                    match = CHAT_REGEX.search(line)
                    actionmatch = ACTION_REGEX.search(line)

                    if actionmatch:
                        action = True

                    # Only one of the two matches need to exist for the check below
                    match = match or actionmatch

                    if match:
                        sender, text = match.group(1, 2)
                        # Update the user dict returned by _sayit(), which automatically spawns users
                        # as they're seen.
                        userdict = _sayit(irc, mysid, userdict, channel,
                                          sender, text, action=action)

                # Pause for a bit to prevent excess flood.
                time.sleep(LINEDELAY)
        else:
            # Once we're done, SQUIT everyone to clean up automagically.
            irc.proto.notice(irc.pseudoclient.uid, channel, 'Finished mimic of %s items' % len(logs))
            irc.proto.squit(irc.sid, mysid)

    threading.Thread(target=talk).start()

