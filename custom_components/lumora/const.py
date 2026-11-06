"""Konstanten der Lumora-Integration."""

from datetime import timedelta

DOMAIN = "lumora"

CONF_VERIFY_SSL = "verify_ssl"

SCAN_INTERVAL = timedelta(seconds=10)

# Bewegung gilt so lange nach der letzten Meldung als erkannt
MOTION_HOLD_SECONDS = 90

SERVICE_SHOW_CAMERA = "show_camera"
SERVICE_SHOW_IMAGE = "show_image"
SERVICE_NOTIFY = "notify"
SERVICE_DISMISS = "dismiss"
SERVICE_DISPLAY_ON_FOR = "display_on_for"
