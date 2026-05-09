"""
LLM servisi.
Groq (Llama 3) → OpenAI → Demo Modu öncelik sırası.
Soru tipine göre (özet, genel, spesifik) farklı prompt kullanır.
"""

import logging
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Sistem Promptu ───────────────────────────────────────────────

SYSTEM_PROMPT = """Sen bir doküman analiz asistanısın. Kullanıcının yüklediği belgeleri analiz ederek sorulara kapsamlı, doğru ve anlaşılır Türkçe cevaplar verirsin.

KURALLAR:
1. Yalnızca verilen BAĞLAM bilgilerini kullan.
2. Bağlamda kısmi bilgi varsa bile onu en iyi şekilde kullan ve yanıtla.
3. Cevabı madde madde, düzenli ve akademik bir dille yaz.
4. Eğer gerçekten hiçbir ilgili bilgi yoksa: "Bu bilgi belgede bulunamadı." de.
5. Asla bilgi uydurmakta, bağlam dışına çıkma.
6. Cevapların sonunda hangi sayfadan yararlandığını belirt."""

SUMMARY_PROMPT = """Sen bir doküman özetleme uzmanısın. Verilen belge içeriğini analiz ederek kapsamlı bir özet çıkarırsın.

GÖREV:
- Belgenin ana konularını belirle
- Her önemli konuyu kısaca açıkla
- Madde madde, düzenli bir özet oluştur
- Türkçe yaz, akademik dil kullan

KURAL: Sadece verilen bağlamdaki bilgileri kullan."""


def generate_answer(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Soru tipini tespit eder, uygun LLM ile cevap üretir.
    """
    if not context_chunks:
        return "Bu konuyla ilgili belgede bilgi bulunamadı. Lütfen farklı bir soru deneyin."

    is_summary = _is_summary_question(question)
    prompt_template = SUMMARY_PROMPT if is_summary else SYSTEM_PROMPT

    if settings.GROQ_API_KEY:
        try:
            return _call_llm_groq(question, context_chunks, prompt_template, is_summary)
        except Exception as e:
            logger.warning(f"Groq hatası: {e}")

    if settings.OPENAI_API_KEY:
        try:
            return _call_llm_openai(question, context_chunks, prompt_template, is_summary)
        except Exception as e:
            logger.warning(f"OpenAI hatası: {e}")

    return _generate_demo(question, context_chunks)


def _is_summary_question(question: str) -> bool:
    """Sorunun özet/genel bilgi isteği olup olmadığını tespit eder."""
    keywords = [
        "özet", "özetle", "özetler", "özetleyebilir",
        "ne hakkında", "hakkında bilgi", "anlat", "açıkla",
        "neler var", "neler anlatıyor", "konular neler",
        "genel", "genel bilgi", "tüm", "hepsini",
        "summary", "summarize", "what is this about"
    ]
    q_lower = question.lower()
    return any(kw in q_lower for kw in keywords)


def _build_context(chunks: List[Dict[str, Any]], is_summary: bool = False) -> str:
    """Chunk'ları okunabilir bağlam metnine dönüştürür."""
    parts = []
    seen_texts = set()

    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata", {})
        page = meta.get("page_number", "?")
        text = chunk["text"].strip()

        # Tekrar eden chunk'ları atla
        text_key = text[:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        if is_summary:
            parts.append(f"[Sayfa {page}]\n{text}")
        else:
            score = chunk.get("score", 0)
            parts.append(f"--- Kaynak {i} (Sayfa {page} | Eşleşme: %{int(score*100)}) ---\n{text}")

    return "\n\n".join(parts)


def _call_llm_groq(
    question: str,
    chunks: List[Dict[str, Any]],
    system_prompt: str,
    is_summary: bool,
) -> str:
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    context = _build_context(chunks, is_summary)

    if is_summary:
        user_msg = f"Aşağıdaki belge içeriğini özetle:\n\n{context}\n\nKapsamlı bir özet yaz:"
    else:
        user_msg = (
            f"BAĞLAM:\n{context}\n\n"
            f"SORU: {question}\n\n"
            f"Yukarıdaki bağlama dayanarak soruyu yanıtla:"
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        max_tokens=2000,
        temperature=0.3,
    )

    answer = response.choices[0].message.content.strip()
    logger.info(f"Groq yanıtı: {len(answer)} karakter")
    return answer


def _call_llm_openai(
    question: str,
    chunks: List[Dict[str, Any]],
    system_prompt: str,
    is_summary: bool,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    context = _build_context(chunks, is_summary)

    if is_summary:
        user_msg = f"Aşağıdaki belge içeriğini özetle:\n\n{context}\n\nKapsamlı bir özet yaz:"
    else:
        user_msg = f"BAĞLAM:\n{context}\n\nSORNA: {question}\n\nCevapla:"

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        max_tokens=2000,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


def _generate_demo(question: str, chunks: List[Dict[str, Any]]) -> str:
    meta = chunks[0].get("metadata", {}) if chunks else {}
    preview = chunks[0]["text"][:500] if chunks else ""
    return (
        f"⚠️ Demo Modu — LLM yapılandırılmamış.\n\n"
        f"{len(chunks)} kaynak bölümü bulundu.\n\n"
        f"En alakalı bölüm (Sayfa {meta.get('page_number','?')}):\n"
        f"«{preview}»\n\n"
        f"Gerçek cevap için .env dosyasına GROQ_API_KEY ekleyin (ücretsiz)."
    )
