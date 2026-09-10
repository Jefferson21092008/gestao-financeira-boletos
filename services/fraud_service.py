from core.finance import as_decimal, from_cents
from core.formatters import format_money
from core.text import digits_only, normalize_document, text_similarity


def boleto_mod10(number: str) -> int:
    total = 0
    weight = 2
    for ch in reversed(number):
        product = int(ch) * weight
        total += (product // 10) + (product % 10)
        weight = 1 if weight == 2 else 2
    return (10 - (total % 10)) % 10


def arrecadacao_mod11(number: str) -> int:
    total = 0
    weight = 2
    for ch in reversed(number):
        total += int(ch) * weight
        weight += 1
        if weight > 9:
            weight = 2
    remainder = total % 11
    if remainder in (0, 1):
        return 0
    if remainder == 10:
        return 1
    return 11 - remainder


def boleto_bank_general_dv(barcode_without_dv: str) -> int:
    total = 0
    weight = 2
    for ch in reversed(barcode_without_dv):
        total += int(ch) * weight
        weight += 1
        if weight > 9:
            weight = 2
    result = 11 - (total % 11)
    return 1 if result in (0, 10, 11) else result


def _set_encoded_value(result: dict, cents: int) -> None:
    result["encoded_value_cents"] = cents if cents else None
    result["encoded_value"] = from_cents(cents) if cents else None


def inspect_payment_code(raw_code: str) -> dict:
    """Validação local de formato e dígitos verificadores; não confirma emissão bancária."""
    code = digits_only(raw_code)
    result = {
        "code": code,
        "kind": "Desconhecido",
        "valid_structure": False,
        "checks_ok": False,
        "bank_code": "",
        "encoded_value": None,
        "encoded_value_cents": None,
        "details": [],
    }

    if len(code) == 47:
        result["kind"] = "Boleto bancário — linha digitável"
        f1, dv1 = code[0:9], int(code[9])
        f2, dv2 = code[10:20], int(code[20])
        f3, dv3 = code[21:31], int(code[31])
        overall_dv = int(code[32])
        result["valid_structure"] = True
        result["bank_code"] = code[:3]
        checks = [boleto_mod10(f1) == dv1, boleto_mod10(f2) == dv2, boleto_mod10(f3) == dv3]
        result["details"].append((all(checks), "Dígitos verificadores dos 3 campos"))
        free_field = code[4:9] + code[10:20] + code[21:31]
        barcode = code[0:4] + code[32] + code[33:47] + free_field
        result["details"].append((boleto_bank_general_dv(barcode[:4] + barcode[5:]) == overall_dv, "Dígito verificador geral"))
        result["details"].append((code[3] == "9", "Código de moeda Real (9)"))
        _set_encoded_value(result, int(code[37:47]))
        result["checks_ok"] = all(x[0] for x in result["details"])
        return result

    if len(code) == 48 and code.startswith("8"):
        result["kind"] = "Arrecadação/convênio — linha digitável"
        result["valid_structure"] = True
        value_id = code[2]
        method = boleto_mod10 if value_id in ("6", "7") else arrecadacao_mod11 if value_id in ("8", "9") else None
        if method is None:
            result["details"].append((False, "Identificador de valor/referência reconhecido"))
        else:
            block_checks = []
            data_blocks = []
            for start in (0, 12, 24, 36):
                block = code[start:start + 12]
                data, dv = block[:11], int(block[11])
                data_blocks.append(data)
                block_checks.append(method(data) == dv)
            result["details"].append((all(block_checks), "Dígitos verificadores dos 4 blocos"))
            barcode = "".join(data_blocks)
            result["details"].append((method(barcode[:3] + barcode[4:]) == int(barcode[3]), "Dígito verificador geral"))
            if value_id in ("6", "8"):
                _set_encoded_value(result, int(barcode[4:15]))
            result["bank_code"] = f"Segmento {code[1]}"
        result["checks_ok"] = bool(result["details"]) and all(x[0] for x in result["details"])
        return result

    if len(code) == 44:
        result["valid_structure"] = True
        if code.startswith("8"):
            result["kind"] = "Arrecadação/convênio — código de barras"
            value_id = code[2]
            method = boleto_mod10 if value_id in ("6", "7") else arrecadacao_mod11 if value_id in ("8", "9") else None
            if method:
                result["details"].append((method(code[:3] + code[4:]) == int(code[3]), "Dígito verificador geral"))
                if value_id in ("6", "8"):
                    _set_encoded_value(result, int(code[4:15]))
                result["bank_code"] = f"Segmento {code[1]}"
                result["checks_ok"] = all(x[0] for x in result["details"])
            else:
                result["details"].append((False, "Identificador de valor/referência reconhecido"))
            return result

        result["kind"] = "Boleto bancário — código de barras"
        result["bank_code"] = code[:3]
        result["details"].append((boleto_bank_general_dv(code[:4] + code[5:]) == int(code[4]), "Dígito verificador geral"))
        result["details"].append((code[3] == "9", "Código de moeda Real (9)"))
        _set_encoded_value(result, int(code[9:19]))
        result["checks_ok"] = all(x[0] for x in result["details"])
        return result

    result["details"].append((False, "Código com 44, 47 ou 48 dígitos"))
    return result


def calculate_fraud_risk(
    inspection: dict,
    expected_name: str,
    expected_doc: str,
    shown_name: str,
    shown_doc: str,
    expected_value=None,
    duplicate_other_company: bool = False,
    unusual_bank: bool = False,
    cnpj_lookup: dict | None = None,
    prior_high_risk_same_line: bool = False,
) -> dict:
    """Triagem conservadora: baixo risco exige dados suficientes para comparação."""
    score = 0
    reasons: list[dict] = []

    def add(points: int, level: str, title: str, detail: str):
        nonlocal score
        score += points
        reasons.append({"points": points, "level": level, "title": title, "detail": detail})

    if not inspection["valid_structure"]:
        add(70, "danger", "Formato inválido", "O código não corresponde aos formatos de 44, 47 ou 48 dígitos reconhecidos.")
    elif not inspection["checks_ok"]:
        add(60, "danger", "Falha matemática", "Um ou mais dígitos verificadores não conferem. Não prossiga sem confirmar a origem.")
    else:
        add(0, "ok", "Estrutura consistente", "Os dígitos verificadores analisados conferem matematicamente.")

    if expected_value is None:
        add(20, "warn", "Valor esperado não informado", "Sem o valor esperado da cobrança, o sistema não libera classificação de baixo risco.")
    else:
        expected = as_decimal(expected_value)
        encoded = inspection.get("encoded_value")
        if encoded is not None:
            encoded = as_decimal(encoded)
            if encoded != expected:
                add(45, "danger", "Valor diferente", f"Código indica {format_money(encoded)}, mas o sistema espera {format_money(expected)}.")
            else:
                add(0, "ok", "Valor confere", f"O valor codificado corresponde a {format_money(expected)}.")
        else:
            add(20, "warn", "Valor não comparável pelo código", "O código não trouxe um valor utilizável para comparação automática. Confira o valor no banco.")

    expected_doc_norm = normalize_document(expected_doc)
    shown_doc_norm = normalize_document(shown_doc)
    if not expected_doc_norm:
        add(20, "warn", "Documento esperado ausente", "Cadastre o CNPJ/CPF esperado para permitir uma conferência forte do favorecido.")
    elif not shown_doc_norm:
        add(22, "warn", "CNPJ/CPF exibido não conferido", "Digite o documento que o aplicativo/site do banco mostra antes de pagar.")
    elif expected_doc_norm != shown_doc_norm:
        add(60, "danger", "CNPJ/CPF diferente", "O documento exibido pelo banco não corresponde ao documento esperado.")
    else:
        add(0, "ok", "CNPJ/CPF confere", "O documento exibido pelo banco corresponde ao cadastro esperado.")

    if not expected_name.strip():
        add(20, "warn", "Beneficiário esperado ausente", "Informe a empresa esperada antes de analisar o pagamento.")
    elif not shown_name.strip():
        add(22, "warn", "Beneficiário exibido não conferido", "Informe exatamente o beneficiário que aparece no aplicativo/site do banco.")
    else:
        sim = text_similarity(expected_name, shown_name)
        if sim < 0.45:
            add(50, "danger", "Beneficiário diferente", "O nome mostrado pelo banco é muito diferente da empresa esperada.")
        elif sim < 0.72:
            add(22, "warn", "Beneficiário merece conferência", "Os nomes são parecidos, mas não o bastante para uma confirmação segura.")
        else:
            add(0, "ok", "Beneficiário compatível", "O nome mostrado pelo banco é compatível com a empresa esperada.")

    if cnpj_lookup:
        lookup_status = cnpj_lookup.get("status")
        if lookup_status == "ok":
            situacao = (cnpj_lookup.get("situacao") or "").upper()
            razao = cnpj_lookup.get("razao_social") or ""
            fantasia = cnpj_lookup.get("nome_fantasia") or ""
            if situacao == "ATIVA":
                add(0, "ok", "CNPJ encontrado e ativo", "A fonte cadastral retornou situação ATIVA.")
            elif situacao:
                add(40, "danger", f"Situação cadastral: {situacao}", "A empresa foi encontrada, mas a situação cadastral não está ativa. Confirme por canal oficial.")
            else:
                add(10, "warn", "Situação cadastral não informada", "A fonte encontrou o CNPJ, mas não retornou situação cadastral clara.")

            registered_names = [n for n in (razao, fantasia) if n]
            if expected_name and registered_names:
                best = max(text_similarity(expected_name, n) for n in registered_names)
                registered = razao or fantasia
                if best < 0.45:
                    add(35, "danger", "Cadastro incompatível com a empresa esperada", f"A consulta identifica “{registered}”, diferente da empresa esperada.")
                elif best < 0.72:
                    add(15, "warn", "Nome cadastral merece conferência", f"A consulta identifica “{registered}”. Confirme se é o fornecedor correto.")
                else:
                    add(0, "ok", "Empresa compatível com cadastro público", f"A empresa esperada é compatível com o cadastro consultado: {registered}.")

            if shown_name and registered_names:
                best_shown = max(text_similarity(shown_name, n) for n in registered_names)
                if best_shown < 0.45:
                    add(45, "danger", "Beneficiário do banco incompatível com o CNPJ", "O nome exibido pelo banco não combina com a razão social/nome fantasia retornado para o CNPJ consultado.")
                elif best_shown < 0.72:
                    add(20, "warn", "Beneficiário e cadastro público diferem", "O nome exibido pelo banco merece conferência adicional com o cadastro do CNPJ.")
                else:
                    add(0, "ok", "Beneficiário compatível com o CNPJ", "O beneficiário exibido também é compatível com o cadastro consultado.")
        elif lookup_status == "not_found":
            add(55, "danger", "CNPJ não encontrado", "A fonte cadastral não encontrou esse CNPJ. Confirme no portal oficial antes de pagar.")
        elif lookup_status == "invalid":
            add(55, "danger", "CNPJ matematicamente inválido", "Os dígitos verificadores do CNPJ não conferem.")
        elif lookup_status == "provider_unsupported":
            add(0, "warn", "CNPJ alfanumérico — confirme no portal oficial", cnpj_lookup.get("message") or "A validação local passou, mas a fonte automática atual não suporta esse formato.")
        elif lookup_status == "unavailable":
            add(0, "warn", "Consulta cadastral indisponível", cnpj_lookup.get("message") or "Não foi possível consultar o CNPJ agora. Isso, isoladamente, não indica fraude.")

    if duplicate_other_company:
        add(60, "danger", "Código reutilizado por outra empresa", "Esta mesma linha já apareceu vinculada a outra empresa no histórico local.")
    if prior_high_risk_same_line:
        add(30, "warn", "Código já teve análise de alto risco", "Esta linha já recebeu classificação ALTO em uma análise anterior. Revise o histórico antes de prosseguir.")
    if unusual_bank:
        add(20, "warn", "Banco/segmento fora do histórico confiável", "O código usa um banco/segmento ainda não visto nas análises de baixo risco desta empresa.")

    score = min(score, 100)
    if score >= 50:
        level, label = "ALTO", "Alto risco — não prossiga"
        decision = "Não pague até confirmar por um canal oficial independente do boleto recebido."
    elif score >= 20:
        level, label = "ATENÇÃO", "Atenção — confira antes de pagar"
        decision = "Há dados ausentes ou divergências que precisam ser conferidos no banco ou com o fornecedor."
    else:
        level, label = "BAIXO", "Baixo risco aparente"
        decision = "As verificações disponíveis estão coerentes, mas a confirmação final continua sendo do banco e do fornecedor."

    return {
        "score": score,
        "level": level,
        "label": label,
        "decision": decision,
        "reasons": reasons,
    }
