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

import datetime
import os
from sys import stderr
import time
import signal
from pydexcom import Dexcom
from prometheus_client import Gauge, Counter, start_http_server

DEXCOM_USERNAME = os.getenv("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.getenv("DEXCOM_PASSWORD")
DEXCOM_REGION = os.getenv("DEXCOM_REGION", "us")
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 8000))
INTERVAL = int(os.getenv("INTERVAL", "60"))

if not DEXCOM_USERNAME:
    raise SystemExit('Environment variable DEXCOM_USERNAME not set (or sadly empty)')
if not DEXCOM_PASSWORD:
    raise SystemExit('Environment variable DEXCOM_PASSWORD not set (or sadly empty)')

dexcom = Dexcom(username=DEXCOM_USERNAME,
                password=DEXCOM_PASSWORD,
                region=DEXCOM_REGION)

glucose_value_old = Gauge('glucose_value',
                      'Current glucose value in mg/dL (OBSOLETE: Use glucose_mg_dl instead)')
glucose_mg_dl = Gauge('glucose_mg_dl',
                      'Current glucose value in mg/dL')
glucose_mmol_old = Gauge('glucose_mmol',
                     'Current glucose value in mmol/L (OBSOLETE: Use glucose_mmol_l instead)')
glucose_mmol_l = Gauge('glucose_mmol_l',
                       'Current glucose value in mmol/L')
trend_direction = Gauge('trend_direction',
                        'Current trend direction as numeric value (OBSOLETE)')

readings_retrieved = Counter(
    'readings_retrieved',
    'Total number of readings successfully obtained from the Dexcom API')
readings_failed = Counter(
    'readings_failed',
    'Total number of times we *failed* to get a reading from the Dexcom API')

reading_age = Gauge(
    'reading_age',
    'Age of the reading in seconds.')

def handle_shutdown(signum, frame):
    raise SystemExit('Received shutdown signal. Bye.')

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

start_http_server(PROMETHEUS_PORT)
print(f"Prometheus metrics server started on port {PROMETHEUS_PORT}")

while True:
    reading = dexcom.get_current_glucose_reading()
    now = datetime.datetime.utcnow()

    if not reading:
        print('Did not get a reading...')
        readings_failed.inc()
    else:
        print(f'Reading: {reading.mg_dl=}, {reading.mmol_l=}, {reading.trend_arrow=}')

        glucose_value_old.set(reading.value)
        glucose_mg_dl.set(reading.mg_dl)
        glucose_mmol_old.set(reading.mmol_l)
        glucose_mmol_l.set(reading.mmol_l)

        # The datetime objecs cannot (necessarily) be subtracted from
        # each other, as you cannot mix timezone-aware and
        # timezone-naive objects. The local time may be timezone
        # aware. Or not. So we just use the epoch timestamps instead.
        reading_age.set(now.timestamp() - reading.datetime.timestamp())

        trend_direction.set(reading.trend)

        readings_retrieved.inc()

    time.sleep(INTERVAL)
