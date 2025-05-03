"""A prometheus collector for a Dexcom glucose meter user

"""
# Copyright 2025 Downtime-Industries

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from sys import stderr
import time
import datetime
import signal
from pydexcom import Dexcom
from prometheus_client import registry, start_http_server
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import Timestamp, GaugeMetricFamily

DEXCOM_USERNAME = os.getenv("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.getenv("DEXCOM_PASSWORD")
DEXCOM_REGION = os.getenv("DEXCOM_REGION", "us")
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))



if not DEXCOM_USERNAME:
    raise SystemExit('Environment variable DEXCOM_USERNAME not set (or sadly empty)')
if not DEXCOM_PASSWORD:
    raise SystemExit('Environment variable DEXCOM_PASSWORD not set (or sadly empty)')

dexcom = Dexcom(username=DEXCOM_USERNAME,
                password=DEXCOM_PASSWORD,
                region=DEXCOM_REGION)

class OurGauge(GaugeMetricFamily):
    """A useful subclass to help make the code shorter"""
    def set(self, value):
        """Set the gauge value and return the gauge."""
        self.samples = []
        self.add_metric(labels=[], value=value)
        return self

    def add_nolabel(self, value: float, timestamp: datetime.datetime):
        """Add a reading without labels"""
        uxtime = timestamp.timestamp()
        secs, nsecs = divmod(uxtime, 1)
        self.add_metric(labels=[],
                        value=value,
                        timestamp=Timestamp(sec=secs , nsec=nsecs * 1000000))
        return self

#pylint: disable=too-few-public-methods
class GlucoCollector(registry.Collector):
    """The actual collector.

    """
    def __init__(self):
        self.glucose_value_old = OurGauge(
            'glucose_value',
            'Current glucose value in mg/dl (OBSOLETE: Use glucose_mg_dl instead)')
        self.glucose_mg_dl = OurGauge(
            'glucose_mg_dl',
            'Current glucose value in mg/dl')
        self.glucose_mmol_old = OurGauge(
            'glucose_mmol',
            'Current glucose value in mmol/L (OBSOLETE: Use glucose_mmol_l instead)')
        self.glucose_mmol_l = OurGauge(
            'glucose_mmol_l',
            'Current glucose value in mmol/L')
        self.trend_direction = OurGauge(
            'trend_direction',
            'Current trend direction as numeric value (OBSOLETE)')

        self._last_reading_stamp = None

    def describe(self):
        """Let the registry know which metrics we collect.

        This is similar to collect(), except it only returns the
        metrics, without actually collecting a new reading

        """
        yield from self._yield_metrics()

    def _yield_metrics(self):
        yield from [
            self.glucose_value_old,
            self.glucose_mg_dl,
            self.glucose_mmol_old,
            self.glucose_mmol_l,
            self.trend_direction
            ]

    def collect(self):
        """Collect data from Dexcom.

        If no data is available, then no metrics will be returned
        """
        if self._last_reading_stamp is None:
            minutes = 1440
        else:
            minutes = int((datetime.datetime.now().timestamp()
                           - self._last_reading_stamp.timestamp())/60 + 1)
            if minutes < 1:
                raise ValueError(f'Internal error - expecting to go back {minutes=}  !?')
            minutes = min(minutes, 1440)

        readings = dexcom.get_glucose_readings(minutes=minutes)
        if not readings:
            print('No reading available from Dexcom within the last {minutes} minutes.')
            yield from self._yield_metrics()
            return

        readings = [reading
                    for reading in readings
                    if self._last_reading_stamp is None
                    or reading.datetime > self._last_reading_stamp]

        if not readings:
            print('Dexcom just repeated the last reading. Either no new actual readings, or scrape interval too tight.')
            yield from self._yield_metrics()
            return

        readings.sort(key=lambda r:r.datetime)
        for reading in readings:
            print(f'Dexcom reading: {reading.mg_dl} mg/dl'
                  f', {reading.mmol_l} mmol/L'
                  f', trend: {reading.trend_arrow}'
                  f' as of {reading.datetime}')
            self._last_reading_stamp = reading.datetime
            self.glucose_value_old.add_nolabel(reading.value, reading.datetime)
            self.glucose_mg_dl.add_nolabel(reading.mg_dl, reading.datetime)
            self.glucose_mmol_old.add_nolabel(reading.mmol_l, reading.datetime)
            self.glucose_mmol_l.add_nolabel(reading.mmol_l, reading.datetime)
            self.trend_direction.add_nolabel(reading.trend, reading.datetime)
            self._last_reading_stamp = reading.datetime

        yield from self._yield_metrics()

collector = GlucoCollector()
REGISTRY.register(collector)

server, thread = start_http_server(PROMETHEUS_PORT)
print(f"Prometheus metrics server started on port {PROMETHEUS_PORT}")

def handle_shutdown(_signum, _frame):
    """Shut down nicely"""
    print('Shutting down', file=stderr)
    server.shutdown()
    thread.join()
    print('Bye', file=stderr)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

while True:
    time.sleep(3600)
