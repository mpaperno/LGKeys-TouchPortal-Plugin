
import os
import sys
from dataclasses import dataclass, field
from threading import (Thread, Timer, Event)
# import socket
# import selectors
# import struct
# import time
import argparse
import logging
from datetime import datetime, timedelta
import traceback
import xml.etree.ElementTree as ET
import modules.TouchPortalAPI as TP
import modules.utils as utils

# Settings defaults
if sys.platform == "win32":
  GK_DEFAULT_LGS_PROFILE_PATH = os.getenv('LOCALAPPDATA', "") + r"\Logitech\Logitech Gaming Software"
elif sys.platform == "darwin":
  GK_DEFAULT_LGS_PROFILE_PATH = os.path.expanduser("~/Library/Application Support/Logitech")
else:
  sys.exit(f"Unsupported/unknown platform: {sys.platform}")

GK_DEFAULT_DEVICE_TYPES = [
    "Keyboard",
    # "LeftHandedController",
    # "Mouse.G700s",
    # "Headset"
  ]


### LGS profile file parsing

# XML namespaces used in profile data, map to short versions for ElementTree parsing.
GK_GP_XMLNS = {
  'pr': 'http://www.logitech.com/Cassandra/2010.7/Profile',
  'ks': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/Keystroke',
  'mk': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/MultiKey',
  'mf': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/MouseFunction',
  'tb': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/TextBlock',
  'hk': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/Hotkeys',
  'sc': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/Shortcut',
  'fn': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/Function',
  'md': 'ttp://www.logitech.com/Cassandra/2010.1/Macros/Media',
}

@dataclass
class GameProfile:
  guid: str = ""
  name: str = ""
  desc: str = ""
  lpd: datetime = datetime(1970, 1, 1)   # last played (used) date
  fsize: int = 0    # profile file size, for change tracking
  target: str = ""  # associated application
  macros: dict = field(default_factory=dict)
  assignments: dict = field(default_factory=dict)

@dataclass
class GameMacro:
  guid:str = ""
  name:str = ""
  mtype:str = ""  # macro type as name of subkey (future use?)

@dataclass
class GameAssignment:
  macroguid:str = ""   # associated macro
  contextid:str = ""   # associated key name
  shiftstate:int = 1   # associated key memory slot (1-3)

def parse_profile(fn, devices, header_only=False):
  log.dbg(f"Loading profile from {fn}")
  try:
    prof = ET.parse(fn).getroot().find('pr:profile', GK_GP_XMLNS)
    if not prof:
      log.warn(f"Could not find 'profile' element in XML tree!")
      return None
    # log.dbg(f"Root: {rootel.tag}; Prof: {prof}")
    new_prof = GameProfile(prof.get('guid'), prof.get('name'))

    if not new_prof.guid or not new_prof.name:
      log.warn(f"Profile was parsed but had no GUID and/or Name.")
      return None

    if lpd := prof.get('lastplayeddate'):
      try: new_prof.lpd = datetime.strptime(lpd, "%Y-%m-%dT%H:%M:%S")
      except: pass
    if desc := prof.find('pr:description', GK_GP_XMLNS):
      new_prof.desc = desc.text
    if tgt := prof.findall('pr:target', GK_GP_XMLNS):
      new_prof.target = tgt[0].get('path')

    if header_only:
      return new_prof

    for macro in prof.iterfind('./pr:macros/pr:macro', GK_GP_XMLNS):
      if macro.get('hidden', "false") == "true" or macro.get('backupguid', None):
        continue
      new_macro = GameMacro(macro.get('guid'), macro.get('name'))
      if not new_macro.guid or not new_macro.name or not len(macro):
        continue
      new_macro.mtype = list(macro)[0].tag.split("}", 1)[1]
      new_prof.macros[new_macro.guid] = new_macro
      # log.dbg(f"Macro: {vars(new_macro)}")

    for assign_device in prof.iterfind('pr:assignments', GK_GP_XMLNS):
      # devicecategory is: Logitech.Gaming.<device_type>[.<model>]
      # we only match on the actual device type and (optionally) model
      devcat_arry = assign_device.get('devicecategory', "").split('.')
      if len(devcat_arry) > 2:
        devcat = ".".join(devcat_arry[2:])
      if devcat not in devices:
        continue
      devcat = devcat_arry[2]  # just keep the base device type
      new_prof.assignments[devcat] = {}
      for assign in assign_device.iterfind('pr:assignment', GK_GP_XMLNS):
        if assign.get('backup') == "true":
          continue
        new_assign = GameAssignment(assign.get('macroguid'), assign.get('contextid'), assign.get('shiftstate'))
        if not new_assign.macroguid:
          continue
        new_prof.assignments[devcat][f"{new_assign.contextid}M{new_assign.shiftstate}"] = new_assign
        # log.dbg(f"Assignment: {vars(new_assign)}")
    # log.dbg(f"Profile: {vars(new_prof)}\n\n")
    return new_prof

  except Exception as e:
    log.err(f"Error parsing {fn}: {e}")
    return None


