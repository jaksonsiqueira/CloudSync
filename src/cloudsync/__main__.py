"""Comandos de manutenção e conexão antes da chegada da interface gráfica."""

import argparse
import logging
import sys
from collections.abc import Sequence

from cloudsync.app import initialize
from cloudsync.cloud import GoogleDriveAuth, GoogleDriveClient
from cloudsync.cloud.errors import DriveIntegrationError
from cloudsync.logging_config import configure_logging


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cloudsync", description="Gerenciamento local do CloudSync")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("drive-connect", help="conecta uma conta Google pelo navegador")
    commands.add_parser("drive-check", help="verifica a conexão e mostra a conta conectada")
    commands.add_parser("drive-disconnect", help="remove a autorização salva deste usuário")
    args = parser.parse_args(argv)

    try:
        if args.command:
            configure_logging()
            auth = GoogleDriveAuth()
            if args.command == "drive-connect":
                auth.connect()
                account = GoogleDriveClient(auth).check_connection()
                print(f"Google Drive conectado: {account.email_address or account.display_name or 'conta autorizada'}")
            elif args.command == "drive-check":
                account = GoogleDriveClient(auth).check_connection()
                print(f"Conexão OK: {account.email_address or account.display_name or 'conta autorizada'}")
            else:
                auth.disconnect()
                print("Autorização Google removida deste usuário.")
            return 0

        services = initialize()
        logging.getLogger(__name__).info("Fundação do CloudSync inicializada em %s", services.data_dir)
        print(f"CloudSync inicializado. Dados locais: {services.data_dir}")
        return 0
    except DriveIntegrationError as error:
        print(f"Erro na integração Google Drive: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

