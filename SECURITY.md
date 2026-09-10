# Segurança

Este projeto é uma aplicação desktop local voltada a controle financeiro e triagem preventiva de boletos. Segurança aqui inclui tanto o código quanto o cuidado para não expor dados operacionais no repositório.

## Dados que nunca devem ser enviados ao Git

- banco SQLite real da empresa;
- backups reais;
- logs ou auditorias com dados operacionais;
- senhas, tokens ou outras credenciais;
- arquivos `.env`;
- boletos, linhas digitáveis, CNPJ/documentos ou dados de beneficiários reais usados em testes;
- screenshots contendo informações reais de clientes, fornecedores ou pagamentos.

O `.gitignore` cobre os formatos mais comuns, mas isso não substitui a revisão de `git status` e `git diff --cached` antes de cada commit.

## Autenticação local

Instalações novas não possuem senha administrativa padrão. A senha é criada no primeiro acesso e armazenada por derivação PBKDF2 com salt aleatório. Bancos antigos migrados podem exigir redefinição de senha sem depender de uma credencial legada hardcoded.

## Guardião Antifraude

O Guardião Antifraude é uma ferramenta de **triagem preventiva**. Ele verifica consistência matemática do código de pagamento e compara informações fornecidas, cadastro de CNPJ e histórico local quando disponíveis.

Um resultado de baixo risco não equivale a garantia de autenticidade. Antes do pagamento, confirme os dados apresentados pelo aplicativo/site oficial do banco ou por outro canal oficial e independente do emissor.

## Reporte responsável

Não publique em uma issue detalhes que possam revelar dados financeiros, credenciais ou informações reais de empresas. Para problemas comuns sem dados sensíveis, use o template de bug do repositório.

Para vulnerabilidades que precisem de informação sensível, prefira o recurso privado **Report a vulnerability** na aba Security do GitHub quando ele estiver habilitado no repositório. Se esse recurso ainda não estiver disponível, abra apenas uma issue genérica pedindo um canal privado, sem incluir o conteúdo sensível.
