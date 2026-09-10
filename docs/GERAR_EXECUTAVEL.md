# Gerar o executável no Windows — V12.1.3

## Correção desta revisão

A primeira V12.1 possuía um `version_info.txt` salvo incorretamente, com sequências `\\n` literais. Como o script antigo enviava esse arquivo ao PyInstaller por `--version-file`, a compilação podia falhar. A V12.1.3 corrige o arquivo e, por segurança, o build principal não depende mais dele.

## Modo recomendado

1. Extraia o ZIP em uma pasta normal, por exemplo `C:\GestaoFinanceira`.
2. Não execute o build diretamente de dentro do ZIP.
3. Tenha Python 3 instalado no Windows. Se instalar pelo python.org, marque **Add python.exe to PATH**.
4. Dê duplo clique em `build_exe.bat`.
5. O script cria um ambiente `.venv-build`, instala o PyInstaller e gera:

```text
dist\GestaoFinanceira\GestaoFinanceira.exe
```

6. Para o PC da empresa, copie a pasta `dist\GestaoFinanceira` inteira.

O computador final não precisa ter Python instalado.

## Se ocorrer erro

O terminal agora permanece aberto e mostra as últimas linhas da falha. Também é criado:

```text
build_exe.log
```

Esse arquivo contém o erro completo. Se a compilação ainda falhar, envie `build_exe.log` para diagnóstico.

## EXE único

`build_exe_unico.bat` cria:

```text
dist_unico\GestaoFinanceira.exe
```

Ele é mais fácil de transportar, mas para uso diário na empresa prefira o modo `onedir` (`build_exe.bat`).

## Dados da empresa

Banco, backups e logs continuam fora do executável:

```text
%APPDATA%\GestaoEmpresasLocal
```

Portanto, recompilar ou substituir o executável não apaga o banco da empresa.