def parse_profiles(path, devices):
  profiles = {}
  if not path:
    return profiles
  log.dbg(f"Loading profiles from {path}")
  try:
    with os.scandir(path) as it:
      for entry in it:
        if entry.is_file and entry.name.endswith(".xml"):
          if new_prof := parse_profile(entry.path, devices):
            new_prof.fsize = entry.stat().st_size
            profiles[new_prof.guid] = new_prof
  except Exception as e:
    log.warn(f"Parse_profiles error: {e}")

  return profiles


### File system watchdog process

def watch_profiles(path, stop_event, interval = 2.0, ext = ".xml"):

  def files_to_timestamp():
    ret = {}
    with os.scandir(path) as it:
      for entry in it:
        if entry.is_file and entry.name.endswith(ext):
          ret[entry.path] = entry.stat().st_mtime_ns
    return ret

  usewin32 = sys.platform == "win32"
  log.dbg(f"Watching {path} [interval: {interval:.02f}s, Win32: {usewin32}]")

  if usewin32:
    import win32file
    import win32event
    import win32con
    iInterval = int(interval * 1000)
    try:
      change_handle = win32file.FindFirstChangeNotification(
        path, False, win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
      )
    except Exception as e:
      log.err(f"Win32 error in FindFirstChangeNotification(), reverting to polling mode. Error: {repr(e)}")
      usewin32 = False

  before = files_to_timestamp()
  try:
    while not stop_event.is_set():
      if usewin32:
        wait_result = win32event.WaitForSingleObject(change_handle, iInterval)
        if wait_result != win32con.WAIT_OBJECT_0:
          continue
      elif stop_event.wait(timeout=interval):
        break

      after = files_to_timestamp()
      added = [f for f in after.keys() if not f in before.keys()]
      removed = []
      modified = []
      # modified = {}
      for (f, m) in before.items():
        if not f in after.keys():
          removed.append(f)
        elif (os.stat(f).st_mtime_ns - m) > 50000000:  # ignore < 50ms deltas
          modified.append(f)
          # modified[f] = m
      if removed:
        log.dbg('Removed: {}'.format(', '.join(removed)))
        Timer(0, onProfilesDeleted, [removed]).start()
      if added or modified:
        modified.extend(added)
        # sort by ascending mtime
        # modsorted = [k for k,_ in sorted(modified.items(), key=lambda x: x[1])]
        log.dbg('Modified: {}'.format(', '.join(modified)))
        Timer(0.001, onProfilesModified, [modified]).start()  # delay 1ms otherwise files may still be unreadable
      # if added: print('Added: {}'.format(', '.join(added)))

      before = after
      if usewin32:
        win32file.FindNextChangeNotification(change_handle)
    #
  except Exception as e:
    log.err(f"Exception in file system watcher, exiting: {repr(e)}")
  else:
    log.dbg("File watcher got IRQ, stopping")
  finally:
    if usewin32:
      win32file.FindCloseChangeNotification(change_handle)


### Plugin main

