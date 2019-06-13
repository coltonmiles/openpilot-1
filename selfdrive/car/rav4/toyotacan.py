import struct

def fix(msg, addr):
  checksum = 0
  idh = (addr & 0xff00) >> 8
  idl = (addr & 0xff)

  checksum = idh + idl + len(msg) + 1
  for d_byte in msg:
    checksum += ord(d_byte)

  #return msg + chr(checksum & 0xFF)
  return msg + struct.pack("B", checksum & 0xFF)


def make_can_msg(addr, dat, alt, cks=False):
  if cks:
    dat = fix(dat, addr)
  return [addr, 0, dat, alt]

def create_fcw_command(packer, fcw):
  values = {
    "FCW": fcw,
    "SET_ME_X20": 0x20,
    "SET_ME_X10": 0x10,
    "SET_ME_X80": 0x80,
  }
  return packer.make_can_msg("ACC_HUD", 0, values)


def create_ui_command(packer, steer, sound1, sound2, left_line, right_line, left_lane_depart, right_lane_depart):
  values = {
    "RIGHT_LINE": 3 if right_lane_depart else 1 if right_line else 2,
    "LEFT_LINE": 3 if left_lane_depart else 1 if left_line else 2,
    "BARRIERS" : 3 if left_lane_depart or right_lane_depart else 0,
    "SET_ME_X0C": 0x0c,
    "SET_ME_X2C": 0x2c,
    "SET_ME_X38": 0x38,
    "SET_ME_X02": 0x02,
    "SET_ME_X01": 1,
    "SET_ME_X01_2": 1,
    "REPEATED_BEEPS": sound1,
    "TWO_BEEPS": sound2,
    "LDA_ALERT": steer,
  }
  return packer.make_can_msg("LKAS_HUD", 0, values)
