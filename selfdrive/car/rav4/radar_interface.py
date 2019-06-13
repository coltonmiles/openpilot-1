#!/usr/bin/env python
import os
import zmq
import time
from selfdrive.can.parser import CANParser
from cereal import car
from common.realtime import sec_since_boot
from selfdrive.services import service_list
import selfdrive.messaging as messaging

class RadarInterface(object):
  def __init__(self, CP):

    context = zmq.Context()
    self.logcan = messaging.sub_sock(context, service_list['can'].port)

  def update(self):

    ret = car.RadarData.new_message()

      # TODO: make a adas dbc file for dsu-less models
      time.sleep(0.05)
      return ret

if __name__ == "__main__":
  RI = RadarInterface(None)
  while 1:
    ret = RI.update()
    print(chr(27) + "[2J")
    print(ret)
