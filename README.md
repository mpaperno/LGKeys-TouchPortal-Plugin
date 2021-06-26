# LGKeys TouchPortal Plugin

This is a "plugin" for the [TouchPortal](https://www.touch-portal.com) software, designed for integrating with Logitech
Gaming devices like keyboards and other peripherals with programmable macro keys (or "G" keys).
Its main purpose is to be used as a reference to display the key mappings which have been set up in the
Logitech Gaming Software (LGS) for each individual profile. The motivation is that I can never remember
all the mappings, especially when frequently switching applications, and printed references are difficult
to maintain. This solves the issue nicely, and in addition to my hardware key macros I can also have
additional application-specific macros provided the regular TouchPortal UI.

## Features

* Supports Logitech Keyboards, Mice, Headsets, and the G13 keypad with programmable macro keys on Windows and MacOS.
* Display names of macros programmed on all "G" keys (or mouse buttons) for any "game" profile.
* Can show macros for all memory (M) slots at once, and/or only the currently selected M slot.
* Detects currently active LGS device profile and (optionally) automatically refreshes the display.
* Macros for all profiles can be shown using a single generic page, and/or custom application-specific layouts can be used as well.
* Automatically detects when current memory slot changes (Windows only).
* Special feature option to assign custom names for the individual memory slots, per game profile.
* Monitors game profiles for changes and automatically updates all displayed macros (manual refresh also available).
* Option to send G key and mouse button press events back to TouchPortal (Windows only).
Allows control of TP actions via hardware keys.

## Setup

### Requirements:
* [TouchPortal](https://www.touch-portal.com) for Windows/MacOS, v2.3.010 or newer.
* [Logitech Gaming Software](https://support.logi.com/hc/en-gb/articles/360025298053-Logitech-Gaming-Software)
(latest and last version) installed. This plugin _may_ work with Logitech G Hub, but this is not tested at all.
* Python 3.8 or newer, with `pip` module (64-bit preferred, tested with
[python.org](https://www.python.org/downloads/) versions).
* Extra Python modules: `pyee`, `requests`, `pywin32` (Windows only). Install using:
  * `pip install pyee requests pywin32`
* Download the latest version of this plugin from the
[Releases](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/releases) page.

### Install:
1. Install Python and the extra modules if necessary. To check if you have Python installed and which version it is,
open a command prompt and just type `python`. If it is installed, this will show you the version and architecture
(32 or 64 bits). (Type <kbd>CTRL+Z</kbd> and <kbd>Enter</kbd> to exit the Python shell.)
2. Unpack the downloaded plugin `.zip` file to a temporary location on your computer.
3. Import the plugin:
    1. Start TouchPortal (if not already running);
    2. Click the "wrench" icon at the top and select "Import plugin..." from the menu;
    3. Browse to where you unpacked this plugin's `.zip` archive, and select the `LGKeys.tpp` file;
    4. When prompted by TouchPortal, select "Yes" to trusting the plugin startup script (the source code is public!).
4. Verify proper operation. The zip file you downloaded contains some sample pages to get you started. You can import
these pages in the usual way: from the TouchPortal _Pages_ screen -> _Manage Page..._ button -> _Import Page_ menu item.
5. After importing the plugin into TouchPortal, the files you unpacked from the plugin's archive are no longer required.
However, you may want to keep them around for a while to use the optional setup scripts, example pages, buttons, or
other assets which are included in the archive (keep reading for more information on all those).

### Configure
Several settings are available in the TouchPortal _Settings_ window (select _Plug-ins_ on the left, then
_LGKeys TouchPortal Plugin_ from the dropdown menu). The current TP settings system for plugins is not very advanced,
so some of these could be easier to use (hopefully this can improve in the future).
The options are as follows:
* `Device Type(s)`: Enter the device(s) you want LGKeys to report settings for. Your profiles may contain mappings
for devices you don't currently use (or own anymore), which will just slow everything down and create
un-necessary data in TouchPortal. This setting can list one or more devices, with multiple devices separated by commas.
Typically you would want to use one or more of the following:
    * `Keyboard` - for a full keyboard device like G11, G15, G510, etc. This is the default setting.
    * `Mouse` - for a mouse, like a G700
    * `Headset` - for a headset with macro keys like a G35
    * `LeftHandedController` - for a G13 keypad

  For example, to get key mappings for both your keyboard and your mouse, use: "Keyboard, Mouse" for the setting value
  (without the quotes).

  It's possible that in your game profiles, the device you want is specified with a model number after the type.
  For example if you owned several models of keyboards or mice, your profiles may have different settings for the
  different device models. For example my mouse device is listed as "Mouse.G700". You would then need to specify
  this full device name in the _Device Type(s)_ list. The only real way to determine this is to open up a game profile
  file (plain-text XML) and see what the device names look like. The profiles are stored in:
    * Windows: `C:\Users\<User_Name>\AppData\Local\Logitech\Logitech Gaming Software\profiles`
    * MacOS: `/homes/<User_Name>/Library/Application Support/Logitech/profiles`

  Scroll down to where the _assignments_ start and you should see lines like:

    `<assignments devicecategory="Logitech.Gaming.Mouse.G700">`

  So in this case you'd want to use "Mouse.G700" in the _Device Type(s)_ list (we ignore the "Logitech.Gaming" part).
  Or, for example combined with a keyboard, that would be "Keyboard, Mouse.G700".

* `Unmapped Button Text`: What to show for buttons/slots which don't have a mapping set. Default is "..."
(three periods). This could be any text value, or be left blank.
* `Profile Change Poll Interval`: Set this to zero to disable monitoring of profiles folder for changes (edited
profiles would need to be refreshed manually, and profile switch detection is disabled unless _LGS Script Integration_
is enabled). On MacOS this also controls how often the folder is scanned for changes.
* `Use LGS Script Integration`: If set to "true", LGKeys will use optional LGS integration which requires some extra
setup (eee below). Only works on Windows with 64-bit Python. Default is "false"
* `Report Button Presses`: Requires _LGS Script Integration_ to also be enabled. If "true" then LGKeys will
send G key and mouse button press and release events to TouchPortal as custom states. Can be used to activate TP
actions with hardware keys, for example. Requires Windows with 64-bit Python and the optional integration as described
below.

The other settings on this page are read-only and only used internally to save plugin state between runs.
They can be ignored.


### Optional integration setup (requires Windows with 64-bit Python):
This optional step provides closer integration with Logitech Gaming Software to allow the following features:
* Quicker/more accurate profile switching.
* Detection of current memory slot (M#) on keyboards and G13 keypad.
* Sending G key/mouse button press events to TouchPortal.

Unfortunately this requires a special Lua script to be configured for each game profile (LGS allows for custom
scripts in profiles). The good news is that I've provided a utility to automatically set up these scripts for all
your existing profiles.  However, if you already use custom scripts, you may want to do this manually.
Only the profiles you want to use the extra features with would need to have this special script set up.

#### Option 1, use provided utility:
1. Shut down/close the Logitech Gaming Software completely (right-click the taskbar icon and select Exit).
2. Open a Windows command prompt in the folder where you unpacked the plugin zip archive.
3. Run the utility by entering: `update_profiles.py --add`
    * You may need to add `py -3` or `python` to the start of that command (but usually .py files just work if you
    have Python installed).
    * The utility will let you know if there is an error or any other problems or warnings.
    * It will also make a backup of all your profiles before it does anything else. The backup will be in a
    sub-folder of your LGS profiles folder.
    * If it can't find your game profiles in the default location, you can specify one on the command line with
    `-p` option. E.g. `update_profiles.py --add -p C:\ProgramData\Logitech\profiles`
    * Run `update_profiles.py -h` to see all command line options.
4. Restart the Logitech Gaming Software application (eg. from your Start menu).

#### Option 2, insert script manually via script editor:
1. Open the Logitech Gaming Software application and go to the device setup page where you normally set up
macros and such.
2. Right-click on the icon of a profile you want to set up and select the _Scripting_ menu item.
This opens up the Lua script editor. Usually every profile has a simple default script which echoes
some event information to the console below the editor window.
3. In the _Script_ menu select _Import..._, navigate to the folder where you unpacked the plugin zip archive,
and select the `lgkeys-integration.lua` file.
    * **Note**: importing will replace any existing script (LGS will warn you). If you have a script you want to
    keep, then you will need to manually "integrate" the code from `lgkeys-integration.lua` into your existing script.
    The code is very basic, so it shouldn't be a problem.
4. In the imported script, find the line with `arg = "PROFILE_NAME"` and replace the `PROFILE_NAME` part with the
profile's actual, full name (or, even better, its GUID, which is that profile's file name in the LGS profiles
folder... see Option 3 for details).
5. <kbd>CTRL+S</kbd> to save the script, and you're done (with that profile).

#### Option 3, insert script by editing profile XML file(s) directly:
This method is ultimately faster if you need to modify several profiles at once, you just need to be a little
careful when editing the files. This is also essentially what my utility script (Option 1) does for you.
You'll need to use Notepad or your favorite plain-text editor to edit the profile XML files.
1. Shut down the Logitech Gaming Software application.
2. Using Explorer browse to the LGS profiles folder, which is in
`C:\Users\<User_Name>\AppData\Local\Logitech\Logitech Gaming Software\profiles`
    * You _may_ want to copy the profiles to a **backup** folder if you don't already have one (in which case also
    strongly consider backing up those profiles regularly).
3. Finding the right profile can be tricky... perhaps sort by modification date and then open each file
in the text editor until you find the right one(s). The profile's name is shown on the 3rd line of each file,
as an attribute of the `profile` XML element.
4. Scroll down to the end of the file to the `<script>...</script>` tags.  Any existing script will be
contained between those tags.
5. Replace the existing script with the contents of `lgkeys-integration.lua` as mentioned above.
6. Also as above, find the script line with `arg = "PROFILE_NAME"` and replace the `PROFILE_NAME`
part with the profile's GUID. The GUID is the file's name (including the curly braces, but without the ".xml" extension)
and can also be found at the top of the profile file, in the `profile` XML tag, as the `guid` attribute.
Using the GUID is preferable to the profile name, because you may change the name later,
but the ID will always remain the same while that profile exists.
7. Save the file. Modify any others you want, then restart the LGS software.


## Usage
The quickest way to get started is to use the example assets (pages/buttons) included with the plugin (and found
in this repository). This includes several page layouts demonstrating how to use the various features. You will
likely want to customize these examples based on your actual devices (eg. how many G keys on your keyboard and how
they're laid out), but they contain all the building blocks you may need.

Further on, we dive into what the plugin actually provides.

### States
Most of the functionality is provided by TouchPortal States. States provide the macro names to display for each
key and memory (M) slot, the currently active profile, M slot names, and so on.  A few of the states always
exist regardless of which device(s) you're using (static states), but most will depend on your actual configuration.

#### Static States
* `Name of currently active LGS profile` - As the title suggests, this contains the name of the active profile.
* `Profiles auto-switch state` - Can be "Enabled" or "Disabled" based on if automatic profile switching is active or
not (see also `Profile Auto-switch Toggle` action).
* `Keyboard Memory Slot` - Reflects the current M slot number of a keyboard device. Possible values: "1", "2", or "3".
See also `Switch Memory Slot` action.
* `Keyboard Memory <N> Name` - Name of the keyboard memory slot for the current profile, where `<N>` is one of
"1", "2", or "3".
* `G13 Memory Slot` - Reflects the current M slot number of a G13 keypad device. Possible values: "1", "2", or "3".
See also `Switch Memory Slot` action.
* `G13 Memory <N> Name` - Name of the G13 memory slot for the current profile, where `<N>` is one of "1", "2", or "3".
* `Status message from the LGKeys Plugin` - Short text messages sent from the plugin, usually to reflect the result
of some action, such as profile switching.

#### Dynamic States
* `<Device> <Button> (current M slot)` - The macro name mapped to the given `<Button>` on `<Device>` for the current
memory slot. `<Device>` would be one of "Keyboard", "Mouse", "Headset", or "LeftHandedController" (G13).
`<Button>` would be "G" (for keys) or "Button" (for mice) followed by a number.
Mice and headsets don't have memory slots, so the "(current M slot)" of the title is omitted for these devices.
The total number of these states depends on the maximum number of buttons a device may have
(18 on a keyboard, 20 on a mouse, 3 on a headset, and 29 on a G13).

* `<Device> <Button> M<N>` - Similar to above, but each of these states shows the macro mapped to each button and
each individual memory slot (not just the current one). `<N>` represents the memory slot number, 1 through 3.
So, each G key on a keyboard would have 3 of these states, in addition to the "current" state explained above.
These states can be used to display all macros for a given profile at the same time, eg. as 3 lines on the image of a
button, one for each memory slot. These states do not exist for mice and headsets (which only have one memory slot).

* `<Device> <Button> Press State` - These are sent only if the `Report Button Presses` setting described previously
is enabled (and LGS scripting integration is used). These states represent when a particular `<Button>` on `<Device>`
is pressed or released. When pressed, the state value is "1", and when released (or not pressed) the value is "0".
These states can be used to trigger any other actions in TouchPortal using the built-in
"When plug-in state changes" Event.


### Actions
* `Switch Profile` - Loads the specified LGS profile. The list of profiles is automatically populated based on
the profiles found in your LGS profiles folder. If profile folder monitoring is enabled in settings, this list will
also automatically update when profiles are added or removed (see reload actions below for manual updates).
* `Profile Auto-switch Toggle` - Turns on or off automatic switching of profiles based on currently active LGS
profile. Turning auto-switch off lets you keep one profile in view regardless of which one is actually active (for example
very useful when setting up macros in LGS).
* `Switch Memory Slot` - Lets you change the currently shown memory slot for either a Keyboard or a G13 device.
This can be useful if you don't have LGS Script Integration enabled but still want to show only one memory slot at
a time on your button images (vs. all 3 slots at once). Note that this does **not** change the active
memory slot on the actual device (there's no way to do that), so this is purely for "display purposes only."
* `Reload Current Profile` - Reloads the currently active profile data from the LGS configuration file. Useful if you
have directory monitoring disabled, or if for some reason a change wasn't automatically detected (it happens).
* `Reload All Profiles` - Performs a full reload of all profiles from the LGS profiles directory.


### Events
* `Current Profile Changed` - This has limited usefulness for now due to some limitations in the current TP plugin
system.  This event should fire whenever the `Name of currently active LGS profile` State (see above) changes.
The format is "When profile changes to (name)" and you have to manually type in the exact profile name you're expecting.
It could be useful for example if you want to load a particular TP page when a specific LGS profile is activated. But the
built-in "When plug-in state changes" event can be used for the same thing.


### Named Memory Slots
While LGS doesn't provide any way to assign names to the M slots, I've designed a custom way to do that using the
profile "description" fields which LGS does provide. These M slot names can then be shown dynamically in TP based on
the current profile, and they become another nice visual reference.

To set this up, simply edit a game profile's _Description_ field (it's in the profile's _Properties_).
Enter something like this:

    M1:EDIT; M2:DIFF; M3:DEBUG;

The syntax is simple: <kbd>M</kbd> followed by the slot number (1-3), then a colon (<kbd>:</kbd>) followed by the name for that memory slot, and ending with a semicolon (<kbd>;</kbd>). If you already have some other description, you could
add the slot names at the end.

You can then use the `<Device> Memory <N> Name` _States_ described above to display the names on your LGKeys page(s).

You do not have to provide names for all memory slots. Any that are not specified in the description will
default to the usual "M1", "M2", or "M3" names.

If you have both a "G" keyboard _and_ a G13 keypad, which have individual memory slots, you can provide names for
the specific devices by using a modified version of the above syntax:

    kb.M1:EDIT; kb.M2:DIFF; kb.M3:DEBUG; lhc.M1:C++; lhc.M2:Python; lhc.M3:Lua;

Where "kb" is for the keyboard memory slots and "lhc" is for the G13 ("LeftHandedController" in LGS-speak).


## Troubleshooting
In TouchPortal, select _"Logs"_ in the left bar, then look for messages in the log with
the word "Plugin" after the time stamp. If everything is working properly, you should see a number of "LOG" type
messages, and no errors. On the other hand, if the plugin couldn't start properly or has some other problem,
there should be a useful error message in the log.  This log may have a lot of entries, so another useful feature is to
select _"Log Errors Only"_ in the _"Current Log Level"_ selector on the right of the _Logs_ screen and then re-start TP
or re-import the plugin.

The LGKeys plugin also keeps its own log file. You can find this in your TouchPortal user data folder, which would be:
* Windows: `C:\Users\<User_Name>\AppData\Roaming\TouchPortal\plugins\LGKeys`
* Mac: `/Documents/TouchPortal/plugins/LGKeys`

Look for a `lgkeys.log` file in that folder. If it does not exist, that means the plugin can't even start for some reason
(check the TouchPortal log for possible reasons). If it does exist, it will likely show useful information for further
troubleshooting.

## Support
Open an Issue here on GitHub or start a Discussion. Please provide as much detail as possible. Logs usually help!

## Credits
The plugin is written, tested, and documented by myself, Maxim (Max) Paperno.
https://github.com/mpaperno/

Uses a version of [TouchPortal-API for Python](https://github.com/KillerBOSS2019/TouchPortal-API)
which is included in this repository and also [published here](https://github.com/mpaperno/TouchPortal-API).
It is used under the MIT License.

LGS Script Integration is provided by [LGS Debug Interceptor](https://gondwanasoftware.net.au/lgsdi.shtml)
library from Gondwana Software. License unspecified. Also check out their
[G Assignments 3](https://gondwanasoftware.net.au/gassignments3.shtml) software which serves a similar purpose
as this plugin (and some of the instructions to set up profile integration are very similar).

## Copyright, License, and Disclaimer
LGKeys TouchPortal Plugin
Copyright Maxim Paperno, all rights reserved.

This program and associated files may be used under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A copy of the GNU General Public License is included in this repository
and is aldo available at <http://www.gnu.org/licenses/>.

This project may also use 3rd-party Open Source software under the terms
of their respective licenses. The copyright notice above does not apply
to any 3rd-party components used within.
