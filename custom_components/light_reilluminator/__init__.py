"""Undo recorder filtering for selected light attributes."""

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
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Attributes you want to restore to recorder
DEFAULT_RESTORED_ATTRS: set[str] = {
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

# Keep a copy of the original unrecorded-attributes set so we can restore it
_ORIGINAL_EXCLUDED: frozenset[str] | None = None


def _patch_light_entity(restored_attrs: set[str]) -> set[str]:
    """Modify LightEntity's unrecorded attribute set.

    Returns the set of attributes that were actually restored.
    """
    global _ORIGINAL_EXCLUDED

    excluded = getattr(
        LightEntity,
        "_entity_component_unrecorded_attributes",
        frozenset(),
    )

    if _ORIGINAL_EXCLUDED is None:
        _ORIGINAL_EXCLUDED = excluded

    if not excluded:
        _LOGGER.warning(
            "LightEntity has no _entity_component_unrecorded_attributes; "
            "nothing to patch"
        )
        return set()

    # Build a new frozenset without the ones we want recorded again
    new_excluded = frozenset(attr for attr in excluded if attr not in restored_attrs)
    actually_restored = set(excluded) - set(new_excluded)

    LightEntity._entity_component_unrecorded_attributes = new_excluded

    if actually_restored:
        _LOGGER.info(
            "light_reilluminator: restoring attributes to recorder: %s",
            ", ".join(sorted(actually_restored)),
        )
    else:
        _LOGGER.info(
            "light_reilluminator: no matching attributes found to restore "
            "(maybe core changed the list?)"
        )

    return actually_restored


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Light Reilluminator from a config entry."""
    _LOGGER.debug("Setting up %s config entry %s", DOMAIN, entry.entry_id)

    # In the future, you could read options from entry.data/entry.options.
    restored_attrs = DEFAULT_RESTORED_ATTRS.copy()
    actually_restored = _patch_light_entity(restored_attrs)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "restored_attrs": restored_attrs,
        "actually_restored": actually_restored,
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    We revert the LightEntity unrecorded-attributes set back to the original,
    since this integration is single_config_entry and only patches once.
    """
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    global _ORIGINAL_EXCLUDED
    if _ORIGINAL_EXCLUDED is not None:
        _LOGGER.info(
            "light_reilluminator: restoring original LightEntity "
            "_entity_component_unrecorded_attributes"
        )
        LightEntity._entity_component_unrecorded_attributes = _ORIGINAL_EXCLUDED

    return True