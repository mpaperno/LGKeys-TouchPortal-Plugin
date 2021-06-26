'''
LGKeys TouchPortal Plugin
This is a "plugin" for the Touch Portal software (https://www.touch-portal.com)
designed for integrating with Logitech keyboards and other peripherals with
programmable macro keys (or "G" keys).  It's main purpose is to display the key
mappings set up for each individual profile in the Logitech Gaming Software.
'''

__copyright__ = '''
Copyright Maxim Paperno; all rights reserved.

This file may be used under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A copy of the GNU General Public License is available at <http://www.gnu.org/licenses/>.

This project may also use 3rd-party Open Source software under the terms
of their respective licenses. The copyright notice above does not apply
to any 3rd-party components used within.
'''

import os
import sys
from dataclasses import (dataclass, field)
from threading import (Thread, Event)
from argparse import (ArgumentParser, SUPPRESS as APSUPPRESS)
from logging import (getLogger, Formatter, NullHandler, FileHandler, StreamHandler, DEBUG, INFO, WARNING)
from datetime import datetime
from traceback import format_exc
from modules.TouchPortalAPI import (Client, TYPES as TPTYPES)
from modules.utils import Logger
from modules.lgsdi import LGSDInterface
from modules.profile_parser import GameProfileParser
from modules.profile_watcher import WatcherThread

# Set the default game profiles path. Unfortunately there's currently no way to set this
# dynamically in the TP `entry.tp` file.
if sys.platform == "win32":
	GK_DEFAULT_LGS_PROFILE_PATH = os.getenv('LOCALAPPDATA', "") + r"\Logitech\Logitech Gaming Software"
elif sys.platform == "darwin":
	GK_DEFAULT_LGS_PROFILE_PATH = os.path.expanduser("~/Library/Application Support/Logitech")
else:
	sys.exit(f"Unsupported/unknown platform: {sys.platform}")

# Refernce for supported device names. May  be followed by a specific
# device ID separated by period, eg.: Mouse.G700s
# These should match what appears in the relevant game profiles
# but without the "Logitech.Gaming." prefix.
#
# Keyboard
# LeftHandedController
# Mouse
# Headset

__version__ = "1.0"
GK_PLUGIN_VERSION = 0x0100  # maj|min
GK_PLUGIN_NAME = "LGKeys TouchPortal Plugin"
GK_PLUGIN_URL = "https://github.com/mpaperno/LGKeys-TouchPortal-Plugin"
GK_PLUGIN_ID = 'us.wdg.max.tpp.lgk'
GK_SET_PROF_DIR = "Profiles Directory"
GK_SET_DEVC_CATS = "Device Type(s)"
GK_SET_AUTO_SWTCH = "Auto-switch Profiles"
GK_SET_USE_LGSDI = "Use LGS Script Integration"
GK_SET_SEND_BTN_STATES = "Report Button Presses"
GK_SET_POLL_INTRVL = "Profile Change Poll Interval (ms)"
GK_SET_UNMAPPED_SLOT = "Unmapped Button Text"
GK_SET_LAST_PROF = "Last Active Profile"
GK_ACT_SWITCH_PROF = GK_PLUGIN_ID + ".act.switchProfile"
GK_ACT_SWITCH_PROF_DATA = GK_ACT_SWITCH_PROF + ".profileName"
GK_ACT_MEM_TOGGLE = GK_PLUGIN_ID + ".act.memToggle"
GK_ACT_MEM_TOGGLE_DEV = GK_ACT_MEM_TOGGLE + ".device"
GK_ACT_MEM_TOGGLE_SLT = GK_ACT_MEM_TOGGLE + ".memSlot"
GK_ACT_AUTOSW_TOGGLE = GK_PLUGIN_ID + ".act.autoSwitch"
GK_ACT_RELOAD_CURR = GK_PLUGIN_ID + ".act.reloadCurrent"
GK_ACT_RELOAD_ALL = GK_PLUGIN_ID + ".act.reloadAll"
GK_STATE_ROOT = GK_PLUGIN_ID + ".state."
GK_STATE_MESSAGE = GK_STATE_ROOT + "message"
GK_STATE_PROF_NAME = GK_STATE_ROOT + "currentProfileName"
GK_STATE_AUTOSW_TOGGLE = GK_STATE_ROOT + "autoSwitch"
GK_STATE_KBD_MEM_SLOT_SFX = ".memorySlot"
# GK_STATE_PROF_LIST = GK_STATE_ROOT + "profilesList"  # can't update Event valueChoices in TP
# GK_EVT_PROF_CHANGE = GK_PLUGIN_ID + ".event.currentProfileChanged"  # also doesn't work
# GK_STATE_PROF_CHANGE_FLG = GK_STATE_ROOT + "currentProfileChangedFlag"  # also doesn't work