GK_PLUGIN_VERSION = 0x0100  # maj|min
GK_PLUGIN_VERSION_STR = "1.0"
GK_PLUGIN_NAME = "LGKeys TouchPortal Plugin"
GK_PLUGIN_ID = 'us.wdg.max.tpp.lgk'
GK_SET_PROF_DIR = "Profiles Directory"
GK_SET_DEVC_CATS = "Device Type(s)"
GK_SET_AUTO_SWTCH = "Auto-switch Profiles"
GK_SET_POLL_INTRVL = "Profile Change Poll Interval (ms)"
GK_SET_UNMAPPED_SLOT = "Unmapped Button Text"
GK_SET_LAST_PROF = "Last Active Profile"
GK_ACT_SWITCH_PROF = GK_PLUGIN_ID + ".act.switchProfile"
GK_ACT_SWITCH_PROF_DATA = GK_ACT_SWITCH_PROF + ".profileName"
GK_ACT_MEM_TOGGLE = GK_PLUGIN_ID + ".act.memToggle"
GK_ACT_AUTOSW_TOGGLE = GK_PLUGIN_ID + ".act.autoSwitch"
GK_STATE_PROF_NAME = GK_PLUGIN_ID + ".state.currentProfileName"
GK_STATE_AUTOSW_TOGGLE = GK_PLUGIN_ID + ".state.autoSwitch"
GK_STATE_MEM_SLOT = GK_PLUGIN_ID + ".state.memorySlot"
GK_STATE_KEYS_PFX = GK_PLUGIN_ID + ".state."
# GK_STATE_PROF_LIST = GK_PLUGIN_ID + ".state.profilesList"  # can't update Event valueChoices in TP
# GK_EVT_PROF_CHANGE = GK_PLUGIN_ID + ".event.currentProfileChanged"  # also doesn't work
# GK_STATE_PROF_CHANGE_FLG = GK_PLUGIN_ID + ".state.currentProfileChangedFlag"  # also doesn't work

# device name : (max keys, max states, game profile contextId prefix, suffix for TP State id)
GK_DEV_DATA_MAP = {
  "Keyboard"             : (18, 3, "G",      "kbd"),
  "LeftHandedController" : (29, 3, "G",      "lhc"),
  "Mouse"                : (20, 1, "Button", "mouse"),
  "Headset"              : ( 3, 1, "G",      "hs")  # not sure of "G"
}

@dataclass
class GKSettings:
  profDir: str = GK_DEFAULT_LGS_PROFILE_PATH
  useDeviceTypes: list = field(default_factory=list)
  currProfileId: str = ""
  currProfileName: str = "Default Profile"
  lastPlayedProfId: str = ""
  unmappedButtonText: str = "..."
  currShiftState: int = 1
  autoSwitchProfiles: bool = True
  profilePollInterval: float = 1.0
  startedByTP: bool = False


log = utils.Logger(logging.getLogger("lgkeys"))
g_settings = GKSettings(GK_DEFAULT_LGS_PROFILE_PATH, GK_DEFAULT_DEVICE_TYPES)
g_profiles = {}
g_observer = None
g_observer_stop_evt = Event()
TPClient = TP.Client(GK_PLUGIN_ID)

## Utilities

def profilesPath():
  return g_settings.profDir + r"\profiles"

def getProfileById(guid):
  return g_profiles.get(guid)

def currentProfile():
  return getProfileById(g_settings.currProfileId)

def getProfileByName(name):
  for _, prof in g_profiles.items():
    if prof.name == name:
      return prof
  return None

def getLastUsedProfile():
  ret = None
  newest = datetime(1970, 1, 1)
  for _, prof in g_profiles.items():
    if prof.lpd > newest:
      newest = prof.lpd
      ret = prof
  log.dbg(f"Last used profile: {ret.name} on {newest}")
  return ret


## File system watcher handling, called by observer thread

def startObserver():
  global g_observer
  if g_observer and g_observer.is_alive():
    return
  g_observer = Thread(target=watch_profiles, args=(profilesPath(), g_observer_stop_evt, g_settings.profilePollInterval))
  g_observer.setDaemon(True)
  log.dbg("Starting Observer")
  g_observer_stop_evt.clear()
  g_observer.start()

def stopObserver():
  global g_observer
  if g_observer is None or not g_observer.is_alive():
    return
  log.dbg("Shutting Down Observer")
  g_observer_stop_evt.set()
  g_observer.join(5)
  g_observer = None


