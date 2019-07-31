import csv
import selfdrive.messaging as messaging
from selfdrive.services import service_list
import time
from common.params import Params
import os.path

_file = '/data/segments.csv'
_temp_file = '/data/temp_segments.csv'


def mark():
  with open(_temp_file) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    for row in csv_reader:
      dongle = row[0]
      datetime = row[1]
      segment = row[2]
      lat = row[3]
      longitude = row[4]

  if not os.path.isfile(_file):
    # making file with header
    with open(_file, mode='a') as file:
      csv_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      csv_writer.writerow(['dongle', 'datetime', 'segment', 'lat', 'longitude'])

  print "writing data"
  with open(_file, mode='a') as file:
    csv_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow([dongle, datetime, segment, lat, longitude])

  print "done"


def get(encodeIdx, loc):
  # get the dongle id
  params = Params()
  dongle = params.get("DongleId")

  # print "waiting for sock data"
  ecode = messaging.recv_sock(encodeIdx)
  location = messaging.recv_sock(loc)

  lat = 0
  longitude = 0
  segment = 0

  # get gps lat and long
  if location is not None:
    lat = location.gpsLocation.latitude
    longitude = location.gpsLocation.longitude

  # get the segment number
  if ecode is not None:
    segment = ecode.encodeIdx.segmentNum

  # get the current data and time (NOT THE SAME AS WHAT LOGGERD WRITES TO DISK!)
  # # TODO: FIX THIS
  datetime = time.strftime("%Y-%m-%d--%H-%M-%S")
  with open(_temp_file, mode='w') as file:
    csv_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow([dongle, datetime, segment, lat, longitude])


def main():
  encodeIdx = messaging.sub_sock(service_list['encodeIdx'].port)
  loc = messaging.sub_sock(service_list['gpsLocation'].port)
  while 1:
    get(encodeIdx, loc)
    time.sleep(5)


if __name__ == "__main__":
  main()
