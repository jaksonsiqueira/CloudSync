"""OAuth desktop e armazenamento protegido das credenciais do Google Drive."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Protocol

import keyring
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import OAuth2Error

from cloudsync.cloud.errors import (
    AuthenticationError,
    CredentialsNotConfiguredError,
    NotAuthenticatedError,
    TokenStorageError,
)
from cloudsync.config import get_app_paths

logger = logging.getLogger(__name__)

# Listagem geral, navegação e criação em pastas existentes exigem acesso ao Drive.
DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)
KEYRING_SERVICE = "CloudSync.GoogleDrive"
KEYRING_USERNAME = "default-account"


class TokenStore(Protocol):
    """Contrato para persistir o JSON de credenciais OAuth."""

    def load(self) -> str | None: ...

    def save(self, value: str) -> None: ...

    def clear(self) -> None: ...


class KeyringTokenStore:
    """Armazena tokens no cofre de credenciais fornecido pelo sistema."""

    def __init__(self, service: str = KEYRING_SERVICE, username: str = KEYRING_USERNAME):
        self.service = service
        self.username = username

    def load(self) -> str | None:
        try:
            return keyring.get_password(self.service, self.username)
        except Exception as error:
            logger.error("Não foi possível ler credenciais do cofre do sistema (%s)", type(error).__name__)
            raise TokenStorageError("O cofre de credenciais do sistema não está disponível.") from error

    def save(self, value: str) -> None:
        try:
            keyring.set_password(self.service, self.username, value)
        except Exception as error:
            logger.error("Não foi possível salvar credenciais no cofre do sistema (%s)", type(error).__name__)
            raise TokenStorageError("Não foi possível salvar a autorização no cofre do sistema.") from error

    def clear(self) -> None:
        try:
            keyring.delete_password(self.service, self.username)
        except keyring.errors.PasswordDeleteError:
            # Desconectar uma conta sem token salvo já é o estado desejado.
            return
        except Exception as error:
            logger.error("Não foi possível remover credenciais do cofre do sistema (%s)", type(error).__name__)
            raise TokenStorageError("Não foi possível remover a autorização do cofre do sistema.") from error


class GoogleDriveAuth:
    """Gerencia conexão, renovação e desconexão de uma conta Google."""

    def __init__(self, client_secrets_path: Path | None = None, token_store: TokenStore | None = None):
        self.client_secrets_path = client_secrets_path or get_app_paths().google_client_secrets
        self.token_store = token_store or KeyringTokenStore()

    def connect(self) -> Credentials:
        """Abre o navegador padrão e conclui o fluxo OAuth para aplicativo desktop."""
        if not self.client_secrets_path.is_file():
            raise CredentialsNotConfiguredError(
                "Arquivo OAuth não encontrado. Configure o arquivo google-oauth-client.json "
                f"em: {self.client_secrets_path}"
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_path),
                scopes=DRIVE_SCOPES,
                autogenerate_code_verifier=True,
            )
            credentials = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=True,
                authorization_prompt_message="Abra esta URL no navegador para conectar o Google Drive: {url}",
                success_message="CloudSync conectado. Você pode fechar esta janela e voltar ao aplicativo.",
                access_type="offline",
                prompt="consent",
            )
            self._save_credentials(credentials)
            logger.info("Autorização do Google Drive concluída")
            return credentials
        except (GoogleAuthError, OAuth2Error, OSError, ValueError) as error:
            logger.warning("Falha durante a autorização Google (%s)", type(error).__name__)
            raise AuthenticationError(
                "Não foi possível concluir a autorização Google. Confira a configuração OAuth e tente novamente."
            ) from error

    def get_credentials(self) -> Credentials:
        """Carrega credenciais e renova um access token expirado quando possível."""
        serialized = self.token_store.load()
        if not serialized:
            raise NotAuthenticatedError("Nenhuma conta Google está conectada. Execute a conexão OAuth primeiro.")

        try:
            credentials = Credentials.from_authorized_user_info(json.loads(serialized), scopes=DRIVE_SCOPES)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            logger.warning("Credenciais armazenadas são inválidas (%s)", type(error).__name__)
            self.token_store.clear()
            raise AuthenticationError("As credenciais armazenadas são inválidas. Conecte a conta novamente.") from error

        if credentials.expired or not credentials.valid:
            if not credentials.refresh_token:
                raise NotAuthenticatedError("A sessão expirou e não pode ser renovada. Conecte a conta novamente.")
            try:
                credentials.refresh(Request())
            except (RefreshError, GoogleAuthError, OSError) as error:
                logger.warning("Falha ao renovar autorização Google (%s)", type(error).__name__)
                raise AuthenticationError("Não foi possível renovar a sessão Google. Conecte a conta novamente.") from error
            self._save_credentials(credentials)
        return credentials

    def save_if_changed(self, credentials: Credentials, previous: str) -> None:
        """Persiste uma renovação automática feita pela camada HTTP do cliente."""
        current = credentials.to_json()
        if current != previous:
            self.token_store.save(current)

    def disconnect(self) -> None:
        """Remove as credenciais salvas no cofre do sistema."""
        self.token_store.clear()
        logger.info("Conta Google desconectada")

    def is_authenticated(self) -> bool:
        """Indica se há credenciais salvas, sem iniciar interação com o navegador."""
        return self.token_store.load() is not None

    def _save_credentials(self, credentials: Credentials) -> None:
        self.token_store.save(credentials.to_json())

\n