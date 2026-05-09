import hashlib
import time
import unittest
from unittest import mock

import core


class CoreTests(unittest.TestCase):
    def test_secret_salt_matches_recovered_cython_table(self):
        self.assertEqual(core.get_secret_salt(), '@o"-#-¥΀£⛓P315@')

    def test_validate_expiring_key(self):
        device_id = "SHA-TESTDEVICE"
        expire_ts = int(time.time()) + 86400
        payload = "AA" + format(expire_ts, "X") + "ZZ"
        digest = hashlib.sha256(f"{device_id}{payload}{core.get_secret_salt()}".encode()).hexdigest()[:8].upper()
        key = digest + payload

        with mock.patch.object(core, "get_real_network_time", return_value=int(time.time())):
            is_valid, status, parsed_expire_ts = core.validate_key(device_id, key)

        self.assertTrue(is_valid)
        self.assertEqual(status, core.VERIFIED)
        self.assertEqual(parsed_expire_ts, expire_ts)

    def test_validate_rejects_short_key(self):
        self.assertEqual(core.validate_key("SHA-TESTDEVICE", "SHORT"), (False, core.INVALID_FORMAT, None))

    def test_normalize_portal_url_falls_back_to_gateway(self):
        self.assertEqual(core._normalize_portal_url(None), "http://192.168.60.1:2060/")

    def test_normalize_portal_url_expands_relative_paths(self):
        self.assertEqual(
            core._normalize_portal_url("/login"),
            "http://192.168.60.1:2060/login",
        )

    def test_extract_portal_url_from_meta_refresh(self):
        response = mock.Mock(headers={}, text='<meta http-equiv="refresh" content="0; url=/portal/login">')
        self.assertEqual(core._extract_portal_url(response), "/portal/login")


if __name__ == "__main__":
    unittest.main()
