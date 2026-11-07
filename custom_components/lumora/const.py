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

# Türklingel (Optionen der Integration)
CONF_DOORBELL_TRIGGERS = "doorbell_triggers"
CONF_DOORBELL_CAMERA = "doorbell_camera"
CONF_DOORBELL_DURATION = "doorbell_duration"
CONF_DOORBELL_TITLE = "doorbell_title"
CONF_DOORBELL_SUBTITLE = "doorbell_subtitle"
CONF_DOORBELL_COOLDOWN = "doorbell_cooldown"
CONF_DOORBELL_WEBHOOK = "doorbell_webhook"
CONF_DOORBELL_WEBHOOK_ID = "doorbell_webhook_id"
DEFAULT_DOORBELL_DURATION = 60
DEFAULT_DOORBELL_TITLE = "Es klingelt"
DEFAULT_DOORBELL_COOLDOWN = 10
DOORBELL_TRIGGER_DOMAINS = ["binary_sensor", "event", "input_boolean", "switch", "button", "input_button"]

# Bewegungsmelder im Raum
CONF_MOTION_SENSORS = "motion_sensors"
