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


if __name__ == "__main__":
    unittest.main()
