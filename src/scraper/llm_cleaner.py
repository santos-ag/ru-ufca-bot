"""Módulo responsável por limpar e estruturar os dados do cardápio usando LLM (Google Gemini)."""

import os
import json
import time
import logging
import google.generativeai as genai
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Variável global para armazenar a instância do modelo, instanciado de forma tardia (lazy load)
_model_instance = None
_llm_configured = False
_groq_client = None
_groq_configured = False
_groq_last_call_ts = 0.0


def _get_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "gemini").strip().lower()


def _groq_delay_seconds() -> float:
    try:
        return float(os.environ.get("GROQ_DELAY_SECONDS", "0.5"))
    except ValueError:
        return 0.5


def _apply_groq_delay() -> None:
    global _groq_last_call_ts
    delay = _groq_delay_seconds()
    if delay <= 0:
        _groq_last_call_ts = time.monotonic()
        return

    now = time.monotonic()
    elapsed = now - _groq_last_call_ts
    remaining = delay - elapsed
    if remaining > 0:
        time.sleep(remaining)
        now = time.monotonic()
    _groq_last_call_ts = now

def get_llm_model():
    """Inicializa e retorna o modelo do Gemini de forma segura, garantindo que o dotenv já foi carregado."""
    global _model_instance, _llm_configured
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
        
    if not _llm_configured:
        try:
            genai.configure(api_key=api_key)
            model_name = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
            _model_instance = genai.GenerativeModel(
                model_name,
                generation_config={"response_mime_type": "application/json"}
            )
            _llm_configured = True
        except Exception as e:
            logger.warning(f"Não foi possível inicializar o modelo Gemini: {e}")
            return None
            
    return _model_instance


def get_groq_client():
    """Inicializa e retorna o cliente Groq de forma segura."""
    global _groq_client, _groq_configured

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    if not _groq_configured:
        try:
            from groq import Groq

            _groq_client = Groq(api_key=api_key)
            _groq_configured = True
        except Exception as e:
            logger.warning(f"Não foi possível inicializar o cliente Groq: {e}")
            return None

    return _groq_client

def is_llm_available() -> bool:
    """Verifica se a chave da API do Gemini foi configurada e o modelo pode ser inicializado."""
    provider = _get_provider()
    if provider == "groq":
        return get_groq_client() is not None
    return get_llm_model() is not None

