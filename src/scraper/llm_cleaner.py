"""Módulo responsável por limpar e estruturar os dados do cardápio usando LLM (Google Gemini)."""

import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Configuramos a API do Gemini. 
# Requer a variável de ambiente GEMINI_API_KEY no arquivo .env
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

# Configuramos o modelo
# Usamos o gemini-1.5-flash pois é muito rápido, grátis e excelente para tarefas de formatação JSON
try:
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    logger.warning(f"Não foi possível inicializar o modelo Gemini: {e}")
    model = None


def is_llm_available() -> bool:
    """Verifica se a chave da API do Gemini foi configurada."""
    return bool(os.environ.get("GEMINI_API_KEY"))


def clean_meal_data_with_llm(raw_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Usa o Gemini para limpar e estruturar os textos sujos extraídos do PDF.
    
    Args:
        raw_data: Dicionário com os textos brutos. 
                 Ex: {"principal": "ESCONDIDINHO DE CARNE FRANGO ACEBOLADO", ...}
                 
    Returns:
        Dicionário estruturado, com listas para pratos múltiplos e formatação em Title Case.
    """
    if not is_llm_available() or model is None:
        logger.warning("GEMINI_API_KEY não configurada. Usando fallback simples.")
        return _fallback_cleaner(raw_data)
        
    prompt = f"""
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
    
    try:
        response = model.generate_content(prompt)
        # O modelo já foi configurado para retornar application/json, 
        # então o response.text deve ser um JSON parseável direto.
        result = json.loads(response.text)
        
        # Converte lista única de prato principal em string pra manter compatibilidade (opcional, vamos manter formato lista para favoritos, depois formatador junta)
        return result
        
    except Exception as e:
        logger.error(f"Erro ao limpar dados com Gemini: {e}")
        return _fallback_cleaner(raw_data)


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
