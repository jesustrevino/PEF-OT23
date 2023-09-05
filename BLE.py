import asyncio
from bleak import BleakClient, discover, BLEDevice, BleakScanner
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
                 dump_size: int = 256,
                 flag: asyncio.Event = False):
        self.loop = loop
        self.uuid = uuid
        self.address = address
        self.read_char = read_char
        self.write_char = write_char
        self.dump_size = dump_size
        self.flag = flag

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

    def set_connect_flag(self):
        self.flag.set()

    async def connect(self) -> None:
        """Connection mainframe between app and ESP32.
            + Contains select_device() and discover_device() as alternate protocol if desired object is not found"""
        print('in connect')
        if self.connected:
            return
        while True:
            try:
                print('trying to connect to device...')
                await self.client.connect()
                self.connected = self.client.is_connected
                print(f"connection status: {self.connected}")
                if self.connected:
                    self.set_connect_flag()  # setting flag into asyncio notify
                    print("CLIENT CONNECTED")
                    self.client.set_disconnected_callback(self.on_disconnect)
                    await self.client.start_notify(self.read_char, self.notification_handler)
                    while True:
                        if not self.connected:
                            break
                        await asyncio.sleep(3.0)
                else:
                    print(f"Failed to connect to {self.connected_device.name}")
            except Exception as e:
                print(f"IN EXCEPTION {e}")
            finally:
                break

    async def select_device(self, uuid: str = None, address: str = None) -> None:
        print(f"Bluetooh LE hardware warming up...{datetime.now()}")
        await asyncio.sleep(3.0)  # Wait for BLE to initialize.
        print(datetime.now())
        if self.uuid and self.address:
            self.connected_device = [uuid, address]
            print('in self.client')
            while True:
                self.client, _ = BleakClient(address, loop=self.loop)
                print(f"in connection protocol")

                if self.client:
                    print("breaking away")
                    break
                else:
                    print('device not found')
                    await asyncio.sleep(1.0)
        else:
            await self.discover_device()

    async def discover_device(self) -> None:
        device_found = False
        response = -1
        while not device_found:
            devices = await asyncio.create_task(BleakScanner.discover())
            print("Please select device: ")
            for i, device in enumerate(devices):
                if device.name == 'CYG':
                    print(f"{i}: {device.name}")
                    device_found = True
                    response = i

        """while True:
            response = await ainput("Select device: ")
            try:
                response = int(response.strip())
                print(response)

            except:
                print("Please make valid selection.")

            if response > -1 and response < len(devices):
                break
            else:
                print("Please make valid selection.")"""

        print(f"Connecting to {devices[response].name}")
        self.connected_device = devices[response]
        self.client = BleakClient(devices[response].address, loop=self.loop)

    def record_time_info(self) -> None:
        present_time = datetime.now()
        self.rx_timestamps.append(present_time)
        self.last_packet_time = present_time
        self.rx_delays.append((present_time - self.last_packet_time).microseconds)

    def clear_lists(self):
        self.rx_data.clear()
        self.rx_delays.clear()
        self.rx_timestamps.clear()

    def notification_handler(self, sender: str, data: Any):
        self.rx_data.append(int.from_bytes(data, byteorder="big"))
        self.record_time_info()
        if len(self.rx_data) >= self.dump_size:
            # self.data_dump_handler(self.rx_data, self.rx_timestamps, self.rx_delays)
            self.clear_lists()


async def communication_manager(connection: Connection,
                                write_char: str, read_char: str,
                                slider_q: asyncio.Queue, speed_q: asyncio.Queue):
    """In charge of sending and receiving information
        + IMPORTANT to pair write and read characteristics between App and ESP32"""
    buffer = list()
    while True:
        if connection.client and connection.connected:
            try:
                input_str = slider_q.get_nowait()
                buffer.append(input_str)
            except asyncio.QueueEmpty:
                if len(buffer) > 0:
                    input_str = f"{buffer[0]} \n"
                    buffer.clear()
                    bytes_to_send = bytearray(map(ord, str(input_str)))
                    await connection.client.write_gatt_char(write_char, bytes_to_send, response=True)
                    print(f"Sent: {input_str}")
                    await asyncio.sleep(0.1)
                else:
                    input_str = '0'
            await asyncio.sleep(0.1)
            msg_read = await connection.client.read_gatt_char(read_char)
            print(f"message received -> {msg_read.decode()}")
            await speed_q.put(str(msg_read.decode()))
            await asyncio.sleep(0.1)


        else:
            await asyncio.sleep(2.0)

async def set_queue():
    speed_q = asyncio.Queue()
