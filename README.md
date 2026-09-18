
# Painel Patrimonial Online

Plataforma multiusuário para acompanhamento pessoal de:
- Ações
- FIIs
- Renda fixa
- Operações
- Proventos
- Metas
- Importação de Posição Detalhada
- Importação de Movimentações da B3
- Cotações automáticas via brapi

## Arquitetura

- **Frontend/app:** Streamlit
- **Hospedagem:** Streamlit Community Cloud
- **Login:** Supabase Auth
- **Banco:** Supabase PostgreSQL
- **Privacidade:** Row Level Security (RLS) por `user_id`
- **Mercado:** brapi

Cada usuário possui login próprio e só consegue consultar/alterar suas próprias linhas no banco.

## 1. Criar o projeto Supabase

1. Crie um projeto no Supabase.
2. Abra **SQL Editor**.
3. Cole e execute todo o conteúdo de `db_schema.sql`.
4. Em **Project Settings > API**, copie:
   - Project URL
   - anon/public key

Não use a `service_role` no app.

## 2. Usuários

No arquivo `.streamlit/secrets.toml`, configure os e-mails que poderão criar conta:

```toml
ALLOWED_EMAILS = [
  "usuario1@exemplo.com",
  "usuario2@exemplo.com",
  "usuario3@exemplo.com"
]
```

O aplicativo suporta mais de três usuários; basta acrescentar outros e-mails.

Por padrão, o Supabase pode exigir confirmação de e-mail. Você pode manter essa proteção ou ajustar em **Authentication > Providers > Email**.

## 3. Segredos locais

Copie:

`.streamlit/secrets.toml.example`

para:

`.streamlit/secrets.toml`

e preencha:

```toml
SUPABASE_URL = "..."
SUPABASE_ANON_KEY = "..."
BRAPI_TOKEN = "..."

ALLOWED_EMAILS = [
  "usuario1@...",
  "usuario2@...",
  "usuario3@..."
]
```

Nunca envie `secrets.toml` ao GitHub.

## 4. Rodar localmente

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python -m streamlit run app.py
```

## 5. Publicar online

1. Crie um repositório GitHub.
2. Envie todos os arquivos **menos** `.streamlit/secrets.toml`.
3. Acesse `share.streamlit.io`.
4. Create app.
5. Selecione repositório, branch `main` e `app.py`.
6. Em **Advanced settings / Secrets**, cole os mesmos segredos do `secrets.toml`.
7. Deploy.

## Segurança

- Use somente a chave `anon` do Supabase no Streamlit.
- As tabelas usam RLS.
- Nunca coloque senhas, BRAPI token ou `service_role` no GitHub.
- O app é ferramenta de acompanhamento e simulação, não recomendação de investimento.

## Observação sobre renda fixa

O saldo é **estimado pelas movimentações B3**:
- aplicações aumentam principal;
- resgates/vencimentos/amortizações reduzem principal;
- juros entram como rendimento.

Isso não equivale a marcação a mercado nem ao saldo atualizado oficial do título.
