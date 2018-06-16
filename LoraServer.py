import codecs
import time as t
import threading
from binascii import hexlify
from datetime import *
from Data import MyLock
from Data import SharedMemory
from PyQt5 import QtCore
from PyQt5.QtCore import *
import urllib.parse
from serial422 import RS422Func
import logging.config
from os import path
import configparser
import threading
from Data import MyLock
from Data import SharedMemory
from PyQt5.QtCore import *

from SX127x.LoRa import *
from SX127x.board_config import BOARD
import time
import RPi.GPIO as GPIO


import logging
MyLog = logging.getLogger('ws_debug_log')       #log data
MajorLog = logging.getLogger('ws_error_log')      #log error

class CanServer(QThread):
    signal = pyqtSignal(str)

    signal_newLock = pyqtSignal(MyLock)
    signal_Lock = pyqtSignal(MyLock)

    def __init__(self):
        super(CanServer,self).__init__()
        MyLog.debug('CanServer in')

        BOARD.setup()

        self.lora = LoRa()

        self.LoraServer_init(self.lora)

        self.WaitCarComeTime = int(120)  # 等待车子停进来的时间，2min不来就升锁
        self.WaitCarLeaveTime = int(300)  # 车子停进来前5min，依旧是2min升锁，超出时间立刻升锁
        self.AfterCarLeaveTime = int(10)  # 超出5min，认为车子是要走了，1min升锁

        try:
            cf = configparser.ConfigParser()
            cf.read(path.expandvars('$HOME') + '/Downloads/WWTFrontServer_SPI/Configuration.ini', encoding="utf-8-sig")

            self.WaitCarComeTime = cf.getint("StartLoad", "WaitCarComeTime")
            self.WaitCarLeaveTime = cf.getint("StartLoad", "WaitCarLeaveTime")
            self.AfterCarLeaveTime = cf.getint("StartLoad", "AfterCarLeaveTime")
        except Exception as ex:
            MajorLog(ex + 'From openfile /waitcartime')

        MyLog.debug("WaitCarComeTime:" + str(self.WaitCarComeTime))
        MyLog.debug("WaitCarLeaveTime:" + str(self.WaitCarLeaveTime))
        MyLog.debug("AfterCarLeaveTime:" + str(self.AfterCarLeaveTime))

        global stridList
        stridList = []

        self.mtimer = QTimer()
        self.mtimer.timeout.connect(self.LockAutoDown)
        self.mtimer.start(1000)

        self.mtimer2 = QTimer()
        self.mtimer2.timeout.connect(self.WaitCarStatusDisable)
        self.mtimer2.start(1000)

        pass

    def LoraServer_init(self,lora):
        print("LoraServer start init----")

        lora.set_mode(MODE.STDBY)
        print(lora.get_freq())
        lora.set_freq(478.0)
        lora.set_coding_rate(CODING_RATE.CR4_6)
        lora.set_rx_crc(1)

        lora.set_register(0x1E, 0x94)
        print(hex(lora.get_register(0x1E)))

        lora.set_register(0x12, 0xff)

        lora.set_mode(MODE.RXCONT)
        lora.set_mode(MODE.RXCONT)
        lora.set_mode(MODE.RXCONT)

        value = lora.get_all_registers()
        print(value)
        print(len(value))
        List = []
        for i in range(0, len(value)):
            List.append(hex(i) + '--' + hex(value[i]))
        print(List)

        for i in range(0, len(List)):
            print(List[i])

        print('0x40--' + hex(lora.get_register(0x40)))
        print('0x41--' + hex(lora.get_register(0x41)))
        print('0x42--' + hex(lora.get_register(0x42)))


        print("LoraServer finish init----")

    def LoraServer_write(self,payload):
        self.lora.clear_irq_flags(TxDone=1)
        self.lora.set_dio_mapping([0] * 6)