# device name : (max keys, max states, profile contextId prefix, the LGS "family" code and suffix for TP State id)
GK_DEV_DATA_MAP = {
	"Keyboard"             : (18, 3, "G",      "kb"),
	"LeftHandedController" : (29, 3, "G",      "lhc"),
	"Mouse"                : (20, 1, "Button", "mouse"),
	"Headset"              : ( 3, 1, "G",      "hs")  # not sure of "G"
}
# inverse mapping of the above, to index device types by their "family" code
GK_DEV_FAMILY_MAP = {
	'kb'    : "Keyboard",
	'lhc'   : "LeftHandedController",
	'mouse' : "Mouse",
	'hs'    : "Headset"
}

@dataclass
class GKSettings:
	profDir: str = GK_DEFAULT_LGS_PROFILE_PATH
	useDeviceTypes: list = field(default_factory=list)
	currProfileId: str = ""
	currProfileName: str = ""
	lastPlayedProfId: str = ""
	unmappedButtonText: str = "..."
	currShiftState: dict = field(default_factory=dict)
	autoSwitchProfiles: bool = True
	profilePollInterval: float = 1.0
	startedByTP: bool = False
	useLGSDI: bool = False
	reportBtnStates: bool = False
	ignoreNextSettingsChange: bool = False
	profiles: dict = field(default_factory=dict)


try:
	TPClient = Client(
		pluginId = GK_PLUGIN_ID,
		sleepPeriod = 0.05,
		autoClose = True,
		checkPluginId = True,
		maxWorkers = 6
	)
except Exception as e:
	sys.exit(f"Could not create TP Client, exiting. Error was:\n{repr(e)}")

g_log = Logger(getLogger())
g_settings = GKSettings()
g_parser = GameProfileParser()
g_observer = None  # WatcherThread
g_lgsdi = None     # LGSDInterface

## Utilities

def profilesPath():
	return os.path.join(g_settings.profDir, "profiles")

def getProfileById(guid):
	return g_settings.profiles.get(guid)

def currentProfile():
	return getProfileById(g_settings.currProfileId)

def getProfileByName(name):
	for _, prof in g_settings.profiles.items():
		if prof.name == name:
			return prof
	return None

def getLastUsedProfile():
	ret = None
	newest = datetime(1970, 1, 1)
	for _, prof in g_settings.profiles.items():
		if prof.lpd > newest:
			newest = prof.lpd
			ret = prof
	# g_log.dbg(f"Last used profile: {ret.name} on {newest}")
	return ret

def profileIdFromPath(path):
	try:
		return os.path.split(path)[1].split(".")[0]
	except:
		return ""

def normalizedDeviceTypes():
	return [x.split(".")[0] for x in g_settings.useDeviceTypes]

def getDataMapForDevice(device):
	return GK_DEV_DATA_MAP.get(device, (0, 0, "", ""))

def stateIdForCurrentMacroName(dev_code, key_pfx, key):
	return GK_STATE_ROOT + dev_code + "." + key_pfx + str(key)

def stateIdForStateMacroName(dev_code, key_pfx, key, state):
	return stateIdForCurrentMacroName(dev_code, key_pfx, key) + f"M{state:d}"

def stateIdForButtonPressState(dev_code, key_pfx, key):
	return stateIdForCurrentMacroName(dev_code, key_pfx, key) + ".pressed"

def boolFromName(name:str):
	return name.lower() not in ("0","false","disable","disabled","no","n")

def boolToName(state:bool):
	return ("Disabled", "Enabled")[int(state)]


## File system watcher handling

def startObserver():
	global g_observer
	if g_observer and g_observer.is_alive():
		return
	g_log.dbg("Starting Observer")
	g_observer = WatcherThread(profilesPath(), onProfilesChanged, g_settings.profilePollInterval)
	g_observer.start()

