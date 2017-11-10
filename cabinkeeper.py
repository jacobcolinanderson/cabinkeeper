import os
import glob
import time
import datetime
import schedule

from ina219 import INA219
from serial import Serial
from sim900 import Sim900

# vars for temperature sensor 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# vars for current sensor
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.2

#vars for run
refresh = 10
count_int = 360

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        pretty_temp = int(round(temp_f))
        return pretty_temp
    
def read_current():
    ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
    ina.configure(ina.RANGE_16V, ina.GAIN_AUTO)
    return(ina.voltage())

def get_time():
    currentTimestamp = datetime.datetime.now()
    currentDate = str(currentTimestamp).split('.')[0].split(' ')[0]
    currentTime = str(currentTimestamp).split('.')[0].split(' ')[1]
    return(str(currentDate) + " " +str(currentTime))
    
    
def notify(message):
    gprs = Sim900(Serial("/dev/serial0", baudrate=115200, timeout=0), delay=0.5)
    gprs.send_cmd('AT+CMGS="1xxxxxxxxxx"')
    gprs.send_cmd(message)
    gprs.send_cmd(Sim900.CTRL_Z)
    
def ping_owner() :
    pwr = read_current()
    if pwr > 1 :
        pwr = "On"
    else :
        pwr = "Off"
    notify("All Good! " + "Temp:" + str(read_temp()) + " Electric: " + pwr)
    
schedule.every().day.at("10:30").do(ping_owner)

def run() :
    temp = read_temp()
    pwr = read_current()
    power_counter = 0
    temp_counter = 0
    if pwr <= 1 :
        notify("Power Outage! @ " + get_time() + " Temp:" + str(temp)) 
        while pwr < 1 :
            pwr = read_current()
            temp = str(read_temp())
            if pwr > 1 :
                notify("Power Restored! @ " + str(get_time()) + " Temp:" + temp)
            elif power_counter == count_int :
                notify("Power is still out! @ " + str(get_time()) + " Temp:" + temp)
                time.sleep(refresh)
                power_counter = 0
            else :
                power_counter = power_counter + 1
                time.sleep(refresh)
    else :
        if temp < 50 :
            notify("Temp is Below Threshold! " + get_time() + " Temp:" + str(temp) + " Power: On")
            while temp <= 50 :
                temp = read_temp()
                pwr = read_current()
                if pwr > 1 :
                    pwr = "On"
                else :
                    pwr = "Off"
                if temp > 50 :
                    notify("Temp Restored! @ " + str(get_time()) + " Temp:" + str(temp) + " Power: " + pwr)
                elif temp_counter == count_int :
                    notify("Temp is still below threshold! Temp: " + str(temp) + " Power: " + pwr)
                    time.sleep(refresh)
                    temp_counter = 0
                else :
                    temp_counter = temp_counter + 1
                    time.sleep(refresh)
        else :
            return(temp, pwr)
                

     
while True:
    run()
    schedule.run_pending()
    time.sleep(refresh)