#        payload1 = [0xEB, 0x90, 0x14, 0x0B, 0xFF, 0xFF, 0xFF, 0xFF, 0x05, 0x10, 0x02, 0xFF, 0x00, 0x29, 0xC1]
#        payload2 = [0xEB, 0x90, 0x14, 0x0B, 0xFF, 0xFF, 0xFF, 0xFF, 0x05, 0x10, 0x03, 0xFF, 0x00, 0x29, 0xC0]
#        payload3 = [0xEB, 0x90, 0x14, 0x0A, 0xFF, 0xFF, 0xFF, 0xFF, 0x04, 0x20, 0x02, 0x00, 0x03, 0x25]

        self.lora.write_payload(payload)
        self.lora.set_mode(MODE.TX)
        self.lora.set_mode(MODE.RXCONT)


    def LoraServer_read(self):
        self.lora.set_register(0x12, 0xff)  # 将GPIO清0
        flags = self.lora.get_irq_flags()
        rx_nb_bytes = self.lora.get_rx_nb_bytes()
        rx_addr = self.lora.get_fifo_rx_current_addr()

        payload = self.lora.read_payload()

        PrintList = []
        for i in range(0, len(payload)):
            PrintList.append(hex(payload[i]))
        print(PrintList)
        return payload


    def LockAutoDown(self):  # 定时器调用，检测无车满60s后自动发送升锁指令
        for lock in SharedMemory.LockList:
            if lock.arm == '10':
                if lock.car == '00':
                    lock.nocaron += 1
                else:
                    lock.nocaron = 0

                if lock.nocaron >= self.WaitCarComeTime and lock.waitcar == False:  # 降锁后等待车子来停
                    lock.nocaron = 0

                    self.sendToCan(lock.addr + '02')

                    lock.carLeave = datetime.now()
                    lock.reservd2 = datetime.strftime(lock.carLeave, '%Y-%m-%d %H:%M:%S')

                    lock.carStayTime = (str(lock.carLeave - lock.carCome).split('.'))[0]

                    lock.reservd3 = lock.carStayTime
                    self.signal_Lock.emit(lock)
                    t.sleep(0.05)

                if lock.nocaron >= self.AfterCarLeaveTime and lock.carFinallyLeave == True:  # 车子离开等待60s就升锁
                    lock.carFinallyLeave = True
                    lock.nocaron = 0

                    self.sendToCan(lock.addr + '02')

                    t.sleep(5)
                    if lock.arm == '10':
                        self.LockUp(lock.addr)
                        t.sleep(5)
                    if lock.arm == '10':
                        self.LockUp(lock.addr)
                        t.sleep(5)

                    if lock.arm == '01':
                        lock.carLeave = datetime.now()
                        lock.reservd2 = datetime.strftime(lock.carLeave, '%Y-%m-%d %H:%M:%S')
                        lock.carStayTime = (str(lock.carLeave - lock.carCome).split('.'))[0]
                        lock.reservd3 = lock.carStayTime
                        self.signal_Lock.emit(lock)
                        t.sleep(0.05)
                    else:  # 连续多次未判断到升锁到位，认为出现故障
                        lock.machine = '88'
                        pass

            if lock.arm == '01' or lock.arm == '00':
                lock.nocaron = 0
        pass

    def WaitCarStatusDisable(self):
        for lock in SharedMemory.LockList:
            if lock.waitcar == True:
                lock.waitcartime += 1

            if lock.carFinallyLeave == False:
                lock.waitcartime2 += 1

            if lock.waitcartime >= self.WaitCarComeTime:
                lock.waitcar = False
                lock.waitcartime = 0

            if lock.waitcartime2 >= self.WaitCarLeaveTime:
                lock.carFinallyLeave = True
                lock.waitcartime2 = 0
        pass


    def run(self):
        MyLog.debug("LoraServer run ")
        self.ThreadTag = True

        t = threading.Thread(target=ServerOn,args=(self.spi,self))
        t.start()



    def LockUp(self, addr):
        buf = [int(addr[0:2],16),int(addr[2:4],16),int(addr[4:6],16),int(addr[6:8],16),2]
        self.mcp2515_write(buf)
        MyLog.info("LockUp"+addr)


    def LockDown(self, addr):
        buf = [int(addr[0:2],16),int(addr[2:4],16),int(addr[4:6],16),int(addr[6:8],16),3]
        self.mcp2515_write(buf)
        MyLog.info('LockDown:' + addr)

        for lock in SharedMemory.LockList:
            if lock.addr == addr:
                lock.waitcar = True
                lock.waitcartime = 0
                lock.waitcartime2 = 0

                lock.carCome = datetime.now()
                lock.reservd1 = datetime.strftime(lock.carCome,'%Y-%m-%d %H:%M:%S')
                lock.reservd2 = ''
                lock.reservd3 = ''
                lock.carFinallyLeave = False
                self.signal_Lock.emit(lock)




    def LockCMDExcute(self, str):
        MyLog.debug("触发Lockcmdexcute")
        if len(str) == 10:
            addr = str[0:8]
            cmd = str[8:10]
            if cmd == '02':
                self.LockUp(addr)
            elif cmd == '03':
                self.LockDown(addr)
            else:
                # to do other things here
                pass
        else:
            MyLog.error("FrontServer-->Lock的控制指令长度不正确")
            pass

    def LockCMDExcute2(self, str):
        MyLog.debug("触发Lockcmdexcute2 本地点击")
        if len(str) == 10:
            addr = str[0:8]
            cmd = str[8:10]
            if cmd == '02':
                self.LockUp(addr)
            elif cmd == '03':
                self.LockDown(addr)
            elif cmd == '04':
                buf = [int(addr[0:2], 16), int(addr[2:4], 16), int(addr[4:6], 16), int(addr[6:8], 16), 4]
                self.mcp2515_write(buf)
                MyLog.info("EnableAlarm" + addr)
            elif cmd == '05':
                buf = [int(addr[0:2], 16), int(addr[2:4], 16), int(addr[4:6], 16), int(addr[6:8], 16), 5]
                self.mcp2515_write(buf)
                MyLog.info("DisableAlarm" + addr)
            elif cmd == '06':
                buf = [int(addr[0:2], 16), int(addr[2:4], 16), int(addr[4:6], 16), int(addr[6:8], 16), 6]
                self.mcp2515_write(buf)
                MyLog.info("LockReset" + addr)

            else:
                # to do other things here
                pass
        else:
            MyLog.error("FrontServer-->Lock的控制指令长度不正确")
            pass


