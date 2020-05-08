Get the car from cache

SUPPORTED_CARS = [CAR.CIVIC_BOSCH]

class BodyCan(object):
  """docstring for BodyCan."""

  def __init__(self, arg):
    super(BodyCan, self).__init__()
    self.arg = arg

  def get_car(self):
    if car not in SUPPORTED_CARS:
