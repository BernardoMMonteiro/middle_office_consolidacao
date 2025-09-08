# Teste de Programação - Middle Office

Solução para o desafio de consolidação de movimentações do Middle Office.

## Pré-requisitos

Para executar este projeto, você precisará ter instalado:

*   Python (versão 3.9 ou superior)
*   Poetry (gerenciador de dependências)
*   Git

## Instalação

 **Instale as dependências com o Poetry:**
    ```bash
    poetry install
    ```

## Execução

Todos os comandos devem ser executados a partir da raiz do projeto. Os arquivos de saída serão gerados, por default, na pasta `outputs/`.

### 1. Executar o Processo Principal

O script principal (`app.py`) simula as diferentes janelas de processamento ao longo do dia e decide se gera ou não os arquivos em cada rodada.

```bash
poetry run python -m src.middle_office.app
```

### 2. Executar a Reconciliação Diária

Após a execução do processo principal (simulando o final do dia), o script de reconciliação pode ser usado para auditar a geração de arquivos e a consistência dos valores contra o banco de dados.

```bash
poetry run python -m src.middle_office.reconciliacao.reconciliar_boletos_gerados```

### 3. (Opcional) Reiniciar o Ambiente

Para testar uma nova execução do zero, um script de utilidade está disponível para limpar as tabelas de controle e arquivar a pasta `outputs`.

```bash
poetry run python -m src.middle_office.scripts_uteis.reiniciar_dados