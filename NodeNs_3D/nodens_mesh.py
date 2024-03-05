import paho.mqtt.client as mqtt
import time
import json
import logging

def on_subscribe(unused_client, unused_userdata, mid, granted_qos):
    logging.debug('MESH: on_subscribe: mid {}, qos {}'.format(mid, granted_qos))

def on_connect(client, userdata, flags, rc):
    logging.debug('MESH: on_connect: {} userdata: {}. flags: {}.'.format(mqtt.connack_string(rc), userdata, flags))

def on_disconnect(client, userdata, rc):
    logging.debug('MESH: on_disconnect: {} userdata: {}.'.format(mqtt.connack_string(rc), userdata))

    if rc == 5:
        time.sleep(1)

def on_unsubscribe(client, userdata, mid):
    logging.debug('MESH: on_unsubscribe: mid {}. userdata: {}.'.format(mid, userdata))

class mesh:
    def __init__(self):
        self.client = mqtt.Client()

        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_subscribe = on_subscribe
        self.client.on_unsubscribe = on_unsubscribe

        self.status = self.Status()

    def end(self):
        self.client.loop_stop()
        self.client.unsubscribe('#')
        self.client.disconnect()

    def connect(self, ip, port, timeout, topic, cb):
        self.client.message_callback_add(topic, cb)
        self.client.connect(ip,port,timeout)
        self.client.subscribe(topic,1)
        self.client.loop_start()

    def reconnect(self, ip, port, timeout):
        self.end()
        self.client.connect(ip, port, timeout)

    def loop_start(self):
        self.client.loop_start()

    def loop_stop(self):
        self.client.loop_stop()

    def multiline_payload(self, ip, port, timeout, topic, payload):
        self.reconnect(ip, port, timeout)
        time.sleep(1)
        for i in range(len(payload)):
            json_message = json.dumps(payload[i])
            logging.debug("CONFIG SEND: {}".format(json_message))
            print("CONFIG SEND: {}".format(json_message))
            self.client.publish(topic, json_message)
            time.sleep(0.01)
        self.client.subscribe('#')
        self.client.loop_start()

        

    class Status:
        def __init__(self):
            self.flag_connect = False
            self.flag_config_proc = False
            self.reset_history()
            self.reset_last_msg()
            self.reset_last_info()

        def reset_last_msg(self):
            self.last_msg = ''
            self.last_msg_timestamp = ''

        def reset_last_info(self):
            self.last_info = ''
            self.last_info_timestamp = ''
        
        def reset_history(self):         
            self.msg_history = []            
            self.msg_timestamp_history = []
            self.info_history = []            
            self.info_timestamp_history = []

        def receive_msg(self, payload, timestamp):
            self.last_msg = payload[5:]
            self.last_msg_timestamp = timestamp
            self.msg_history.insert(0,payload[5:])
            self.msg_timestamp_history.insert(0,timestamp)
            print(self.last_msg)

        def receive_info(self, payload, timestamp):
            self.last_info = payload
            self.last_info_timestamp = timestamp
            self.info_history.insert(0,payload)
            self.info_timestamp_history.insert(0,timestamp)
            print(self.last_info)


MESH = mesh()

