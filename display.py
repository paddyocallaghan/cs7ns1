import asyncio
import logging
import os
import random
import sys
import tcdicn

async def sensor_main(sensor_name, client):
    # if sensor_name == "CoSensor":
    #     tag = "co"
    #     value_range = range(0, 100)  # Simulating binary occupancy detection
    # elif sensor_name == "SmokeSensor":
    #     tag = "smoke"
    #     value_range = range(0, 100)  # Simulating intensity values
    # elif sensor_name == "FlameSensor":
    #     tag = "flame"
    #     value_range = [0, 1]
    # elif sensor_name == "TempSensor":
    #     tag = "temp"
    #     value_range = range(0, 100)
    if sensor_name == "IRSensor":
        tag = "ir"
        value_range = [0, 5]  
    elif sensor_name == "IntensitySensor":
        tag = "intensity"
        value_range = [0, 120]  # Simulating intensity values
    elif sensor_name == "BluetoothSensor":
        tag = "bluetooth"
        value_range = [0, 10]  # Simulating intensity values
    elif sensor_name == "ProximitySensor":
        tag = "proximity"
        value_range = [0, 10]  # Simulating intensity values
    else:
        raise ValueError(f"Unknown sensor type: {sensor_name}")
    async def run_sensor():
        while True:
            await asyncio.sleep(random.uniform(1, 2))
            # value = random.choice(value_range) if sensor_name == "OccupancySensor" else random.uniform(*value_range)
            value = random.choice(value_range)
            logging.info(f"{sensor_name} - Publishing {tag}={value}...")
            try:
                await client.set(tag, value)
            except OSError as e:
                logging.error(f"{sensor_name} - Failed to publish: {e}")

    # Initialise execution of the sensor logic as a coroutine
    logging.info(f"{sensor_name} - Starting sensor...")
    sensor = run_sensor()

    # Wait for the client to shutdown while executing the sensor coroutine
    both_tasks = asyncio.gather(client.task, sensor)
    try:
        await both_tasks
    except asyncio.exceptions.CancelledError:
        logging.info(f"{sensor_name} - Client has shutdown.")

async def run_actuator(client, intensity_tag, brightness_tag):
    brightness = 0  # Initial brightness level

    while True:
        # Read intensity value from the IntensitySensor
        intensity = await client.get(intensity_tag)

        # Adjust brightness based on intensity value (example logic)
        if intensity is not None:
            brightness = min(intensity, 100)  # Limit brightness to 100
            logging.info(f"Brightness Actuator - Adjusting brightness to {brightness} based on intensity {intensity}")

        # Set the brightness value
        try:
            await client.set(brightness_tag, brightness)
        except OSError as e:
            logging.error(f"Brightness Actuator - Failed to set brightness: {e}")

        # Sleep for a random interval before checking intensity again
        await asyncio.sleep(random.uniform(1, 2))
        
async def actuator_main(actuator_name, client, sensor_tag, actuator_tag):
    logging.info(f"{actuator_name} - Starting actuator...")

    # Define the parameters for the get method
    get_ttl = int(os.environ.get("TCDICN_GET_TTL", 180))
    get_tpf = int(os.environ.get("TCDICN_GET_TPF", 3))
    get_ttp = float(os.environ.get("TCDICN_GET_TTP", 0))

    sensor_value = ""
    actuator_value = 0
    while True:
        if sensor_tag == "intensity":
            sensor_value = await client.get(sensor_tag, get_ttl, get_tpf, get_ttp)
            if sensor_value >= 100:
                actuator_value = 100
                # logging.info(f"Sprinklers Siwtched ON based on flame sensor value {sensor_value}")
                logging.info(f"Brightness Actuator - Adjusting brightness to {actuator_value} based on intensity {sensor_value}")
    

        if sensor_tag == "mirophone":
            sensor_value = await client.get(sensor_tag, get_ttl, get_tpf, get_ttp)
            if sensor_value > 50:
                actuator_value = 50
                # logging.info(f"Safety Lights Switched ON based on smoke sensor value {sensor_value}")        
                logging.info(f"Volume Actuator - Adjusting volume to {actuator_value} based on microphone {sensor_value}")

        if sensor_tag == "occupancy":
            sensor_value = await client.get(sensor_tag, get_ttl, get_tpf, get_ttp)
            if sensor_value == 0:
                actuator_value = 0
                # logging.info(f"Safety Lights Switched ON based on smoke sensor value {sensor_value}")        
                logging.info(f"Sleep Actuator - Adjusting device to sleep {actuator_value} based on occupancy {sensor_value}")


        # Set the brightness value
        try:
            await client.set(actuator_tag, sensor_value)
        except OSError as e:
            logging.error(f"Actuator - Failed to set value: {e}")

        # Sleep for a random interval before checking intensity again
        await asyncio.sleep(random.uniform(1, 2))


async def main():
    # Get parameters or defaults
    id = os.environ.get("TCDICN_ID")
    port = int(os.environ.get("TCDICN_PORT", random.randint(33334, 65536)))
    server_host = os.environ.get("TCDICN_SERVER_HOST", "localhost")
    server_port = int(os.environ.get("TCDICN_SERVER_PORT", 33333))
    net_ttl = int(os.environ.get("TCDICN_NET_TTL", 180))
    net_tpf = int(os.environ.get("TCDICN_NET_TPF", 3))
    net_ttp = float(os.environ.get("TCDICN_NET_TTP", 0))
    get_ttl = int(os.environ.get("TCDICN_GET_TTL", 180))
    get_tpf = int(os.environ.get("TCDICN_GET_TPF", 3))
    get_ttp = float(os.environ.get("TCDICN_GET_TTP", 0))
    if id is None:
        sys.exit("Please give your client a unique ID by setting TCDICN_ID")

    # Logging verbosity
    logging.basicConfig(
        format="%(asctime)s.%(msecs)04d [%(levelname)s] %(message)s",
        level=logging.INFO, datefmt="%H:%M:%S:%m")

    # Start the client as a background task
    logging.info("Starting client...")
    client = tcdicn.Client(
        id, port, ["always"],
        server_host, server_port,
        net_ttl, net_tpf, net_ttp)

    # Start the Sensors
    asyncio.create_task(sensor_main("IRSensor", client))
    asyncio.create_task(sensor_main("IntensitySensor", client))
    asyncio.create_task(sensor_main("ProximitySensor", client))
    asyncio.create_task(sensor_main("BluetoothSensor", client))

    asyncio.create_task(actuator_main("BrightnessActuator", client, "intensity", "brightness"))

    asyncio.create_task(actuator_main("SleepActuator", client, "occupancy", "sleep"))

    asyncio.create_task(actuator_main("VolumeActuator", client, "microphone", "volume"))


    # Start the Brightness Actuator
    # asyncio.create_task(actuator_main("BrightnessActuator", client, "intensity", "brightness"))

    # Wait for the client to shutdown
    try:
        await client.task
    except asyncio.exceptions.CancelledError:
        logging.info("Client has shutdown.")

if __name__ == "__main__":
    asyncio.run(main())
