import time
import datetime
import serial
import struct
import sqlite3

DATABASE_NAME                   ="/home/www/low_power_radio.sqlite"

# Message types
MESSAGE_STATUS_INDICATION       = 0x30
MESSAGE_STATUS_RESPONSE         = 0x31
MESSAGE_GPIO_SET_REQUEST        = 0x33
MESSAGE_GPIO_SET_CONFIRMATION   = 0x34

# Message
MESSAGE_LENGHT                  = 20
MESSAGE_START                   = 0xaf
MESSAGE_END                     = 0x5f

current_time                    = 0.0

message_rx                      = []
message_tx                      = [0xaf, 0x00, 0x00, 0x00, 0x00,
                                   0x00, 0x00, 0x00, 0x00, 0x00,
                                   0x00, 0x00, 0x00, 0x00, 0x00,
                                   0x00, 0x00, 0x00, 0x00, 0x5f]

# Serial port handle
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=0.01)

def si7006_temperature (register_value):
    return (((175.72 * register_value) / 65536) - 46.85)

def si7006_humidity (register_value):
    return (((125 * register_value) / 65536) - 6)

def send_message (message):
        for b in message:
            ser.write(struct.pack('B', b))
            time.sleep(0.01)

def append_radio_data(id, counter, temperature, 
                      humidity, input, output, address):
    conn = sqlite3.connect(DATABASE_NAME)
    curs = conn.cursor()
    curs.execute("INSERT INTO data VALUES(datetime('now'), %i, %i, %.2f, %i, %i, %i, %i)"
                 % (id, counter, temperature, humidity, input, output, address))
    conn.commit()
    conn.close()

while True:

    try:
        byte = struct.unpack('B', ser.read())
        message_rx.append(byte[0])

        if message_rx[0] != MESSAGE_START:
            del message_rx[0]
            continue

        if len(message_rx) < MESSAGE_LENGHT:
            continue

        if message_rx[MESSAGE_LENGHT-1] != MESSAGE_END:
            del message_rx[:MESSAGE_LENGHT-1]
            continue

        # Response to indication
        if message_rx[1] == MESSAGE_STATUS_INDICATION:
            message_tx[1] = MESSAGE_STATUS_RESPONSE
            message_tx[2] = message_rx[4]
            message_tx[3] = message_rx[5]
            message_tx[10] = 1 # GPIO out on EXT3
            send_message(message_tx)
        
        append_radio_data(message_rx[1],
                          (message_rx[6]*256 + message_rx[7]),
                          si7006_temperature(message_rx[13]*256 + message_rx[14]),
                          si7006_humidity(message_rx[15]*256 + message_rx[16]),
                          message_rx[9],
                          message_rx[10],
                          (message_rx[4]*256 + message_rx[5]))

        del message_rx[:MESSAGE_LENGHT-1]
        
    except:
        pass

