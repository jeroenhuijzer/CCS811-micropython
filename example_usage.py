import machine
import utime
from ccs811 import CCS811

def main():
    # Initialize I2C bus
    scl = machine.Pin(5)
    sda = machine.Pin(4)
    i2c = machine.SoftI2C(scl, sda)

    sensor = CCS811(i2c)

    #call begin to reset and check the sensor
    available = sensor.begin()
    if available is False:
        return

    # set measurement mode (1, 2, 3 or 4) see reference for description default 1: (1 measurement/second)
    sensor.start(1)

    while True:
        #enter a loop and call read to update _eCo2 and _eTVOC
        sensor.read()
        #do something with the results
        print(" CO2: ", sensor._eCO2, "ppm\n", "TVOC: ", sensor._eTVOC, "ppb\n")
        #wait
        utime.sleep(1)
        