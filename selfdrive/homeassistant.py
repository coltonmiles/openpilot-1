#!/usr/bin/env python
import time
from selfdrive import messaging
from selfdrive.services import service_list
import requests
import subprocess
from common.params import Params

# gpsLocation
latitude = -1
longitude = -1
altitude = -1
speed = -1
# health
car_voltage = -1
# thermal
eon_soc = -1
bat_temp = -1

# store these in /data/params/d/
# can also move these somewhere else, and replace the params() read code with something else. I'm lazy

# To get an auth token for you device, go into HA and click on your avatar (first letter of your username if no picture) to get to your profle, then scroll down to make a long life token. it only appears once, so put it somewhere safe
AUTH_TOKEN = params.get("HA_auth_token")
# the url and what you want to call your EON entity. ie, 'https://myhomeassistanturl.com/api/states/eon.chris'
API_URL = params.get("HA_api_url")
# where you want to ping before attemtping a send. probably your 'myhomeassistanturl.com' url
PING_URL = params.get("HA_ping_url")

# a mode for more frequent reads and sends. my pi had problems with updates every second after several hours. your mileage may vary
fast_mode = False

last_read = 0
last_send = 0

if fast_mode:
  time_to_read = 0.1
  time_to_send = 1
else:
  time_to_read = 10
  time_to_send = 60


def main(gctx=None):
  global last_read
  global last_send

  location = messaging.sub_sock(service_list['gpsLocation'].port)
  health = messaging.sub_sock(service_list['health'].port)
  thermal = messaging.sub_sock(service_list['thermal'].port)

  while 1:
    time_now = time.time()
    # read every n seconds
    if time_now - last_read >= time_to_read:
      last_read = read(location, health, thermal)
      time_now = time.time()
    # send ever n seconds
    if time_now - last_send >= time_to_send:
      last_send = send()
      time_now = time.time()
    time.sleep(1)


def read(location, health, thermal):
  global latitude
  global longitude
  global altitude
  global speed
  global car_voltage
  global eon_soc
  global bat_temp
  try:
    location_sock = messaging.recv_sock(location)
    if location_sock is not None:
      latitude = location_sock.gpsLocation.latitude
      longitude = location_sock.gpsLocation.longitude
      altitude = location_sock.gpsLocation.altitude
      speed = location_sock.gpsLocation.speed
  except:
    print "Location sock failed"

  try:
    health_sock = messaging.recv_sock(health)
    if health_sock is not None:
      car_voltage = health_sock.health.voltage
  except:
    print "Health sock failed"

  try:
    thermal_sock = messaging.recv_sock(thermal, wait=True)
    if thermal_sock is not None:
      eon_soc = thermal_sock.thermal.batteryPercent
      bat_temp = thermal_sock.thermal.bat * .001
      bat_temp = round(bat_temp)
  except:
    print "Thermal sock failed"

  return time.time()

def send():
  global latitude
  global longitude
  global altitude
  global speed
  global car_voltage
  global eon_soc
  global bat_temp
  while 1:
    ping = subprocess.call(["ping", "-W", "4", "-c", "1", PING_URL])
    if ping:
      # didn't get a good ping. sleep and try again
      time.sleep(5)
    else:
      break

  # print "Transmitting to Home Assistant..."
  time_sent = time.ctime()

  # we have to add 'Bearer ' to the header string. yes, the space after Bearer is necessary
  token_string = 'Bearer ' + AUTH_TOKEN

  headers = {
  'Authorization': token_string,
  'content-type': 'application/json',
  }
  stats = {'latitude': latitude,
  'longitude': longitude,
  'altitude': altitude,
  'speed': speed,
  'car_voltage': car_voltage,
  'eon_soc': eon_soc,
  'bat_temp': bat_temp
  }
  data = {'state': time_sent,
  'attributes': stats,
  }
  try:
    r = requests.post(API_URL, headers=headers, json=data)
    if r.status_code == requests.codes.ok:
      # print "Received by Home Assistant"
    else:
      print "Problem sending. Retry"
  except:
    print "Sending totally failed"
  return time.time()


if __name__ == '__main__':
  main()
