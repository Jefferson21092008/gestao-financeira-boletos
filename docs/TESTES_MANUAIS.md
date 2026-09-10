# Testes manuais recomendados

Antes de uso real na empresa, valide principalmente:

1. primeiro acesso e login;
2. cadastro e consulta de empresa/CNPJ;
3. lançamentos de entrada e despesa;
4. precisão dos valores e divisão de parcelas;
5. vencimentos em viradas de mês/ano;
6. persistência de parcelas pagas;
7. alertas e filtros;
8. edição, exclusão e duplicação de lançamentos;
9. Guardião Antifraude com boleto coerente;
10. divergência de valor, documento e beneficiário;
11. dados insuficientes no Guardião;
12. linha digitável inválida;
13. histórico e reutilização suspeita de código;
14. auditoria;
15. backup, restauração e backup externo;
16. execução pelo `.exe`;
17. encerramento inesperado em banco de testes;
18. volume maior de empresas/lançamentos;
19. fluxo real: receber boleto -> cadastrar/localizar empresa -> lançar -> conferir -> analisar -> pagar -> marcar como pago.

Para homologação, todos os cenários críticos de antifraude, valores e backup devem passar antes do uso com dados reais.
