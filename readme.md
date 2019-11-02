# Overview

This is a tool that bridges the MQTT data stream from opendata.dekart.com and adapts it to the HTTP payloads that the Yandex Maps service expects.


# How to run it

## Prerequisites

1. Make a copy of `res/config-sample.yaml` to your own config file, e.g. `config-development.yaml`, supplying the required information in the file
2. Replicate the environment using `virtualenv` or `pipenv`, as described below
3. When done, run it with `python main.py res/config-development.yaml`

- The credentials as well as the server connection details are given in the [API documentation](https://github.com/roataway/api-documentation)
- Information about [routes and vehicles](https://github.com/roataway/infrastructure-data)

## Virtualenv

1. Create the virtualenv `virtualenv venv-roatayandex` to install the dependencies in it
2. Activate the venv with `source venv-roatayandex/bin/activate`
3. Install the dependencies with `pip install -r requirements.txt`


## Pipenv

1. Install pipenv `pip install pipenv`
2. Then run `pipenv install --dev`. It will deal automatically with the venv creation and dependecy installing


# How to contribute

1. Run `make autoformat` to format all `.py` files
2. Run `make verify` and examine the output, looking for issues that need to be addressed


# Maintenance

Whenever new trackers are added to the Roataway system, they should be assigned a UUID for use within the Yandex system. This is done by periodically running `python helpers.py infrastructure-data/vehicles.csv res/yandex-vehicles.csv` (the first argument is the path to `vehicles.csv` in Roataway, the second one is the path to the Yandex vehicle map, which will be updated in-place).

Note that once these UUIDs were generated, they should remain constant, because Yandex relies on them.

When running for the first time, you will see something like this:

```
2019-11-02 12:53:53,015 Loaded 218 entries from Roataway, infrastructure-data/vehicles.csv
2019-11-02 12:53:53,018 Loaded 0 entries from Yandex, res/yandex-vehicles.csv
2019-11-02 12:53:53,019 Roataway->Yandex update count: 218
2019-11-02 12:53:53,020 Updating the Yandex data
2019-11-02 12:53:53,021 Wrote 218 entries to res/yandex-vehicles.csv
2019-11-02 12:53:53,021 Done
```

Subsequent runs will leave it untouched, unless new trackers were added to Roataway:

```
2019-11-02 12:54:56,029 Loaded 218 entries from Roataway, infrastructure-data/vehicles.csv
2019-11-02 12:54:56,029 Loaded 218 entries from Yandex, res/yandex-vehicles.csv
2019-11-02 12:54:56,029 Roataway->Yandex update count: 0
2019-11-02 12:54:56,030 Done
```