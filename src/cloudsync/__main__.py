"""Inicialização temporária da fundação, antes da chegada da interface."""

import logging

from cloudsync.app import initialize


def main() -> None:
    services = initialize()
    logging.getLogger(__name__).info("Fundação do CloudSync inicializada em %s", services.data_dir)
    print(f"CloudSync inicializado. Dados locais: {services.data_dir}")


if __name__ == "__main__":
    main()

