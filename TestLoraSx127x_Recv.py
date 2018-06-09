from SX127x.LoRa import *
from SX127x.board_config import BOARD
import time
import RPi.GPIO as GPIO

BOARD.setup()
lora = LoRa()


lora.set_mode(MODE.STDBY)
print(lora.get_freq())
lora.set_freq(478.0)
lora.set_coding_rate(CODING_RATE.CR4_6)
lora.set_rx_crc(1)

lora.set_register(0x1E,0x94)
print(hex(lora.get_register(0x1E)))

lora.set_register(0x12,0xff)

lora.set_mode(MODE.RXCONT)
lora.set_mode(MODE.RXCONT)
lora.set_mode(MODE.RXCONT)

value = lora.get_all_registers()
print(value)
print(len(value))
List = []
for i in range(0,len(value)):
    List.append(hex(i)+'--'+hex(value[i]))
print(List)

for i in range(0,len(List)):
    print(List[i])

print('0x40--'+hex(lora.get_register(0x40)))
print('0x41--'+hex(lora.get_register(0x41)))
print('0x42--'+hex(lora.get_register(0x42)))

while True:
    if GPIO.input(BOARD.DIO0)==1:
        lora.set_register(0x12,0xff)#将GPIO清0
#        print(GPIO.input(BOARD.DIO0))
        flags = lora.get_irq_flags()
#        print(flags)

        rx_nb_bytes = lora.get_rx_nb_bytes()
     #   print(rx_nb_bytes)

        rx_addr = lora.get_fifo_rx_current_addr()
    #    print(rx_addr)
        payload = []
        payload = lora.read_payload()

        PrintList = []
        for i in range(0,len(payload)):
            PrintList.append(hex(payload[i]))
        print(PrintList)
    else:
        time.sleep(0.1)
