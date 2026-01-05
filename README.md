# Dashboard Streamlit

## Descrição

Aplicação simples em Streamlit que exibe métricas a partir de um arquivo CSV local. Por motivos de segurança os dados sensíveis foram removidos do repositório e `*.csv` está listado em `.gitignore`.

## Objetivo

- Demonstrar visualizações e métricas a partir de dados exportados em CSV.
- Servir como painel inicial para análises rápidas e prototipagem.

## Requisitos

- Python 3.9+ (recomendado)
- `pip` instalado

## Instalação rápida

1. Crie e ative um virtualenv (opcional mas recomendado):

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Windows cmd
.\.venv\Scripts\activate.bat
```

2. Instale dependências:

```bash
pip install -r requirements.txt
```

## Executando a aplicação

```bash
streamlit run app.py
```

## Sobre os arquivos CSV

- O repositório ignora `*.csv` por padrão para evitar vazamento de dados sensíveis. Você pode manter o(s) CSV(s) localmente (por exemplo `JIRA.csv`) sem comitar.
- Se precisar compartilhar um exemplo não sensível, gere um arquivo de amostra com valores fictícios.

## Esquema de exemplo (exemplo genérico, sem dados sensíveis)

- id: identificador único
- title: título curto do item
- description: descrição (pode conter texto longo)
- created_at: data de criação (YYYY-MM-DD)
- status: estado/etapa (ex: "open", "closed")
- assignee: responsável (nome ou identificador)

## Boas práticas

- Não commite arquivos com dados pessoais ou sensíveis.
- Use variáveis de ambiente para tokens/credenciais e registre-as em `.env` (também ignorado).
- Para backups seguros, armazene dados em serviços com controle de acesso (S3, Azure Blob, Google Cloud Storage) e não no repositório.

## Ajuda / próximos passos

Se quiser, eu posso:

- Gerar um `sample.csv` com dados fictícios para testes.
- Adicionar um `README` mais detalhado com screenshots e exemplos de uso do painel.
- Comitar e dar push do `README.md` para o repositório remoto (se desejar).