def clean_meal_data_with_llm(raw_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Usa o Gemini para limpar e estruturar os textos sujos extraídos do PDF.
    
    Args:
        raw_data: Dicionário com os textos brutos. 
                 Ex: {"principal": "ESCONDIDINHO DE CARNE FRANGO ACEBOLADO", ...}
                 
    Returns:
        Dicionário estruturado, com listas para pratos múltiplos e formatação em Title Case.
    """
    provider = _get_provider()
    if provider == "groq":
        return _clean_with_groq(raw_data)
    return _clean_with_gemini(raw_data)


def _build_prompt(raw_data: Dict[str, str]) -> str:
    return f"""
    Você é um assistente de estruturação de dados.
    Aqui estão os textos extraídos de um cardápio de restaurante universitário (com possíveis erros de OCR ou falta de separação, e muitas vezes em CAPS LOCK):
    
    {json.dumps(raw_data, ensure_ascii=False, indent=2)}
    
    Sua tarefa é limpar esses dados e retornar EXATAMENTE um objeto JSON seguindo estas regras rigorosamente:
    1. Capitalização: Use Title Case para todos os itens (ex: "Escondidinho de Carne", não "ESCONDIDINHO DE CARNE").
    2. Separação: Se "principal" contiver dois pratos colados (ex: "ESCONDIDINHO DE CARNE FRANGO ACEBOLADO" ou "ISCAS DE PORCO OU FRANGO"), separe-os em uma lista de strings.
    3. Retorne APENAS um JSON válido. Não adicione crases (```json) ou texto extra.
    
    O schema do JSON de saída DEVE ser estritamente este:
    {{
      "prato_principal": ["string", "string"],  // Pode ter 1 ou mais itens
      "vegetariano": "string",
      "acompanhamentos": ["string", "string"], // Junte guarnição e acompanhamento aqui
      "saladas": ["string", "string"],
      "suco": "string",
      "sobremesa": "string"
    }}
    
    Se alguma categoria estiver vazia no texto original, retorne string vazia "" ou lista vazia [].
    Se "vegetariano", "suco" ou "sobremesa" tiverem mais de uma opção, junte com " ou " (ex: "Laranja ou Caju").
    """


def _parse_json_response(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start != -1:
            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(text[start:])
            return parsed
        raise


def _clean_with_gemini(raw_data: Dict[str, str]) -> Dict[str, Any]:
    model = get_llm_model()

    if model is None:
        logger.warning("GOOGLE_API_KEY não configurada ou modelo indisponível. Usando fallback simples.")
        return _post_process(_fallback_cleaner(raw_data))

    prompt = _build_prompt(raw_data)

    try:
        response = model.generate_content(prompt)
        # O modelo já foi configurado para retornar application/json, 
        # então o response.text deve ser um JSON parseável direto.
        result = _parse_json_response(response.text)
        return _post_process(result)

    except Exception as e:
        logger.error(f"Erro ao limpar dados com Gemini: {e}")
        return _post_process(_fallback_cleaner(raw_data))


def _clean_with_groq(raw_data: Dict[str, str]) -> Dict[str, Any]:
    client = get_groq_client()
    if client is None:
        logger.warning("GROQ_API_KEY não configurada ou cliente indisponível. Usando fallback simples.")
        return _post_process(_fallback_cleaner(raw_data))

    prompt = _build_prompt(raw_data)
    model_name = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    system_message = "Responda apenas com um JSON válido, sem texto extra."

    try:
        _apply_groq_delay()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        result = _parse_json_response(content)
        return _post_process(result)
    except Exception as e:
        logger.error(f"Erro ao limpar dados com Groq: {e}")
        return _post_process(_fallback_cleaner(raw_data))


def _fallback_cleaner(raw_data: Dict[str, str]) -> Dict[str, Any]:
    """Fallback simples caso a API falhe ou não esteja configurada."""
    
    def _clean_str(text: str) -> str:
        if not text:
            return ""
        # Remove multiplos espacos, title case
        text = " ".join(text.split()).title()
        # Remove trailing comma
        if text.endswith(','):
            text = text[:-1]
        # Escapar caracteres do telegram
        return text.replace('*', '\\*').replace('_', '\\_')
        
    def _clean_list(text: str) -> List[str]:
        if not text:
            return []
        # Tenta separar por vírgula ou " Ou "
        parts = text.replace(" OU ", ",").replace(" Ou ", ",").split(",")
        return [_clean_str(p.strip()) for p in parts if p.strip()]

    # Simula a mesma estrutura de saída
    acomp = _clean_list(raw_data.get("guarnição", ""))
    acomp.extend(_clean_list(raw_data.get("acompanhamento", "")))

    return {
        "prato_principal": [_clean_str(raw_data.get("principal", "Não disponível"))],
        "vegetariano": _clean_str(raw_data.get("vegetariano", "")),
        "acompanhamentos": acomp,
        "saladas": _clean_list(raw_data.get("saladas", "")),
        "suco": _clean_str(raw_data.get("suco", "")),
        "sobremesa": _clean_str(raw_data.get("sobremesa", ""))
    }


def _post_process(cleaned_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza a saída da LLM/fallback para o formato esperado."""
    principal = cleaned_data.get("prato_principal", [])
    cleaned_data["prato_principal"] = _normalize_prato_principal(principal)
    return cleaned_data


def _normalize_prato_principal(principal: Any) -> List[str]:
    """Garante que prato_principal seja uma lista e separa por vírgula."""
    if principal is None:
        return []

    if isinstance(principal, list):
        items = principal
    else:
        items = [str(principal)]

    normalized = []
    for item in items:
        if not item:
            continue
        parts = [p.strip() for p in str(item).split(",") if p.strip()]
        normalized.extend([_title_case(p) for p in parts])

    return normalized


def _title_case(text: str) -> str:
    """Aplica Title Case e remove vírgula no final."""
    text = " ".join(text.split()).title()
    if text.endswith(','):
        text = text[:-1]
    return text.replace('*', '\\*').replace('_', '\\_')
