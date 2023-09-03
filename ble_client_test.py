import asyncio
from bleak import BleakClient

class Debug:
    def __init__(self, flag: asyncio.Event):
        self.connected = False
        self.flag = flag
        asyncio.ensure_future(self.start())


    async def start(self):
        for i in range(20):
            print(f"in start::: {i}")
            if i == 3:
                self.flag.set()
                self.connected = True
            await asyncio.sleep(1)
        #self.connected = True


"""async def main():
    async with BleakClient("78:21:84:9D:37:10") as client:
        # Read a characteristic, etc.
        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))

    # Device will disconnect when block exits.
    ...

# Using asyncio.run() is important to ensure that device disconnects on
# KeyboardInterrupt or other unhandled exception.
asyncio.run(main())"""