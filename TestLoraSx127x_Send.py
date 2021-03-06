from SX127x.LoRa import *
from SX127x.board_config import BOARD
import time
import RPi.GPIO as GPIO

BOARD.setup()
lora = LoRa()


lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1, 0, 0, 0, 0, 0])

lora.set_mode(MODE.STDBY)
print(lora.get_freq())
lora.set_freq(478.0)
lora.set_coding_rate(CODING_RATE.CR4_6)
lora.set_rx_crc(1)

lora.set_register(0x1E,0x94)
print(hex(lora.get_register(0x1E)))

lora.set_register(0x12,0xff)

value = lora.get_all_registers()
print(value)
print(len(value))
List = []
for i in range(0,len(value)):
    List.append(hex(i)+'--'+hex(value[i]))
print(List)


lora.set_pa_config(pa_select=1)

lora.clear_irq_flags(TxDone=1)


byte1 = 0x00

payload1 = [0xEB,0x90,0x14,0x0B,0xFF,0xFF,0xFF,0xFF,0x05,0x10,0x02,0xFF,0x00,0x29,0xC1]
payload2 = [0xEB,0x90,0x14,0x0B,0xFF,0xFF,0xFF,0xFF,0x05,0x10,0x03,0xFF,0x00,0x29,0xC0]
payload3 = [0xEB,0x90,0x14,0x0A,0xFF,0xFF,0xFF,0xFF,0x04,0x20,0x02,0x00,0x03,0x25]

lora.write_payload(payload1)
lora.set_mode(MODE.TX)
#time.sleep(1)
lora.set_mode(MODE.RXCONT)



#while True:
#    byte1 = byte1 +0x01
#    payload = [byte1,0x5a,0xa5,0x00,0x01,0x02,0x03,0x09,0xDF]
#    lora.write_payload(payload)
#    lora.set_mode(MODE.TX)
#    time.sleep(1)
#    lora.set_mode(MODE.RXCONT)


