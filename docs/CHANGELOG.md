# V12 — principais mudanças

- primeiro acesso sem senha padrão;
- troca obrigatória de senha para usuários vindos de schemas antigos;
- política mínima de senha local;
- dinheiro processado com `Decimal` e armazenado também em centavos inteiros;
- migração automática dos valores antigos `REAL` para centavos;
- auditoria local de ações importantes;
- nova tela de Auditoria;
- conexões SQLite fechadas automaticamente após blocos `with`;
- `busy_timeout` do SQLite para reduzir erros transitórios de banco ocupado;
- Guardião Antifraude mais conservador para liberar `BAIXO`;
- comparação adicional entre beneficiário exibido e cadastro público do CNPJ;
- alerta quando a mesma linha já teve análise de alto risco;
- histórico bancário baseado somente em análises anteriores de baixo risco;
- falha de backup automático deixa registro em log em vez de ser ignorada silenciosamente;
- suíte ampliada para 20 testes automatizados, além de teste gráfico das janelas.


## V12.1

- projeto preparado para geração de executável Windows com PyInstaller;
- scripts separados para modo pasta (recomendado) e EXE único;
- metadados de versão do executável;
- backup externo validado para pendrive, HD externo ou pasta de rede;
- dados continuam fora do executável em `%APPDATA%\GestaoEmpresasLocal`.


## V12.1.2 — preparação para repositório público

- removida a senha administrativa legada hardcoded do código de produção;
- migração de bancos antigos passa a marcar usuários legados para troca de senha pela estrutura do schema, sem conhecer a senha anterior;
- dados de CNPJ/documentos e linha digitável usados nos testes foram substituídos por fixtures sintéticas;
- CNPJ válido de teste passa a ser calculado em tempo de execução;
- `User-Agent` da consulta de CNPJ passa a usar a versão real da aplicação.


## V12.1.3 — qualidade para publicação

- README reorganizado como vitrine técnica do projeto;
- badge de CI e documentação explícita das limitações do Guardião Antifraude;
- GitHub Actions com compilação, Ruff, testes e cobertura;
- cobertura mínima inicial de 55% nas camadas `core`, `database`, `repositories` e `services`;
- Ruff configurado inicialmente para erros objetivos e nomes indefinidos;
- `requirements-dev.txt` para ferramentas de desenvolvimento;
- `.gitattributes` para padronizar LF/CRLF entre código e scripts Windows;
- template de Pull Request e formulário de bug com orientação para não expor dados reais;
- `CONTRIBUTING.md` e `docs/QUALIDADE.md` adicionados;
- `SECURITY.md` revisado para um repositório público;
- verificação automatizada pré-publicação para impedir arquivos e padrões sensíveis conhecidos.
