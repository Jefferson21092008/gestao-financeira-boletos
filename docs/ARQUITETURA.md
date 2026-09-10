# Arquitetura V12.1.3

## Objetivo

Manter o sistema simples para um único computador da empresa, mas com separação suficiente para reduzir risco de manutenção e permitir evolução do módulo de boletos/antifraude.

## Fluxo

```text
Tkinter UI
   |
   v
Services / Database facade
   |
   v
Repositories por domínio
   |
   v
SQLite local
```

## Camadas

### `core/`
Funções independentes de interface e banco: `Decimal`/centavos, datas, CNPJ, hashes de senha, logging e formatação.

### `database/`
Responsável pela conexão, criação do schema e migrações aditivas. A conexão fecha automaticamente ao sair de blocos `with` e usa `busy_timeout` para evitar falhas transitórias de bloqueio.

### `repositories/`
Acesso ao SQLite separado em autenticação, empresas, lançamentos, boletos, antifraude, auditoria e backup. A classe `Database` é somente uma fachada que reúne esses módulos.

### `services/`
Regras que não pertencem à interface nem diretamente ao SQL, principalmente análise antifraude e consulta cadastral.

### `ui/`
Cada janela Tkinter fica isolada. A interface solicita operações à fachada/serviços e não contém SQL.

## Compatibilidade monetária

A V12.1.3 mantém uma migração aditiva. As colunas `REAL` antigas permanecem para que bancos V10/V11 e backups anteriores continuem abrindo. Novas colunas `*_centavos INTEGER` são preenchidas automaticamente e passam a ser a referência exata para cálculos financeiros.

## Autenticação

Bancos novos não recebem senha administrativa padrão: o primeiro acesso cria uma senha própria. Em bancos de versões antigas que ainda não possuíam o campo `must_change_password`, a migração marca os usuários existentes para troca obrigatória. Esse processo não depende de nenhuma senha legada codificada no código-fonte.

## Auditoria

A tabela `auditoria` mantém eventos importantes com ator, ação, entidade, identificador, detalhes JSON e data/hora. Nenhuma senha é incluída nos eventos.

## Guardião Antifraude

A triagem combina:

- estrutura de 44/47/48 dígitos;
- dígitos verificadores;
- valor codificado x valor esperado;
- documento esperado x documento exibido pelo banco;
- beneficiário esperado x beneficiário exibido;
- cadastro de CNPJ quando disponível;
- compatibilidade entre nome exibido e cadastro do CNPJ;
- reutilização da mesma linha por outra empresa;
- histórico de análises de alto risco;
- banco/segmento fora do histórico de análises confiáveis.

Uma consulta online indisponível, isoladamente, não é tratada como fraude.

## Decisão de arquitetura

Para este cenário local, não há necessidade de servidor, Docker, microserviços ou API própria. SQLite + camadas internas mantém o sistema menor, auditável e mais simples de operar no computador da empresa.
