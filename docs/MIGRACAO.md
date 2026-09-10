# Migração para a V12.1.3

## Antes de usar na empresa

1. Feche a versão antiga do sistema.
2. Faça uma cópia do arquivo `gestao_empresas.db` e da pasta de backups.
3. Extraia a V12.1.3 em uma pasta própria.
4. Execute `iniciar.bat` ou `python main.py`.
5. A V12.1.3 continuará usando o banco na pasta local `GestaoEmpresasLocal`.

## O que a migração faz automaticamente

- mantém as tabelas e dados existentes;
- adiciona campos monetários em centavos inteiros;
- converte os valores antigos para centavos sem apagar as colunas antigas;
- adiciona a tabela de auditoria;
- adiciona campos de controle de primeiro acesso/troca de senha;
- ao detectar um schema antigo sem o campo de controle de troca de senha, marca os usuários existentes para redefinição obrigatória, sem manter senhas legadas hardcoded.

## Importante

O Guardião Antifraude é uma ferramenta de triagem. Mesmo quando o resultado for `BAIXO`, o pagamento deve ser concluído somente após conferir os dados apresentados pelo aplicativo/site oficial do banco.


## Executável

A V12.1.3 pode ser empacotada como executável Windows. O banco continua em `%APPDATA%\GestaoEmpresasLocal`, portanto o processo de atualização do programa não exige mover o banco para dentro da pasta do EXE. Faça uma cópia externa antes de atualizar.
