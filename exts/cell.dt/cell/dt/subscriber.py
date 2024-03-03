import paho.mqtt.client as mqtt
from .spb.sparkplug_b import *
import omni.ext
import carb.events

config_path = "Documents/CNC_robot_cell_DT/exts/cell.dt/data/Node.config"


def read_config(config_path):
    """Simplified configuration reader."""
    config = {}
    try:
        with open(config_path) as f:
            for line in f:
                if " = " in line:
                    key, value = line.strip().split(" = ", 1)
                    config[key] = value
    except FileNotFoundError:
        print(f"Configuration file {config_path} not found.")
    return config


def setup_mqtt_client(config):
    """Setup MQTT client based on configuration."""
    client_id = config.get("client_id", "Omniverse Client")
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, clean_session=True
    )

    username = config.get("myUsername")
    password = config.get("myPassword")
    if username and password:
        client.username_pw_set(username, password)

    return client


class DT:
    def __init__(self, config_path=config_path):
        self.config = read_config(config_path)
        self.client = setup_mqtt_client(self.config)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

        # Define coordinate names here
        self.coord_names = (
            "Present machine coordinate position X",
            "Present machine coordinate position Y",
            "Present machine coordinate position Z",
        )
        self.coordinates = {"X": 0, "Y": 0, "Z": 0}

    def connect(self):
        broker = self.config.get("broker", "localhost")
        port = int(self.config.get("port", 1883))
        keepalive = int(self.config.get("keepalive", 60))
        self.client.connect(broker, port, keepalive)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("Device disconnected")

    def on_connect(self, client, userdata, flags, rc):
        """Handle successful connection."""
        if rc == 0:
            print(f"Device connected with result code {rc}")
            topics = [
                (
                    f"{self.config['spBv']}/{self.config['myGroupId']}/{sub}/{self.config['myNodeName']}/#",
                    int(self.config["QoS"]),
                )
                for sub in ["DBIRTH", "DDEATH", "DDATA"]
            ]
            for topic, qos in topics:
                client.subscribe(topic, qos)
                print(f"Succesfully subscribed to topic {topic}")
        else:
            print("Device Failed to connect with result code %s" % rc)
            self.disconnect()  # Ensure a clean disconnect if connection fails.

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        print("Device message arrived: %s" % msg.topic)
        tokens = msg.topic.split("/")
        # Basic validation of the message topic structure
        if (
            tokens[0] == self.config["spBv"]
            and tokens[1] == self.config["myGroupId"]
            and tokens[3] == self.config["myNodeName"]
        ):
            self.handle_message(tokens, msg)
        else:
            print("Unknown namespace received: %s" % msg.topic)

    def handle_message(self, tokens, msg):
        """Dispatches message handling based on the topic."""
        if tokens[2] == "DBIRTH":
            self.handle_birth_message(msg)
        elif tokens[2] == "DDEATH":
            self.handle_death_message()
        elif tokens[2] == "DDATA":
            self.handle_data_message(msg)
        else:
            print("Unhandled message type: %s" % "/".join(tokens))

    def handle_death_message(self):
        """Handles device death messages."""
        print("Device Death Certificate has been published. Oh well...")

    def handle_birth_message(self, msg):
        """Handles device birth messages."""
        print("Device Birth Certificate has been published. Yay!!!")

    def handle_data_message(self, msg):
        """Processes device data messages."""
        try:
            inboundPayload = sparkplug_b_pb2.Payload()
            inboundPayload.ParseFromString(msg.payload)
            for metric in inboundPayload.metrics:
                if metric.name in self.coord_names:
                    coord = metric.name.split()[-1]
                    self.coordinates[coord] = round(metric.float_value * 0.0254, 5)
            print(f"Updated coordinates: {self.coordinates}")
            BUS.push(NEW_MESSAGE, payload=self.coordinates)

        except Exception as e:
            print(f"Failed to parse inbound payload: {e}")


NEW_MESSAGE = carb.events.type_from_string("cell.dt.NEW_MESSAGE_EVENT")
BUS = omni.kit.app.get_app().get_message_bus_event_stream()

if __name__ == "__main__":
    dt = DT(config_path)
    dt.connect()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        dt.disconnect()
