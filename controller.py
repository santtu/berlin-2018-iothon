#!/usr/bin/env python3
import random
import argparse
import time
import asyncio
from aiocoap import Context, resource, Message, CHANGED
import struct
from contextlib import contextmanager
try:
    import smbus2
    have_smbus2 = True
except:
    have_smbus2 = False
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    have_gpio = True
except:
    have_gpio = False


# This has been set up with Adafruit HTU21D-F temperature and humidity
# sensor for temperature measurements, and for SG90 servo.

class Hardware(object):
    def __init__(self,
                 i2c_bus=1,
                 sensor_addr=0x40,
                 led_pin=17,
                 servo_pin=18, servo_left=2, servo_right=9.5):
        assert have_smbus2, "hardware interface requires smbus2 to be installed"
        assert have_gpio, "hardware interface requires RPi.GPIO to be installed"

        self.bus = smbus2.SMBus(i2c_bus)
        self.addr = sensor_addr
        self.led_pin = led_pin
        self.pwm = None
        self.servo_pin = servo_pin

        if self.led_pin is not None:
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.output(self.led_pin, GPIO.LOW)

        if self.servo_pin is not None:
            GPIO.setup(servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(servo_pin, 50)

            self.servo_left = servo_left
            self.servo_range = servo_right - servo_left

            # Run the servo from 0% to 100% to 50% and then start
            self.pwm.start(servo_left)
            self.set_actuator(0)
            time.sleep(2)
            self.set_actuator(100)
            time.sleep(2)
            self.set_actuator(50)

    @contextmanager
    def led(self):
        if self.led_pin is not None:
            GPIO.output(self.led_pin, GPIO.HIGH)
        yield
        if self.led_pin is not None:
            GPIO.output(self.led_pin, GPIO.LOW)

    def get_temperature(self):
        with self.led():
            self.bus.write_byte(self.addr, 0xe3)
            time.sleep(0.055)
            msg = smbus2.i2c_msg.read(self.addr, 3)
            data = self.bus.i2c_rdwr(msg)
            # There's a CRC which we ignore completely, in a real
            # implementation you'd want to verify that
            value, = struct.unpack(">H", msg.buf[0:2])

            # round 2 decimal places since that's the maximum accuracy
            temp = round((float(value) / 2**16) * 175.72 - 46.85 + 273.15, 2)
            return temp

    def set_actuator(self, value):
        if self.servo_pin is not None:
            with self.led():
                # ensure range is 0 to 100 and normalize to 0 to 1
                value = float(max(0, min(100, value))) / 100.0
                cycle = self.servo_left + value * self.servo_range
                self.pwm.ChangeDutyCycle(cycle)


class Fake(object):
    def get_temperature(self):
        return random.gauss(293.15, 2.5)
        #return 293.15

    def set_actuator(self, value):
        print("[fake] Actuator updated:", value)


class TemperatureResource(resource.Resource):
    def __init__(self, hw):
        super().__init__()
        self.hw = hw

    async def render_get(self, request):
        temp = "{:.2f}".format(self.hw.get_temperature())
        print("[controller] Read temperature:", temp)
        return Message(payload=temp.encode())

class ActuatorResource(resource.Resource):
    def __init__(self, hw):
        super().__init__()
        self.hw = hw

    async def render_put(self, request):
        value = int(request.payload.decode())
        self.hw.set_actuator(value)
        print("[controller] Actuator updated:", value)
        return Message(code=CHANGED, payload=str(value).encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fake', dest='real', action='store_false')
    parser.add_argument('--real', dest='real', action='store_true')

    parser.add_argument('--coap-server', '--server', default="coap://localhost")

    parser.add_argument('--temperature-resource', default='temperature',
                        metavar='RESOURCE')
    parser.add_argument('--actuator-resource', default='actuator',
                        metavar='RESOURCE')

    parser.add_argument('--update-interval', default=60, type=int,
                        metavar='SECS')

    parser.set_defaults(real=True)

    args = parser.parse_args()

    if args.real:
        hw = Hardware()
    else:
        hw = Fake()

    root = resource.Site()

    root.add_resource((args.temperature_resource,), TemperatureResource(hw))
    root.add_resource((args.actuator_resource,), ActuatorResource(hw))

    asyncio.Task(Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
