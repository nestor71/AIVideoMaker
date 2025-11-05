"""
Modulo AI per generazione metadati SEO YouTube
Generazione automatica di: Titolo, Descrizione, Hashtag, Tag

INTEGRAZIONE OPENAI:
Per usare la generazione AI reale, configura la variabile d'ambiente OPENAI_API_KEY
Se non configurata, usa stub simulato per testing
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Configurazione OpenAI (se disponibile)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_REAL_AI = bool(OPENAI_API_KEY)

if USE_REAL_AI:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI configurato - Generazione AI REALE attiva")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI non disponibile: {e} - Uso stub simulato")
        USE_REAL_AI = False
else:
    logger.info("ℹ️ OPENAI_API_KEY non trovata - Uso stub simulato per testing")


def generate_metadata_from_transcription(
    video_filename: str,
    transcription_text: str,
    video_duration: Optional[float] = None,
    num_hashtags: int = 5,
    num_tags: int = 12
) -> Dict[str, any]:
    """
    Genera metadati SEO YouTube da trascrizione video

    Args:
        video_filename: Nome del file video
        transcription_text: Testo trascritto dal video
        video_duration: Durata video in secondi (opzionale)
        num_hashtags: Numero di hashtag da generare (1-20)
        num_tags: Numero di tag da generare (1-20)

    Returns:
        Dict con: title, description, hashtags (list), tags (list)
    """

    if USE_REAL_AI:
        return _generate_with_openai(
            video_filename, transcription_text, video_duration,
            num_hashtags, num_tags
        )
    else:
        return _generate_stub(
            video_filename, transcription_text, video_duration,
            num_hashtags, num_tags
        )


def _generate_with_openai(
    video_filename: str,
    transcription_text: str,
    video_duration: Optional[float],
    num_hashtags: int,
    num_tags: int
) -> Dict[str, any]:
    """
    🔴 INTEGRAZIONE OPENAI REALE
    Genera metadati SEO usando GPT-4
    """

    try:
        # Prepara prompt ottimizzato per SEO YouTube
        duration_info = f"Durata video: {int(video_duration)} secondi\n" if video_duration else ""

        prompt = f"""Sei un esperto SEO YouTube. Analizza questa trascrizione video e genera metadati ottimizzati per massimizzare visualizzazioni e CTR.

TRASCRIZIONE VIDEO:
{transcription_text[:3000]}  # Limita a 3000 caratteri per evitare token limit

{duration_info}
Nome file: {video_filename}

GENERA (rispondi SOLO con JSON valido):
{{
  "title": "Titolo SEO 45-70 caratteri, accattivante, con keyword principale",
  "description": "Descrizione 2-3 paragrafi. Prima riga con keyword + CTA. Poi dettagli contenuto. Poi timestamp se possibile.",
  "hashtags": ["{num_hashtags} hashtag rilevanti, formato #parola"],
  "tags": ["{num_tags} tag separati, mix keyword principali e long-tail"]
}}

REGOLE SEO:
- Titolo: max 70 caratteri, keyword all'inizio, emotivamente coinvolgente
- Descrizione: keyword nei primi 150 caratteri, CTA chiara, formattazione leggibile
- Hashtag: no keyword stuffing, max 3-5 rilevanti, trending quando possibile
- Tag: mix keyword generiche + specifiche, sinonimi, varianti

