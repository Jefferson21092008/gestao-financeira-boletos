import os
import sqlite3
from pathlib import Path
import subprocess
import sys
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

from config import APP_NAME, DATE_FMT_UI, MOVEMENT_TYPES
from core.cnpj import validate_cnpj
from core.finance import from_cents
from core.formatters import format_date_ui, format_money, parse_date_ui, parse_money
from core.paths import escape_ps, get_entrypoint_path, get_windows_desktop_path
from ui.alerts_window import AlertsWindow
from ui.backup_window import BackupWindow
from ui.bills_window import BillsWindow
from ui.dashboard_window import DashboardWindow


class MainFrameActionsMixin:
    def get_filter_values(self, silent: bool = False):
        try:
            start = parse_date_ui(self.filter_start_var.get(), "a data inicial", allow_empty=True)
            end = parse_date_ui(self.filter_end_var.get(), "a data final", allow_empty=True)
            if start and end and start > end:
                raise ValueError("A data inicial não pode ser posterior à data final.")
            return start, end
        except ValueError as exc:
            if not silent:
                messagebox.showerror("Filtros", str(exc))
            return None, None

    def clear_filters(self) -> None:
        self.search_var.set("")
        self.filter_start_var.set("")
        self.filter_end_var.set("")
        self.filter_type_var.set("Todos")
        self.filter_status_var.set("Todos")
        self.filter_cost_var.set("Todos")
        self.refresh_table()

    def _validate_financial_form(self) -> dict:
        """Valida os campos financeiros básicos do lançamento."""
        empresa = self.vars["empresa"].get().strip()
        nota = self.vars["numero_nota_fiscal"].get().strip()
        boleto = self.vars["numero_boleto"].get().strip()
        movement_type = self.vars["tipo_movimentacao"].get().strip()
        cost_center = self.vars["centro_custo"].get().strip()

        if not empresa:
            raise ValueError("Informe o nome da empresa.")
        if movement_type not in MOVEMENT_TYPES:
            raise ValueError("Selecione Entrada ou Despesa.")
        if not cost_center:
            raise ValueError("Informe o centro de custo.")
        if not nota:
            raise ValueError("Informe o número da nota fiscal.")
        if not boleto:
            raise ValueError("Informe o número do boleto.")

        launch_date = parse_date_ui(self.vars["data_lancamento"].get(), "a data do lançamento")
        first_due = parse_date_ui(self.vars["primeiro_vencimento"].get(), "o primeiro vencimento")
        assert launch_date and first_due

        try:
            qtd = int(self.vars["quantidade_boletos"].get().strip())
        except ValueError as exc:
            raise ValueError("A quantidade de boletos deve ser um número inteiro.") from exc
        if qtd <= 0:
            raise ValueError("A quantidade de boletos deve ser maior que zero.")

        try:
            valor_nf = parse_money(self.vars["valor_nota_fiscal"].get())
            especial = parse_money(self.vars["valor_parte_especial"].get())
            total = parse_money(self.vars["valor_total"].get())
        except ValueError as exc:
            raise ValueError("Confira os campos de valores. Ex.: 1500,50") from exc

        if valor_nf < 0 or especial < 0 or total < 0:
            raise ValueError("Os valores não podem ser negativos.")

        return {
            "empresa": empresa,
            "cnpj": self.vars["cnpj"].get().strip(),
            "tipo_movimentacao": movement_type,
            "centro_custo": cost_center,
            "data_lancamento": launch_date,
            "numero_nota_fiscal": nota,
            "numero_boleto": boleto,
            "quantidade_boletos": qtd,
            "primeiro_vencimento": first_due,
            "valor_nota_fiscal": valor_nf,
            "valor_parte_especial": especial,
            "valor_total": total,
        }

    def calculate_total(self) -> None:
        try:
            nf = parse_money(self.vars["valor_nota_fiscal"].get())
            especial = parse_money(self.vars["valor_parte_especial"].get())
        except ValueError:
            messagebox.showwarning("Valores inválidos", "Informe o valor da nota fiscal e da parte especial primeiro.")
            return
        self.vars["valor_total"].set(format_money(nf + especial).replace("R$ ", ""))

    def _refresh_company_info(self) -> None:
        if not hasattr(self, "company_info_var"):
            return
        name = self.vars["empresa"].get().strip()
        row = self.db.get_company_exact(name)
        if not row:
            self.vars["cnpj"].set("")
            self.company_info_var.set("Empresa não selecionada. Escolha uma empresa cadastrada na lista ou cadastre-a pelo menu Empresas.")
            return
        self.vars["empresa"].set(row["nome"])
        self.vars["cnpj"].set(row["cnpj"] or "")
        display = row["nome_fantasia"] or row["razao_social"] or row["nome"]
        legal = row["razao_social"] or row["nome"]
        local = " / ".join(x for x in (row["municipio"], row["uf"]) if x) or "local não informado"
        status = row["situacao_cadastral"] or "cadastro local ainda não validado online"
        self.company_info_var.set(f"{display}  •  Razão social: {legal}\nCNPJ: {row['cnpj'] or 'não informado'}  •  Situação: {status}  •  {local}")

    def on_company_typing(self, _event=None) -> None:
        if not hasattr(self, "company_combo"):
            return
        typed = self.vars["empresa"].get().strip()
        rows = self.db.list_companies(typed, limit=50)
        self.company_combo.configure(values=[r["nome"] for r in rows])
        self._refresh_company_info()

    def on_company_selected(self, _event=None) -> None:
        self._refresh_company_info()

    def validate_form(self) -> dict:
        """Valida o lançamento e garante que a empresa venha do cadastro local."""
        # Executa primeiro as validações financeiras básicas desta própria classe.
        data = self._validate_financial_form()
        company = self.db.get_company_exact(self.vars["empresa"].get().strip())
        if not company:
            raise ValueError("Selecione uma empresa já cadastrada. Para cadastrar uma nova empresa, abra o menu 'Empresas' e consulte o CNPJ.")
        if not company["cnpj"]:
            raise ValueError("A empresa selecionada não possui CNPJ cadastrado. Atualize a ficha no menu 'Empresas' antes de criar boletos.")
        if not validate_cnpj(company["cnpj"]):
            raise ValueError("O CNPJ salvo para esta empresa é inválido. Atualize a empresa no menu 'Empresas' antes de criar boletos.")
        data["empresa_id"] = int(company["id"])
        data["empresa"] = company["nome"]
        data["cnpj"] = company["cnpj"]
        return data

    def duplicate_record(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Duplicar", "Selecione um lançamento na tabela primeiro.")
            return
        row = self.db.get_purchase(self.selected_id)
        if not row:
            return
        source_id = self.selected_id
        self.selected_id = None
        self.vars["empresa"].set(row["empresa"])
        self.vars["cnpj"].set(row["cnpj"] or "")
        self.vars["tipo_movimentacao"].set(row["tipo_movimentacao"] or "Despesa")
        self.vars["centro_custo"].set(row["centro_custo"] or "Administrativo")
        self.vars["data_lancamento"].set(date.today().strftime(DATE_FMT_UI))
        self.vars["numero_nota_fiscal"].set("")
        self.vars["numero_boleto"].set("")
        self.vars["quantidade_boletos"].set(str(row["quantidade_boletos"]))
        self.vars["primeiro_vencimento"].set("")
        self.vars["valor_nota_fiscal"].set(format_money(from_cents(row["valor_nota_fiscal_centavos"])).replace("R$ ", ""))
        self.vars["valor_parte_especial"].set(format_money(from_cents(row["valor_parte_especial_centavos"])).replace("R$ ", ""))
        self.vars["valor_total"].set(format_money(from_cents(row["valor_total_centavos"])).replace("R$ ", ""))
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self.status_var.set(f"Rascunho duplicado do lançamento #{source_id}. Informe nova nota, boleto e vencimento antes de salvar.")
        self.entries["numero_nota_fiscal"].focus_set()

    def save_record(self) -> None:
        try:
            data = self.validate_form()
            new_id = self.db.insert_purchase(data)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Não foi possível salvar", str(exc))
            return

        self.status_var.set(f"Lançamento #{new_id} salvo. Parcelas e vencimentos foram gerados.")
        self.refresh_table()
        self.clear_form(keep_status=True)

    def update_record(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Atualizar", "Selecione um lançamento na tabela primeiro.")
            return
        try:
            data = self.validate_form()
            self.db.update_purchase(self.selected_id, data)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Não foi possível atualizar", str(exc))
            return

        updated_id = self.selected_id
        self.status_var.set(f"Lançamento #{updated_id} atualizado com sucesso.")
        self.refresh_table()
        self.clear_form(keep_status=True)

    def delete_record(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Excluir", "Selecione um lançamento na tabela primeiro.")
            return
        if not messagebox.askyesno("Confirmar exclusão", f"Deseja realmente excluir o lançamento #{self.selected_id} e seus boletos?"):
            return
        try:
            deleted_id = self.selected_id
            self.db.delete_purchase(deleted_id)
        except sqlite3.Error as exc:
            messagebox.showerror("Não foi possível excluir", str(exc))
            return
        self.status_var.set(f"Lançamento #{deleted_id} excluído.")
        self.refresh_table()
        self.clear_form(keep_status=True)

    def load_selected_record(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        row = self.db.get_purchase(self.selected_id)
        if not row:
            return
        self.vars["empresa"].set(row["empresa"])
        self.vars["cnpj"].set(row["cnpj"])
        self.vars["tipo_movimentacao"].set(row["tipo_movimentacao"] or "Despesa")
        self.vars["centro_custo"].set(row["centro_custo"] or "Administrativo")
        self.vars["data_lancamento"].set(format_date_ui(row["data_lancamento"]))
        self.vars["numero_nota_fiscal"].set(row["numero_nota_fiscal"])
        self.vars["numero_boleto"].set(row["numero_boleto"])
        self.vars["quantidade_boletos"].set(str(row["quantidade_boletos"]))
        self.vars["primeiro_vencimento"].set(format_date_ui(row["primeiro_vencimento"]))
        self.vars["valor_nota_fiscal"].set(format_money(from_cents(row["valor_nota_fiscal_centavos"])).replace("R$ ", ""))
        self.vars["valor_parte_especial"].set(format_money(from_cents(row["valor_parte_especial_centavos"])).replace("R$ ", ""))
        self.vars["valor_total"].set(format_money(from_cents(row["valor_total_centavos"])).replace("R$ ", ""))
        self.status_var.set(f"Editando o lançamento #{self.selected_id}.")

    def clear_form(self, keep_status: bool = False) -> None:
        self.selected_id = None
        self.vars["empresa"].set("")
        self.vars["cnpj"].set("")
        self.vars["tipo_movimentacao"].set("Despesa")
        self.vars["centro_custo"].set("Administrativo")
        self.vars["data_lancamento"].set(date.today().strftime(DATE_FMT_UI))
        self.vars["numero_nota_fiscal"].set("")
        self.vars["numero_boleto"].set("")
        self.vars["quantidade_boletos"].set("1")
        self.vars["primeiro_vencimento"].set("")
        self.vars["valor_nota_fiscal"].set("")
        self.vars["valor_parte_especial"].set("0,00")
        self.vars["valor_total"].set("")
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        if not keep_status:
            self.status_var.set("Pronto para cadastrar um novo lançamento.")
        self.entries["empresa"].focus_set()

    def open_bills(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Boletos", "Selecione um lançamento primeiro.")
            return
        bills = self.db.list_bills(self.selected_id)
        if not bills:
            messagebox.showwarning(
                "Boletos",
                "Este lançamento é antigo e ainda não possui vencimentos gerados.\n\n"
                "Preencha o campo '1º vencimento' e clique em Atualizar para gerar as parcelas.",
            )
            return
        BillsWindow(self, self.db, self.selected_id, self.refresh_table)

    def open_dashboard(self) -> None:
        DashboardWindow(self, self.db)

    def open_backups(self) -> None:
        BackupWindow(self, self.db, self.on_database_restored)

    def on_database_restored(self) -> None:
        self.clear_form()
        self.refresh_table()
        if hasattr(self, "company_combo"):
            self.company_combo.configure(values=[r["nome"] for r in self.db.list_companies("", limit=500)])

    def open_alerts(self) -> None:
        AlertsWindow(self, self.db, self.refresh_table)

    def show_startup_alerts(self) -> None:
        if self.startup_alert_shown:
            return
        self.startup_alert_shown = True
        counts = self.db.alert_counts_detailed()
        if counts["atrasados"] or counts["hoje"] or counts["amanha"]:
            text = []
            if counts["atrasados"]:
                text.append(f"{counts['atrasados']} boleto(s) atrasado(s)")
            if counts["hoje"]:
                text.append(f"{counts['hoje']} boleto(s) vence(m) hoje")
            if counts["amanha"]:
                text.append(f"{counts['amanha']} boleto(s) vence(m) amanhã")
            messagebox.showwarning(
                "Alertas de pagamento",
                "Há pagamentos que precisam de atenção:\n\n" + "\n".join(f"• {x}" for x in text) + "\n\nAbra 'Alertas' para ver os próximos 7 dias.",
            )

    def create_desktop_shortcut(self) -> None:
        if os.name != "nt":
            messagebox.showinfo("Atalho", "A criação automática de atalho está configurada para Windows.")
            return
        try:
            desktop = get_windows_desktop_path()
            shortcut_path = desktop / f"{APP_NAME}.lnk"

            if getattr(sys, "frozen", False):
                target = Path(sys.executable).resolve()
                arguments = ""
                working_dir = target.parent
                icon = target
            else:
                python_exe = Path(sys.executable).resolve()
                pythonw = python_exe.with_name("pythonw.exe")
                target = pythonw if pythonw.exists() else python_exe
                script = get_entrypoint_path()
                arguments = f'"{script}"'
                working_dir = script.parent
                icon = python_exe

            ps_command = (
                "$ws = New-Object -ComObject WScript.Shell; "
                f"$sc = $ws.CreateShortcut('{escape_ps(str(shortcut_path))}'); "
                f"$sc.TargetPath = '{escape_ps(str(target))}'; "
                f"$sc.Arguments = '{escape_ps(arguments)}'; "
                f"$sc.WorkingDirectory = '{escape_ps(str(working_dir))}'; "
                f"$sc.IconLocation = '{escape_ps(str(icon))},0'; "
                "$sc.Save();"
            )
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            messagebox.showinfo("Atalho criado", f"Atalho criado com sucesso em:\n{shortcut_path}")
        except Exception as exc:
            messagebox.showerror("Erro ao criar atalho", str(exc))
