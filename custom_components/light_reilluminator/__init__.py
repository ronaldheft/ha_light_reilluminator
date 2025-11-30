from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_XY_COLOR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

DOMAIN = "light_reilluminator"
_LOGGER = logging.getLogger(__name__)

# This tells HA we are config-entry only and silences the CONFIG_SCHEMA warning
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_PATCHED = False
_ORIGINAL_EXCLUDED: frozenset[str] | None = None


def _apply_patch() -> None:
    """Monkey patch LightEntity so brightness / color_temp are recorded again."""
    global _PATCHED, _ORIGINAL_EXCLUDED

    if _PATCHED:
        return

    excluded = getattr(
        LightEntity,
        "_entity_component_unrecorded_attributes",
        None,
    )

    _LOGGER.info(
        "light_reilluminator: current LightEntity._entity_component_unrecorded_attributes=%r",
        excluded,
    )

    # If HA ever changes the type, don't blindly patch
    if not isinstance(excluded, frozenset):
        _LOGGER.warning(
            "light_reilluminator: unexpected type for _entity_component_unrecorded_attributes "
            "(%s); not patching",
            type(excluded),
        )
        return

    _ORIGINAL_EXCLUDED = excluded

    to_restore = {
        ATTR_BRIGHTNESS,
        ATTR_COLOR_MODE,
        ATTR_COLOR_TEMP_KELVIN,
        ATTR_EFFECT,
        ATTR_HS_COLOR,
        ATTR_RGB_COLOR,
        ATTR_RGBW_COLOR,
        ATTR_RGBWW_COLOR,
        ATTR_XY_COLOR,
    }
    restored = to_restore & excluded

    if not restored:
        _LOGGER.warning(
            "light_reilluminator: none of %s are in the excluded set; nothing to restore",
            sorted(to_restore),
        )
        return

    new_excluded = frozenset(attr for attr in excluded if attr not in restored)

    LightEntity._entity_component_unrecorded_attributes = new_excluded

    _LOGGER.info(
        "light_reilluminator: restored attributes %s (original=%r, new=%r)",
        sorted(restored),
        excluded,
        new_excluded,
    )

    _PATCHED = True


# Apply the patch as early as possible (module import time)
_apply_patch()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Light Reilluminator from a config entry."""
    _LOGGER.info("light_reilluminator: async_setup_entry called for %s", entry.entry_id)

    # Just in case we were imported before the light component was ready,
    # run the patch again (it is idempotent).
    _apply_patch()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of a config entry.

    We intentionally do NOT try to revert the patch here; at this point
    there may already be live entities using the modified behavior.
    """
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    _LOGGER.info("light_reilluminator: config entry %s unloaded", entry.entry_id)
    return True