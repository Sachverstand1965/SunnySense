"""Constants for Self-learning Is Sunny."""

DOMAIN = "is_sunny"
PLATFORMS = ["binary_sensor"]

CONF_PV = "pv_entity"
CONF_AZIMUTH = "azimuth_entity"
CONF_ELEVATION = "elevation_entity"
CONF_LUX = "lux_entity"
CONF_CLOUD = "cloud_entity"
CONF_TEMPERATURE = "temperature_entity"
CONF_ON_THRESHOLD = "on_threshold"
CONF_OFF_THRESHOLD = "off_threshold"
CONF_MIN_ELEVATION = "min_elevation"
CONF_MIN_SAMPLES = "min_samples"

DEFAULTS = {
    CONF_PV: "sensor.solaredge_aktuelle_leistung",
    CONF_AZIMUTH: "sensor.sun_solar_azimuth",
    CONF_ELEVATION: "sensor.sun_solar_elevation",
    CONF_LUX: "sensor.bewegungsmelder_garten_illuminance",
    CONF_CLOUD: "sensor.dwd_bewoelkung",
    CONF_TEMPERATURE: "sensor.openweathermap_temperature",
    CONF_ON_THRESHOLD: 0.82,
    CONF_OFF_THRESHOLD: 0.68,
    CONF_MIN_ELEVATION: 5.0,
    CONF_MIN_SAMPLES: 6,
}

FACADES = (
    {"name": "northeast", "bearing": 25.0},
    {"name": "southwest", "bearing": 205.0},
    {"name": "northwest", "bearing": 295.0},
)

# Direct light can reach a facade while the sun is within 85° of its normal.
FACADE_HALF_ANGLE = 85.0

ROOF_WINDOWS = (
    {"name": "roof_northeast", "bearing": 25.0, "tilt": 42.0},
)

MODEL_NAMES = tuple(facade["name"] for facade in FACADES) + tuple(
    roof["name"] for roof in ROOF_WINDOWS
)
