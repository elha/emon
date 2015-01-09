!/usr/bin/python

# emon logger
# elha 20141220
# version 1.0
#
# inspired by OpenEnergyMonitor.org

import math
import time
import requests
import Queue
import threading

# const
NUMBER_OF_SAMPLES = 850         # take 850 Samples per Measurement (takes approx 1.2 secs)
ICAL = 1000 / 33                # CT 1000:1 / Burden 33 Ohms
VOLT_PER_TICK = 1.8 / 4096      # VDC BBB / 12 bit ADC Resolution
VOLT_AC = 230                   # fixed value
INTERVAL = 60                   # measure every 60 secs

# globals
buffer = [0 for i in range(NUMBER_OF_SAMPLES)]
logfile = "/var/log/emon.log"
pins = ["0", "1", "2", "3", "4", "5", "6"]
url = "http://emoncms.org/input/post.json?node=1&apikey=<EMONAPIKEY>"
paramts = "&time="
paramcsv = "&csv="

# read ADC
def Read(pin):
        pinfile = "/sys/bus/iio/devices/iio:device0/in_voltage" + pin + "_raw"
        with open(pinfile, "r") as analog:
                return int(analog.readline())


# calc RMS power for single pin
def CalcPower(pin):
        a = 0
        # sampling
        while a < NUMBER_OF_SAMPLES:
                buffer[a] = Read(pin)
                a += 1

        # sort and median
        sort = sorted(buffer)
        median = sort[NUMBER_OF_SAMPLES / 2]

        # suppress zero power
        # only report power if third (99.x quantile) smallest value is more then 8 ticks away from median
        if(median - sort[3] < 9):
                return 0

        # calc RMS (sum squares -> average ->  squareroot)      
        sumI = 0.0
        a = 0
        while a < NUMBER_OF_SAMPLES:
                sumI += float(math.sqr(buffer[a] - median))
                a += 1

        return VOLT_AC * ICAL * VOLT_PER_TICK * math.sqrt(sumI / NUMBER_OF_SAMPLES)


# calc power for each pin and return csv-data
def Calc():
        out = ""
        for pin in pins:
                out += "%1.1f," % CalcPower(pin)
        return out[:-1]


# log to logfile
def log(msg):
        with open(logfile, "a") as f:
                f.write(msg + '\n')


# send to emoncms.org
def sendworker():
    item = ""
    while 1:
        if(item == ""):
                item = backlog.get()

        try:
                requests.get(item)
                backlog.task_done()
                item=""
        except:
                pass

        time.sleep(1)


# main, init
try:
        print("emon logger")
        print("logging to " + logfile)

        log("-----------------------------------------------")
        log("start %10d" % int(time.time()))

        backlog = Queue.Queue()

        sender = threading.Thread(target=sendworker)
        sender.daemon = True
        sender.start()

        # main, run loop
        while 1:
                # wait until next query
                time.sleep(INTERVAL - (int(time.time()) % INTERVAL))

                # query data
                csv = Calc()
                ts = "%10d" % int(time.time())

                # report in backlog
                backlog.put(url + paramts + ts + paramcsv + csv)

                # log to logfile (if something goes wrong)
                log(ts + ',' + csv)

except:
        print("shutdown.")
