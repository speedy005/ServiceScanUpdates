# -*- coding: utf-8 -*-
from __future__ import print_function

from Plugins.Plugin import PluginDescriptor
from Components.config import config

# Kompatibler Import für ServiceScan
try:
    from Screens.ServiceScan import ServiceScan
except ImportError:
    from Components.ServiceScan import ServiceScan

from Tools.Directories import resolveFilename, SCOPE_CONFIG
from . import _

from .speedy005SSULameDBParser import speedy005SSULameDBParser

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

baseServiceScan_execBegin = None
baseServiceScan_execEnd = None
# baseServiceScan_scanStatusChanged = None

preScanDB = None


def dictHasKey(dictionary, key):
    if PY2:
        return dictionary.has_key(key)
    else:
        return key in dictionary


def safeClose(db):
    if hasattr(db, "close"):
        db.close()


def ServiceScan_execBegin(self):
    flags = None
    try:
        flags = self.scanList[self.run]["flags"]
    except (AttributeError, KeyError, IndexError, TypeError):
        flags = "N/A"
    print("[speedy005ServiceScanUpdates] ServiceScan_execBegin [%s]" % str(flags))

    global preScanDB
    if not preScanDB and (config.plugins.speedy005servicescanupdates.add_new_tv_services.value or
                          config.plugins.speedy005servicescanupdates.add_new_radio_services.value):
        preScanDB = speedy005SSULameDBParser(resolveFilename(SCOPE_CONFIG) + "/lamedb")
    baseServiceScan_execBegin(self)


def ServiceScan_execEnd(self, onClose=True):
    flags = None
    try:
        flags = self.scanList[self.run]["flags"]
    except (AttributeError, KeyError, IndexError, TypeError):
        flags = "N/A"

    # Sicherstellen, dass self.state existiert
    state_val = getattr(self, "state", -1)
    print("[speedy005ServiceScanUpdates] ServiceScan_execEnd (%d) [%s]" % (state_val, str(flags)))

    # Auch hier getattr nutzen, um Absturz zu vermeiden
    if getattr(self, "state", None) == getattr(self, "DONE", None):
        if config.plugins.speedy005servicescanupdates.add_new_tv_services.value or config.plugins.servicescanupdates.add_new_radio_services.value:
            postScanDB = speedy005SSULameDBParser(resolveFilename(SCOPE_CONFIG) + "/lamedb")
            postScanServices = postScanDB.getServices()
            safeClose(postScanDB)  # <- Hier statt direktem postScanDB.close()

            global preScanDB
            if preScanDB:
                preScanServices = preScanDB.getServices()

                newTVServices = []
                newRadioServices = []

                # Neue Services finden
                for service_ref in postScanServices.keys():
                    if not dictHasKey(preScanServices, service_ref):
                        if speedy005SSULameDBParser.isVideoService(service_ref):
                            newTVServices.append(service_ref)
                        elif speedy005SSULameDBParser.isRadioService(service_ref):
                            newRadioServices.append(service_ref)

                from speedy005SSUBouquetHandler import speedy005SSUBouquetHandler
                bouquet_handler = speedy005SSUBouquetHandler()

                # TV-Services
                print("[speedy005ServiceScanUpdates] Found %d new TV services" % len(newTVServices))
                if config.plugins.speedy005servicescanupdates.add_new_tv_services.value and len(newTVServices) > 0:
                    bouquet_handler.addToIndexBouquet("tv")
                    if config.plugins.speedy005servicescanupdates.clear_bouquet.value:
                        bouquet_handler.createSSUBouquet(newTVServices, "tv")
                    else:
                        if bouquet_handler.doesSSUBouquetFileExists("tv"):
                            bouquet_handler.appendToSSUBouquet(newTVServices, "tv")
                        else:
                            bouquet_handler.createSSUBouquet(newTVServices, "tv")

                # Radio-Services
                print("[speedy005ServiceScanUpdates] Found %d new radio services" % len(newRadioServices))
                if config.plugins.speedy005servicescanupdates.add_new_radio_services.value and len(newRadioServices) > 0:
                    bouquet_handler.addToIndexBouquet("radio")
                    if config.plugins.speedy005servicescanupdates.clear_bouquet.value:
                        bouquet_handler.createSSUBouquet(newRadioServices, "radio")
                    else:
                        if bouquet_handler.doesSSUBouquetFileExists("radio"):
                            bouquet_handler.appendToSSUBouquet(newRadioServices, "radio")
                        else:
                            bouquet_handler.createSSUBouquet(newRadioServices, "radio")

                bouquet_handler.reloadBouquets()

                # Reset pre scan db
                preScanDB = None

    baseServiceScan_execEnd(self)


# def ServiceScan_scanStatusChanged(self):
#     #print("[speedy005ServiceScanUpdates] ServiceScan_scanStatusChanged (%d)" % self.state)
#     baseServiceScan_scanStatusChanged(self)


##############################################

def autostart(reason, **kwargs):
    if reason == 0 and "session" in kwargs:
        global baseServiceScan_execBegin
        if baseServiceScan_execBegin is None:
            baseServiceScan_execBegin = ServiceScan.execBegin
        ServiceScan.execBegin = ServiceScan_execBegin

        global baseServiceScan_execEnd
        if baseServiceScan_execEnd is None:
            baseServiceScan_execEnd = ServiceScan.execEnd
        ServiceScan.execEnd = ServiceScan_execEnd

        # global baseServiceScan_scanStatusChanged
        # if baseServiceScan_scanStatusChanged is None:
        #     baseServiceScan_scanStatusChanged = ServiceScan.scanStatusChanged
        # ServiceScan.scanStatusChanged = ServiceScan_scanStatusChanged


def SSUMain(session, **kwargs):
    from .speedy005SSUSetupScreen import speedy005SSUSetupScreen
    session.open(speedy005SSUSetupScreen)


def SSUMenuItem(menuid, **kwargs):
    if menuid == "scan":
        return [("speedy005 Service Scan Updates " + _("Setup"), SSUMain, "servicescanupdates", None)]
    else:
        return []


##############################################

def menu(menuid, **kwargs):
    if menuid == "mainmenu":
        return [(_("speedy005 Service Scan Updates") + " " + _("Setup"), SSUMain, "servicescanupdates_mainmenu", 50)]
    return []


def Plugins(**kwargs):
    return [
        # Autostart / Sessionstart
        PluginDescriptor(
            where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART],
            fnc=autostart
        ),

        # Plugin-Menü
        PluginDescriptor(
            name="speedy005 Service Scan Updates " + _("Setup"),
            description=_("Updates during service scan"),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=SSUMain
        ),

        # Erweiterungen (Extensions-Menü)
        PluginDescriptor(
            name="speedy005 Service Scan Updates " + _("Setup"),
            description=_("Updates during service scan"),
            where=PluginDescriptor.WHERE_EXTENSIONSMENU,
            icon="plugin.png",
            fnc=SSUMain
        ),

        # Hauptmenü über menu()
        PluginDescriptor(
            where=PluginDescriptor.WHERE_MENU,
            fnc=menu
        ),

        # Main menu via SSUMenuItem
        PluginDescriptor(
            where=PluginDescriptor.WHERE_MENU,
            fnc=SSUMenuItem
        )
]