def ServerOn(SPI,self):
    MyLog.info('LoraServer On through SPI Port!!')
    while self.ThreadTag:
        if GPIO.input(BOARD.DIO0) == 1:
            data = self.LoraServer_read()
            if data != None and len(data) > 0:
                if data[0]==0xeb and data[1]==0x90:
                    strid = data[8:16]

                    if strid not in stridList:
                        stridList.append(strid)
                        print('Not in the list and Add on')

                        newLock = MyLock()
                        newLock.addr = data[8:16]

                        tempstatus = bin(int(data[16:18], 16))[2:].zfill(8)
                        newLock.arm = tempstatus[-4:-2]
                        newLock.car = data[18:20]
                        newLock.reservd4 = data[20:22]
                        newLock.sensor = data[22:24]
                        newLock.machine = data[22:24]

                        SharedMemory.LockList.append(newLock)
                        self.signal_newLock.emit(newLock)
                        MyLog.info('New lock detected!')
                    else:
                        # print('Already in the list')
                        for lock in SharedMemory.LockList:
                            if lock.addr == strid:

                                tempstatus = bin(int(data[16:18], 16))[2:].zfill(8)
                                print(tempstatus)
                                if lock.arm != tempstatus[-4:-2]:
                                    lock.arm = tempstatus[-4:-2]
                                    lock.StatusChanged = True

                                if lock.car != data[10:12]:
                                    lock.car = data[10:12]
                                    lock.StatusChanged = True

                                if lock.reservd4 != data[12:14]:
                                    lock.reservd4 = data[12:14]
                                    lock.StatusChanged = True

                                if lock.sensor != data[14:16]:
                                    lock.sensor = data[14:16]
                                    lock.StatusChanged = True

                                if lock.machine != data[14:16]:
                                    lock.machine = data[14:16]
                                    lock.StatusChanged = True

                                self.signal_Lock.emit(lock)
        else:
            t.sleep(0.1)