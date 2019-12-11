# -*- coding: utf-8 -*-
#
# FKF3 E-Parking Demo 1.0
# https://fkf3parking.devnetcloud.com
# Flo Pachinger / flopach, Cisco Systems, Dec 2019
# Apache License 2.0
#
import paho.mqtt.client as mqtt
from pymemcache.client import base
import time
import json
from webexteamsbot import TeamsBot
from webexteamssdk import WebexTeamsAPI
from influxdb import InfluxDBClient
from datetime import datetime
import requests
import logging
from flask_cors import CORS

"""
CONFIG
"""

# LoRa devices info
parkEUI1 = ""
parkEUI2 = ""
parkEUI3 = ""
parkEUI4 = ""

# InfluxDB Connect
influx_client = InfluxDBClient(host="", port="", username='', password='', database="")

# Memcache for faster status retrieval
memcache_client = base.Client(('127.0.0.1', 11211))

# MQTT broker credentials
client = mqtt.Client("")
client.tls_set("", tls_version=2)
client.username_pw_set("", "")
client.connect("", 8883, 60)

# Cisco Webex Teams Infos
bot_email = ""
bot_token = ""
bot_url = ""
bot_app_name = ""
webexAPI = WebexTeamsAPI(access_token=bot_token)

# Create the Bot Object
bot = TeamsBot(
    bot_app_name,
    teams_bot_token=bot_token,
    teams_bot_url=bot_url,
    teams_bot_email=bot_email,
)

#allow CORS for the website
CORS(bot)

# Create Logs
# for the future - not implemented yet
#logger = logging.getLogger()
#logger.setLevel(logging.INFO)

"""
MQTT FUNCTIONS
"""

def on_message(client, userdata, message):
    # Get JSON data into a dict
    rawjson = message.payload.decode('utf-8')
    data = json.loads(rawjson)

    """
    check which lora devices is sending the data
    static mapping of EUI and device
    """
    if data["DevEUI"] == parkEUI1:
        parkingspace = 1
    elif data["DevEUI"] == parkEUI2:
        parkingspace = 2
    elif data["DevEUI"] == parkEUI3:
        parkingspace = 3
    elif data["DevEUI"] == parkEUI4:
        parkingspace = 4
    else:
        parkingspace = 0

    """
    Bosch Parking sensors payload_hex: 1 = occupied, 0 = empty
    """
    if data["payload_hex"] == "01":
        msg_status = "OCCUPIED"
        parkingstatus = 1
    elif data["payload_hex"] == "00":
        msg_status = "EMPTY"
        parkingstatus = 0
    else:
        msg_status = "unknown"
        parkingstatus = 2

    """
    Bosch Parking sensors have for each message type a different port.
    Port 1 = parking change | Port 2 = 24h heartbeat | Port 3 = Startup Message
    Write everything in the database, but change the temp information only on port 1
    """
    if data["FPort"] == "1":
        port = 1

        # Insert data into memcache
        memcache_client.set("park{}".format(parkingspace), parkingstatus)

        """
        Check if ALL parking spaces are occupied.
        Check if only ONE parking space is empty
        Only if so, send a webex message now
        """
        sum = int(memcache_client.get('park1')) + int(memcache_client.get('park2')) + int(
            memcache_client.get('park3')) + int(memcache_client.get('park4'))

        if sum == 3:
            send_webex_msg("Only **ONE** parking space is still **available now**")
        elif sum == 4:
            send_webex_msg("**ALL** parking spaces are now **OCCUPIED**")

        # send Webex Message only if parking change
        # send_webex_msg("**Parking Space {}** is now **{}**".format(parkingspace, msg_status))

    elif data["FPort"] == "2":
        port = 2
    elif data["FPort"] == "3":
        port = 3
    else:
        port = 0

    # Insert data into influx database
    try:
        insert_json_influx(parkingspace, parkingstatus, port)
    except:
        print('DB Error - could not insert data into influx')


# Get all rooms of the webex user (max 200 for now) and send a message out
def send_webex_msg(content):
    rooms = webexAPI.rooms.list(max=200)
    for room in rooms:
        webexAPI.messages.create(roomId=room.id, markdown=content)


