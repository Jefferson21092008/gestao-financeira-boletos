# Como publicar este projeto no GitHub

## 1. Crie o repositório

No GitHub, crie um repositório chamado, por exemplo:

`gestao-financeira-boletos`

Durante a fase de testes, a recomendação é usar **Private**.

Ao criar pelo site, não marque a criação automática de README, `.gitignore` ou licença, pois este pacote já contém README e `.gitignore`.

## 2. Abra o terminal na pasta do projeto

No PowerShell ou Prompt de Comando, entre na pasta extraída deste pacote.

## 3. Inicialize o Git

```bash
git init
git branch -M main
```

Se esta for a primeira vez usando Git neste computador, configure sua identidade:

```bash
git config --global user.name "Seu nome"
git config --global user.email "seu-email-do-github@example.com"
```

## 4. Confira o que será enviado

```bash
git status
```

O `.gitignore` bloqueia banco SQLite, backups, logs, ambientes virtuais, arquivos de build e segredos comuns.

Antes do primeiro commit, confira novamente:

```bash
git add .
git status
```

Não continue se aparecer algum banco real (`.db`, `.sqlite`, `.sqlite3`), backup, `.env`, log ou dado financeiro real.

## 5. Faça o primeiro commit

```bash
git commit -m "feat: adiciona versao inicial modular do sistema financeiro"
```

## 6. Conecte ao repositório remoto

Substitua `SEU_USUARIO` pelo seu usuário do GitHub:

```bash
git remote add origin https://github.com/SEU_USUARIO/gestao-financeira-boletos.git
git remote -v
```

## 7. Envie

```bash
git push -u origin main
```

O GitHub pode pedir autenticação pelo navegador ou outro método configurado no Git Credential Manager.

## 8. Fluxo recomendado para próximas mudanças

Não trabalhe diretamente na `main` quando a alteração for relevante.

```bash
git switch main
git pull origin main
git switch -c feat/nome-da-melhoria
```

Depois de alterar o código:

```bash
python -m unittest discover -s tests -v
git status
git diff --check
git add .
git commit -m "feat: descreva a melhoria"
git push -u origin feat/nome-da-melhoria
```

Então abra um Pull Request no GitHub para a `main`.

## 9. Antes de tornar público

Faça uma revisão completa para garantir que não existam:

- banco ou backup real da empresa;
- logs/auditoria reais;
- documentos de fornecedor ou boleto real;
- senhas ou credenciais;
- nomes/caminhos pessoais desnecessários;
- dados financeiros reais.

O repositório pode ser útil como portfólio, mas a versão pública deve conter somente código e dados fictícios/de demonstração.
