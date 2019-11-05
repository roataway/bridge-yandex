VERSION = "1.1.1"

# MQTT quality of service
QOS_EXACTLY_ONCE = 2
QOS_ATLEAST_ONCE = 1
QOS_MAYBE = 0

FORMAT_TIME_UPSTREAM = '%Y-%m-%dT%H:%M:%SZ'  # used by opendata.dekart.com
FORMAT_TIME_YANDEX = '%d%m%Y:%H%M%S'  # expected by Yandex

# send the data to Yandex every FREQ_PUBLISH seconds
FREQ_PUBLISH = 20

# telemetry data points that are not older than this many seconds are considered
# fresh and will be sent to Yandex. Anything older than this is considered
# outdated and will be discarded
THRESHOLD_FRESH = 30

PATH_YANDEX_VEHICLES = 'res/yandex-vehicles.csv'