# create a json with the parameters and insert it to influxdb
def insert_json_influx(parkingspace, parkingstatus, port):
    json_body = [
        {
            "measurement": "parkingstatus",
            "tags": {
                "parkingspace": parkingspace,
                "port": port
            },
            "fields": {
                "value": parkingstatus,
            },
            "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        }
    ]
    # write data into the influxdb
    influx_client.write_points(json_body)

#Initaliaze Memcache ang get latest data from influx
def init_memcache_parkingstatus():
    parkingstatus_1 = influx_client.query("SELECT LAST(value) FROM parkingstatus WHERE parkingspace = '1'")
    parkingstatus_2 = influx_client.query("SELECT LAST(value) FROM parkingstatus WHERE parkingspace = '2'")
    parkingstatus_3 = influx_client.query("SELECT LAST(value) FROM parkingstatus WHERE parkingspace = '3'")
    parkingstatus_4 = influx_client.query("SELECT LAST(value) FROM parkingstatus WHERE parkingspace = '4'")

    memcache_client.set('park1', list(parkingstatus_1.get_points())[0]["last"])
    memcache_client.set('park2', list(parkingstatus_2.get_points())[0]["last"])
    memcache_client.set('park3', list(parkingstatus_3.get_points())[0]["last"])
    memcache_client.set('park4', list(parkingstatus_4.get_points())[0]["last"])
    print("Memcache setted up!")

# Define event callbacks
def on_connect(client, userdata, flags, rc):
    print("Result code " + str(rc))


# disconnect message
def on_disconnect(client, userdata, flags, rc=0):
    print("Result code " + str(rc))
    client.loop_stop()


def on_subscribe(client, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_publish(client, obj, msg):
    print(str(msg.payload))


def on_log(client, userdata, level, buf):
    print("log: " + buf)


"""
WEBEX BOT FUNCTIONS
"""

# Get current status and send as webex card
def getc(incoming_msg):
    card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [{
                "type": "Container",
                "items": [{
                    "type": "TextBlock",
                    "text": "FKF3 E-Parking Status",
                    "size": "Medium"
                }]
            },{
                "type": "Container",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "",
                        "weight": "Bolder",
                        "color": ""
                    },
                    {
                        "type": "TextBlock",
                        "text": "",
                        "weight": "Bolder",
                        "color": ""
                    },
                    {
                        "type": "TextBlock",
                        "text": "",
                        "weight": "Bolder",
                        "color": ""
                    },
                    {
                        "type": "TextBlock",
                        "text": "",
                        "weight": "Bolder",
                        "color": ""
                    }
                    ]
            }
            ],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.0"
        }
    }

    y=1
    markdown = "FKF3 E-Parking Status:\n"
    for x in range(4):
        if int(memcache_client.get('park{}'.format(y))) == 0:
            card["content"]["body"][1]["items"][x]["text"] = "P{} - EMPTY".format(y)
            card["content"]["body"][1]["items"][x]["color"] = "Good"
            markdown = markdown + "* **P{} EMPTY**\n".format(y)
        else:
            card["content"]["body"][1]["items"][x]["text"] = "P{} - OCCUPIED".format(y)
            card["content"]["body"][1]["items"][x]["color"] = "Attention"
            markdown = markdown + "* **P{} OCCUPIED**\n".format(y)
        y=y+1

    #send a message with a card attachment not yet supported by webexteamssdk
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + bot_token
    }
    data = {"roomId": incoming_msg.roomId, "attachments": card, "markdown": markdown}
    requests.post("https://api.ciscospark.com/v1/messages", json=data, headers=headers)
    return ""

"""
SERVICES for WEBSITE
"""

#Get current status for the website
def wc():
    status = { "park1": int(memcache_client.get('park1')),
               "park2": int(memcache_client.get('park2')),
               "park3": int(memcache_client.get('park3')),
               "park4": int(memcache_client.get('park4'))
               }
    return json.dumps(status)

"""
MAIN
"""

if __name__ == "__main__":
    # MQTT connection parameters
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    #client.on_log = on_log
    client.on_publish = on_publish

    # Topics to subscribe
    client.subscribe("eschbornoffice/things/{}/uplink".format(parkEUI1))
    client.subscribe("eschbornoffice/things/{}/uplink".format(parkEUI2))
    client.subscribe("eschbornoffice/things/{}/uplink".format(parkEUI3))
    client.subscribe("eschbornoffice/things/{}/uplink".format(parkEUI4))

    #Initaliaze Memcached
    init_memcache_parkingstatus()

    # Bot commands
    bot.set_help_message("Hi! I will automatically notify you if one parking space is still available or all are occupied. You can also ask me, see commands below. More information: https://fkf3parking.devnetcloud.com:\n")
    bot.remove_command("/echo")
    bot.add_command("/c", "Get the current parking status", getc)
    bot.add_new_url("/wc", "website-current", wc)

    # Start MQTT client and run bot
    client.loop_start()
    bot.run(host="0.0.0.0", port=5000)
