# LoRaWAN E-Parking Demo

This is a real showcase of a Cisco IoT solution: Getting sensor data via LoRaWAN to display its information on this website and via a Webex Teams bot.

It is currently in use in the Cisco office in Frankfurt, Germany for owners of electric vehicles to check if available e-parking spaces (with charging stations) are available.

This example should showcase how easy and with a few lines of code a simple IoT deployment can look like.

More Information: [https://fkf3parking.devnetcloud.com](https://fkf3parking.devnetcloud.com)

## Built With

* Cisco LoRaWAN gateway
* Actility Thingpark Enterprise SaaS
* InfluxDB, Mosquitto
* Memcached
* Paho-MQTT, Flask, Webexteamsbot, Webexteamssdk

## Contributing

* **Flo Pachinger** - [flopach](https://github.com/flopach)
* **Michael Eder** - [miceder](https://github.com/miceder)

## Versioning

**1.1 - 02/2020:** added dashboard functionality, fixed timezone + last update
**1.0 - 12/2019:** Initial release - Webex Teams bot, website service, MQTT & DB handling

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE.md](LICENSE.md) file for details

## Further Links

* [Project Website](https://fkf3parking.devnetcloud.com/)
* [Cisco DevNet Website](https://developer.cisco.com)
* [Webex Developers Website](https://developer.webex.com)
* [Cisco LoRaWAN IXM Gateway](https://www.cisco.com/c/en/us/products/collateral/se/internet-of-things/datasheet-c78-737307.html)