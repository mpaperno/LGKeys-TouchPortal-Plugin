<p align="center">
<img src="https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/wiki/images/banner/Banne1_fade_720x307.png" alt="LGKeys Banner"/>
</p>

# LGKeys Touch Portal Plugin

This is a "plugin" for the [Touch Portal](https://www.touch-portal.com) software, designed for integrating with Logitech
Gaming devices like keyboards and other peripherals with programmable macro keys (or "G" keys).
Its main purpose is to be used as a reference to display the key mappings which have been set up in the
Logitech Gaming Software (LGS) for each individual profile. The motivation is that I can never remember
all the mappings, especially when frequently switching applications, and printed references are difficult
to maintain. This solves the issue nicely, and in addition to my hardware key macros I can also have
additional application-specific macros provided the regular _Touch Portal_ UI.

## Features

* Supports Logitech Keyboards, Mice, Headsets, and the G13 keypad with programmable macro keys on Windows and MacOS.
* Display names of macros programmed on all "G" keys (or mouse buttons) for any "game" profile.
* Can show macros for all memory (M) slots at once, and/or only the currently selected M slot.
* Detects currently active LGS device profile and (optionally) automatically refreshes the display.
* Macros for all profiles can be shown using a single generic page, and/or custom application-specific layouts can be used as well.
* Automatically detects when current memory slot changes (Windows only).
* Special feature option to assign custom names for the individual memory slots, per game profile.
* Monitors game profiles for changes and automatically updates all displayed macros (manual refresh also available).
* Option to send G key and mouse button press events back to _Touch Portal_ (Windows only).
Allows control of TP actions via hardware keys.

## Examples

Some example pages are included in the plugin distribution (download). The examples are kept in this
repository, in the `assets` folder, and may be updated more often than the plugin releases. Be sure to
check the [assets](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/tree/master/assets) folder in this repo
for the latest examples.

Some page images are available on the [Screenshots](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/wiki/Screenshots)
wiki page.

## Setup

### Requirements:
* [Touch Portal](https://www.touch-portal.com) for Windows/MacOS, v2.3.010 or newer.
* [Logitech Gaming Software](https://support.logi.com/hc/en-gb/articles/360025298053-Logitech-Gaming-Software)
(latest and last version) installed. This plugin _may_ work with Logitech G Hub, but this is not tested at all.
* Download the latest version of this plugin from the
[Releases](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/releases) page. Grab the .zip file which matches
your operating system<br>
(eg. `LGKeys-TouchPortal-Plugin_v1.0_windows.zip` or `LGKeys-TouchPortal-Plugin_v1.0_macos.zip`).

### Install:
1. Unpack the downloaded _LGKeys_ `.zip` file to a temporary location on your computer.
2. Import the plugin:
    1. Start _Touch Portal_ (if not already running);
    2. Click the "wrench" icon at the top and select "Import plugin..." from the menu;
    3. Browse to where you unpacked this plugin's `.zip` archive, and select the `LGKeys.tpp` file;
    4. When prompted by _Touch Portal_, select "Yes" to trusting the plugin startup script (the source code is public!).
3. Verify proper operation. The zip file you downloaded contains some sample pages to get you started. You can import
these pages in the usual way: from the _Touch Portal_ _Pages_ screen -> _Manage Page..._ button -> _Import Page_ menu item.
4. After importing the plugin into _Touch Portal_, the `LGKeys.tpp` file you extracted earlier is no longer
required. If you don't want/need to use the other assets and tools provided in the plugin archive, those can of course
also be deleted.

### Configure
Several settings are available in the _Touch Portal_ _Settings_ window (select _Plug-ins_ on the left, then
_LGKeys _Touch Portal_ Plugin_ from the dropdown menu). The current TP settings system for plugins is not very advanced,
so some of these could be easier to use (hopefully this can improve in the future).
The options are as follows:

* `Device Type(s)`: Enter the device(s) you want LGKeys to report settings for. Your profiles may contain mappings
for devices you don't currently use (or own anymore), which will just slow everything down and create
un-necessary data in _Touch Portal_. This setting can list one or more devices, with multiple devices separated by commas.
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
  this full device name in the _Device Type(s)_ list. The only real way to determine this is to look inside the
  game profile files and see what's in there... which is not very convenient.

  Instead, I have provided a small utility which will scan all your game profiles and find the device names
  listed in them. It will show you which devices are in each profile, and also provides an aggregated list of
  unique device names found across all profiles.

  The utility is named `list_devices` and is included in this plugin's distribution .zip file, in the `tools` folder
  (the code for it is in this repository as well).  Simply run this file, either from a command prompt or by
  double-clicking it. If your profiles aren't in the standard location, run the utility from a command prompt
  and specify the path to your profiles with the `-p` option.

  So for example if the utility reports that your mouse is called "Mouse.G700" in the profiles, you'd want to use
  that exact name in the _Device Type(s)_ list. Or, for example combined with a keyboard, that would be
  "Keyboard, Mouse.G700".

* `Unmapped Button Text`: What to show for buttons/slots which don't have a mapping set. Default is "..."
(three periods). This could be any text value, or be left blank.

* `Profile Change Poll Interval`: Set this to zero to disable monitoring of profiles folder for changes (edited
profiles would need to be refreshed manually, and profile switch detection is disabled unless _LGS Script Integration_
is enabled). On MacOS this also controls how often the folder is scanned for changes.

* `Use LGS Script Integration`: If set to "true", LGKeys will use optional LGS integration which requires some extra
setup (eee below). Only works on Windows with 64-bit Python. Default is "false"

* `Report Button Presses`: Requires _LGS Script Integration_ to also be enabled. If "true" then LGKeys will
send G key and mouse button press and release events to _Touch Portal_ as custom states. Can be used to activate TP
actions with hardware keys, for example. Requires Windows with 64-bit Python and the optional integration as described
below.

The other settings on this page are read-only and only used internally to save plugin state between runs.
They can be ignored.


### Optional integration setup (Windows only):
This optional step provides closer integration with Logitech Gaming Software to allow the following features:
* Quicker/more accurate profile switching.
* Detection of current memory slot (M#) on keyboards and G13 keypad.
* Sending G key/mouse button press events to _Touch Portal_.

Unfortunately this requires a special Lua script to be configured for each game profile (LGS allows for custom
scripts in profiles). The good news is that I've provided a utility to automatically set up these scripts for all
your existing profiles.  However, if you already use custom scripts, you may want to do this manually.
Only the profiles you want to use the extra features with would need to have this special script set up.

#### Integration Setup Option 1
1. If LGKeys Plugin is already running, you should stop it. This can be done from the TP Settings -> Plug-ins screen.
2. Shut down/close the Logitech Gaming Software completely (right-click the taskbar icon and select Exit).
3. Open a Windows command prompt in the `tools` folder where you unpacked the downloaded plugin zip archive.
4. Run the utility by entering: `update_profiles` (you can also just double-click to run this file
from Explorer, but I recommend you use a command prompt).
    * Read the warnings. It will ask you to confirm that you want to proceed (you must answer with a "y" or "yes").
    * By default it will also make a backup of all your profiles before it does anything else.
    The backup will be in a uniquely-named sub-folder of your LGS profiles folder.
    You can also specify a backup folder using the `-b` startup option.<br/>
    Eg. `update_profiles -b C:\temp\LGS_profiles`
    * The utility will let you know if there is an error or any other problems or warnings.
    * If it can't find your game profiles in the default location, you can specify one on the command line with
    `-p` option.<br/>
    Eg. `update_profiles -p C:\ProgramData\Logitech\profiles`
    * You can update only one, or some, of your profiles, using the `--names` option.<br/>
    Eg. `update_profiles --names "Default Profile" "My Game"`
    * Run `update_profiles -h` to see all command line options.
5. Restart the Logitech Gaming Software application (eg. from your Start menu), and _Touch Portal_ or just the plugin
itself (agin from the TP Settings screen).

For more integration options, especially if you already use Lua scripting in profiles, see the
[LGS Script Integration Options](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/wiki/LGS-Script-Integration)
wiki page.


### Named Memory Slots
While LGS doesn't provide any way to assign names to the M slots, I've designed a custom way to do that using the
profile "description" fields within LGS. These M slot names can then be shown dynamically in TP based on
the current profile, and they become another nice visual reference.

To set this up, simply edit a game profile's _Description_ field (it's in the profile's _Properties_).
Enter something like this:

    M1:EDIT; M2:DIFF; M3:DEBUG;

The syntax is simple: <kbd>M</kbd> followed by the slot number (1-3), then a colon (<kbd>:</kbd>) followed by the name for that memory slot, and ending with a semicolon (<kbd>;</kbd>). If you already have some other description, you could
add the slot names at the end.

You can then use the `<Device> Memory <N> Name` _States_ (described below) to display the names on your LGKeys page(s).

You do not have to provide names for all memory slots. Any that are not specified in the description will
default to the usual "M1", "M2", or "M3" names.

If you have both a "G" keyboard _and_ a G13 keypad, which have individual memory slots, you can provide names for
the specific devices by using a modified version of the above syntax:

    kb.M1:EDIT; kb.M2:DIFF; kb.M3:DEBUG; lhc.M1:C++; lhc.M2:Python; lhc.M3:Lua;

Where "kb" is for the keyboard memory slots and "lhc" is for the G13 ("LeftHandedController" in LGS-speak).


## Usage
The quickest way to get started is to use the example assets (pages/buttons) included with the plugin (and found
in this repository). This includes several page layouts demonstrating how to use the various features. You will
likely want to customize these examples based on your actual devices (eg. how many G keys on your keyboard and how
they're laid out), but they contain all the building blocks you may need.

For further reference, we dive into what the plugin actually provides.

### States
Most of the functionality is provided by _Touch Portal_ _States_. _States_ provide the macro names to display for each
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
These states can be used to trigger any other actions in _Touch Portal_ using the built-in
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


## Troubleshooting
Check out the [Troubleshooting](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/wiki/Troubleshooting) wiki page.

## Running From Source / Development
Please see the [Using Plugin Source Code Version](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/wiki/Using-Source-Version)
wiki page.

## Bugs and Support
I've only tested this whole thing in very limited conditions so far (my main Windows 10 PC and a little in a "hackintosh" VM).
Your mileage may vary, as they say!  But I'm happy to help figure out any problems and improve the plugin.

Open an [Issue](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/issues) here on GitHub or start a
[Discussion](https://github.com/mpaperno/LGKeys-TouchPortal-Plugin/discussions).
Please provide as much detail as possible. Logs usually help!

## Credits
The plugin is written, tested, and documented by myself, Maxim (Max) Paperno.<br/>
https://github.com/mpaperno/

Uses a version of [TouchPortal-API for Python](https://github.com/KillerBOSS2019/TouchPortal-API)
which is included in this repository and also [published here](https://github.com/mpaperno/TouchPortal-API).
It is used under the MIT License.

LGS Script Integration is provided by [LGS Debug Interceptor](https://gondwanasoftware.net.au/lgsdi.shtml)
library from Gondwana Software. License unspecified. Also check out their
[G Assignments 3](https://gondwanasoftware.net.au/gassignments3.shtml) software which serves a similar purpose
as this plugin (and some of the instructions to set up profile integration are very similar).

## Copyright, License, and Disclaimer
LGKeys TouchPortal Plugin<br/>
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
