from __future__ import annotations

import json
import unittest

from mqtt_router.adapters.mapping_loader import load_vendor_config
from mqtt_router.adapters.shelly_native_adapter import transform_shelly_native
from mqtt_router.topic_mapper import IncomingTopic


class ShellyNativeAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vendor_config = load_vendor_config("shelly")

    def transform(self, native_path: str, payload: bytes) -> dict[str, object]:
        transformed = transform_shelly_native(
            IncomingTopic(
                tenant_slug="1234",
                message_type="telemetry",
                vendor="shelly",
                device_id="shellymot0",
                native_topic=True,
                native_path=native_path,
            ),
            payload,
            self.vendor_config,
        )
        return json.loads(transformed.decode("utf-8"))

    def test_scalar_native_mapping_still_works(self) -> None:
        result = self.transform("relay/0/power", b"12.5")

        self.assertEqual(result["device_id"], "shellymot0")
        self.assertEqual(result["device_name"], "shellymot0")
        self.assertEqual(result["vendor"], "shelly")
        self.assertEqual(result["power"], 12.5)

    def test_status_json_mapping_extracts_motion_fields(self) -> None:
        result = self.transform(
            "status",
            b'{"motion":true,"timestamp":1778604953,"active":true,"vibration":false,"lux":160,"bat":100}',
        )

        self.assertIs(result["motion"], True)
        self.assertIs(result["vibration"], False)
        self.assertEqual(result["lux"], 160.0)
        self.assertEqual(result["battery"], 100.0)
        self.assertEqual(result["sensor_timestamp"], 1778604953)
        self.assertIs(result["sensor_active"], True)

    def test_info_json_mapping_extracts_motion_and_device_fields(self) -> None:
        result = self.transform(
            "info",
            (
                b'{"wifi_sta":{"connected":true,"ssid":"WIFIU6_2G","ip":"192.168.1.135","rssi":-43},'
                b'"cloud":{"enabled":false,"connected":false},"mqtt":{"connected":true},"time":"18:55",'
                b'"unixtime":1778604953,"mac":"588E81A618D1",'
                b'"lux":{"value":160,"illumination":"twilight","is_valid":true},'
                b'"sensor":{"vibration":false,"motion":true,"timestamp":1778604953,"active":true,"is_valid":true},'
                b'"bat":{"value":100,"voltage":4.149},"charger":false,"uptime":23483,'
                b'"fw_info":{"device":"shellymotionsensor-588E81A618D1","fw":"20240619-130804/v2.2.4@ee290818"}}'
            ),
        )

        self.assertEqual(result["device_name"], "shellymotionsensor-588E81A618D1")
        self.assertIs(result["motion"], True)
        self.assertEqual(result["lux"], 160.0)
        self.assertEqual(result["battery_voltage"], 4.149)
        self.assertEqual(result["wifi_rssi"], -43)
        self.assertEqual(result["firmware"], "20240619-130804/v2.2.4@ee290818")
        self.assertEqual(result["time"], "18:55")

    def test_missing_payload_path_does_not_break_transform(self) -> None:
        result = self.transform("status", b'{"motion":true}')

        self.assertIs(result["motion"], True)
        self.assertNotIn("lux", result)
        self.assertNotIn("battery", result)

    def test_failed_json_field_conversion_does_not_break_other_fields(self) -> None:
        result = self.transform("status", b'{"motion":true,"lux":"not-a-number","bat":88}')

        self.assertIs(result["motion"], True)
        self.assertEqual(result["battery"], 88.0)
        self.assertNotIn("lux", result)


if __name__ == "__main__":
    unittest.main()
