"""Exceções de autenticação e comunicação com o Google Drive."""


class DriveIntegrationError(RuntimeError):
    """Erro base da integração com Google Drive."""


class CredentialsNotConfiguredError(DriveIntegrationError):
    """O arquivo OAuth de aplicativo não foi configurado."""


class NotAuthenticatedError(DriveIntegrationError):
    """Não há uma conta Google conectada."""


class AuthenticationError(DriveIntegrationError):
    """A autorização ou renovação do token falhou."""


class TokenStorageError(DriveIntegrationError):
    """O armazenamento seguro do token não está disponível."""


class DriveConnectionError(DriveIntegrationError):
    """A API do Drive não pôde ser alcançada."""


class DrivePermissionError(DriveIntegrationError):
    """A conta não tem permissão para executar a operação."""


class DriveApiError(DriveIntegrationError):
    """A API do Drive retornou uma resposta de erro."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

\n