Rispondi SOLO con il JSON, niente altro."""

        # Chiamata GPT-4
        logger.info("📡 Chiamata OpenAI GPT-4 per generazione metadati...")

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # o "gpt-4" se hai accesso
            messages=[
                {"role": "system", "content": "Sei un esperto SEO YouTube. Rispondi sempre in JSON valido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Creatività moderata
            max_tokens=1000,
            response_format={"type": "json_object"}  # Forza risposta JSON
        )

        # Parse risposta
        result = json.loads(response.choices[0].message.content)

        logger.info("✅ Metadati generati con OpenAI")
        logger.debug(f"Risultato: {result}")

        # Valida e normalizza
        return _validate_and_normalize_metadata(result, num_hashtags, num_tags)

    except Exception as e:
        logger.error(f"❌ Errore generazione OpenAI: {e}")
        logger.warning("⚠️ Fallback a stub simulato")
        return _generate_stub(video_filename, transcription_text, video_duration, num_hashtags, num_tags)


def _generate_stub(
    video_filename: str,
    transcription_text: str,
    video_duration: Optional[float],
    num_hashtags: int,
    num_tags: int
) -> Dict[str, any]:
    """
    🟡 STUB SIMULATO per testing
    Genera metadati intelligenti ma senza AI reale
    """

    logger.info("🧪 Generazione metadati con STUB (no AI reale)")

    # Estrai parole chiave dalla trascrizione (semplice analisi frequenza)
    words = transcription_text.lower().split()
    # Rimuovi parole comuni italiane
    stopwords = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'e', 'o', 'di', 'da', 'a', 'in', 'per', 'con', 'su', 'del', 'della', 'dei', 'delle', 'che', 'non', 'è', 'sono', 'questo', 'questa', 'come', 'anche', 'molto', 'più', 'tutto', 'tutti'}
    keywords = [w for w in words if len(w) > 4 and w not in stopwords]

    # Conta frequenze (semplice)
    from collections import Counter
    word_freq = Counter(keywords)
    top_keywords = [word for word, count in word_freq.most_common(15)]

    # Keyword principale (più frequente o dal nome file)
    main_keyword = top_keywords[0] if top_keywords else video_filename.replace('_', ' ').replace('-', ' ')

    # Genera titolo
    duration_minutes = int(video_duration / 60) if video_duration else "?"
    title = f"Come {main_keyword.capitalize()} in {duration_minutes} Minuti | Guida Completa 2024"
    if len(title) > 70:
        title = f"{main_keyword.capitalize()} - Guida Completa 2024"

    # Genera descrizione
    preview_text = transcription_text[:200].strip() + "..." if len(transcription_text) > 200 else transcription_text
    description = f"""🎯 {main_keyword.upper()} - Tutto quello che devi sapere!

{preview_text}

📌 In questo video scoprirai:
✅ I concetti fondamentali di {main_keyword}
✅ Tecniche e strategie pratiche
✅ Consigli ed esempi reali

⏱️ TIMESTAMP:
00:00 - Introduzione
00:30 - Spiegazione {main_keyword}
{duration_minutes-1 if duration_minutes != '?' else '05'}:00 - Conclusioni

👍 Se il video ti è piaciuto, lascia un LIKE e ISCRIVITI al canale!
🔔 Attiva la campanella per non perdere i prossimi video!

💬 Hai domande? Lascia un commento qui sotto!

#tutorial #guida #italiano"""

    # Genera hashtag
    hashtags = []
    if top_keywords:
        for kw in top_keywords[:num_hashtags-2]:
            hashtag = f"#{kw.replace(' ', '')}"
            hashtags.append(hashtag)
    hashtags.append("#tutorial")
    hashtags.append("#italiano")
    hashtags = hashtags[:num_hashtags]

    # Genera tag
    tags = []
    if top_keywords:
        tags.extend(top_keywords[:num_tags-5])
    tags.extend([
        "tutorial italiano",
        "guida completa",
        "come fare",
        "spiegazione",
        "italiano"
    ])
    tags = tags[:num_tags]

    result = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags
    }

    logger.info(f"✅ Stub generato: {len(hashtags)} hashtag, {len(tags)} tag")
    return result


def generate_metadata_from_filename(
    video_filename: str,
    video_duration: Optional[float] = None,
    num_hashtags: int = 5,
    num_tags: int = 12
) -> Dict[str, any]:
    """
    Genera metadati SEO solo dal nome file (quando non c'è trascrizione)
    Utile per video senza audio o quando la trascrizione non è disponibile
    """

    logger.info(f"⚠️ Generazione metadati solo da filename: {video_filename}")

    # Pulisci nome file per estrarre parole chiave
    name_clean = Path(video_filename).stem
    name_clean = name_clean.replace('_', ' ').replace('-', ' ')
    keywords = [w for w in name_clean.split() if len(w) > 2]

    # Usa trascrizione vuota per lo stub
    fake_transcription = ' '.join(keywords) * 10  # Ripeti per dare peso

    return _generate_stub(
        video_filename, fake_transcription, video_duration,
        num_hashtags, num_tags
    )


