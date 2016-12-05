"""
passgen.py: Generates passwords/random strings given inputt criteria.
"""

__authors__ = [('Ken Spencer (Iota)', 'iota@electrocode.net')]
__version__ = '0.1'

from pylinkirc import utils
from pylinkirc.log import log

from strgen import StringGenerator as sg

def passgen(irc, source, args):
    r"""[length] [template]
    The template is in format '[codesets]'. If something like the following was required.
    'a password shall have 6 - 20 characters of which at least one must be a digit and at least one must be a special character'
    That could be done with '[\l\d]{4:18}&[\d]&[\p]'
    These 'code sets' are an easy way to group certain types of characters together.
    +----------+--------------------------+
    | Set Code |         Provides         |
    +----------+--------------------------+
    | \W       | whitespace + punctuation |
    +----------+--------------------------+
    | \a       | ascii_letters            |
    +----------+--------------------------+
    | \c       | lowercase                |
    +----------+--------------------------+
    | \d       | digits                   |
    +----------+--------------------------+
    | \h       | hexdigits                |
    +----------+--------------------------+
    | \l       | letters                  |
    +----------+--------------------------+
    | \o       | octdigits                |
    +----------+--------------------------+
    | \p       | punctuation              |
    +----------+--------------------------+
    | \r       | printable                |
    +----------+--------------------------+
    | \s       | whitespace               |
    +----------+--------------------------+
    | \u       | uppercase                |
    +----------+--------------------------+
    | \w       | _ + letters + digits     |
    +----------+--------------------------+"""
    template = ""
    length = 15
    lengtharg = ""
    try:
        inputargs = args[0]
    except IndexError:
        irc.error("no input given, using sane defaults")

    try:
        lengtharg = int(args[0])

        if lengtharg < 0:
            raise TypeError("length must be an unsigned integer, a positive number, or 0 (to use default length")
        elif lengtharg == 0:
            pass


    except TypeError:
        irc.error("length must be an unsigned integer")

    try:
        template = args[1]
    except IndexError:
        irc.error("no template given, using default")

    if lengtharg == 0 and template == "":
        irc.error("using default length and a default template")

    result = ""
    if isinstance(lengtharg, int):
        if lengtharg == "" and template == "":
            template = "[\c\\u\d]"
            template = template + "{%s}" % length
            result = sg("%s" % template).render()
        if lengtharg == 0 and template == "":
            template = "[\c\\u\d\p]"
            template = template + "{%s}" % length
            result = sg("%s" % template).render()
        elif lengtharg > 0 and template == "":
            template = "[\c\\u\d\p]"
            result = sg("%s{%s}" % (template, lengtharg)).render()
        elif lengtharg == 0 and template != "":
            result = sg("%s" % template).render()
        else:
            irc.error("part of your input was invalid")

    password = result
    irc.reply(password, private=True)
utils.add_cmd(passgen, "passgen")