def stopObserver():
	global g_observer
	if g_observer is None or not g_observer.is_alive():
		return
	g_log.dbg("Shutting Down Observer")
	g_observer.join(5)
	g_observer = None

# called by observer thread using Timer
def onProfilesChanged(added, modified, deleted):
	modified.extend(added)
	if modified: onProfilesModified(modified)
	if deleted: onProfilesDeleted(deleted)

def onProfilesModified(paths):
	global g_settings
	switch_to = None
	last_played = datetime(1970, 1, 1)
	if (last_prof := getProfileById(g_settings.lastPlayedProfId)):
		last_played = last_prof.lpd
	for path in paths:
		if not (prof_id := profileIdFromPath(path)):
			continue
		saved_prof = g_settings.profiles.get(prof_id)
		if saved_prof and saved_prof.fsize == os.stat(path).st_size:
			# if using debug interface for profile swithces and size has not changed, assume it's just a profile switch
			if g_settings.useLGSDI:
				continue
			# quick check for modified profile by just parsing the "header" meta data
			if not (new_prof := g_parser.parse_profile(path, header_only=True)):
				continue
			# Check if only the "last played date" has channged, w/out file size change, meaning profile was only selected (not edited)
			if new_prof.lpd > saved_prof.lpd:
				g_settings.profiles[prof_id].lpd = new_prof.lpd
				if new_prof.lpd > last_played:
					switch_to = saved_prof
					last_played = new_prof.lpd
				continue
		# new or modified profile, parse the whole file
		if (new_prof := reloadProfile(prof_id)):
			if new_prof.lpd > last_played:
				switch_to = new_prof
				last_played = new_prof.lpd
	#
	if switch_to:
		g_settings.lastPlayedProfId = switch_to.guid
		if g_settings.autoSwitchProfiles:
			setCurrentProfile(switch_to)

def onProfilesDeleted(paths):
	global g_settings
	for path in paths:
		if (prof_id := profileIdFromPath(path)):
			del g_settings.profiles[prof_id]
			if prof_id == g_settings.currProfileId:
				setCurrentProfile(getProfileByName("Default Profile"))
	updateAvailableProfilesChoice()


## LGS Debug Interface handler

def startLGSDI():
	global g_lgsdi, g_settings
	if sys.platform != "win32" or g_lgsdi:
		return
	try:
		g_lgsdi = LGSDInterface(onLgsdiMessage)
		lgsdiSetFilter()
		g_lgsdi.connect()
	except Exception as e:
		g_log.warn(f"Error starting LGSDI: {repr(e)}")
		g_lgsdi = None
	else:
		g_settings.useLGSDI = True
		g_log.info("Using LGS Debug Interface for monitoring events.")

def stopLGSDI():
	global g_lgsdi
	if g_lgsdi:
		g_log.dbg("Stopping LGSDI...")
		g_settings.useLGSDI = False
		g_lgsdi.disconnect()
		g_lgsdi = None

def lgsdiSetFilter():
	global g_lgsdi
	if not g_lgsdi:
		return
	filt = ["M_PRESSED", "PROFILE_ACTIVATED"]
	if g_settings.reportBtnStates:
		devices = normalizedDeviceTypes()
		if "Keyboard" in devices:
			filt.extend(["G_PRESSED", "G_RELEASED"])
		if "Mouse" in devices:
			filt.extend(["MOUSE_BUTTON_PRESSED", "MOUSE_BUTTON_RELEASED"])
	g_lgsdi.set_filter(filt)


# called directly by LGSDInterface
def onLgsdiMessage(msg):
	global g_settings
	g_log.dbg(f"Get message from LGSDI: {msg}")
	parts = msg.split(".")
	if len(parts) < 3:
		g_log.warn(f"Got LSGDI message in wrong format: {msg}")
		return
	act = str(parts[0])
	dev = str(parts[1])
	arg = ".".join(parts[2:])
	if act == "PROFILE_ACTIVATED":
		prof = None
		if arg.startswith("{"):
			prof = getProfileById(arg)
		else:
			prof = getProfileByName(arg)
		if not prof:
			g_log.warn(f"Could not find profile for name/id: {arg}")
			return
		g_settings.profiles[prof.guid].lpd = datetime.now()
		g_settings.lastPlayedProfId = prof.guid
		if g_settings.autoSwitchProfiles:
			setCurrentProfile(prof)
	elif act == "M_PRESSED":
		setCurrentShiftState(dev, int(arg))
	elif g_settings.reportBtnStates:
		# this assumes we're already filtering out "M_RELEASED" events
		state = act.endswith("_PRESSED")
		if state or act.endswith("_RELEASED"):
			if (key_pfx := getDataMapForDevice(GK_DEV_FAMILY_MAP.get(dev))[2]):
				TPClient.stateUpdate(stateIdForButtonPressState(dev, key_pfx, int(arg)), str(int(state)))


