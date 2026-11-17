# CloudSync

Aplicativo desktop para gerenciar backups e, futuramente, sincronizações entre pastas locais e o Google Drive. A integração inicial com Drive oferece OAuth desktop, consulta de conta, navegação, busca e criação de pastas.

O projeto está sendo desenvolvido incrementalmente. A interface gráfica e o mecanismo de backup/sincronização ainda serão adicionados nas próximas etapas.

## Desenvolvimento

Requer Python 3.11 ou superior.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Os dados de execução ficam no diretório de dados do usuário definido pelo Windows e pelo `platformdirs` (normalmente `%LOCALAPPDATA%\CloudSync`). O banco e os logs não devem ser armazenados no repositório. O JSON OAuth fica nesse diretório local e os tokens de usuário ficam no cofre de credenciais do sistema, por meio do `keyring`.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Plano de desenvolvimento](docs/development-plan.md)

## Configurar Google Drive e OAuth

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto para o CloudSync (ou selecione um projeto dedicado).
2. Em **APIs e serviços → Biblioteca**, habilite **Google Drive API**.
3. Em **Google Auth Platform**, configure a tela de consentimento: nome do aplicativo, email de suporte e público. Para uso pessoal/teste, selecione **Externo** e adicione sua conta Google como usuário de teste, se o aplicativo estiver no modo de teste.
4. Em **Clientes**, crie um cliente OAuth com tipo **Aplicativo para computador (Desktop app)** e baixe o arquivo JSON. O fluxo usa o navegador do sistema e redirecionamento local, conforme o [guia oficial OAuth para aplicativos desktop](https://developers.google.com/identity/protocols/oauth2/native-app).
5. Copie o JSON baixado para:

   ```text
   %LOCALAPPDATA%\CloudSync\google-oauth-client.json
   ```

   Se a pasta ainda não existir, execute primeiro `python -m cloudsync` ou crie a pasta manualmente. Não renomeie nem edite o conteúdo do JSON. O `.gitignore` exclui esse nome de arquivo; mantenha-o fora de commits e compartilhamentos.

6. No terminal, dentro do ambiente virtual do projeto, conecte a conta:

   ```powershell
   python -m cloudsync drive-connect
   ```

   O CloudSync abre o navegador padrão; entre na conta desejada e conceda acesso. O retorno OAuth chega por um servidor local temporário em `127.0.0.1`. As credenciais de usuário são guardadas no cofre de credenciais do Windows pelo `keyring`, e o access token é renovado automaticamente quando expira.

O primeiro incremento solicita o escopo `https://www.googleapis.com/auth/drive` para listar e criar pastas em toda a unidade do usuário. Esse escopo concede acesso amplo ao Drive e pode exigir verificação do Google para distribuição pública. Para uma aplicação em modo de teste, autorize somente contas de teste no projeto Cloud.

### Comandos de conexão

```powershell
python -m cloudsync drive-check       # testa API e mostra os dados básicos da conta
python -m cloudsync drive-disconnect  # remove os tokens do cofre deste usuário
python -m unittest discover -s tests -v  # testes locais com mocks; sem conta real
```

`GoogleDriveClient.list_files(parent_id="root")` lista o conteúdo de uma pasta com paginação automática. Cada resultado contém o ID do item. Use `find_folders("Nome")` para localizar pastas com esse nome e `create_folder("Nome", parent_id="root")` para criar uma pasta, ou `get_or_create_folder(...)` para reutilizar uma pasta existente com mesmo nome no diretório pai. A conta pode ser consultada por `check_connection()`. A paginação e a criação seguem os recursos `files.list` e `files.create` da [Drive API v3](https://developers.google.com/workspace/drive/api/guides/search-files).

