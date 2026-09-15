# yb.config

User configuration for `yb` publishing defaults.

Single source of truth for the publishing defaults you don’t want to repeat on
every call — the privacy a new upload gets, and a playlist to drop every upload
into so you can find your videos later. The config lives next to the OAuth token
(`$XDG_CONFIG_HOME/yb/config.json` or `~/.config/yb/config.json`) so all of
`yb`’s persistent state sits in one directory.

The file is **optional**: with no file present the built-in defaults apply
(`privacy_status="unlisted"`, no playlist). Any subset of keys may be set;
unspecified keys fall back to the built-in defaults, and unknown keys are
ignored (forward-compatible).

Example `~/.config/yb/config.json`:

```default
{
    "privacy_status": "unlisted",
    "playlist": "TW Uploads",
    "create_playlist_if_missing": true,
    "playlist_privacy_status": "private"
}
```

### Module Attributes

| [`DEFAULT_PRIVACY_STATUS`](#yb.config.DEFAULT_PRIVACY_STATUS)          | Default privacy for a freshly uploaded video when neither the call nor the config file specifies one.   |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [`DEFAULT_PLAYLIST_PRIVACY_STATUS`](#yb.config.DEFAULT_PLAYLIST_PRIVACY_STATUS) | Default privacy for a playlist that `yb` auto-creates.                                                  |

### Functions

| [`default_config_file`](#yb.config.default_config_file)()      | Config file location (`$XDG_CONFIG_HOME` or `~/.config`).              |
|-----------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`load_config`](#yb.config.load_config)([config_file]) | Load publishing defaults from `config_file` (or the default location). |

### Classes

| [`YbConfig`](#yb.config.YbConfig)([privacy_status, playlist, ...])   | Resolved publishing defaults.   |
|----------------------------------------------------------------------------------------------|---------------------------------|

### yb.config.DEFAULT_PLAYLIST_PRIVACY_STATUS *= 'private'*

Default privacy for a playlist that `yb` auto-creates. `"private"` means
only you see it — ideal for a personal “find my uploads” playlist.

### yb.config.DEFAULT_PRIVACY_STATUS *= 'unlisted'*

Default privacy for a freshly uploaded video when neither the call nor the
config file specifies one. `"unlisted"` keeps videos off your public feed
but shareable by link until you deliberately make one `"public"`.

### *class* yb.config.YbConfig(privacy_status='unlisted', playlist=None, create_playlist_if_missing=True, playlist_privacy_status='private')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Resolved publishing defaults.

#### privacy_status

Privacy a new upload gets (`unlisted` | `private` |
`public`) when the call doesn’t override it.

#### playlist

Title of a playlist every upload is added to (`None` = none).

#### create_playlist_if_missing

Create `playlist` if no playlist of that
title exists yet, rather than erroring.

#### playlist_privacy_status

Privacy for an auto-created playlist.

#### *classmethod* from_mapping(mapping)

Build a config from a mapping, ignoring unknown keys.

* **Return type:**
  [`YbConfig`](#yb.config.YbConfig)

### yb.config.default_config_file()

Config file location (`$XDG_CONFIG_HOME` or `~/.config`).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.config.load_config(config_file=None, \*\*overrides)

Load publishing defaults from `config_file` (or the default location).

A missing file yields the built-in defaults. `overrides` (typically the
explicit keyword arguments a caller passed) take precedence when not
`None`, so call-site arguments always win over the file.

* **Return type:**
  [`YbConfig`](#yb.config.YbConfig)
