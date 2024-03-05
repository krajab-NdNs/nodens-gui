#!/usr/bin/env python

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python sample for connecting to Google Cloud IoT Core via MQTT, using JWT.
This example connects to Google Cloud IoT Core via MQTT, using a JWT for device
authentication. After connecting, by default the device publishes 100 messages
to the device's MQTT topic at a rate of one per second, and then exits.
Before you run the sample, you must follow the instructions in the README
for this sample.
"""

# [START iot_mqtt_includes]
import argparse
import datetime
import logging
import os
import random
import ssl
import time

import paho.mqtt.client as mqtt
from socket import gaierror
import nodens_fns as ndns_fns
import nodens_mesh as ndns_mesh

# [END iot_mqtt_includes]

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.CRITICAL)

# The initial backoff time after a disconnection occurs, in seconds.
minimum_backoff_time = 1

# The maximum backoff time before giving up, in seconds.
MAXIMUM_BACKOFF_TIME = 32

# Whether to wait with exponential backoff before publishing.
should_backoff = False


# [START iot_mqtt_jwt]
def create_jwt(project_id, private_key_file, algorithm, jwt_expires_minutes):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
    Args:
       project_id: The cloud project ID this device belongs to
       private_key_file: A path to a file containing either an RSA256 or
                       ES256 private key.
       algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
       jwt_expires_minutes: The time in minutes before the JWT expires.
    Returns:
        An MQTT generated from the given project_id and private key, which
        expires in 20 minutes. After 20 minutes, your client will be
        disconnected, and a new JWT will have to be generated.
    Raises:
        ValueError: If the private_key_file does not contain a known key.
    """

    token = {
      # The time that the token was issued at
      'iat': datetime.datetime.utcnow(),
      # The time the token expires.
      'exp':
      datetime.datetime.utcnow() +
      datetime.timedelta(minutes=jwt_expires_minutes),
      # The audience field should always be set to the GCP project id.
      'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    logging.debug('Creating JWT using {} from private key file {}'.format(
        algorithm, private_key_file))

    return 0

# [END iot_mqtt_jwt]


# [START iot_mqtt_config]
def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return "{}: {}".format(rc, mqtt.error_string(rc))