## TP interaciton handlers, mostly called by TPClient (directly or indirectly)

def sendMessage(msg):
	TPClient.stateUpdate(GK_STATE_MESSAGE, msg)

def setCurrentProfile(profile):
	global g_settings  #, state_change_flag
	if not profile or g_settings.currProfileId == profile.guid:
		return
	g_settings.currProfileId = profile.guid
	g_settings.currProfileName = profile.name
	updateStatesForProfile(profile)
	g_settings.ignoreNextSettingsChange = True
	TPClient.settingUpdate(GK_SET_LAST_PROF, profile.guid)
	sendMessage("Profile activated: " + profile.name)

def setCurrentShiftState(device, state, force=False):
	global g_settings
	if g_settings.currShiftState.get(device) == state and not force:
		return
	g_settings.currShiftState[device] = state
	state_name = GK_STATE_ROOT + device + GK_STATE_KBD_MEM_SLOT_SFX
	TPClient.stateUpdate(state_name, str(state))
	updateKeyStates(currentProfile(), True)

def updateStatesForProfile(profile):
	if not profile:
		return
	TPClient.stateUpdate(GK_STATE_PROF_NAME, profile.name)
	updateKeyStates(profile, False)
	updateMemorySlotNameStates(profile)

def updateAutoswitchState(state = True):
	text = boolToName(state)  # ("Disabled", "Enabled")[int(state)]
	TPClient.stateUpdate(GK_STATE_AUTOSW_TOGGLE, text)
	sendMessage("Automatic profile switching " + text)

def updateAvailableProfilesChoice():
	names = []
	for (_, prof) in g_settings.profiles.items():
		names.append(prof.name)
	names.sort()
	TPClient.choiceUpdate(GK_ACT_SWITCH_PROF_DATA, names)
	# TPClient.choiceUpdate(GK_EVT_PROF_CHANGE, names)  # can't update event valueChoices in TP :(

def updateMemorySlotNameStates(profile):
	states = []
	for dev in GK_DEV_DATA_MAP.values():
		_, max_sts, _, dev_code = dev
		if max_sts < 2:
			continue
		sname = GK_STATE_ROOT + dev_code + "."
		for slot, name in profile.getStateNames(dev_code, max_sts).items():
			states.append({"id": sname + slot + ".name", "value": name})
	if len(states):
		TPClient.stateUpdateMany(states)

def updateKeyStates(profile, state_only=False):
	if not profile:
		return
	states = []
	for devtype in normalizedDeviceTypes():
		max_keys, max_sts, key_pfx, dev_code = getDataMapForDevice(devtype)
		curr_state = g_settings.currShiftState.get(dev_code, 1)
		# print(devtype, st_name, max_keys)
		for key in range(1, max_keys+1):
			for state in range(1, max_sts+1):
				keyname = f"{key_pfx:s}{key:d}M{state:d}"
				value = g_settings.unmappedButtonText
				if (macro := profile.getMacroForDeviceKey(devtype, keyname)):
					value = macro.name
				if state == curr_state or max_sts == 1:
					# sname = GK_STATE_ROOT + dev_code + "." + currkeyname
					sname = stateIdForCurrentMacroName(dev_code, key_pfx, key)
					currkeyname = key_pfx + str(key)
					if max_sts > 1: currkeyname += " (current M slot)"
					states.append({"id": sname, 'desc': devtype+" "+currkeyname, "value": value})
					# print(sname, currkeyname, value)
				if not state_only and max_sts > 1:
					sname = stateIdForStateMacroName(dev_code, key_pfx, key, state)
					states.append({"id": sname, 'desc': devtype+" "+keyname, "value": value})
		# default shift state for this device
		if not g_settings.currShiftState.get(dev_code):
			g_settings.currShiftState[dev_code] = 1
	if states:
		TPClient.createStateMany(states)

