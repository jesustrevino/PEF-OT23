import asyncio
from bleak import BleakClient


async def ble_connection(address: str, uuid: str) -> None:
    "Async function in charge of making and mantaining BLE connection between Android and ESP32"
    if address == "" or uuid == "":
        return
    async with BleakClient(address) as client:
        model_number = await client.read_gatt_char(uuid)
        print("Model Number: {0}".format("".join(map(chr, model_number))))
