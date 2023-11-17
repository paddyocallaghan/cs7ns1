import asyncio
import logging
import os
import random
import sys
import tcdicn


async def sensor_main(sensor_name, client):
    if sensor_name == "TemperatureSensor":
        tag = "temperature"
        value_range = [0, 30]
    elif sensor_name == "IntensitySensor":
        tag = "intensity"
        value_range = [0, 100]
    elif sensor_name == "TouchSensor":
        tag = "Touch"
        value_range = [0, 1]
    elif sensor_name == "AmbianceSensor":
        tag = "Ambiance"
        value_range = [0, 100]
    elif sensor_name == "ToneSensor":
        tag = "Tone"
        value_range = [0, 256]
    elif sensor_name == "BrightnessSensor":
        tag = "Brightness"
        value_range = [0, 100]
    else:
        raise ValueError(f"Unknown sensor type: {sensor_name}")

    async def run_sensor():
        while True:
            await asyncio.sleep(random.uniform(1, 2))
            # value = random.choice(value_range) if sensor_name == "OccupancySensor" else random.uniform(*value_range)
            if sensor_name in ["TouchSensor", "TemperatureSensor", "ToneSensor"]:
                value = random.choice(value_range)
            elif sensor_name in ["IntensitySensor", "AmbianceSensor"]:
                value = random.uniform(*value_range)
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


async def actuator_main(actuator_name, client, sensor_tag, actuator_tag):
    logging.info(f"{actuator_name} - Starting actuator...")
    brightness = 0
    # Define the parameters for the get method
    get_ttl = int(os.environ.get("TCDICN_GET_TTL", 180))
    get_tpf = int(os.environ.get("TCDICN_GET_TPF", 3))
    get_ttp = float(os.environ.get("TCDICN_GET_TTP", 0))

    sensor_value = ""
    while True:
        if sensor_tag == "Touch":
            sensor_value = await client.get(sensor_tag, get_ttl, get_tpf, get_ttp)
            if sensor_value == 1:
                logging.info(f"Turned on Light due to Touch set to {sensor_value}")
                brightness = 100

            elif sensor_value == 0:
                logging.info(f"Turned off Light due to Touch set to {sensor_value}")
                brightness = 0

        if sensor_tag == "Occupancy":
            sensor_value = await client.get(sensor_tag, get_ttl, get_tpf, get_ttp)
            if sensor_value == 0:
                logging.info(f" Turned off Light due to empty room")
                brightness = 0

        # Set the brightness value
        try:
            await client.set(actuator_tag, brightness)
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
        level=logging.INFO,
        datefmt="%H:%M:%S:%m",
    )

    # Start the client as a background task
    logging.info("Starting client...")
    client = tcdicn.Client(
        id, port, ["always"], server_host, server_port, net_ttl, net_tpf, net_ttp
    )

    # Start the Sensors
    asyncio.create_task(sensor_main("TemperatureSensor", client))
    asyncio.create_task(sensor_main("IntensitySensor", client))
    asyncio.create_task(sensor_main("TouchSensor", client))
    asyncio.create_task(sensor_main("AmbianceSensor", client))
    asyncio.create_task(sensor_main("ToneSensor", client))

    asyncio.create_task(actuator_main("TouchActuator", client, "Touch", "Brightness"))

    asyncio.create_task(
        actuator_main("OccupancyActuator", client, "Occupancy", "Brightness")
    )

    # Start the Brightness Actuator
    # asyncio.create_task(actuator_main("BrightnessActuator", client, "intensity", "brightness"))

    # Wait for the client to shutdown
    try:
        await client.task
    except asyncio.exceptions.CancelledError:
        logging.info("Client has shutdown.")


if __name__ == "__main__":
    asyncio.run(main())
