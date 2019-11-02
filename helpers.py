import csv
import sys
import logging
from uuid import uuid4
import collections

log = logging.getLogger("help")


def load_roataway_tracker_ids(path):
    """Load the roataway tracker_ids from a csv file into a set
    :param path: str, path to CSV file with roataway data from vehicles.csv
    :returns: set of tracker_ids; note that vehicles without trackers are ignored"""
    result = set()
    with open(path_roataway, mode='r') as vehicles:
        reader = csv.reader(vehicles)
        next(reader, None)  # skip the headers
        for row in reader:
            tracker_id = row[0]
            if tracker_id:
                result.add(tracker_id)
    log.info('Loaded %i entries from Roataway, %s', len(result), path)
    return result


def load_yandex_tracker_ids(path):
    """Load vehicle metadata with UUIDs assigned to each vehicle. This is necessary
    because they have their own identifiers, and they cannot use our tracker_id
    :param path: str, path to vehicles csv with roataway data
    :returns: dict, k=tracker_id, v=yandex_tracker_id"""
    result = {}
    with open(path, mode='r') as vehicles:
        reader = csv.reader(vehicles)
        next(reader, None)  # skip the headers
        for row in reader:
            tracker_id = row[0]
            tracker_id_yandex = row[1]
            result[tracker_id] = tracker_id_yandex
    log.info('Loaded %i entries from Yandex, %s', len(result), path)
    return result


def extend_yandex_tracker_ids(trackers_roataway, trackers_yandex):
    """Add new trackers to the yandex data structure, generating UUIDs for them.
    :param trackers_roataway: set of str, tracker ids used in roataway
    :param trackers_yandex: dict, k=roataway_tracker_id, v=yandex_tracker_id, this
                            will be updated in-place!
    :returns int: number of new entries added to trackers_yandex"""
    update_count = 0
    for tracker_id in trackers_roataway:
        if tracker_id not in trackers_yandex:
            # Yandex wants UUIDs without dashes
            trackers_yandex[tracker_id] = str(uuid4()).replace('-', '')
            update_count += 1
    log.info('Roataway->Yandex update count: %i', update_count)
    return update_count


def save_yandex_tracker_ids(trackers_yandex, path):
    """Save vehicle metadata for Yandex tracker identifiers in a CSV file.
    :param path: str, path to output file, for use in Yandex"""
    # to make the diffs easier to track and the file itself more usable, we
    # will sort it by tracker_id
    sorted_trackers = collections.OrderedDict(sorted(trackers_yandex.items()))
    with open(path, 'w', newline='') as csvfile:
        fieldnames = ['tracker_id', 'yandex_tracker_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for tracker_id, yandex_tracker_id in sorted_trackers.items():
            writer.writerow({'tracker_id': tracker_id, 'yandex_tracker_id': yandex_tracker_id})
    log.info('Wrote %s entries to %s', len(sorted_trackers), path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s")

    if len(sys.argv) < 2:
        log.info('Missing command line args, example:')
        log.info('python helpers.py infrastructure-data/vehicles.csv res/yandex-vehicles.csv')
        sys.exit()

    path_roataway = sys.argv[-2]
    path_yandex = sys.argv[-1]

    roataway = load_roataway_tracker_ids(path_roataway)
    yandex = load_yandex_tracker_ids(path_yandex)

    updates = extend_yandex_tracker_ids(roataway, yandex)
    if updates:
        log.info('Updating the Yandex data')
        save_yandex_tracker_ids(yandex, path_yandex)

    log.info('Done')
