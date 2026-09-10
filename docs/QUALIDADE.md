# Qualidade e integração contínua

A camada de qualidade do projeto combina testes unitários, cobertura e análise estática. O objetivo é detectar regressões sem adicionar uma infraestrutura desnecessária para um aplicativo desktop local.

## Preparar ambiente de desenvolvimento

```bash
python -m pip install -r requirements-dev.txt
```

## Testes

```bash
python -m unittest discover -s tests -v
```

## Cobertura

```bash
coverage erase
python -m coverage run -m unittest discover -s tests -v
python -m coverage report -m
```

A configuração atual mede `core/`, `database/`, `repositories/` e `services/` e exige pelo menos **55%** de cobertura. Esse piso é um guardrail inicial e deve subir conforme novos testes forem adicionados.

## Ruff

```bash
python -m ruff check .
```

O conjunto inicial de regras está intencionalmente focado em erros objetivos, como problemas de sintaxe e nomes indefinidos. Regras cosméticas podem ser incorporadas gradualmente.

## GitHub Actions

O workflow `.github/workflows/ci.yml` executa automaticamente, em pushes e pull requests para `main`:

1. preparação do Python;
2. compilação de todos os módulos;
3. Ruff;
4. 21 testes automatizados;
5. relatório e limite mínimo de cobertura.

O CI não acessa banco de produção, backups nem dados reais.

## Verificação pré-publicação

Antes de abrir o repositório ou publicar uma versão, execute:

```bash
python scripts/pre_public_check.py
```

O script falha se encontrar, entre os arquivos rastreados pelo Git, formatos de banco/log, `.env`, diretórios operacionais de backup/log, caminhos pessoais do Windows, o antigo símbolo de senha legada ou sequências contínuas com comprimento de código de pagamento.
