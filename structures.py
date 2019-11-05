import logging
from datetime import datetime
from dataclasses import dataclass

import constants as c

log = logging.getLogger("struct")


@dataclass
class Tracker:
    latitude: float = None
    longitude: float = None
    # where it goes, North=0, West=270, South=180, East=90
    direction: int = None
    # usually numeric, this is the number written on the trolleybus, e.g. "3913",
    # but we have to assume the can contain non-digit characters
    board_name: str = None
    # human-readable RTU_ID
    tracker_id: str = None
    speed: int = 0
    timestamp: datetime = None  # when we last heard from it
    route_name: str = None

    # these attributes are required by Yandex and are specific to their API
    ya_tracker_id: str = None
    ya_vehicle_type: str = 'trolleybus'

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

    def to_xml_point(self):
        """Produce an XML string that represents a Point structure, defined by Yandex Maps API"""
        time = self.timestamp.strftime(c.FORMAT_TIME_YANDEX)
        return f'<point latitude="{self.latitude}" longitude="{self.longitude}" ' \
            f'avg_speed="{self.speed}" direction="{self.direction}" time="{time}"/>'

    def to_xml_track(self):
        """Produce an XML string that represents a Track structure, defined by Yandex Maps API"""
        head = f'<track uuid="{self.ya_tracker_id}" category="s" route="{self.route_name}" ' \
            f'vehicle_type="{self.ya_vehicle_type}">'
        tail = '</track>'
        return head + self.to_xml_point() + tail
