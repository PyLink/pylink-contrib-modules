"""
Experimental, WIP protocol module connecting PyLink to Terraria.

This requires a modified terrabot library from https://github.com/GLolol/terrabot.

Sample configuration:

servers:
    terraria:
        ip: 45.32.253.99
        protocol: terraria

        # Port is optional and defaults to 7777.
        port: 7777

        # Server password, for servers that require one.
        sendpass: "blahblah"

        # Sets the Terraria username the bot should use - defaults to "PyLink".
        ingamename: "troublemaker"
"""

import threading

from terrabot import TerraBot, packets
from terrabot.events import Events

from pylinkirc import utils, conf
from pylinkirc.log import log
from pylinkirc.classes import *

class TerraBotWrapper(TerraBot):
    """
    Wrapper around TerraBot that implements a threading event for checking whether the connection is down.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_aborted = threading.Event()

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        self._is_aborted.clear()

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        self._is_aborted.set()

class TerraBotProtocol(PyLinkNetworkCoreWithUtils):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.protocol_caps = {'clear-channels-on-leave', 'slash-in-nicks', 'slash-in-hosts', 'underscore-in-hosts'}

        self.has_eob = False

        # Remove conf key checks for those not needed for Clientbot.
        self.conf_keys -= {'port', 'recvpass', 'sendpass', 'sid', 'sidrange', 'hostname'}

        self.casemapping = 'ascii'

    def connect(self):
        """Initializes a connection to a server."""
        self.uidgen = utils.PUIDGenerator('ClientbotInternalUID')
        self.sidgen = utils.PUIDGenerator('ClientbotInternalSID')

        self.bot = TerraBotWrapper(self.serverdata['ip'], port=self.serverdata.get('port') or 7777, password=self.serverdata.get('sendpass'),
                                   name=self.serverdata.get('ingamename') or 'PyLink')
        self.eventmgr = self.bot.get_event_manager()

        self.eventmgr.method_on_event(Events.Chat, self.handle_chat)
        self.bot.start()

        threading.Thread(name='Dummy connect loop for network %s' % self.name, target=lambda: self.bot._is_aborted.wait()).start()

    def handle_chat(self, event_id, msg):
        log.debug(msg)

    # Note: clientbot clients are initialized with umode +i by default
    def spawn_client(self, nick, ident='unknown', host='unknown.host', realhost=None, modes={('i', None)},
            server=None, ip='0.0.0.0', realname='', ts=None, opertype=None,
            manipulatable=False):
        """
        STUB: Pretends to spawn a new client with a subset of the given options.
        """

        server = server or self.sid
        uid = self.uidgen.next_uid(prefix=nick)

        ts = ts or int(time.time())

        log.debug('(%s) spawn_client stub called, saving nick %s as PUID %s', self.name, nick, uid)
        u = self.users[uid] = User(nick, ts, uid, server, ident=ident, host=host, realname=realname,
                                          manipulatable=manipulatable, realhost=realhost, ip=ip)
        self.servers[server].users.add(uid)

        self.apply_modes(uid, modes)

        return u

    def spawn_server(self, name, sid=None, uplink=None, desc=None, endburst_delay=0, internal=True):
        """
        STUB: Pretends to spawn a new server with a subset of the given options.
        """
        name = name.lower()
        if internal:
            # Use a custom pseudo-SID format for internal servers to prevent any server name clashes
            sid = self.sidgen.next_sid(prefix=name)
        else:
            # For others servers, just use the server name as the SID.
            sid = name

        self.servers[sid] = Server(uplink, name, internal=internal)
        return sid

    def _stub(self, *args):
        """Stub outgoing command function (does nothing)."""
        return
    kill = topic = topic_burst = knock = numeric = away = invite = kick = _stub

    def join(self, client, channel):
        """STUB: Joins a user to a channel."""
        self.channels[channel].users.add(client)
        self.users[client].channels.add(channel)
        self.call_hooks([client, 'CLIENTBOT_JOIN', {'channel': channel}])

    def message(self, source, target, text, notice=False):
        """Sends messages to the target."""
        command = 'NOTICE' if notice else 'PRIVMSG'

        if self.pseudoclient and self.pseudoclient.uid == source:
            self.send('%s %s :%s' % (command, self._expandPUID(target), text))
        else:
            self.call_hooks([source, 'CLIENTBOT_MESSAGE', {'target': target, 'is_notice': notice, 'text': text}])
    notice = message

    def part(self, source, channel, reason=''):
        """STUB: Parts a user from a channel."""
        if self.pseudoclient and source == self.pseudoclient.uid:
            return

        self.channels[channel].remove_user(source)
        self.users[source].channels.discard(channel)

        # Forward this as a clientbot relay message
        self.call_hooks([source, 'CLIENTBOT_PART', {'channel': channel, 'text': reason}])

    def quit(self, source, reason):
        """STUB: Quits a client."""
        userdata = self.users[source]
        self._remove_client(source)
        self.call_hooks([source, 'CLIENTBOT_QUIT', {'text': reason, 'userdata': userdata}])

    def sjoin(self, server, channel, users, ts=None, modes=set()):
        """STUB: bursts joins from a server."""
        # This stub only updates the state internally with the users
        # given. modes and TS are currently ignored.
        puids = {u[-1] for u in users}
        for user in puids:
            self.users[user].channels.add(channel)
        self.channels[channel].users |= puids

        nicks = {self.get_friendly_name(u) for u in puids}
        self.call_hooks([server, 'CLIENTBOT_SJOIN', {'channel': channel, 'nicks': nicks}])

    def squit(self, source, target, text):
        """STUB: SQUITs a server."""
        # What this actually does is just handle the SQUIT internally: i.e.
        # Removing pseudoclients and pseudoservers.
        squit_data = self._squit(source, 'CLIENTBOT_VIRTUAL_SQUIT', [target, text])

        if squit_data.get('nicks'):
            self.call_hooks([source, 'CLIENTBOT_SQUIT', squit_data])

    def update_client(self, target, field, text):
        """Updates the known ident, host, or realname of a client."""
        if target not in self.users:
            log.warning("(%s) Unknown target %s for update_client()", self.name, target)
            return

        u = self.users[target]

        if field == 'IDENT' and u.ident != text:
            u.ident = text
            if not self.is_internal_client(target):
                # We're updating the host of an external client in our state, so send the appropriate
                # hook payloads.
                self.call_hooks([self.sid, 'CHGIDENT',
                                   {'target': target, 'newident': text}])
        elif field == 'HOST' and u.host != text:
            u.host = text
            if not self.is_internal_client(target):
                self.call_hooks([self.sid, 'CHGHOST',
                                   {'target': target, 'newhost': text}])
        elif field in ('REALNAME', 'GECOS') and u.realname != text:
            u.realname = text
            if not self.is_internal_client(target):
                self.call_hooks([self.sid, 'CHGNAME',
                                   {'target': target, 'newgecos': text}])
        else:
            return  # Nothing changed

    '''
    def _get_UID(self, nick, ident=None, host=None):
        """
        Fetches the UID for the given nick, creating one if it does not already exist.

        Limited (internal) nick collision checking is done here to prevent Clientbot users from
        being confused with virtual clients, and vice versa."""
        self._check_puid_collision(nick)
        idsource = self.nick_to_uid(nick)
        is_internal = self.is_internal_client(idsource)

        # If this sender isn't known or it is one of our virtual clients, spawn a new one.
        # This also takes care of any nick collisions caused by new, Clientbot users
        # taking the same nick as one of our virtual clients, and will force the virtual client to lose.
        if (not idsource) or (is_internal and self.pseudoclient and idsource != self.pseudoclient.uid):
            if idsource:
                log.debug('(%s) Nick-colliding virtual client %s/%s', self.name, idsource, nick)
                self.call_hooks([self.sid, 'CLIENTBOT_NICKCOLLIDE', {'target': idsource, 'parse_as': 'SAVE'}])

            idsource = self.spawn_client(nick, ident or 'unknown', host or 'unknown',
                                        server=self.uplink, realname=FALLBACK_REALNAME).uid

        return idsource
    '''


Class = TerraBotProtocol