def removeDynamicDeviceStates():
	states = []
	for devtype in normalizedDeviceTypes():
		max_keys, max_sts, key_pfx, dev_code = getDataMapForDevice(devtype)
		for key in range(1, max_keys+1):
			for state in range(1, max_sts+1):
				states.append(stateIdForCurrentMacroName(dev_code, key_pfx, key))
				states.append(stateIdForStateMacroName(dev_code, key_pfx, key, state))
	if states:
		TPClient.removeStateMany(states)

def addDynamicPressStates():
	states = []
	for devtype in normalizedDeviceTypes():
		max_keys, _, key_pfx, dev_code = getDataMapForDevice(devtype)
		for key in range(1, max_keys+1):
			states.append({
				"id": stateIdForButtonPressState(dev_code, key_pfx, key),
				'desc': f"{devtype} {key_pfx}{key} Press State",
				"value": "0"
			})
	if states:
		TPClient.createStateMany(states)

def removeDynamicPressStates():
	states = []
	for devtype in normalizedDeviceTypes():
		max_keys, _, key_pfx, dev_code = getDataMapForDevice(devtype)
		for key in range(1, max_keys+1):
			states.append(stateIdForButtonPressState(dev_code, key_pfx, key))
	if states:
		TPClient.removeStateMany(states)

def reloadProfile(prof_id):
	global g_settings
	path = os.path.join(profilesPath(), prof_id + ".xml")
	if not os.path.isfile(path):
		g_log.warn(f"Profile file not found at: {path}")
		return None
	if (new_prof := g_parser.parse_profile(path, devices=g_settings.useDeviceTypes)):
		# new_prof.fsize = os.path.
		g_settings.profiles[prof_id] = new_prof
		updateAvailableProfilesChoice()
		if prof_id == g_settings.currProfileId:
			updateStatesForProfile(new_prof)
		return new_prof
	return None

def reloadAllProfiles():
	global g_settings
	if not g_settings.profDir:
		return
	g_settings.profiles = g_parser.parse_profiles(profilesPath(), g_settings.useDeviceTypes)
	# print(g_settings.profiles)
	updateAvailableProfilesChoice()
	updateStatesForProfile(currentProfile())

def handleSettingsChange(val_arry, on_connect=False):
	global g_settings
	g_log.dbg(f"Got Settings: {val_arry}")
	ignore = g_settings.ignoreNextSettingsChange
	g_settings.ignoreNextSettingsChange = False
	if ignore or not val_arry:
		return
	# the settings array can just be flattened to a single dict
	settings = {list(val_arry[i])[0]:list(val_arry[i].values())[0] for i in range(len(val_arry))}
	profile_reload = not len(g_settings.profiles)
	# profile path
	if (value := settings.get(GK_SET_PROF_DIR)) is not None:
		newpath = value if value else g_settings.profDir
		profile_reload = profile_reload or g_settings.profDir != newpath
		g_settings.profDir = newpath
		if value != newpath:
			TPClient.settingUpdate(GK_SET_PROF_DIR, newpath)
			return
	# device types to use
	if (value := settings.get(GK_SET_DEVC_CATS)) is not None:
		value = [x.strip() for x in value.split(',')]
		if value and value != g_settings.useDeviceTypes:
			g_settings.useDeviceTypes = []
			for devtype in value:
				if GK_DEV_DATA_MAP.get(devtype.split(".")[0]):
					g_settings.useDeviceTypes.append(devtype)
				else:
					g_log.warn(f"Could not find data map for device type: {devtype}")
			# remove old states, if any
			removeDynamicDeviceStates()
			profile_reload = True
	# LGSDI enable/disable
	if (value := settings.get(GK_SET_USE_LGSDI)) is not None:
		value = boolFromName(value)
		if value != g_settings.useLGSDI:
			if value: startLGSDI()
			else: stopLGSDI()
	# button press/release state reporting
	if (value := settings.get(GK_SET_SEND_BTN_STATES)) is not None:
		value = boolFromName(value)
		if value != g_settings.reportBtnStates:
			if g_settings.reportBtnStates:
				removeDynamicPressStates()
			elif g_settings.useLGSDI:
				addDynamicPressStates()
			g_settings.reportBtnStates = value
			lgsdiSetFilter()
	# profiles change poll interval
	if (value := settings.get(GK_SET_POLL_INTRVL)) is not None:
		value = max(0.0, float(int(value) / 1000))
		if value != g_settings.profilePollInterval:
			g_settings.profilePollInterval = value
			stopObserver()
			if value > 0.0:
				startObserver()
	# auto-switching of profiles
	if (value := settings.get(GK_SET_AUTO_SWTCH)) is not None:
		value = boolFromName(value)
		if value != g_settings.autoSwitchProfiles:
			g_settings.autoSwitchProfiles = value
			updateAutoswitchState(value)
			if value and g_settings.lastPlayedProfId:
				setCurrentProfile(getProfileById(g_settings.lastPlayedProfId))
	# unmapped button text
	if (value := settings.get(GK_SET_UNMAPPED_SLOT)) is not None:
		if value != g_settings.unmappedButtonText:
			g_settings.unmappedButtonText = value
			if not profile_reload:
				updateKeyStates(currentProfile())
	# set current profile ID, should only happen at initial connection
	if on_connect and (value := settings.get(GK_SET_LAST_PROF)):
		g_settings.currProfileId = value

	if profile_reload:
		reloadAllProfiles()


