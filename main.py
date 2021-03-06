import logging
import sys
import os
import json
from datetime import datetime, timedelta
from time import sleep
import gzip

from reyaml import load_from_file
import requests
import fastjsonschema

from helpers import load_yandex_tracker_ids
from structures import Tracker
import constants as c
from mqtt_client import MqttClient

log = logging.getLogger("briya")


class NoFreshTelemetry(Exception):
    # this is raised when there is no fresh telemetry to report
    pass


class Subscriber:
    def __init__(self, mqtt, config):
        """Constructor
        :param mqtt: instance of MqttClient object
        :param config: dict, the raw config (normally loaded from YAML)"""
        self.mqtt = mqtt
        self.config = config

        # this will contain the last known state of each vehicle
        self.trackers = {}

        # this is a dict that maps a roataway tracker ID to a Yandex tracker ID,
        # which is a stringified UUID without dashes
        self.yandex_trackers = load_yandex_tracker_ids(c.PATH_YANDEX_VEHICLES)

        # this will keep track of the devices we haven't got identifiers for, the
        # first time we encounter them, we'll log it; subsequent log entries will
        # be suppressed, to reduce clutter
        self.unprovisioned_trackers = set()

        # this flag is used as a "once-place toggle" for the compression feature
        self.compress = self.config['yandex'].get('compress', True)

        # load the JSON schema and initialize the validator with it, for later use
        schema_path = os.path.join('api-documentation', 'schema', 'routeTelemetry.json')
        schema = json.loads(open(schema_path, 'r').read())
        self.validate = fastjsonschema.compile(schema)

    def serve(self):
        """The main loop"""
        self.mqtt.set_external_handler(self.on_mqtt)
        for topic in self.config['mqtt']['topics']:
            self.mqtt.client.subscribe((topic, c.QOS_MAYBE))
        log.info('Starting MQTT loop')
        self.mqtt.client.loop_start()

        log.info('Starting main loop; compress=%s', self.compress)
        while True:
            try:
                payload = self.form_payload(compressed=self.compress)
            except NoFreshTelemetry:
                # nothing to report to the server, all telemetry points are outdated,
                # so we just sleep and try again at the next iteration
                pass
            else:
                response = self.publish_payload(payload, compressed=self.compress)
                if not response.ok:
                    log.warning('Negative response from Yandex: status=%s, reason=%s',
                                response.status_code, response.reason)
                    if response.status_code == 400:
                        # when they say the request is bad, log it, so we can share it
                        # for troubleshooting purposes
                        log.debug('Payload `%s`', payload)
                        log.debug('Response `%s`', response.text)
            try:
                sleep(c.FREQ_PUBLISH)
            except KeyboardInterrupt:
                log.info('Interactive quit')
                self.mqtt.client.loop_stop(force=False)
                sys.exit()

        log.warning('Somehow I got out of an infinite loop!')

    def form_payload(self, compressed=True):
        """Produce a payload out of the existing telemetry, forming an XML that contains
        fresh telemetry points. Optionally, it can compress the payload with Gzip
        :returns: bytes, payload
        :raises: StopIteration if no fresh telemetry points available"""
        head_xml = f"""<?xml version="1.0" encoding="utf-8"?><tracks clid="{self.config['yandex']['clid']}">"""
        tail = '</tracks>'.encode('utf-8')
        telemetry_chunks = b''

        now = datetime.utcnow()
        telemetry_chunks_count = 0
        for tracker, meta in self.trackers.items():
            if (now - meta.timestamp).seconds < c.THRESHOLD_FRESH:
                telemetry_chunks += meta.to_xml_track().encode('utf-8')
                telemetry_chunks_count += 1

        if not telemetry_chunks_count:
            raise NoFreshTelemetry

        payload = bytes(head_xml.encode('utf-8') + telemetry_chunks + tail)
        if compressed:
            payload = gzip.compress(payload)

        head = f'compressed={int(compressed)}&data='
        return bytes(head.encode('utf-8')) + payload

    def publish_payload(self, payload, compressed=True):
        """Send the data to Yandex over HTTP POST
        :param payload: str, a string that represents an XML payload to be sent"""
        if compressed:
            headers = {'Content-Type': 'multipart/form-data'}
        else:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        return requests.post(url=self.config['yandex']['url'], data=payload, headers=headers)

    def on_mqtt(self, client, userdata, msg):
        # log.debug('MQTT IN %s %i bytes `%s`', msg.topic, len(msg.payload), repr(msg.payload))
        try:
            data = json.loads(msg.payload)
            self.validate(data)

            # additional check to ensure the timestamp is sane, for it to be valid
            # it cannot be from the future
            now = datetime.utcnow()
            timestamp = datetime.strptime(data['timestamp'], c.FORMAT_TIME_UPSTREAM)
            if timestamp > now + timedelta(seconds=c.DRIFT_TOLERANCE):
                raise ValueError('Telemetry from the future cannot be right')

        except (ValueError, fastjsonschema.JsonSchemaException) as err:
            log.debug("Ignoring bad MQTT data, err: `%s`, raw: %s", err, repr(msg.payload))
            return

        tracker_id = data['rtu_id']
        if tracker_id not in self.yandex_trackers:
            # This is telemetry from a tracker that has not yet been provisioned, it has no
            # Yandex tracker ID, so we skip it for now. If this happens, check the Maintenance
            # section of the readme
            if tracker_id not in self.unprovisioned_trackers:
                log.warning('Unprovisioned tracker %s', tracker_id)
                self.unprovisioned_trackers.add(tracker_id)
            return

        try:
            state = self.trackers[tracker_id]
        except KeyError:
            vehicle = Tracker(data['latitude'], data['longitude'], int(data['direction']),
                              data['board'], tracker_id, data['speed'],
                              now, data['route'],
                              self.yandex_trackers[tracker_id])
            self.trackers[tracker_id] = vehicle

        else:
            state.latitude = data['latitude']
            state.longitude = data['longitude']
            state.direction = int(data['direction'])
            state.speed = data['speed']
            state.timestamp = timestamp
            # this shouldn't change often, but because we don't know exactly when it changes,
            # it is easier to just update it all the time
            state.route = data['route']


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)5s %(name)5s - %(message)s",
    )

    log.info("Starting Bridge-Yandex v%s", c.VERSION)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    config_path = sys.argv[-1]

    log.info("Processing config from `%s`", config_path)
    config = load_from_file(config_path)

    if config["yandex"].get('debugHttp', False):
        log.info('Activating debug log for HTTP')
        import http
        http.client.HTTPConnection.debuglevel = 1

    mqtt_conf = config["mqtt"]
    mqtt = MqttClient(
        name="roatarest",
        broker=mqtt_conf["host"],
        port=mqtt_conf["port"],
        username=mqtt_conf["username"],
        password=mqtt_conf["password"],
    )

    subscriber = Subscriber(mqtt, config)
    subscriber.serve()
