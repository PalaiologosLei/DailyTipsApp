from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    key: str
    label: str
    width: int
    height: int


DEVICE_PROFILES = [
    DeviceProfile("iphone_15_pro", "iPhone 15 Pro", 1179, 2556),
    DeviceProfile("iphone_15_pro_max", "iPhone 15 Pro Max", 1290, 2796),
    DeviceProfile("iphone_14", "iPhone 14 / 13 / 12", 1170, 2532),
    DeviceProfile("iphone_14_plus", "iPhone 14 Plus / 13 Pro Max / 12 Pro Max", 1284, 2778),
    DeviceProfile("iphone_se", "iPhone SE / 8 / 7 / 6", 750, 1334),
    DeviceProfile("custom", "Custom", 1179, 2556),
]

DEVICE_PROFILE_MAP = {profile.key: profile for profile in DEVICE_PROFILES}


def get_device_profile(key: str) -> DeviceProfile:
    return DEVICE_PROFILE_MAP.get(key, DEVICE_PROFILE_MAP["iphone_15_pro"])