## TP Client event handler callbacks

# Initial connection handler
@TPClient.on(TPTYPES.onConnect)
def onConnect(data):
	global g_settings
	vstr = f"{data.get('pluginVersion', 0) * 0.01:.02f}"
	g_log.info(f"Connected to TP v{data.get('tpVersionString', '?')}, plugin v{vstr}.")
	# g_log.dbg(f"Connection: {g_log.format_json(data)}")
	if settings := data.get('settings'):
		handleSettingsChange(settings, True)
	if g_settings.profiles:
		load_prof = getLastUsedProfile() or getProfileByName("Default Profile") or g_settings.profiles.values()[0]
		g_settings.lastPlayedProfId = load_prof.guid
		if g_settings.autoSwitchProfiles:
			setCurrentProfile(load_prof)
	updateAutoswitchState(g_settings.autoSwitchProfiles)
	for dev_id in ["kb", "lhc"]:
		setCurrentShiftState(dev_id, g_settings.currShiftState.get(dev_id, 1), True)
	if g_settings.profilePollInterval > 0.0:
		startObserver()  # may have happened in handleSettingsChange() but make sure
	sendMessage(f"Connected to {GK_PLUGIN_NAME} v{__version__}")

# Action handler
@TPClient.on(TPTYPES.onAction)
def onActions(data):
	g_log.dbg(f"Action: {repr(data)}")
	if not (action_data := data.get('data')) or not (aid := data.get('actionId')):
		return
	if aid == GK_ACT_MEM_TOGGLE:
		slot_num = TPClient.getActionDataValue(action_data, GK_ACT_MEM_TOGGLE_SLT)
		dev_id = TPClient.getActionDataValue(action_data, GK_ACT_MEM_TOGGLE_DEV)
		if slot_num and dev_id:
			if (dev_id := getDataMapForDevice(dev_id)[3]):
				setCurrentShiftState(str(dev_id), int(slot_num))
	elif aid == GK_ACT_SWITCH_PROF:
		if (pname := TPClient.getActionDataValue(action_data, GK_ACT_SWITCH_PROF_DATA)):
			setCurrentProfile(getProfileByName(pname))
	elif aid == GK_ACT_AUTOSW_TOGGLE:
		# the actual toggle happens in handleSettingsChange()
		TPClient.settingUpdate(GK_SET_AUTO_SWTCH, boolToName(not g_settings.autoSwitchProfiles))
	elif aid == GK_ACT_RELOAD_CURR and g_settings.currProfileId:
		reloadProfile(g_settings.currProfileId)
		sendMessage(f"Reloaded profile {g_settings.currProfileName}.")
	elif aid == GK_ACT_RELOAD_ALL:
		reloadAllProfiles()
		sendMessage("All profiles reloaded.")
	else:
		g_log.warn("Got unknown action ID: " + aid)