def _validate_and_normalize_metadata(
    metadata: Dict,
    num_hashtags: int,
    num_tags: int
) -> Dict[str, any]:
    """
    Valida e normalizza metadati generati da AI
    """

    # Limita titolo a 100 caratteri (limite YouTube)
    if len(metadata.get('title', '')) > 100:
        metadata['title'] = metadata['title'][:97] + "..."

    # Limita descrizione a 5000 caratteri (limite YouTube)
    if len(metadata.get('description', '')) > 5000:
        metadata['description'] = metadata['description'][:4997] + "..."

    # Normalizza hashtag
    hashtags = metadata.get('hashtags', [])
    hashtags = [h if h.startswith('#') else f"#{h}" for h in hashtags]
    hashtags = [h.replace(' ', '') for h in hashtags]  # Rimuovi spazi
    metadata['hashtags'] = hashtags[:num_hashtags]

    # Normalizza tag
    tags = metadata.get('tags', [])
    tags = [t.strip() for t in tags]
    tags = list(dict.fromkeys(tags))  # Rimuovi duplicati mantenendo ordine
    metadata['tags'] = tags[:num_tags]

    return metadata


def merge_user_customizations(
    metadata: Dict,
    title_addon: Optional[str] = None,
    title_addon_position: str = "end",  # "start" o "end"
    description_addon: Optional[str] = None,
    description_addon_position: str = "end",
    fixed_hashtags: Optional[List[str]] = None,
    fixed_tags: Optional[List[str]] = None,
    max_hashtags: int = 5,
    max_tags: int = 12
) -> Dict[str, any]:
    """
    Applica personalizzazioni utente ai metadati generati da AI

    Args:
        metadata: Metadati generati da AI
        title_addon: Testo da concatenare al titolo
        title_addon_position: "start" o "end"
        description_addon: Testo da concatenare alla descrizione
        description_addon_position: "start" o "end"
        fixed_hashtags: Hashtag fissi da includere sempre
        fixed_tags: Tag fissi da includere sempre
        max_hashtags: Limite massimo hashtag
        max_tags: Limite massimo tag

    Returns:
        Metadati personalizzati
    """

    result = metadata.copy()

    # Concatena titolo
    if title_addon:
        original_title = result.get('title', '')
        if title_addon_position == "start":
            result['title'] = f"{title_addon} {original_title}"
        else:
            result['title'] = f"{original_title} {title_addon}"

        # Tronca se troppo lungo
        if len(result['title']) > 100:
            result['title'] = result['title'][:97] + "..."

    # Concatena descrizione
    if description_addon:
        original_desc = result.get('description', '')
        if description_addon_position == "start":
            result['description'] = f"{description_addon}\n\n{original_desc}"
        else:
            result['description'] = f"{original_desc}\n\n{description_addon}"

        # Tronca se troppo lungo
        if len(result['description']) > 5000:
            result['description'] = result['description'][:4997] + "..."

    # Merge hashtag fissi + AI
    if fixed_hashtags:
        fixed_clean = [h if h.startswith('#') else f"#{h}" for h in fixed_hashtags]
        fixed_clean = [h.replace(' ', '') for h in fixed_clean]

        ai_hashtags = result.get('hashtags', [])

        # Priorità ai fissi, completa con AI fino al limite
        merged_hashtags = fixed_clean.copy()
        for h in ai_hashtags:
            if h not in merged_hashtags and len(merged_hashtags) < max_hashtags:
                merged_hashtags.append(h)

        result['hashtags'] = merged_hashtags[:max_hashtags]

    # Merge tag fissi + AI
    if fixed_tags:
        fixed_clean = [t.strip() for t in fixed_tags]
        ai_tags = result.get('tags', [])

        # Priorità ai fissi, completa con AI fino al limite
        merged_tags = fixed_clean.copy()
        for t in ai_tags:
            if t not in merged_tags and len(merged_tags) < max_tags:
                merged_tags.append(t)

        result['tags'] = merged_tags[:max_tags]

    logger.info(f"✅ Personalizzazioni applicate: {len(result['hashtags'])} hashtag, {len(result['tags'])} tag")

    return result


# Utility per formattare output finale
def format_metadata_for_youtube(metadata: Dict) -> str:
    """
    Formatta metadati in testo pronto per copia/incolla su YouTube
    """

    output = []
    output.append("=" * 60)
    output.append("📹 METADATI YOUTUBE - COPIA/INCOLLA")
    output.append("=" * 60)
    output.append("")

    output.append("🎯 TITOLO:")
    output.append(metadata.get('title', ''))
    output.append("")

    output.append("📝 DESCRIZIONE:")
    output.append(metadata.get('description', ''))
    output.append("")

    output.append("# HASHTAG:")
    output.append(' '.join(metadata.get('hashtags', [])))
    output.append("")

    output.append("🏷️ TAG (separa con virgola su YouTube):")
    output.append(', '.join(metadata.get('tags', [])))
    output.append("")

    output.append("=" * 60)

    return '\n'.join(output)
