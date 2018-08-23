"""
Extended reload functions for PyLink.

The commands provided here are hacks with respect to Python internals, so do not rely on them for anything critical!
"""

import pkg_resources
import sys
import importlib

import pylinkirc
from pylinkirc import utils
from pylinkirc.log import log

MODULE_NAME = "pylinkirc"

# Derived from https://stackoverflow.com/questions/23206376/
# However, we take a Distribution instance here and do NOT remove any existing modules
def _deactivate(dist):
    # pkg_resources stores a WorkingSet instance of all loaded distributions
    ws = pkg_resources.working_set

    # The WorkingSet in turn stores distributions in three separate items:
    #   by_key, entries, and entry_keys all need to have the target removed
    log.debug('extreload: deactivating distribution %s' % dist)
    distpath = ws.by_key.pop(dist.key).location
    ws.entry_keys.pop(distpath)
    ws.entries.remove(distpath)

    # Then remove references in sys.path
    sys.path.remove(distpath)

def _refresh_packages():
    # Reload our packages, but not the individual modules
    for module in (pylinkirc, pylinkirc.plugins, pylinkirc.protocols):
        log.debug('extreload: refreshing package %s' % module)
        importlib.reload(module)
    utils._reset_module_dirs()

@utils.add_cmd
def newsrc(irc, source, args):
    """<new version>

    Updates the PyLink source version to the target version, so that modules
    can be reloaded.
    """
    try:
        new_version = args[0]
    except IndexError:
        irc.error("Needs 1 argument: new version")
        return

    # Backup & deactivate our current distribution
    current_distribution = pkg_resources.get_distribution(MODULE_NAME)
    _deactivate(current_distribution)

    # Create the new one
    new_version = "%s==%s" % (MODULE_NAME, args[0])

    # Load it!
    try:
        log.debug('extreload: trying to activate new version %s' % new_version)
        new_distribution = pkg_resources.get_distribution(new_version)
        new_distribution.activate()
    except Exception as e:
        log.exception("Failed to load new distribution for %s, restoring current last distribution %r",
                      new_version, current_distribution)
        current_distribution.activate()
        irc.error("Failed to activate new distribution: %s: %s" % (e.__class__.__name__, str(e)))
    else:
        _refresh_packages()
        log.info("Successfully upgraded %s => %s", current_distribution, new_distribution)
        irc.reply("Done. Upgraded %s => %s" % (str(current_distribution), str(new_distribution)))
