# Contribuindo

Este projeto é uma aplicação desktop local de gestão financeira. Alterações devem preservar simplicidade operacional, integridade dos dados e o caráter preventivo do Guardião Antifraude.

## Fluxo recomendado

Crie uma branch a partir de `main`:

```bash
git switch main
git pull
git switch -c feat/nome-da-melhoria
```

Use prefixos como `feat/`, `fix/`, `docs/`, `test/` ou `refactor/`.

Antes do commit:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m unittest discover -s tests -v
python -m coverage run -m unittest discover -s tests -v
python -m coverage report -m
```

## Regras de segurança

Nunca adicione ao Git:

- bancos SQLite reais;
- backups ou logs operacionais;
- boletos, linhas digitáveis ou documentos reais;
- credenciais, tokens ou arquivos `.env`;
- dados de clientes, fornecedores ou empresas usados em produção.

Fixtures automatizadas devem ser sintéticas e claramente identificadas como teste.

## Guardião Antifraude

Mudanças no módulo antifraude devem manter a premissa de **triagem preventiva**. O sistema não deve afirmar que um boleto é autêntico apenas com base na análise local; a confirmação final ocorre no canal oficial do banco/emissor.

## Commits

Mensagens curtas e descritivas são preferidas, por exemplo:

```text
feat: adiciona filtro por vencimento
fix: preserva parcela paga ao editar compra
test: cobre migração de banco legado
docs: atualiza guia de build
```