def onProfilesModified(paths):
  global g_profiles, g_settings
  switch_to = None
  last_played = datetime(1970, 1, 1)
  for path in paths:
    try:
      prof_id = os.path.split(path)[1].split(".")[0]
    except:
      return
    saved_prof = g_profiles.get(prof_id)
    new_prof = parse_profile(path, g_settings.useDeviceTypes, True)
    if not new_prof:
      return
    fsize = os.stat(path).st_size
    # Check if only the "last played date" has channged, w/out file size change, meaning profile was only selected (not edited)
    if saved_prof and new_prof.lpd > saved_prof.lpd and fsize == saved_prof.fsize:
      if g_settings.lastPlayedProfId and log.logger.isEnabledFor(logging.DEBUG):
        log.dbg(f"Detected profile switch from {g_profiles[g_settings.lastPlayedProfId].name} to {new_prof.name} (LPD:{saved_prof.lpd} -> {new_prof.lpd})")
      g_profiles[prof_id].lpd = new_prof.lpd
      # last_played = max(last_played, new_prof.lpd)
      if new_prof.lpd > last_played:
        switch_to = saved_prof
        last_played = new_prof.lpd
      continue
    # new or modified profile
    new_prof = parse_profile(path, g_settings.useDeviceTypes, False)
    new_prof.fsize = fsize
    g_profiles[prof_id] = new_prof
    updateAvailableProfilesChoice()
    if prof_id == g_settings.currProfileId:
      updateKeyStates(new_prof)
      TPClient.stateUpdate(GK_STATE_PROF_NAME, new_prof.name)
  #
  if switch_to and g_settings.lastPlayedProfId != switch_to.guid:
    g_settings.lastPlayedProfId = switch_to.guid
    if g_settings.autoSwitchProfiles:
      setCurrentProfile(switch_to)

def onProfilesDeleted(paths):
  global g_profiles
  for path in paths:
    try:
      prof_id = os.path.split(path)[1].split(".")[0]
    except:
      continue
    del g_profiles[prof_id]
    if prof_id == g_settings.currProfileId:
      setCurrentProfile(getProfileByName("Default Profile"))


## TP interaciton handlers, called by TPClient (directly or indirectly)

def updateKeyStates(profile, state_only=False):
  if not profile:
    return
  states = []
  curr_state = g_settings.currShiftState
  for devtype in g_settings.useDeviceTypes:
    devtype = devtype.split(".")[0]
    max_keys, max_sts, key_pfx, st_name = GK_DEV_DATA_MAP.get(devtype, (0, 0, "", ""))
    if not max_keys:
      log.warn(f"Could not find data map for device type: {devtype}")
      continue
    assignments = profile.assignments.get(devtype)
    # print(devtype, st_name, max_keys, assignments)
    for key in range(1, max_keys+1):
      for state in range(1, max_sts+1):
        value = g_settings.unmappedButtonText
        keyname = f"{key_pfx:s}{key:d}M{state:d}"
        if assignments and (assign := assignments.get(keyname)):
          if macro := profile.macros.get(assign.macroguid):
            value = macro.name
        if state == curr_state or max_sts == 1:
          currkeyname = key_pfx + str(key)
          sname = GK_STATE_KEYS_PFX + st_name + "." + currkeyname
          if sname not in TPClient.currentStates:
            if max_sts > 1: currkeyname += " (current M slot)"
            TPClient.createState(sname, f"{devtype} {currkeyname}", value)
          else:
            states.append({"id": sname, "value": value})
          # print(sname, currkeyname, value)
        if not state_only and max_sts > 1:
          sname = GK_STATE_KEYS_PFX + st_name + "." + keyname
          if sname not in TPClient.currentStates:
            TPClient.createState(sname, f"{devtype} {keyname}", value)
          else:
            states.append({"id": sname, "value": value})
  if len(states):
    TPClient.stateUpdateMany(states)
    # print(states)


def updateAvailableProfilesChoice():
  names = []
  for (_, prof) in g_profiles.items():
    names.append(prof.name)
  names.sort()
  TPClient.choiceUpdate(GK_ACT_SWITCH_PROF_DATA, names)
  # TPClient.choiceUpdate(GK_EVT_PROF_CHANGE, names)  # can't update event valueChoices in TP