# Settings handler
@TPClient.on(TPTYPES.onSettingUpdate)
def onSettings(data):
	# g_log.dbg(f"Settings: {g_log.format_json(data)}")
	if (settings := data.get('values')):
		handleSettingsChange(settings)

# Page change handler
@TPClient.on(TPTYPES.onBroadcast)
def onBroadcast(data):
	# g_log.dbg(f"Broadcast: {g_log.format_json(data)}")
	if data.get('event', "") == "pageChange":
		setCurrentProfile(getProfileByName(data.get("pageName", "")))

# Shutdown handler
@TPClient.on(TPTYPES.onShutdown)
def onShutdown(data):
	g_log.info('Received shutdown event from TP Client.')
	# TPClient.disconnect()

# Error handler
@TPClient.on(TPTYPES.onError)
def onError(exc):
	g_log.err(f'Error in TP Client event handler: {repr(exc)}')
	# ... do something ?

# Held action pressed handler
# @TPClient.on(TPTYPES.onHold_down)
# def onHoldDown(_, data):
# 	g_log.dbg(f"down: {g_log.format_json(data)}")

# Held action released handler
# @TPClient.on(TPTYPES.onHold_up)
# def onHoldUp(_, data):
# 	g_log.dbg(f"up: {g_log.format_json(data)}")

# List selection change handler
# @TPClient.on(TPTYPES.onListChange)
# def onListChange(_, data):
#   g_log.dbg(f"listChange: {g_log.format_json(data)}")


## main

def main():
	global g_settings, TPClient
	ret = 0

	# handle CLI arguments
	parser = ArgumentParser()
	parser.add_argument("-d", action='store_true',
											help="Use debug logging.")
	parser.add_argument("-w", action='store_true',
											help="Only logging warnings and errors.")
	parser.add_argument("-q", action='store_true',
											help="Disable all logging (quiet).")
	parser.add_argument("-l", metavar="<logfile>",
											help="Log to this file (default is stdout).")
	parser.add_argument("-s", action='store_true',
											help="If logging to file, also output to stdout.")
	parser.add_argument("--tpstart", action='store_true',
											help=APSUPPRESS) # Started by TouchPortal. Do not use interactively.

	opts = parser.parse_args()
	del parser

	# set up logging
	logger = g_log.logger
	if opts.q:
		logger.addHandler(NullHandler())
	else:
		fmt = Formatter(
			fmt="{asctime:s}.{msecs:03.0f} [{levelname:.1s}] [{filename:s}:{lineno:d}] {message:s}",
			datefmt="%m%dT%H%M%S", style="{"
		)
		if opts.d:
			logger.setLevel(DEBUG)
		elif opts.w:
			logger.setLevel(WARNING)
		else:
			logger.setLevel(INFO)
		if opts.l:
			try:
				if os.path.exists(opts.l):
					# "rotate" old log to backup
					bak = opts.l + ".bak"
					if os.path.exists(bak):
						os.remove(bak)
					os.rename(opts.l, bak)
				fh = FileHandler(str(opts.l))
				fh.setFormatter(fmt)
				logger.addHandler(fh)
			except Exception as e:
				opts.s = True
				print(f"Error while creating file logger, falling back to stdout. {repr(e)}")
		if not opts.l or opts.s:
			sh = StreamHandler(sys.stdout)
			sh.setFormatter(fmt)
			logger.addHandler(sh)
	del logger

	# check if started by TouchPortal
	started_by = ""
	if opts.tpstart:
		g_settings.startedByTP = True
		started_by = "Started by TouchPortal."

	# ready to go
	g_log.info(f"Starting {GK_PLUGIN_NAME} v{__version__} on {sys.platform}. {started_by}")

	try:
		TPClient.connect()  # blocking
		g_log.info('TP Client closed.')
	except KeyboardInterrupt:
		g_log.warn("Caught keyboard interrupt, exiting.")
	except Exception:
		g_log.err(f"Exception in TP Client:\n{format_exc()}")
		ret = -1
	finally:
		TPClient.disconnect()  # make sure it's stopped, no-op if alredy stopped.
	# TP disconnected, clean up.
	stopLGSDI()
	stopObserver()
	del TPClient
	del g_settings

	g_log.info(f"{GK_PLUGIN_NAME} stopped.")
	return ret


if __name__ == "__main__":
	sys.exit(main())