def on_connect_GCP(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    logging.warning('GCP: on_connect: {}. rc = {}.'.format(mqtt.connack_string(rc), rc))

    # After a successful connect, reset backoff time and stop backing off.
    global should_backoff
    global minimum_backoff_time
    should_backoff = False
    minimum_backoff_time = 1


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print("on_disconnect", error_str(rc))

    # Since a disconnect occurred, the next loop iteration will wait with
    # exponential backoff.
    global should_backoff
    should_backoff = True


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    i=1


def on_message_GCP(client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = str(message.payload.decode("utf-8"))
    print(        "********************************\nReceived message '{}' on topic '{}' with Qos {}\n********************************".format(
            payload, message.topic, str(message.qos)))

    global sv

    payload = message.payload.decode('utf8')
    logging.debug('GCP: Received message \'{}\' on topic \'{}\' with Qos {}'.format(
            payload, message.topic, str(message.qos)))

    # KZR: check error if reattach is needed
    try:
        temp_msg = json.loads(payload)
    except:
        temp_msg = []

    if "error_type" in temp_msg:
        if (temp_msg["error_type"].startswith("GATEWAY_DEVICE_NOT_FOUND")):
            print("Reattach to gateway")
            attach_state = 0

            while not gateway_state.connected:
                time.sleep(0.5)
            if attach_state == 0:
                detach_topic = "/devices/{}/detach".format(cp.MQTT_TOPIC)
                logging.debug("DETACHING: {}".format(detach_topic))
                client.publish(detach_topic, "{}", qos=1)

                attach_topic = '/devices/' + cp.MQTT_TOPIC+ '/attach'
                auth = ''  # TODO:    auth = command["jwt"]
                attach_payload = '{{"authorization" : "{}"}}'.format(auth)
                response, attach_mid = client.publish(
                            attach_topic, attach_payload, qos=1)
                attach_state = 1
                logging.debug("ATTACH. State: {}. Response: {}. mid: {}.".format(attach_state, response, attach_mid))

    # Parse topic
    #rcp = radar_config_params()
    rx_topic = message.topic
    rx_topic_split = rx_topic.split('/')
    #try:
    if 1:
        rx_dev_idx = [i for i,s in enumerate(rx_topic_split) if 'devices' in s]
        rx_dev_idx = rx_dev_idx[0]
    
        rx_gw = rx_topic_split[rx_dev_idx + 1]
        rx_msgtype = rx_topic_split[rx_dev_idx + 2]

        if rx_msgtype == 'commands':
            if len(rx_topic_split) - 1 == rx_dev_idx + 2:
                rx_msg_subtopic = []
                logging.debug('no subtopic')
            else:
                rx_msg_subtopic = rx_topic_split[rx_dev_idx+3]
                if len(rx_msg_subtopic) == 12:
                    logging.debug('subtopic is: {}'.format(rx_msg_subtopic))
                else:
                    logging.warning('Subtopic ({}) has incorrect format.'.format(rx_msg_subtopic) +
                          'It should be the sensor id (12 characters).')
                    rx_msg_subtopic = []
        
            #payload = re.sub(u'\u201c','"',payload)
            #payload = re.sub(u'\u201d','"',payload)
            try:
                command_json = json.loads((payload.lower()))
            except:
                command_json = []

            # Set TI reset flag
            flag_ti_reset = 0
            print("step 1:{}".format(ndns_fns.rcp.SENSOR_TARGET))
            # First determine the correct sensor to configure
            if "sensor id" in command_json:
                if command_json["sensor id"] == rx_msg_subtopic:
                    ndns_fns.rcp.SENSOR_TARGET = rx_msg_subtopic
                    logging.debug('(a) Sensor command sent to: {}'.format(ndns_fns.rcp.SENSOR_TARGET))
                else:
                    logging.warning('WARNING: Submitted sensor ID does not match with subtopic!' +
                          'Sending configuration to submitted Sensor ID.')
                    ndns_fns.rcp.SENSOR_TARGET = command_json["sensor id"]
            elif len(rx_msg_subtopic) > 0:
                ndns_fns.rcp.SENSOR_TARGET = rx_msg_subtopic
                logging.debug('(b) Sensor command sent to: {}'.format(ndns_fns.rcp.SENSOR_TARGET))
            else:
                ndns_fns.rcp.SENSOR_TARGET = []
                logging.warning('No sensor defined for new configuration!')
            
            # Reset config payload message
            payload_msg = []
            print("step 2:{}".format(ndns_mesh.MESH.client))
            # After selecting the sensor for configuration, parse the configs
            if (len(ndns_fns.rcp.SENSOR_TARGET)>0):
                # Check version
                print("step 3")
                ndns_fns.sv = ndns_fns.sensor_version()
                print("step 4")
                ndns_fns.sv.request(ndns_mesh.MESH.client,ndns_fns.rcp.SENSOR_TOPIC, ndns_fns.rcp.SENSOR_TARGET)
                logging.debug("Published sensor version request")

            
                # TODO : Update to check for 3D
                # scanning config
                if "scanning config" in command_json:
                    command_scanning = command_json["scanning config"]
                    if "scan time" in command_scanning:
                        ndns_fns.rcp.SCAN_TIME = command_scanning["scan time"]
                        rate_unit = 2 # Baseline data transmission rate
                        config_pub_rate = "CMD: PUBLISH RATE: " + str(round(ndns_fns.rcp.SCAN_TIME/rate_unit))
                        payload_msg.append({ "addr" : [ndns_fns.rcp.SENSOR_TARGET],
                            "type" : "json",
                            "data" : config_pub_rate + "\n"})
                    if "full data flag" in command_scanning:
                        full_data_flag = command_scanning["full data flag"]
                        if full_data_flag == 1 or full_data_flag == "on":
                            if "full data time" in command_scanning:
                                ndns_fns.rcp.FULL_DATA_TIME = command_scanning["full data time"]
                            else:
                                logging.debug("Full data time not specified. Reverting to default value: {}.".format(ndns_fns.rcp.FULL_DATA_TIME))
                            config_full_data = "CMD: FULL DATA ON. RATE: " + str(max(1,ndns_fns.rcp.FULL_DATA_TIME/ndns_fns.rcp.SCAN_TIME))
                        else:
                            config_full_data = "CMD: FULL DATA OFF."
                        payload_msg.append({ "addr" : [ndns_fns.rcp.SENSOR_TARGET],
                            "type" : "json",
                            "data" : config_full_data + "\n"})
                # check the radar config
                if "radar config" in command_json:
                    flag_ti_reset = 1
                    command_radar = command_json["radar config"]
                    if "room x min" in command_radar:
                        ndns_fns.rcp.ROOM_X_MIN = command_radar["room x min"]
                    if "room x max" in command_radar:
                        ndns_fns.rcp.ROOM_X_MAX = command_radar["room x max"]
                    if "room y min" in command_radar:
                        ndns_fns.rcp.ROOM_Y_MIN = command_radar["room y min"]
                    if "room y max" in command_radar:
                        ndns_fns.rcp.ROOM_Y_MAX = command_radar["room y max"]  
                    if "room z min" in command_radar:
                        ndns_fns.rcp.ROOM_Y_MIN = command_radar["room z min"]
                    if "room z max" in command_radar:
                        ndns_fns.rcp.ROOM_Y_MAX = command_radar["room z max"]                       
         
                    # Room size #
                    if ndns_fns.sv.radar_dim == 2:
                        param_temp = ndns_fns.rcp.config_radar[15].split(" ")
                        param_temp[1:5] = [str(ndns_fns.rcp.ROOM_X_MIN), str(ndns_fns.rcp.ROOM_X_MAX), str(ndns_fns.rcp.ROOM_Y_MIN), str(ndns_fns.rcp.ROOM_Y_MAX)]
                        ndns_fns.rcp.config_radar[15] = " ".join(param_temp)
                        logging.debug(ndns_fns.rcp.config_radar[15])
                    elif ndns_fns.sv.radar_dim == 3:
                        # Static - 20
                        param_temp = ndns_fns.rcp.config_radar[20].split(" ")
                        param_temp[1:5] = [str(ndns_fns.rcp.ROOM_X_MIN)+0.5, str(ndns_fns.rcp.ROOM_X_MAX)-0.5, str(ndns_fns.rcp.ROOM_Y_MIN)+0.5, str(ndns_fns.rcp.ROOM_Y_MAX)-0.5, str(ndns_fns.rcp.ROOM_Z_MIN), str(ndns_fns.rcp.ROOM_Z_MAX)]
                        ndns_fns.rcp.config_radar[20] = " ".join(param_temp)
                        logging.debug(ndns_fns.rcp.config_radar[20])

                        # Boundary - 21
                        param_temp = ndns_fns.rcp.config_radar[21].split(" ")
                        param_temp[1:5] = [str(ndns_fns.rcp.ROOM_X_MIN), str(ndns_fns.rcp.ROOM_X_MAX), str(ndns_fns.rcp.ROOM_Y_MIN), str(ndns_fns.rcp.ROOM_Y_MAX), str(ndns_fns.rcp.ROOM_Z_MIN), str(ndns_fns.rcp.ROOM_Z_MAX)]
                        ndns_fns.rcp.config_radar[21] = " ".join(param_temp)
                        logging.debug(ndns_fns.rcp.config_radar[21])

                        # Presence - 28
                        param_temp = ndns_fns.rcp.config_radar[28].split(" ")
                        param_temp[1:5] = [str(ndns_fns.rcp.ROOM_X_MIN), str(ndns_fns.rcp.ROOM_X_MAX), str(ndns_fns.rcp.ROOM_Y_MIN), str(ndns_fns.rcp.ROOM_Y_MAX), str(ndns_fns.rcp.ROOM_Z_MIN), str(ndns_fns.rcp.ROOM_Z_MAX)]
                        ndns_fns.rcp.config_radar[28] = " ".join(param_temp)
                        logging.debug(ndns_fns.rcp.config_radar[28])

                    if "occ sensitivity" in command_radar:
                        if ndns_fns.sv.radar_dim == 2:
                            ndns_fns.rcp.OCC_SENSITIVITY = command_radar["occ sensitivity"]
                            param_temp = ndns_fns.rcp.config_radar[12].split(" ")
                            param_temp[1] = str(round(np.exp(1.8/float(ndns_fns.rcp.OCC_SENSITIVITY)+2.1)))
                            param_temp[2] = str(round(np.exp(0.7/float(ndns_fns.rcp.OCC_SENSITIVITY)+5.3)))
                            param_temp[4] = str(round(np.exp(0.7/float(ndns_fns.rcp.OCC_SENSITIVITY)+2)))
                            ndns_fns.rcp.config_radar[12] = " ".join(param_temp)

                    if "sensitivity" in command_radar:
                        if ndns_fns.sv.radar_dim == 2:
                            ndns_fns.rcp.SENSITIVITY = command_radar["sensitivity"]
                            param_temp = ndns_fns.rcp.config_radar[10].split(" ")
                            param_temp[10] = str(round(np.exp(0.7/float(ndns_fns.rcp.SENSITIVITY)+2.3)))
                            param_temp[11] = str(round(np.exp(0.5/float(ndns_fns.rcp.SENSITIVITY)+3)))
                            ndns_fns.rcp.config_radar[10] = " ".join(param_temp)

                    # Parse config to payload #
                    for i in range(len(ndns_fns.rcp.config_radar)):
                        payload_msg.append({ "addr" : [ndns_fns.rcp.SENSOR_TARGET],
                                    "type" : "json",
                                    "data" : ndns_fns.rcp.config_radar[i] + "\n"})  
                if (flag_ti_reset):
                    payload_msg.append({ "addr" : [ndns_fns.rcp.SENSOR_TARGET],
                        "type" : "json",
                        "data" : "CMD: TI RESET" + "\n"})

                #pub_mqtt = Publish_mqtt(payload_msg, cp, ndns_fns.rcp)
                ndns_mesh.MESH.multiline_payload(ndns_fns.cp.SENSOR_IP,ndns_fns.cp.SENSOR_PORT,60, ndns_fns.rcp.SENSOR_TOPIC, payload_msg)

        # Check if config:
        # ?        
        elif rx_msgtype == 'config':
            logging.debug('********** \n NEW CONFIG \n Gateway: {} \n Config: {} \n **********'.format(rx_gw, payload))
    #except:
    #    print('nope')

    # Check if command:
        # /Command/deviceid - > send new config to device

    # Check if config:
        # ?


def get_client(
    project_id,
    cloud_region,
    registry_id,
    device_id,
    private_key_file,
    algorithm,
    ca_certs,
    mqtt_bridge_hostname,
    mqtt_bridge_port,
    jwt_expires_minutes,
):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client_id = "projects/{}/locations/{}/registries/{}/devices/{}".format(
        project_id, cloud_region, registry_id, device_id
    )
    print("Device client_id is '{}'".format(client_id))

    client = mqtt.Client(client_id=client_id)

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(
        username="unused", password=create_jwt(project_id, private_key_file, algorithm, jwt_expires_minutes)
        )

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect_GCP
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message_GCP

    print("connect")

    # Connect to the Google MQTT bridge.
    
    while 1:
        try:
            should_backoff = True
            #while should_backoff:
            client.connect(mqtt_bridge_hostname, mqtt_bridge_port)
            time.sleep(1)
            break
        except gaierror as e:
            logging.warning('Gaierror {}.'.format(e))
            logging.warning('Waiting {} seconds before restarting Main'.format(1))
            time.sleep(1)

    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = "/devices/{}/config".format(device_id)

    # Subscribe to the config topic.
    client.subscribe(mqtt_config_topic, qos=1)

    # The topic that the device will receive commands on.
    mqtt_command_topic = "/devices/{}/commands/#".format(device_id)

    # Subscribe to the commands topic, QoS 1 enables message acknowledgement.
    print("Subscribing to {}".format(mqtt_command_topic))
    client.subscribe(mqtt_command_topic, qos=0)

    return client

def disconnect_client(
    client,
    mqtt_bridge_hostname,
    mqtt_bridge_port
):


    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect_GCP
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message_GCP

    print("disconnect")

    # Disconnect from the Google MQTT bridge.
    client.disconnect(mqtt_bridge_hostname, mqtt_bridge_port)


    return client

# [END iot_mqtt_config]


def detach_device(client, device_id):
    """Detach the device from the gateway."""
    # [START iot_detach_device]
    detach_topic = "/devices/{}/detach".format(device_id)
    print("Detaching: {}".format(detach_topic))
    client.publish(detach_topic, "{}", qos=1)
    # [END iot_detach_device]


def attach_device(client, device_id, auth):
    """Attach the device to the gateway."""
    # [START iot_attach_device]
    attach_topic = "/devices/{}/attach".format(device_id)
    attach_payload = '{{"authorization" : "{}"}}'.format(auth)
    response, attach_mid = client.publish(attach_topic, attach_payload, qos=1)
    print("ATTACH. Response: {}. mid: {}.".format(response, attach_mid))

    # [END iot_attach_device]


def listen_for_messages(
    config_params,
    gateway_state,
    duration,
    cb=None,
):
    """Listens for messages sent to the gateway and bound devices."""
    # [START iot_listen_for_messages]
    global minimum_backoff_time

    jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
    jwt_exp_mins = config_params.JWT_TIME_MINS
    # Use gateway to connect to server
    client = get_client(
        config_params.PROJECT_ID,
        config_params.PROJECT_REGION,
        config_params.MQTT_REGISTRY,
        config_params.MQTT_GATEWAY,
        config_params.PRIVATE_CERT,
        'RS256',
        config_params.CA_CERT,
        'mqtt.googleapis.com', #gateway_state.mqtt_bridge_hostname,
        8883, #gateway_state.mqtt_bridge_port,
        config_params.JWT_TIME_MINS,
    )

    attach_device(client, config_params.MQTT_TOPIC, "")
    print("Waiting for device to attach.")
    time.sleep(5)

    # The topic devices receive configuration updates on.
    #device_id = config_params.MQTT_GATEWAY # NodeNs KZR: temporary until device is added
    #device_config_topic = "/devices/{}/config".format(device_id)
    #client.subscribe(device_config_topic, qos=1)

    # The topic gateways receive configuration updates on.
    #gateway_config_topic = "/devices/{}/config".format(config_params.MQTT_GATEWAY)
    #client.subscribe(gateway_config_topic, qos=1)

    # The topic gateways receive error updates on. QoS must be 0.
    error_topic = "/devices/{}/errors".format(config_params.MQTT_GATEWAY)
    client.subscribe(error_topic, qos=0)

    # Wait for about a minute for config messages.
    for i in range(1, duration):
        client.loop_start()
        if cb is not None:
            cb(client)

        #if should_backoff:
        #    # If backoff time is too large, give up.
        #    if minimum_backoff_time > MAXIMUM_BACKOFF_TIME:
        #        print("listen. Exceeded maximum backoff time. Giving up.")
        #        break

        #    delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
        #    time.sleep(delay)
        #    minimum_backoff_time *= 2
        #    client.connect(gateway_state.mqtt_bridge_hostname, gateway_state.mqtt_bridge_port)

        #seconds_since_issue = (datetime.datetime.now(tz=datetime.timezone.utc) - jwt_iat).seconds
        #if seconds_since_issue > 60 * jwt_exp_mins:
        #    print("Refreshing token after {}s".format(seconds_since_issue))
        #    jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
        #    client.loop()
        #    client.disconnect()
        #    client = get_client(
        #        config_params.PROJECT_ID,
        #        config_params.PROJECT_REGION,
        #        config_params.MQTT_REGISTRY,
        #        config_params.MQTT_GATEWAY,
        #        config_params.PRIVATE_CERT,
        #        'RS256',
        #        config_params.CA_CERT,
        #        'mqtt.googleapis.com', #gateway_state.mqtt_bridge_hostname,
        #        8883, #gateway_state.mqtt_bridge_port,
        #        config_params.JWT_TIME_MINS,
        #    )

        #time.sleep(1)

    #detach_device(client, config_params.MQTT_TOPIC)

    return client

    # [END iot_listen_for_messages]


def send_data_from_bound_device(
    client,
    config_params,
    gateway_state,
    num_messages,
    payload,
    jwt_iat,
):
    """Sends data from a gateway on behalf of a device that is bound to it."""
    # [START send_data_from_bound_device]
    global minimum_backoff_time

    # Publish device events and gateway state.
    
    device_topic = "/devices/{}/{}".format(config_params.MQTT_TOPIC, "events")
    mqtt_topic = '/devices/{}/{}'.format(config_params.MQTT_REGISTRY,'state')
    gateway_topic = "/devices/{}/{}".format(config_params.MQTT_REGISTRY,"events")

    #jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
    jwt_exp_mins = config_params.JWT_TIME_MINS


    # Publish num_messages messages to the MQTT bridge
    for i in range(1, num_messages + 1):

        client.publish(device_topic, payload, qos=0)

        time.sleep(1)

    #detach_device(client, config_params.MQTT_TOPIC)
    #return jwt_iat

    # [END send_data_from_bound_device]


def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=("Example Google Cloud IoT Core MQTT device connection code.")
    )
    parser.add_argument(
        "--algorithm",
        choices=("RS256", "ES256"),
        required=True,
        help="Which encryption algorithm to use to generate the JWT.",
    )
    parser.add_argument(
        "--ca_certs",
        default="roots.pem",
        help="CA root from https://pki.google.com/roots.pem",
    )
    parser.add_argument(
        "--cloud_region", default="us-central1", help="GCP cloud region"
    )
    parser.add_argument(
        "--data",
        default="Hello there",
        help="The telemetry data sent on behalf of a device",
    )
    parser.add_argument("--device_id", required=True, help="Cloud IoT Core device id")
    parser.add_argument("--gateway_id", required=False, help="Gateway identifier.")
    parser.add_argument(
        "--jwt_expires_minutes",
        default=20,
        type=int,
        help="Expiration time, in minutes, for JWT tokens.",
    )
    parser.add_argument(
        "--listen_dur",
        default=60,
        type=int,
        help="Duration (seconds) to listen for configuration messages",
    )
    parser.add_argument(
        "--message_type",
        choices=("event", "state"),
        default="event",
        help=(
            "Indicates whether the message to be published is a "
            "telemetry event or a device state message."
        ),
    )
    parser.add_argument(
        "--mqtt_bridge_hostname",
        default="mqtt.googleapis.com",
        help="MQTT bridge hostname.",
    )
    parser.add_argument(
        "--mqtt_bridge_port",
        choices=(8883, 443),
        default=8883,
        type=int,
        help="MQTT bridge port.",
    )
    parser.add_argument(
        "--num_messages", type=int, default=100, help="Number of messages to publish."
    )
    parser.add_argument(
        "--private_key_file", required=True, help="Path to private key file."
    )
    parser.add_argument(
        "--project_id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="GCP cloud project name",
    )
    parser.add_argument(
        "--registry_id", required=True, help="Cloud IoT Core registry id"
    )
    parser.add_argument(
        "--service_account_json",
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        help="Path to service account json file.",
    )

    # Command subparser
    command = parser.add_subparsers(dest="command")

    command.add_parser("device_demo", help=mqtt_device_demo.__doc__)

    command.add_parser("gateway_send", help=send_data_from_bound_device.__doc__)

    command.add_parser("gateway_listen", help=listen_for_messages.__doc__)

    return parser.parse_args()


def mqtt_device_demo(args):
    """Connects a device, sends data, and receives data."""
    # [START iot_mqtt_run]
    global minimum_backoff_time
    global MAXIMUM_BACKOFF_TIME

    # Publish to the events or state topic based on the flag.
    sub_topic = "events" if args.message_type == "event" else "state"

    mqtt_topic = "/devices/{}/{}".format(args.device_id, sub_topic)

    jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
    jwt_exp_mins = args.jwt_expires_minutes
    client = get_client(
        args.project_id,
        args.cloud_region,
        args.registry_id,
        args.device_id,
        args.private_key_file,
        args.algorithm,
        args.ca_certs,
        args.mqtt_bridge_hostname,
        args.mqtt_bridge_port,
    )

    # Publish num_messages messages to the MQTT bridge once per second.
    for i in range(1, args.num_messages + 1):
        # Process network events.
        client.loop()

        # Wait if backoff is required.
        if should_backoff:
            # If backoff time is too large, give up.
            if minimum_backoff_time > MAXIMUM_BACKOFF_TIME:
                print("Exceeded maximum backoff time. Giving up.")
                break

            # Otherwise, wait and connect again.
            delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
            print("Waiting for {} before reconnecting.".format(delay))
            time.sleep(delay)
            minimum_backoff_time *= 2
            client.connect(args.mqtt_bridge_hostname, args.mqtt_bridge_port)

        payload = "{}/{}-payload-{}".format(args.registry_id, args.device_id, i)
        print("Publishing message {}/{}: '{}'".format(i, args.num_messages, payload))
        # [START iot_mqtt_jwt_refresh]
        seconds_since_issue = (datetime.datetime.now(tz=datetime.timezone.utc) - jwt_iat).seconds
        if seconds_since_issue > 60 * jwt_exp_mins:
            print("Refreshing token after {}s".format(seconds_since_issue))
            jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
            client.loop()
            client.disconnect()
            client = get_client(
                args.project_id,
                args.cloud_region,
                args.registry_id,
                args.device_id,
                args.private_key_file,
                args.algorithm,
                args.ca_certs,
                args.mqtt_bridge_hostname,
                args.mqtt_bridge_port,
            )
        # [END iot_mqtt_jwt_refresh]
        # Publish "payload" to the MQTT topic. qos=1 means at least once
        # delivery. Cloud IoT Core also supports qos=0 for at most once
        # delivery.
        client.publish(mqtt_topic, payload, qos=1)

        # Send events every second. State should not be updated as often
        for i in range(0, 60):
            time.sleep(1)
            client.loop()
    # [END iot_mqtt_run]


def main():
    args = parse_command_line_args()

    if args.command and args.command.startswith("gateway"):
        if args.gateway_id is None:
            print("Error: For gateway commands you must specify a gateway ID")
            return

    if args.command == "gateway_listen":
        listen_for_messages(
            args.service_account_json,
            args.project_id,
            args.cloud_region,
            args.registry_id,
            args.device_id,
            args.gateway_id,
            args.num_messages,
            args.private_key_file,
            args.algorithm,
            args.ca_certs,
            args.mqtt_bridge_hostname,
            args.mqtt_bridge_port,
            args.jwt_expires_minutes,
            args.listen_dur,
        )
        return
    elif args.command == "gateway_send":
        send_data_from_bound_device(
            args.service_account_json,
            args.project_id,
            args.cloud_region,
            args.registry_id,
            args.device_id,
            args.gateway_id,
            args.num_messages,
            args.private_key_file,
            args.algorithm,
            args.ca_certs,
            args.mqtt_bridge_hostname,
            args.mqtt_bridge_port,
            args.jwt_expires_minutes,
            args.data,
        )
        return
    else:
        mqtt_device_demo(args)
    print("Finished.")

class GatewayState:
    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = ''

    # This is the topic that the device will receive error updates on.
    mqtt_error_topic = ''

    # KZR: This is the topic that the device will receive command updates on.
    mqtt_command_topic = ''

    # Host the gateway will connect to
    mqtt_bridge_hostname = ''
    mqtt_bridge_port = 8883

    # for all PUBLISH messages which are waiting for PUBACK. The key is 'mid'
    # returned by publish().
    pending_responses = {}

    # SUBSCRIBE messages waiting for SUBACK. The key is 'mid' from Paho.
    pending_subscribes = {}

    # for all SUBSCRIPTIONS. The key is subscription topic.
    subscriptions = {}

    # Indicates if MQTT client is connected or not
    connected = False

gateway_state = GatewayState()

if __name__ == "__main__":
    main()