# state_change_flag = 0
def setCurrentProfile(profile):
  global g_settings  #, state_change_flag
  if not profile or g_settings.currProfileId == profile.guid:
    return
  g_settings.currProfileId = profile.guid
  g_settings.currProfileName = profile.name
  TPClient.stateUpdate(GK_STATE_PROF_NAME, profile.name)
  # TPClient.stateUpdate(GK_STATE_PROF_CHANGE_FLG, str(state_change_flag))
  # state_change_flag += 1
  TPClient.settingUpdate(GK_SET_LAST_PROF, profile.guid)
  updateKeyStates(profile, False)

def setCurrentShiftState(state):
  global g_settings
  if g_settings.currShiftState == state:
    return
  g_settings.currShiftState = state
  TPClient.stateUpdate(GK_STATE_MEM_SLOT, str(g_settings.currShiftState))
  curr_prof = currentProfile()
  if curr_prof is not None:
    updateKeyStates(curr_prof, True)

def updateAutoswitchState(state = True):
  TPClient.stateUpdate(GK_STATE_AUTOSW_TOGGLE, ("Disabled", "Enabled")[int(state)])

def handleSettingsChange(val_arry):
  global g_settings, g_profiles
  log.dbg(f"Got Settings: {val_arry}")
  if not val_arry:
    return
  # the settings array can just be flattened to a single dict
  settings = {list(val_arry[i])[0]:list(val_arry[i].values())[0] for i in range(len(val_arry))}
  profile_reload = not len(g_profiles)
  # log.dbg(settings)
  # profile path
  if (value := settings.get(GK_SET_PROF_DIR)) is not None:
    newpath = value if value else g_settings.profDir
    profile_reload = profile_reload or g_settings.profDir != newpath
    g_settings.profDir = newpath
    if value != newpath:
      TPClient.settingUpdate(GK_SET_PROF_DIR, newpath)
  # device types to use
  if (value := settings.get(GK_SET_DEVC_CATS)) is not None:
    value = [x.strip() for x in value.split(',')]
    # value = list(filter(lambda x: x in GK_DEV_CAT_MAP, value))
    if value != g_settings.useDeviceTypes:
      # log.dbg(f"New device type(s): {value} - current: {g_settings.useDeviceTypes}")
      g_settings.useDeviceTypes = value
      profile_reload = True
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
    value = bool(int(value))
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
  # last saved profile, used at startup
  # if msgtype == "info" and (value := settings.get(GK_SET_LAST_PROF)):
  #   g_settings.currProfileId = value
    # onConnect() will handle loading profile if needed

  if profile_reload and g_settings.profDir:
    g_profiles = parse_profiles(profilesPath(), g_settings.useDeviceTypes)
    # print(g_profiles)
    updateAvailableProfilesChoice()
    updateKeyStates(currentProfile())


# Initial connection handler
@TPClient.on(TP.TYPES.onConnect)
def onConnect(client, data):
  vstr = f"{data.get('pluginVersion', 0) * 0.01:.02f}"
  log.info(f"Connected to TP v{data.get('tpVersionString', '?')}, plugin v{vstr}.")
  log.dbg(f"Connection: {log.format_json(data)}")
  if settings := data.get('settings'):
    if (value := next((x.get(GK_SET_LAST_PROF) for x in settings if x.get(GK_SET_LAST_PROF)), None)):
      g_settings.currProfileId = value
    handleSettingsChange(settings)
  if g_profiles:
    load_prof = getLastUsedProfile() or getProfileByName("Default Profile") or g_profiles.values()[0]
    g_settings.lastPlayedProfId = load_prof.guid
    # load_prof = getProfileById(g_settings.currProfileId) if g_settings.currProfileId else getProfileByName("Default Profile")
    if g_settings.autoSwitchProfiles:
      setCurrentProfile(load_prof)
    # else:
    #   updateKeyStates(currentProfile())
  updateAutoswitchState(g_settings.autoSwitchProfiles)
  TPClient.stateUpdate(GK_STATE_MEM_SLOT, str(g_settings.currShiftState))
  if g_settings.profilePollInterval > 0.0:
    startObserver()  # may have happened in handleSettingsChange() but make sure

