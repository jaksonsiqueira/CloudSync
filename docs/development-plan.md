# Plano de desenvolvimento

## Etapas

1. **Fundação (concluída):** pacote, configuração, logs com rotação, modelos de domínio, esquema SQLite versionado e repositórios básicos.
2. **Interface inicial:** janela principal, dashboard, lista de tarefas e formulário de cadastro.
3. **Comparação local:** varrer diretórios e apresentar arquivos novos, modificados e removidos.
4. **Google Drive:** OAuth desktop, escolha de destino, listagem e upload retomável.
5. **Backup seguro:** envio incremental sem exclusões remotas, com política definida para preservar versões.
6. **Histórico e controle:** progresso, cancelamento, retomada e histórico persistido.
7. **Agendamento:** recorrência com APScheduler e prevenção de execuções duplicadas.
8. **Sincronização controlada:** comparação bidirecional, prévia e salvaguardas para exclusões.
9. **Distribuição e expansão:** empacotamento Windows; avaliar inicialização automática e monitoramento contínuo.

## Critérios para encerrar a etapa 1

- O pacote pode ser instalado em modo editável.
- Configuração resolve diretório de dados do usuário sem gravar dados runtime no repositório.
- O banco é criado com esquema versionado e suporte a tarefas e execuções.
- Repositório oferece operações básicas de cadastro/listagem de tarefas e registro/listagem de execuções.
- Logs são gravados em arquivo com rotação.

## Registro de progresso

- 2026-11-16: criada a estrutura inicial do pacote, documentação, inicialização de serviços, configuração de caminhos, logs, modelos de tarefa/execução, tabelas `tasks` e `runs` e repositórios básicos.
- Não foram executados testes automatizados nesta etapa.

