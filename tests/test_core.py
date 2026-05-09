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

    def test_extract_portal_url_from_star_href_script(self):
        response = mock.Mock(headers={}, text="<script>href='https://portal-as.ruijienetworks.com/api/auth/wifidog?sessionId=SID123'</script>")
        self.assertEqual(
            core._extract_portal_url(response),
            "https://portal-as.ruijienetworks.com/api/auth/wifidog?sessionId=SID123",
        )

    def test_portal_session_from_star_url(self):
        portal = core._portal_session_from_url(
            "https://portal-as.ruijienetworks.com/api/auth/wifidog?"
            "gw_address=192.168.110.1&gw_port=2060&ip=192.168.110.63&sessionId=SID123"
        )

        self.assertEqual(portal.gateway_ip, "192.168.110.1")
        self.assertEqual(portal.gateway_port, "2060")
        self.assertEqual(portal.session_id, "SID123")

    def test_find_logon_url_from_json(self):
        response = mock.Mock()
        response.json.return_value = {"logonUrl": "http://192.168.110.1:2060/wifidog/auth?token=TOK"}

        self.assertEqual(
            core._find_logon_url(response),
            "http://192.168.110.1:2060/wifidog/auth?token=TOK",
        )

    def test_send_wifidog_auth_uses_star_params(self):
        session = mock.Mock()
        session.post.return_value = mock.Mock(status_code=200)
        portal = core.PortalSession(
            session_url="https://portal-as.ruijienetworks.com/api/auth/wifidog?sessionId=SID123",
            gateway_ip="192.168.110.1",
            gateway_port="2060",
            session_id="SID123",
        )

        with mock.patch.object(core, "DEFAULT_PHONE_NUMBER", "admin"):
            self.assertEqual(core._send_wifidog_auth(session, portal, "SID123"), 200)

        session.post.assert_called_once()
        self.assertEqual(session.post.call_args.args[0], "http://192.168.110.1:2060/wifidog/auth")
        self.assertEqual(session.post.call_args.kwargs["params"], {"token": "SID123", "phoneNumber": "admin"})

    def test_post_cloud_voucher_requires_logon_url_for_success(self):
        session = mock.Mock()
        response = mock.Mock(status_code=200, text='{"status":"failed"}')
        response.json.return_value = {"status": "failed"}
        session.post.return_value = response
        portal = core.PortalSession(
            session_url="https://portal-as.ruijienetworks.com/api/auth/wifidog?sessionId=SID123",
            gateway_ip="192.168.110.1",
            gateway_port="2060",
            session_id="SID123",
        )

        self.assertEqual(core._post_cloud_voucher(session, portal), (False, "SID123"))
        session.get.assert_not_called()

    def test_auth_burst_falls_back_when_async_unavailable(self):
        async def no_async_statuses(*_args, **_kwargs):
            return []

        session = mock.Mock()
        portal = core.PortalSession(
            session_url="https://portal-as.ruijienetworks.com/api/auth/wifidog?sessionId=SID123",
            gateway_ip="192.168.110.1",
            gateway_port="2060",
            session_id="SID123",
        )

        with (
            mock.patch.object(core, "AUTH_WORKERS", 2),
            mock.patch.object(core, "_send_wifidog_auth_async", side_effect=no_async_statuses),
            mock.patch.object(core, "_send_wifidog_auth", return_value=200) as send_auth,
        ):
            self.assertEqual(core._send_wifidog_auth_burst(session, portal, "SID123"), [200, 200])

        self.assertEqual(send_auth.call_count, 2)


if __name__ == "__main__":
    unittest.main()