# Action handler
@TPClient.on(TP.TYPES.onAction)
def onActions(client, data):
  log.dbg(f"Action: {log.format_json(data)}")
  aid = data['actionId']
  if aid == GK_ACT_MEM_TOGGLE:
    setCurrentShiftState(int(data['data'][0]['value']))
  elif aid == GK_ACT_SWITCH_PROF:
    setCurrentProfile(getProfileByName(data['data'][0]['value']))
  elif aid == GK_ACT_AUTOSW_TOGGLE:
    state = not g_settings.autoSwitchProfiles
    TPClient.settingUpdate(GK_SET_AUTO_SWTCH, str(int(state)))
    # updateAutoswitchState(g_settings.autoSwitchProfiles)

# Settings handler
@TPClient.on(TP.TYPES.onSettingUpdate)
def onSettings(client, data):
  # log.dbg(f"Settings: {log.format_json(data)}")
  if settings := data.get('values'):
    handleSettingsChange(settings)

# Page change handler
@TPClient.on(TP.TYPES.onBroadcast)
def onBroadcast(client, data):
  log.dbg(f"Broadcast: {log.format_json(data)}")
  if data.get('event', "") == "pageChange":
    setCurrentProfile(getProfileByName(data.get("pageName", "")))

# List selection change handler
# @TPClient.on(TP.TYPES.onListChange)
# def onListChange(client, data):
#   log.dbg(f"listChange: {log.format_json(data)}")

# Shutdown handler
@TPClient.on(TP.TYPES.onShutdown)
def onShutdown(client, data):
  log.info('Received shutdown message from TP.')
  TPClient.disconnect()


## main

def main():
  global g_settings
  ret = 0

  # handle CLI arguments
  parser = argparse.ArgumentParser()
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
                      help=argparse.SUPPRESS) # Started by TouchPortal. Do not use interactively.

  opts = parser.parse_args()
  del parser

  # set up logging
  logger = log.logger
  if opts.q:
    logger.addHandler(logging.NullHandler())
  else:
    fmt = logging.Formatter(
      fmt="{asctime:s}.{msecs:03.0f} [{levelname:.1s}] [{filename:s}:{lineno:d}] {message:s}",
      datefmt="%m%dT%H%M%S", style="{"
    )
    if opts.d:
      logger.setLevel(logging.DEBUG)
    elif opts.w:
      logger.setLevel(logging.WARNING)
    else:
      logger.setLevel(logging.INFO)
    if opts.l:
      try:
        if os.path.exists(opts.l):
          # "rotate" old log to backup
          bak = opts.l + ".bak"
          if os.path.exists(bak):
            os.remove(bak)
          os.rename(opts.l, bak)
        fh = logging.FileHandler(str(opts.l))
        fh.setFormatter(fmt)
        logger.addHandler(fh)
      except Exception as e:
        opts.s = True
        print(f"Error while creating file logger, falling back to stdout. {repr(e)}")
    if not opts.l or opts.s:
      sh = logging.StreamHandler(sys.stdout)
      sh.setFormatter(fmt)
      logger.addHandler(sh)

  # check if started by TouchPortal
  started_by = ""
  if opts.tpstart:
    g_settings.startedByTP = True
    started_by = "Started by TouchPortal."

  # ready to go
  log.info(f"Starting {GK_PLUGIN_NAME} v{GK_PLUGIN_VERSION_STR} on {sys.platform}. {started_by}")

  try:
    TPClient.connect()  # blocking
  except KeyboardInterrupt:
    log.warn("Caught keyboard interrupt, exiting.")
  except Exception:
    log.err(f"Exception in TP client.\n{traceback.format_exc()}")
    ret = -1
  finally:
    TPClient.disconnect()  # make sure it's stopped, no-op if alredy stopped.
  # TP disconnected, clean up.
  stopObserver()
  log.info(f"{GK_PLUGIN_NAME} stopped.")
  return ret


if __name__ == "__main__":
  sys.exit(main())
