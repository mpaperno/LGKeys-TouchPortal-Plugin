'''
GameProfileParser parses and extracts data from Logitech Gaming Software
"game" profiles, specifically macro mappings for the various programmable
buttons.
'''

__copyright__ = '''
This file is part of the LGKeys TouchPortal Plugin project
Copyright Maxim Paperno; all rights reserved.

This file may be used under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A copy of the GNU General Public License is available at <http://www.gnu.org/licenses/>.
'''

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
import xml.etree.ElementTree as ET
import modules.utils as utils

__all__ = ['GameProfileParser']

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
class GameMacro:
	guid:str = ""
	name:str = ""
	mtype:str = ""  # macro type as name of subkey (future use?)

@dataclass
class GameAssignment:
	macroguid:str = ""   # associated macro
	contextid:str = ""   # associated key name
	shiftstate:int = 1   # associated key memory slot (1-3)

@dataclass
class GameProfile:
	guid: str = ""
	name: str = ""
	desc: str = ""
	lpd: datetime = datetime(1970, 1, 1)   # last played (used) date
	fsize: int = 0    # profile file size, for change tracking
	targets: list = field(default_factory=list)      # associated application(s)
	macros: dict = field(default_factory=dict)       # { 'macroguid' : GameMacro(), ... }
	assignments: dict = field(default_factory=dict)  # { 'device_type' : { '<contextid>M<shiftstate>' : GameAssignment(), 'G2M1' : GameAssignment(), ... } , ... }
	state_names: dict = field(default_factory=dict)  # { 'device_type' : {'m<shiftstate>':"name", 'm2':"Edit", ...}, ... }

	def getMacroForDeviceKey(self, device, keyname):
		if (a := self.assignments.get(device)) and (da := a.get(keyname)):
			return self.macros.get(da.macroguid)
		return None

	def getStateNames(self, device, max_slots=3):
		names = self.state_names.get(device, {})
		a_names = self.state_names.get("any", {})
		for i in range(1, max_slots+1):
			key = f"m{i}"
			if not names.get(key):
				names[key] = a_names.get(key, key.upper())
		return names


class GameProfileParser():
	def __init__(self):
		self.log = utils.Logger(getLogger(__name__))
		self.rx_state_names = re.compile(r"(?:(?:([a-z]+)\.)?M(\d):([^;]+)(?:;|\Z)\s*)", re.I)

	def parse_state_names(self, text):
		ret = {}
		for m in self.rx_state_names.finditer(text):
			(d, i, n) = m.groups()
			if i and n:
				if not d: d = "any"
				else: d = d.lower()
				if not ret.get(d):
					ret[d] = {}
				ret[d]["m" + i] = n
		# self.log.dbg(f"'{text}' {repr(ret)}")
		return ret

	def parse_profile(self, fn, devices=[], header_only=False):
		log = self.log
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

			new_prof.fsize = os.stat(fn).st_size

			if lpd := prof.get('lastplayeddate'):
				try: new_prof.lpd = datetime.strptime(lpd, "%Y-%m-%dT%H:%M:%S")
				except: pass

			if (desc := prof.findall('pr:description', GK_GP_XMLNS)):
				new_prof.desc = "".join(desc[0].itertext())
				new_prof.state_names = self.parse_state_names(new_prof.desc)

			for tgt in prof.iterfind('pr:target', GK_GP_XMLNS):
				if (tpath := tgt.get('path')):
					new_prof.targets.append(tpath)

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
				devcat = ".".join(devcat_arry[2:])
				if devcat not in devices:
					continue
				devcat = devcat_arry[2]  # just keep the base device type
				new_prof.assignments[devcat] = {}
				for assign in assign_device.iterfind('pr:assignment', GK_GP_XMLNS):
					if assign.get('backup', "") == "true":
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


	def parse_profiles(self, path, devices):
		log = self.log
		profiles = {}
		if not path:
			return profiles
		log.dbg(f"Loading profiles from {path}")
		try:
			with os.scandir(path) as it:
				for entry in it:
					if entry.is_file and entry.name.endswith(".xml"):
						if new_prof := self.parse_profile(entry.path, devices):
							profiles[new_prof.guid] = new_prof
		except Exception as e:
			log.warn(f"Error while handling profile directory {path} for {devices}: {e}")

		return profiles
