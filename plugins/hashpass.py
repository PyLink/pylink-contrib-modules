# -*- coding: utf-8 -*-
# hashpass.py

# Author: Ken Spencer
# Author Nick: Iota
# Version: 0.0.1
# License: MPL

from pylinkirc import utils
from pylinkirc.log import log

import re
import hashlib
    

def _hash(irc, source, args):
    """<password> [digest]
    Hashes a given password with the given digest, when 'digest' isn't given, defaults to sha256"""
    digest = ""
    try:
        password = args[0]
        try:
            digest = args[1]
        except IndexError:
            digest = "sha256"
        # DRY'ing
        digests = hashlib.algorithms_available 
        if digest:
            if digest in digests:
                d = hashlib.new("%s" % digest)
                d.update(b'%s' % password.encode('utf-8'))
                irc.reply(d.hexdigest(), private=True)
            else:
                irc.error("hash algorithm '%s' unavailable, see 'algorithms'" % digest, private=True)
        else:
            d = hashlib.new("sha256")
            d.update(b'%s' % password.encode('utf-8'))
            irc.reply(d.hexdigest(), private=True)
    except IndexError:
        irc.error("Not enough arguments. Needs 1-2: password, digest (optional).", private=True)


def algorithms(irc, source, args):
    """algorithms [query]
    When given '.' gives all available algorithms, or will filter the available when given a starting few characters."""
    try:
        digest = args[0]
        pattern = re.compile(r"%s.*" % digest, re.I)
        avail_digests = filter(pattern.search, list(hashlib.algorithms_available))
        avail_digests = " \xB7 ".join(avail_digests)
        irc.reply(avail_digests, private=True)
    except IndexError:
        irc.error("Not enough arguments. Needs 1: query.", private=True)

    
utils.add_cmd(algorithms, "algorithms", featured=True)
utils.add_cmd(_hash, "hash", featured=True)
