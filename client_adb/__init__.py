"""
PhoneClaw ADB-Only client package.

Subpacote com os módulos de controle ADB, ponte de áudio Bluetooth,
integração com a API Xiaomi MiMo (ASR/TTS) e configurações.
"""

from client_adb.config import (
    XIAOMI_MIMO_API_KEY,
    XIAOMI_MIMO_BASE_URL,
    BLUETOOTH_INPUT_DEVICE_NAME,
    BLUETOOTH_OUTPUT_DEVICE_NAME,
    SAMPLE_RATE,
    CHANNELS,
    CHUNK_SIZE,
    RECORDINGS_DIR,
)

__all__ = [
    "XIAOMI_MIMO_API_KEY",
    "XIAOMI_MIMO_BASE_URL",
    "BLUETOOTH_INPUT_DEVICE_NAME",
    "BLUETOOTH_OUTPUT_DEVICE_NAME",
    "SAMPLE_RATE",
    "CHANNELS",
    "CHUNK_SIZE",
    "RECORDINGS_DIR",
]
