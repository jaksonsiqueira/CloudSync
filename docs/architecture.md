# Arquitetura do CloudSync

## Princípios

- Separar interface, coordenação de casos de uso, domínio e infraestrutura.
- Manter o motor de arquivos independente da interface gráfica.
- Não guardar credenciais ou tokens no código, no banco de configurações ou no repositório.
- Tornar operações destrutivas explícitas e seguras, especialmente no modo de sincronização.
- Persistir tarefas e execuções para que o histórico sobreviva ao fechamento do aplicativo.

## Camadas e responsabilidades

- `domain`: modelos e políticas sem dependência de interface, banco ou Google API.
- `application`: coordena casos de uso como cadastro e execução de tarefas.
- `engine`: varredura, comparação e execução de cópias locais/nuvem.
- `cloud`: autenticação e adaptador para Google Drive API.
- `storage`: SQLite e repositórios para persistência.
- `scheduler`: agendamento de execuções.
- `ui`: janelas e componentes PySide6; comunica progresso sem bloquear a interface.
- `config.py` e `logging_config.py`: caminhos e configuração transversal.

## Decisões iniciais

- **Interface:** PySide6 com Qt Widgets.
- **Persistência:** SQLite via `sqlite3` da biblioteca padrão; `platformdirs` determina caminhos de dados do usuário.
- **Drive/OAuth:** `cloud.auth` implementa OAuth desktop por navegador e armazena tokens via `keyring`; `cloud.drive` encapsula a Drive API v3 e não depende do banco ou da interface.
- **Agendamento (etapa futura):** APScheduler executado no processo do aplicativo.
- **Logs:** módulo `logging` da biblioteca padrão, com rotação de arquivos.

## Integração Google Drive

- `cloud.auth.GoogleDriveAuth` conecta, carrega, renova e desconecta credenciais OAuth.
- `cloud.auth.KeyringTokenStore` guarda o JSON de tokens no cofre do sistema operacional; o arquivo OAuth de aplicativo fica separado dos tokens em `%LOCALAPPDATA%\CloudSync\google-oauth-client.json`.
- `cloud.drive.GoogleDriveClient` fornece verificação de conexão, informações básicas da conta, paginação de itens filhos, busca de pastas por nome e criação de pastas.
- `cloud.drive.DriveItem` representa metadados Drive com ID, nome, MIME type, pastas pai e link opcional.
- `cloud.errors` define erros de integração sem expor respostas sensíveis para a interface/CLI.
- `__main__.py` fornece comandos de conexão e diagnóstico sem inicializar nem depender do SQLite.

O escopo atual é `drive`, necessário para pesquisar todo o Drive e criar itens em diretórios existentes. É um escopo amplo; a distribuição pública deverá avaliar verificação OAuth e possível redução de escopo quando houver um seletor de arquivos/pastas.

## Dados persistidos

- `tasks`: nome, pasta local, identificador/nome da pasta remota, modo, política, agenda e estado habilitado.
- `runs`: início/fim, status, contadores, mensagem de erro resumida.
- `file_state` (etapa futura): caminho relativo, metadados/hash local e identificador/metadados remotos para comparação incremental.

Datas são armazenadas em UTC no formato ISO 8601. Caminhos locais são tratados como caminhos Windows e normalizados nos serviços que os utilizam.

## Segurança e consistência

- Backup não exclui conteúdo remoto.
- Sincronização deverá apresentar prévia e exigir política explícita antes de remover conteúdo; implementar proteção contra grandes lotes de exclusão.
- Tamanho e horário de modificação podem filtrar candidatos; hash confirma conteúdo quando necessário.
- Uploads grandes devem usar sessões retomáveis do Drive e persistir progresso recuperável.
- Operações longas rodam fora da thread da interface e enviam eventos de progresso/cancelamento.

