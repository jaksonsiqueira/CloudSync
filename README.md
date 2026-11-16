# CloudSync

Aplicativo desktop para gerenciar backups e, futuramente, sincronizações entre pastas locais e o Google Drive.

O projeto está sendo desenvolvido incrementalmente. Nesta etapa há a fundação do pacote, modelos de domínio, configuração, logs e persistência SQLite. A interface gráfica e a conexão com o Drive ainda serão adicionadas nas próximas etapas.

## Desenvolvimento

Requer Python 3.11 ou superior.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Os dados de execução ficam no diretório de dados do usuário definido pelo Windows e pelo `platformdirs` (normalmente `%LOCALAPPDATA%\CloudSync`). O banco e os logs não devem ser armazenados no repositório.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Plano de desenvolvimento](docs/development-plan.md)

