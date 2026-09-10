import json
import urllib.error
import urllib.request

from config import APP_VERSION, BRASILAPI_CNPJ_URL, HTTP_TIMEOUT_SECONDS
from core.cnpj import cnpj_compact, validate_cnpj

def query_cnpj_brasilapi(cnpj: str) -> dict:
    """Consulta cadastral pontual. Não faz crawling nem consultas em lote."""
    c = cnpj_compact(cnpj)
    if len(c) != 14 or not validate_cnpj(c):
        return {
            "status": "invalid",
            "cnpj": c,
            "source": "Validação local",
            "message": "O CNPJ não passa na validação dos dígitos verificadores.",
        }
    # Em setembro/2026 a documentação pública do endpoint BrasilAPI ainda descreve
    # somente CNPJ numérico. Para CNPJ alfanumérico, fazemos a validação local e
    # encaminhamos o usuário ao portal oficial, sem inventar um resultado online.
    if not c.isdigit():
        return {
            "status": "provider_unsupported",
            "cnpj": c,
            "source": "Validação local + portal oficial",
            "message": "CNPJ alfanumérico válido localmente. A fonte automática configurada ainda não documenta suporte a esse formato; confirme no Portal oficial.",
        }

    request = urllib.request.Request(
        BRASILAPI_CNPJ_URL.format(cnpj=c),
        headers={
            "Accept": "application/json",
            "User-Agent": f"GestaoFinanceiraLocal/{APP_VERSION} (desktop; consulta-cnpj-manual)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "status": "ok",
            "cnpj": cnpj_compact(str(payload.get("cnpj", c))),
            "razao_social": str(payload.get("razao_social") or "").strip(),
            "nome_fantasia": str(payload.get("nome_fantasia") or "").strip(),
            "situacao": str(payload.get("descricao_situacao_cadastral") or "").strip().upper(),
            "municipio": str(payload.get("municipio") or "").strip(),
            "uf": str(payload.get("uf") or "").strip(),
            "logradouro": str(payload.get("logradouro") or "").strip(),
            "numero": str(payload.get("numero") or "").strip(),
            "complemento": str(payload.get("complemento") or "").strip(),
            "bairro": str(payload.get("bairro") or "").strip(),
            "cep": str(payload.get("cep") or "").strip(),
            "telefone": str(payload.get("ddd_telefone_1") or payload.get("telefone") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "natureza_juridica": str(payload.get("descricao_natureza_juridica") or "").strip(),
            "source": "BrasilAPI / Minha Receita",
            "message": "Consulta cadastral concluída.",
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"status": "not_found", "cnpj": c, "source": "BrasilAPI", "message": "CNPJ não encontrado na fonte consultada."}
        if exc.code == 400:
            return {"status": "invalid", "cnpj": c, "source": "BrasilAPI", "message": "A fonte recusou o CNPJ como inválido."}
        if exc.code == 429:
            msg = "Limite temporário de consultas atingido. Tente novamente mais tarde."
        elif exc.code == 403:
            msg = "A fonte recusou temporariamente a consulta. Tente novamente mais tarde."
        else:
            msg = f"Consulta indisponível no momento (HTTP {exc.code})."
        return {"status": "unavailable", "cnpj": c, "source": "BrasilAPI", "message": msg}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "status": "unavailable",
            "cnpj": c,
            "source": "BrasilAPI",
            "message": "Não foi possível consultar o cadastro agora. Verifique a internet e tente novamente.",
            "technical": str(exc),
        }
    except Exception as exc:
        # Falha inesperada do provedor não deve derrubar a interface nem virar falso positivo de fraude.
        return {
            "status": "unavailable",
            "cnpj": c,
            "source": "BrasilAPI",
            "message": "A fonte cadastral retornou uma resposta inesperada. Tente novamente mais tarde.",
            "technical": str(exc),
        }
