"""Cliente Google Drive v3 para consulta, navegação e criação de pastas."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from cloudsync.cloud.auth import GoogleDriveAuth
from cloudsync.cloud.errors import (
    AuthenticationError,
    DriveApiError,
    DriveConnectionError,
    DrivePermissionError,
)

logger = logging.getLogger(__name__)
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
FILE_FIELDS = "id,name,mimeType,parents,modifiedTime,webViewLink"


@dataclass(frozen=True, slots=True)
class DriveItem:
    """Representação estável dos metadados de um item do Drive."""

    id: str
    name: str
    mime_type: str
    parent_ids: tuple[str, ...] = ()
    modified_time: str | None = None
    web_view_link: str | None = None

    @property
    def is_folder(self) -> bool:
        return self.mime_type == FOLDER_MIME_TYPE

    @classmethod
    def from_resource(cls, resource: dict[str, Any]) -> "DriveItem":
        return cls(
            id=resource["id"],
            name=resource.get("name", ""),
            mime_type=resource.get("mimeType", "application/octet-stream"),
            parent_ids=tuple(resource.get("parents", ())),
            modified_time=resource.get("modifiedTime"),
            web_view_link=resource.get("webViewLink"),
        )


@dataclass(frozen=True, slots=True)
class DriveAccount:
    """Informações básicas que a API disponibiliza para a conta atual."""

    display_name: str | None
    email_address: str | None
    permission_id: str | None


def _default_service_factory(credentials: Any) -> Any:
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


class GoogleDriveClient:
    """Adaptador independente para as operações básicas do Google Drive."""

    def __init__(
        self,
        auth: GoogleDriveAuth,
        service_factory: Callable[[Any], Any] | None = None,
    ):
        self.auth = auth
        self.service_factory = service_factory or _default_service_factory

    def check_connection(self) -> DriveAccount:
        """Testa autenticação e devolve os dados básicos da conta conectada."""
        response = self._request(
            "account_info",
            lambda service: service.about().get(
                fields="user(displayName,emailAddress,permissionId)"
            ),
        )
        user = response.get("user", {})
        return DriveAccount(
            display_name=user.get("displayName"),
            email_address=user.get("emailAddress"),
            permission_id=user.get("permissionId"),
        )

    def list_files(
        self,
        parent_id: str = "root",
        *,
        page_size: int = 100,
        name: str | None = None,
        folders_only: bool = False,
    ) -> Iterator[DriveItem]:
        """Percorre os itens filhos de uma pasta, buscando todas as páginas."""
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size deve estar entre 1 e 1000.")
        filters = ["trashed = false", f"'{self._escape_query_value(parent_id)}' in parents"]
        if name is not None:
            filters.append(f"name = '{self._escape_query_value(name)}'")
        if folders_only:
            filters.append(f"mimeType = '{FOLDER_MIME_TYPE}'")
        query = " and ".join(filters)
        credentials = self.auth.get_credentials()
        service = self.service_factory(credentials)
        previous = credentials.to_json()
        page_token: str | None = None
        try:
            while True:
                request = service.files().list(
                    q=query,
                    pageSize=page_size,
                    pageToken=page_token,
                    fields=f"nextPageToken,files({FILE_FIELDS})",
                    orderBy="folder,name",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                response = self._execute(request, "list_files")
                for resource in response.get("files", []):
                    yield DriveItem.from_resource(resource)
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        finally:
            self.auth.save_if_changed(credentials, previous)

    def find_folders(self, name: str) -> list[DriveItem]:
        """Localiza pastas com nome exato em toda a unidade visível à conta."""
        if not name.strip():
            raise ValueError("O nome da pasta não pode estar vazio.")
        query = (
            f"trashed = false and mimeType = '{FOLDER_MIME_TYPE}' and "
            f"name = '{self._escape_query_value(name)}'"
        )
        return self._list_query(query)

    def create_folder(self, name: str, parent_id: str = "root") -> DriveItem:
        """Cria uma pasta e retorna seu ID e metadados básicos."""
        if not name.strip():
            raise ValueError("O nome da pasta não pode estar vazio.")
        body: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME_TYPE}
        if parent_id:
            body["parents"] = [parent_id]
        response = self._request(
            "create_folder",
            lambda service: service.files().create(
                body=body,
                fields=FILE_FIELDS,
                supportsAllDrives=True,
            ),
        )
        return DriveItem.from_resource(response)

    def get_or_create_folder(self, name: str, parent_id: str = "root") -> DriveItem:
        """Retorna uma pasta de mesmo nome no diretório pai ou cria uma nova."""
        if not name.strip():
            raise ValueError("O nome da pasta não pode estar vazio.")
        filters = [
            "trashed = false",
            f"'{self._escape_query_value(parent_id)}' in parents",
            f"mimeType = '{FOLDER_MIME_TYPE}'",
            f"name = '{self._escape_query_value(name)}'",
        ]
        matches = self._list_query(" and ".join(filters), page_size=100)
        if matches:
            return matches[0]
        return self.create_folder(name, parent_id)

    def _list_query(self, query: str, page_size: int = 100) -> list[DriveItem]:
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size deve estar entre 1 e 1000.")
        credentials = self.auth.get_credentials()
        service = self.service_factory(credentials)
        previous = credentials.to_json()
        items: list[DriveItem] = []
        page_token: str | None = None
        try:
            while True:
                request = service.files().list(
                    q=query,
                    pageSize=page_size,
                    pageToken=page_token,
                    fields=f"nextPageToken,files({FILE_FIELDS})",
                    orderBy="folder,name",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                response = self._execute(request, "find_folders")
                items.extend(DriveItem.from_resource(resource) for resource in response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    return items
        finally:
            self.auth.save_if_changed(credentials, previous)

    def _request(self, operation: str, request_factory: Callable[[Any], Any]) -> dict[str, Any]:
        credentials = self.auth.get_credentials()
        service = self.service_factory(credentials)
        previous = credentials.to_json()
        try:
            return self._execute(request_factory(service), operation)
        finally:
            self.auth.save_if_changed(credentials, previous)

    @staticmethod
    def _execute(request: Any, operation: str) -> dict[str, Any]:
        try:
            return request.execute()
        except HttpError as error:
            status_code = getattr(error.resp, "status", None)
            if status_code == 401:
                logger.warning("Google Drive recusou a autenticação durante %s", operation)
                raise AuthenticationError("A sessão Google foi recusada. Conecte a conta novamente.") from error
            if status_code == 403:
                logger.warning("Permissão insuficiente no Google Drive durante %s", operation)
                raise DrivePermissionError("A conta não tem permissão para executar esta operação.") from error
            logger.error("Google Drive retornou HTTP %s durante %s", status_code, operation)
            raise DriveApiError(
                f"A API do Google Drive retornou um erro durante {operation}.", status_code=status_code
            ) from error
        except (httplib2.HttpLib2Error, socket.timeout, TimeoutError, ConnectionError, OSError) as error:
            logger.warning("Falha de rede com Google Drive durante %s (%s)", operation, type(error).__name__)
            raise DriveConnectionError("Não foi possível conectar ao Google Drive. Verifique a rede e tente novamente.") from error

    @staticmethod
    def _escape_query_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

\n