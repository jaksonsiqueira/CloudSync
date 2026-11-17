"""Testes locais da autenticação e do adaptador Google Drive sem chamadas reais."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from google.oauth2.credentials import Credentials
from oauthlib.oauth2 import OAuth2Error

from cloudsync.cloud import GoogleDriveAuth, GoogleDriveClient
from cloudsync.cloud.auth import DRIVE_SCOPES
from cloudsync.cloud.drive import DriveItem, FOLDER_MIME_TYPE
from cloudsync.cloud.errors import (
    AuthenticationError,
    CredentialsNotConfiguredError,
    DriveConnectionError,
    DrivePermissionError,
    NotAuthenticatedError,
)


class MemoryTokenStore:
    def __init__(self, value: str | None = None):
        self.value = value

    def load(self) -> str | None:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = None


class GoogleDriveAuthTests(unittest.TestCase):
    def test_module_exports_auth_and_drive_client(self):
        from cloudsync import cloud

        self.assertIs(cloud.GoogleDriveAuth, GoogleDriveAuth)
        self.assertIs(cloud.GoogleDriveClient, GoogleDriveClient)

    def test_missing_credentials_file_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            auth = GoogleDriveAuth(Path(folder) / "missing.json", MemoryTokenStore())
            with self.assertRaises(CredentialsNotConfiguredError):
                auth.connect()

    def test_missing_saved_token_requires_connection(self):
        auth = GoogleDriveAuth(Path("unused.json"), MemoryTokenStore())
        with self.assertRaises(NotAuthenticatedError):
            auth.get_credentials()

    def test_oauth_failure_is_wrapped(self):
        with tempfile.TemporaryDirectory() as folder:
            secret_file = Path(folder) / "oauth.json"
            secret_file.write_text("{}", encoding="utf-8")
            auth = GoogleDriveAuth(secret_file, MemoryTokenStore())
            with patch("cloudsync.cloud.auth.InstalledAppFlow.from_client_secrets_file", side_effect=OAuth2Error("denied")):
                with self.assertRaises(AuthenticationError):
                    auth.connect()

    def test_connect_uses_desktop_browser_flow_and_saves_token(self):
        with tempfile.TemporaryDirectory() as folder:
            secret_file = Path(folder) / "oauth.json"
            secret_file.write_text("{}", encoding="utf-8")
            store = MemoryTokenStore()
            auth = GoogleDriveAuth(secret_file, store)
            credentials = Credentials(token="access", scopes=DRIVE_SCOPES)
            flow = MagicMock()
            flow.run_local_server.return_value = credentials
            with patch("cloudsync.cloud.auth.InstalledAppFlow.from_client_secrets_file", return_value=flow) as create_flow:
                result = auth.connect()
            create_flow.assert_called_once_with(
                str(secret_file), scopes=DRIVE_SCOPES, autogenerate_code_verifier=True
            )
            self.assertTrue(flow.run_local_server.call_args.kwargs["open_browser"])
            self.assertEqual(result.token, "access")
            self.assertIn('"token": "access"', store.value)

    def test_expired_token_is_refreshed_and_persisted(self):
        expired = Credentials(
            token="old-access",
            refresh_token="refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="desktop-client",
            client_secret="desktop-secret",
            scopes=DRIVE_SCOPES,
            expiry=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        store = MemoryTokenStore(expired.to_json())
        auth = GoogleDriveAuth(Path("unused.json"), store)

        def refresh(credentials, request):
            credentials.token = "new-access"
            credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(Credentials, "refresh", autospec=True, side_effect=refresh) as refresh_mock:
            result = auth.get_credentials()
        refresh_mock.assert_called_once()
        self.assertEqual(result.token, "new-access")
        self.assertIn('"token": "new-access"', store.value)

    def test_disconnect_clears_saved_token(self):
        store = MemoryTokenStore("serialized-token")
        GoogleDriveAuth(Path("unused.json"), store).disconnect()
        self.assertIsNone(store.value)


class GoogleDriveClientTests(unittest.TestCase):
    def setUp(self):
        self.auth = MagicMock()
        self.credentials = MagicMock()
        self.credentials.to_json.return_value = "unchanged"
        self.auth.get_credentials.return_value = self.credentials
        self.service = MagicMock()
        self.client = GoogleDriveClient(self.auth, service_factory=lambda _credentials: self.service)

    def test_connection_check_returns_available_account_info(self):
        request = self.service.about.return_value.get.return_value
        request.execute.return_value = {
            "user": {"displayName": "Jakson", "emailAddress": "user@example.com", "permissionId": "p-1"}
        }
        result = self.client.check_connection()
        self.assertEqual(result.email_address, "user@example.com")
        self.assertEqual(result.display_name, "Jakson")
        self.service.about.return_value.get.assert_called_once_with(
            fields="user(displayName,emailAddress,permissionId)"
        )

    def test_list_files_follows_all_pages(self):
        request = self.service.files.return_value.list.return_value
        request.execute.side_effect = [
            {"files": [{"id": "folder-1", "name": "Docs", "mimeType": FOLDER_MIME_TYPE}], "nextPageToken": "next"},
            {"files": [{"id": "file-1", "name": "report.txt", "mimeType": "text/plain"}]},
        ]
        items = list(self.client.list_files(parent_id="root", page_size=2))
        self.assertEqual([item.id for item in items], ["folder-1", "file-1"])
        self.assertTrue(items[0].is_folder)
        self.assertEqual(self.service.files.return_value.list.call_count, 2)
        self.assertIsNone(self.service.files.return_value.list.call_args_list[0].kwargs["pageToken"])
        self.assertEqual(self.service.files.return_value.list.call_args_list[1].kwargs["pageToken"], "next")

    def test_find_folders_escapes_apostrophe_in_name(self):
        request = self.service.files.return_value.list.return_value
        request.execute.return_value = {"files": [{"id": "folder-2", "name": "Jack's", "mimeType": FOLDER_MIME_TYPE}]}
        found = self.client.find_folders("Jack's")
        self.assertEqual(found[0].id, "folder-2")
        query = self.service.files.return_value.list.call_args.kwargs["q"]
        self.assertIn("Jack\\'s", query)

    def test_create_folder_returns_new_folder_id(self):
        request = self.service.files.return_value.create.return_value
        request.execute.return_value = {"id": "new-id", "name": "Archive", "mimeType": FOLDER_MIME_TYPE}
        result = self.client.create_folder("Archive", parent_id="parent-id")
        self.assertEqual(result.id, "new-id")
        self.assertTrue(result.is_folder)
        self.service.files.return_value.create.assert_called_once()
        body = self.service.files.return_value.create.call_args.kwargs["body"]
        self.assertEqual(body["parents"], ["parent-id"])

    def test_get_or_create_folder_reuses_existing_folder(self):
        request = self.service.files.return_value.list.return_value
        request.execute.return_value = {
            "files": [{"id": "existing-id", "name": "Archive", "mimeType": FOLDER_MIME_TYPE}]
        }
        result = self.client.get_or_create_folder("Archive", parent_id="parent-id")
        self.assertEqual(result.id, "existing-id")
        self.service.files.return_value.create.assert_not_called()

    def test_connection_failure_is_wrapped(self):
        request = self.service.about.return_value.get.return_value
        request.execute.side_effect = ConnectionError("network unavailable")
        with self.assertRaises(DriveConnectionError):
            self.client.check_connection()

    def test_unauthorized_api_response_is_authentication_error(self):
        from googleapiclient.errors import HttpError

        request = self.service.about.return_value.get.return_value
        response = MagicMock(status=401)
        request.execute.side_effect = HttpError(response, b"unauthorized")
        with self.assertRaises(AuthenticationError):
            self.client.check_connection()

    def test_forbidden_api_response_is_permission_error(self):
        from googleapiclient.errors import HttpError

        request = self.service.about.return_value.get.return_value
        response = MagicMock(status=403)
        request.execute.side_effect = HttpError(response, b"forbidden")
        with self.assertRaises(DrivePermissionError):
            self.client.check_connection()

    def test_drive_item_maps_resource_fields(self):
        item = DriveItem.from_resource(
            {"id": "id-1", "name": "Folder", "mimeType": FOLDER_MIME_TYPE, "parents": ["root"]}
        )
        self.assertEqual(item.parent_ids, ("root",))
        self.assertTrue(item.is_folder)


if __name__ == "__main__":
    unittest.main()
