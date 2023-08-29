import asyncio
from bleak import BleakClient, discover, BLEDevice
from aioconsole import ainput

from datetime import datetime
from typing import Callable, Any



async def ble_connection(address: str, uuid: str) -> None:
    """Async function in charge of making and mantaining BLE connection between Android and ESP32
        + NOT USED - just for debugging purposes"""
    for _ in range(10):
        print('connecting...')
        if address == "" or uuid == "":
            pass
        else:
            async with BleakClient(address) as client:
                model_number = await client.read_gatt_char(uuid)
                print("Model Number: {0}".format("".join(map(chr, model_number))))
            break
        await asyncio.sleep(0.1)

class Connection:
    client: BleakClient = None

    def __init__(self,
                 loop: asyncio.AbstractEventLoop,
                 uuid: str, address: str,
                 read_char: str, write_char: str,
                 dump_size: int = 256,):
        self.loop = loop
        self.uuid = uuid
        self.address = address
        self.read_char = read_char
        self.write_char = write_char
        self.dump_size = dump_size

        self.connected = False
        self.connected_device = None

        self.rx_data = []
        self.rx_timestamps = []
        self.rx_delays = []

    def on_disconnect(self, client: BleakClient, future: asyncio.Future) -> None:
        """Protocol on disconnect of BLE"""
        self.connected = False
        print(f"Disconnected from {self.connected_device.name}!")

    async def cleanup(self) -> None:
        """Notification and client cleanup"""
        if self.client:
            await self.client.stop_notify(self.read_char)
            await self.client.disconnect()

    async def manager(self) -> None:
        """Connection manager. Makes sure that client exists and establishes connection"""
        print("Starting connection manager.")
        while True:
            if self.client:
                await self.connect()
                await asyncio.sleep(1.0)
            else:
                await self.select_device()
                await asyncio.sleep(15.0)

    async def connect(self) -> None:
        """Connection mainframe between app and ESP32.
            + Contains select_device() and discover_device() as alternate protocol if desired object is not found"""
        print('in connect')
        if self.connected:
            return
        try:
            print('trying to connect to device...')
            await self.client.connect()
            print(f"connection status: {self.connected}")
            self.connected = await self.client.is_connected()
            if self.connected:
                self.client.set_disconnected_callback(self.on_disconnect)
                await self.client.start_notify(self.read_char,self.notification_handler)
                while True:
                    if not self.connected:
                        break
                    await asyncio.sleep(3.0)
            else:
                print(f"Failed to connect to {self.connected_device.name}")
        except Exception as e:
            print(e)

    async def select_device(self, uuid: str = None, address: str = None) -> None:
        print(f"Bluetooh LE hardware warming up...{datetime.now()}")
        await asyncio.sleep(2.0)  # Wait for BLE to initialize.
        print(datetime.now())
        if self.uuid and self.address:
            self.connected_device = [uuid, address]
            print('in self.client')
            while True:
                self.client = BleakClient(address, loop=self.loop)
                print(self.client)
                if self.client:
                    break
                else:
                    print('device not found')
                    await asyncio.sleep(1.0)
        else:
            await self.discover_device()

    async def discover_device(self) -> None:
        devices = await asyncio.create_task(discover())
        print("Please select device: ")
        for i, device in enumerate(devices):
            print(f"{i}: {device.name}")
        response = -1
        while True:
            response = await ainput("Select device: ")
            try:
                response = int(response.strip())
            except:
                print("Please make valid selection.")

            if response > -1 and response < len(devices):
                break
            else:
                print("Please make valid selection.")

        print(f"Connecting to {devices[response].name}")
        self.connected_device = devices[response]
        self.client = BleakClient(devices[response].address, loop=self.loop)

    def record_time_info(self) -> None:
        present_time = datetime.now()
        self.rx_timestamps.append(present_time)
        self.rx_delays.append((present_time - self.last_packet_time).microseconds)
        self.last_packet_time = present_time

    def clear_lists(self):
        self.rx_data.clear()
        self.rx_delays.clear()
        self.rx_timestamps.clear()

    def notification_handler(self, sender: str, data: Any):
        self.rx_data.append(int.from_bytes(data, byteorder="big"))
        self.record_time_info()
        if len(self.rx_data) >= self.dump_size:
            self.data_dump_handler(self.rx_data, self.rx_timestamps, self.rx_delays)
            self.clear_lists()

async def communication_manager(connection: Connection, write_char: str, read_char: str):
    """In charge of sending and receiving information
        + IMPORTANT to pair write and read characteristics between App and ESP32"""
    while True:
        if connection.client and connection.connected:
            input_str = ""
            bytes_to_send = bytearray(map(ord, input_str))
            await connection.client.write_gatt_char(write_char, bytes_to_send)
            print(f"Sent: {input_str}")
            msg_read = await connection.client.read_gatt_char(read_char)
            print(msg_read)
        else:
            await asyncio.sleep(2.0)





