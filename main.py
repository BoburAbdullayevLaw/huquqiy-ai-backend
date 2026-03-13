# ============================================================
# MAIN.PY - HUQUQIY AI ASOSIY BACKEND (JK MODDALARI UCHUN)
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import sys
import os
import logging
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from config import API_PORT, OPENROUTER_API_KEY, OPENROUTER_URL, MODEL_ID
# Eski Google API kodlari bilan moslik uchun
from ai_service import AIService

# documents papkasidan import
try:
    from documents.organ import ORGAN_HUJJATLARI

    logger.info(f"✅ Organ hujjatlari yuklandi: {len(ORGAN_HUJJATLARI)} ta")
except Exception as e:
    logger.error(f"❌ Organ hujjatlarini yuklashda xato: {e}")
    ORGAN_HUJJATLARI = {}

try:
    from documents.fuqaro import FUQARO_HUJJATLARI

    logger.info(f"✅ Fuqaro hujjatlari yuklandi: {len(FUQARO_HUJJATLARI)} ta")
except Exception as e:
    logger.error(f"❌ Fuqaro hujjatlarini yuklashda xato: {e}")
    FUQARO_HUJJATLARI = {}

app = FastAPI(
    title="Huquqiy AI",
    description="O'zbekiston Respublikasi qonunchiligi asosida huquqiy yordam beruvchi AI tizimi",
    version="3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS sozlamalari - barcha frontend ilovalar uchun ochiq
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI xizmatini yaratish
ai = AIService()

# ============================================================
# JINOYAT KODEKSI JSONL MA'LUMOTLARINI YUKLASH
# ============================================================

JINOYAT_JSONL_PATH = Path(__file__).parent / "documents" / "chatbot" / "jinoyat.jsonl"


def load_jinoyat_jsonl():
    """jinoyat.jsonl faylidan JK moddalari ma'lumotlarini yuklash"""
    data = []
    try:
        if JINOYAT_JSONL_PATH.exists():
            with open(JINOYAT_JSONL_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            # JK moddasi uchun "modda" maydoni bo'lishi kerak
                            if "modda" in item:
                                data.append(item)
                            else:
                                logger.warning(f"JSONL {line_num}-qator: 'modda' maydoni yo'q")
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSONL {line_num}-qator: JSON parse xatosi - {e}")
                            continue
            logger.info(f"✅ jinoyat.jsonl dan {len(data)} ta JK moddasi yuklandi")

            # Moddalarni modda raqami bo'yicha tartiblash
            data.sort(key=lambda x: int(x.get('modda', 0)) if str(x.get('modda', '')).isdigit() else 0)
        else:
            logger.warning(f"⚠️ jinoyat.jsonl fayli topilmadi: {JINOYAT_JSONL_PATH}")
            # Test ma'lumotlarini yaratish (96-97-moddalar)
            data = [
                {
                    "modda": "96",
                    "nomi": "Jazo bilan birga tayinlanadigan tibbiy yo‘sindagi majburlov choralarini qo‘llash",
                    "dispozitsiya": "Alkogolizmga, giyohvandlikka yoki zaharvandlikka yo‘liqqan yoxud aqli rasolikni istisno etmaydigan tarzda ruhiy holati buzilgan shaxslar tomonidan jinoyat sodir etilgan taqdirda, agar tibbiy xulosa mavjud bo‘lsa, sud jazo bilan birga tibbiy majburlov choralarini tayinlashi mumkin.",
                    "sanksiya_1": "",
                    "sanksiya_2": "",
                    "kvalifikatsiya": "Yo'q",
                    "farqlash": "96-modda (jazo bilan birga) vs JK 91(2) va 93,94",
                    "yuridik_nyuanslar": "Sud-narkologiya ekspertizasi talab qilinadi.",
                    "sud_amaliyoti": ""
                },
                {
                    "modda": "97",
                    "nomi": "Qasddan odam o‘ldirish",
                    "dispozitsiya": "O‘zga shaxsni huquqqa xilof ravishda, qasddan (to'g'ri yoki egri qasd) hayotdan mahrum qilish.",
                    "sanksiya_1": "10-15 yil ozodlikdan mahrum qilish.",
                    "sanksiya_2": "15-25 yil yoki umrbod ozodlikdan mahrum qilish.",
                    "kvalifikatsiya": "a) 2+ shaxs; b) homilador ayol; v) ojiz ahvoldagi shaxs; g) xizmat/fuqarolik burchini bajarishi munosabati bilan; d) xavfli usulda; ye) ommaviy tartibsizlikda; j) o‘ta shafqatsizlik bilan; z) nomusga tegish/g'ayritabiiy jinsiy ehtiyoj qondirish bilan bog‘liq holda; i) tamagirlik niyatida; k) milliy/irqiy adovat; l) bezorilik; m) diniy taassub; n) organ/to‘qima olish maqsadida; o) boshqa jinoyatni yashirish/osonlashtirish; p) guruh/uyushgan guruh; r) takroran/xavfli retsidivist; s) o‘ta xavfli retsidivist.",
                    "farqlash": "97 (1-qism) vs 97 (2-qism): 1-qism istisno qilish usuli bilan belgilanadi. 97 vs 104 (3-qism d): 97-moddada qasd o'limga qaratilgan bo'ladi.",
                    "yuridik_nyuanslar": "Subyekt yoshi — 14 yosh. Sababiy bog'lanish — harakat va jismoniy (biologik) o'lim o'rtasida qat'iy bo'lishi shart.",
                    "sud_amaliyoti": "Turli vaqtlarda 2 va undan ortiq odam o'ldirilsa va u yagona qasd bilan qamrab olinmasa, ikki shaxsni o'ldirish emas, balki takroran (97 r) etib belgilanadi."
                }
            ]
            logger.info(f"✅ Test ma'lumotlari yaratildi: {len(data)} ta")
    except Exception as e:
        logger.error(f"❌ JSONL yuklashda xato: {e}")
        data = []

    return data


# JSONL ma'lumotlarini yuklash
jinoyat_jsonl_data = load_jinoyat_jsonl()


# ============================================================
# MODELLAR
# ============================================================

class ChatRequest(BaseModel):
    """Chat so'rovi modeli"""
    question: str
    doc_kod: str
    form_data: Dict[str, Any] = {}
    history: List[Dict[str, str]] = []
    tur: str = "organ"


class JinoyatChatRequest(BaseModel):
    """Jinoyat huquqi chat so'rovi modeli"""
    question: str
    history: List[Dict[str, str]] = []


class HealthResponse(BaseModel):
    """Tizim holati javobi"""
    status: str
    organ: int
    fuqaro: int
    jami: int
    jinoyat_jsonl: int
    model: str
    api_key_configured: bool
    version: str


# ============================================================
# ROOT ENDPOINTLAR
# ============================================================

@app.get("/")
def root():
    """Asosiy endpoint - API haqida ma'lumot"""
    return {
        "status": "ok",
        "message": "Huquqiy AI API",
        "version": "3.0",
        "model": MODEL_ID,
        "api_key_configured": bool(OPENROUTER_API_KEY),
        "endpoints": [
            "/health",
            "/organ/hujjatlar",
            "/fuqaro/hujjatlar",
            "/hujjat/{doc_kod}",
            "/chat",
            "/chat/jinoyat",
            "/jinoyat/moddalar",
            "/jinoyat/qidirish",
            "/statistika",
            "/qidirish",
            "/test/gemini"
        ],
        "total_documents": len(ORGAN_HUJJATLARI) + len(FUQARO_HUJJATLARI),
        "jinoyat_jsonl_count": len(jinoyat_jsonl_data)
    }


@app.get("/health", response_model=HealthResponse)
def health():
    """Tizim holatini tekshirish"""
    organ_soni = len(ORGAN_HUJJATLARI)
    fuqaro_soni = len(FUQARO_HUJJATLARI)

    # API kalit mavjudligini tekshirish
    api_key_configured = bool(OPENROUTER_API_KEY)

    return {
        "status": "ok",
        "organ": organ_soni,
        "fuqaro": fuqaro_soni,
        "jami": organ_soni + fuqaro_soni,
        "jinoyat_jsonl": len(jinoyat_jsonl_data),
        "model": MODEL_ID,
        "api_key_configured": api_key_configured,
        "version": "3.0"
    }


# ============================================================
# ORGAN ENDPOINTLARI
# ============================================================

@app.get("/organ/hujjatlar")
def get_organ_hujjatlar():
    """Barcha organ hujjatlarini qaytaradi"""
    logger.info(f"Organ hujjatlari so'raldi: {len(ORGAN_HUJJATLARI)} ta")
    return {
        "count": len(ORGAN_HUJJATLARI),
        "documents": ORGAN_HUJJATLARI
    }


@app.get("/organ/kodlar")
def get_organ_kodlar():
    """Organ hujjat kodlarini qaytaradi"""
    kodlar = list(ORGAN_HUJJATLARI.keys())
    return {
        "count": len(kodlar),
        "codes": kodlar
    }


@app.get("/organ/tayyor")
def get_organ_tayyor():
    """Tayyor bo'lgan organ hujjatlarini qaytaradi (JQ- va JR- prefiksli)"""
    result = {}
    for kod, doc in ORGAN_HUJJATLARI.items():
        if kod.startswith(("JQ-", "JR-")):
            result[kod] = doc
    return {
        "count": len(result),
        "documents": result
    }


# ============================================================
# FUQARO ENDPOINTLARI
# ============================================================

@app.get("/fuqaro/hujjatlar")
def get_fuqaro_hujjatlar():
    """Barcha fuqaro hujjatlarini qaytaradi"""
    logger.info(f"Fuqaro hujjatlari so'raldi: {len(FUQARO_HUJJATLARI)} ta")
    return {
        "count": len(FUQARO_HUJJATLARI),
        "documents": FUQARO_HUJJATLARI
    }


@app.get("/fuqaro/mehnat")
def get_fuqaro_mehnat():
    """Mehnat nizolari bo'limidagi hujjatlarni qaytaradi (FQ-MN prefiksli)"""
    result = {}
    for kod, doc in FUQARO_HUJJATLARI.items():
        if kod.startswith("FQ-MN"):
            result[kod] = doc

    return {
        "count": len(result),
        "title": "Mehnat nizolari",
        "documents": result
    }


@app.get("/fuqaro/uyjoy")
def get_fuqaro_uyjoy():
    """Uy-joy nizolari bo'limidagi hujjatlarni qaytaradi (FQ-UJ prefiksli)"""
    result = {}
    for kod, doc in FUQARO_HUJJATLARI.items():
        if kod.startswith("FQ-UJ"):
            result[kod] = doc

    return {
        "count": len(result),
        "title": "Uy-joy nizolari",
        "documents": result
    }


@app.get("/fuqaro/kodlar")
def get_fuqaro_kodlar():
    """Barcha fuqaro hujjat kodlarini qaytaradi"""
    kodlar = list(FUQARO_HUJJATLARI.keys())
    return {
        "count": len(kodlar),
        "codes": kodlar
    }


# ============================================================
# HUJJAT ENDPOINTLARI (UMUMIY)
# ============================================================

@app.get("/hujjat/{doc_kod}")
def get_hujjat(doc_kod: str, tur: Optional[str] = None):
    """
    Hujjat ma'lumotlarini olish

    - `doc_kod`: Hujjat kodi (masalan: JQ-A, FQ-MN-001)
    - `tur`: (ixtiyoriy) 'organ' yoki 'fuqaro'
    """
    logger.info(f"Hujjat so'raldi: {doc_kod}, tur: {tur}")

    doc = None
    detected_tur = tur

    if tur == "organ":
        doc = ORGAN_HUJJATLARI.get(doc_kod)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Organ hujjati topilmadi: {doc_kod}")

    elif tur == "fuqaro":
        doc = FUQARO_HUJJATLARI.get(doc_kod)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Fuqaro hujjati topilmadi: {doc_kod}")

    else:
        if doc_kod.startswith(("JQ-", "JR-")):
            doc = ORGAN_HUJJATLARI.get(doc_kod)
            detected_tur = "organ"
        elif doc_kod.startswith("FQ-"):
            doc = FUQARO_HUJJATLARI.get(doc_kod)
            detected_tur = "fuqaro"
        else:
            doc = ORGAN_HUJJATLARI.get(doc_kod)
            if doc:
                detected_tur = "organ"
            else:
                doc = FUQARO_HUJJATLARI.get(doc_kod)
                if doc:
                    detected_tur = "fuqaro"

    if not doc:
        raise HTTPException(status_code=404, detail=f"Hujjat topilmadi: {doc_kod}")

    result = dict(doc)
    result["_tur"] = detected_tur
    result["kod"] = doc_kod

    return result


@app.get("/hujjat")
def get_hujjat_with_params(doc_kod: str, tur: str = "organ"):
    """Hujjat ma'lumotlarini olish (tur ko'rsatilgan holda)"""
    return get_hujjat(doc_kod, tur)


# ============================================================
# JINOYAT KODEKSI ENDPOINTLARI
# ============================================================

@app.get("/jinoyat/moddalar")
def get_jinoyat_moddalar():
    """Barcha JK moddalari ro'yxatini qaytaradi"""
    moddalar = []
    for item in jinoyat_jsonl_data:
        moddalar.append({
            "modda": item.get("modda", ""),
            "nomi": item.get("nomi", ""),
            "qisqacha": item.get("dispozitsiya", "")[:100] + "..." if len(
                item.get("dispozitsiya", "")) > 100 else item.get("dispozitsiya", "")
        })

    return {
        "count": len(moddalar),
        "moddalar": moddalar
    }


@app.get("/jinoyat/moddasi/{modda_raqami}")
def get_jinoyat_moddasi(modda_raqami: str):
    """Berilgan modda raqami bo'yicha JK moddasini qaytaradi"""
    for item in jinoyat_jsonl_data:
        if item.get("modda") == modda_raqami:
            return item

    raise HTTPException(status_code=404, detail=f"{modda_raqami}-modda topilmadi")


@app.get("/jinoyat/qidirish")
def search_jinoyat_moddalari(q: str):
    """JK moddalaridan qidirish"""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Qidiruv so'zi kamida 2 ta belgidan iborat bo'lishi kerak")

    q = q.lower()
    results = []

    for item in jinoyat_jsonl_data:
        modda = item.get("modda", "")
        nomi = item.get("nomi", "").lower()
        dispozitsiya = item.get("dispozitsiya", "").lower()
        kvalifikatsiya = item.get("kvalifikatsiya", "").lower()
        farqlash = item.get("farqlash", "").lower()

        if (q in modda or
                q in nomi or
                q in dispozitsiya or
                q in kvalifikatsiya or
                q in farqlash):
            results.append({
                "modda": item.get("modda"),
                "nomi": item.get("nomi"),
                "relevance": calculate_relevance_jk(q, nomi + " " + dispozitsiya)
            })

    # Relevance bo'yicha tartiblash
    results.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": q,
        "count": len(results),
        "results": results[:20]  # Faqat eng mos 20 tasi
    }


@app.post("/chat/jinoyat/jsonl")
async def chat_jinoyat_jsonl(req: JinoyatChatRequest):
    """
    Jinoyat kodeksi moddalari asosida javob berish
    """
    question = req.question.lower().strip()
    logger.info(f"JSONL chat so'rovi: {question[:50]}...")

    # Qidiruv uchun kalit so'zlar
    keywords = []
    for word in question.split():
        if len(word) > 2 and word.isdigit() == False:
            keywords.append(word)

    # Modda raqamini qidirish (masalan: "97-modda", "97")
    modda_match = re.search(r'(\d+)(?:-modda)?', question)
    modda_raqami = modda_match.group(1) if modda_match else None

    best_match = None
    best_score = 0

    for item in jinoyat_jsonl_data:
        score = 0
        modda = item.get("modda", "")
        nomi = item.get("nomi", "").lower()
        dispozitsiya = item.get("dispozitsiya", "").lower()
        kvalifikatsiya = item.get("kvalifikatsiya", "").lower()
        farqlash = item.get("farqlash", "").lower()
        yuridik_nyuanslar = item.get("yuridik_nyuanslar", "").lower()

        # Modda raqami bo'yicha
        if modda_raqami and modda == modda_raqami:
            score += 50

        # Kalit so'zlar bo'yicha
        for keyword in keywords:
            if keyword in nomi:
                score += 10
            if keyword in dispozitsiya:
                score += 5
            if keyword in kvalifikatsiya:
                score += 3
            if keyword in farqlash:
                score += 2
            if keyword in yuridik_nyuanslar:
                score += 1

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score > 5:
        # Javobni tayyorlash
        javob = f"**{best_match.get('modda')}-modda. {best_match.get('nomi')}**\n\n"
        javob += f"{best_match.get('dispozitsiya', '')}\n\n"

        if best_match.get('sanksiya_1'):
            javob += f"1-qism: {best_match.get('sanksiya_1')}\n"
        if best_match.get('sanksiya_2'):
            javob += f"2-qism: {best_match.get('sanksiya_2')}\n"

        if best_match.get('kvalifikatsiya') and best_match.get('kvalifikatsiya') != "Yo'q":
            javob += f"\n**Kvalifikatsiya:** {best_match.get('kvalifikatsiya')}\n"

        if best_match.get('farqlash'):
            javob += f"\n**Farqlash:** {best_match.get('farqlash')}\n"

        if best_match.get('yuridik_nyuanslar'):
            javob += f"\n**Yuridik nyuanslar:** {best_match.get('yuridik_nyuanslar')}\n"

        if best_match.get('sud_amaliyoti'):
            javob += f"\n**Sud amaliyoti:** {best_match.get('sud_amaliyoti')}\n"

        return {
            "javob": javob,
            "manba": "jinoyat_kodeksi",
            "modda": best_match.get('modda'),
            "aniqlik": best_score
        }

    return {
        "javob": None,
        "manba": "none",
        "aniqlik": 0
    }


# ============================================================
# STATISTIKA ENDPOINTI
# ============================================================

@app.get("/statistika")
def get_statistika():
    """Batafsil statistika"""
    organ_soni = len(ORGAN_HUJJATLARI)
    fuqaro_soni = len(FUQARO_HUJJATLARI)

    mehnat_soni = sum(1 for kod in FUQARO_HUJJATLARI if kod.startswith("FQ-MN"))
    uyjoy_soni = sum(1 for kod in FUQARO_HUJJATLARI if kod.startswith("FQ-UJ"))
    organ_tayyor = sum(1 for kod in ORGAN_HUJJATLARI if kod.startswith(("JQ-", "JR-")))
    api_key_configured = bool(OPENROUTER_API_KEY)

    return {
        "organ": {
            "jami": organ_soni,
            "tayyor": organ_tayyor,
            "tez_kunda": organ_soni - organ_tayyor,
            "foiz": round((organ_tayyor / organ_soni) * 100, 1) if organ_soni else 0
        },
        "fuqaro": {
            "jami": fuqaro_soni,
            "mehnat": mehnat_soni,
            "uyjoy": uyjoy_soni,
            "tayyor": fuqaro_soni,
            "tez_kunda": 0,
            "foiz": 100
        },
        "jinoyat_kodeksi": {
            "jami": len(jinoyat_jsonl_data),
            "tayyor": len(jinoyat_jsonl_data),
            "foiz": 100
        },
        "jami": organ_soni + fuqaro_soni + len(jinoyat_jsonl_data),
        "model": MODEL_ID,
        "api_key_configured": api_key_configured,
        "version": "3.0"
    }


# ============================================================
# QIDIRUV ENDPOINTI
# ============================================================

@app.get("/qidirish")
def search_hujjatlar(q: str, tur: Optional[str] = None):
    """Barcha hujjatlardan qidirish"""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Qidiruv so'zi kamida 2 ta belgidan iborat bo'lishi kerak")

    q = q.lower()
    results = {}

    # Jinoyat kodeksidan qidirish
    if not tur or tur == "jinoyat":
        for item in jinoyat_jsonl_data:
            modda = item.get("modda", "")
            nomi = item.get("nomi", "").lower()
            dispozitsiya = item.get("dispozitsiya", "").lower()
            if q in modda or q in nomi or q in dispozitsiya:
                results[f"jk_{modda}"] = {
                    "nomi": item.get("nomi", ""),
                    "modda": item.get("modda", ""),
                    "qisqacha": item.get("dispozitsiya", "")[:150],
                    "_tur": "jinoyat_kodeksi",
                    "_relevance": calculate_relevance(q, modda + " " + nomi + " " + dispozitsiya)
                }

    # Organ hujjatlaridan qidirish
    if not tur or tur == "organ":
        for kod, doc in ORGAN_HUJJATLARI.items():
            nomi = doc.get("nomi", "").lower()
            jpk = doc.get("jpk", "").lower()
            if q in nomi or q in jpk or q in kod.lower():
                results[kod] = {
                    **doc,
                    "_tur": "organ",
                    "_relevance": calculate_relevance(q, nomi + " " + jpk)
                }

    # Fuqaro hujjatlaridan qidirish
    if not tur or tur == "fuqaro":
        for kod, doc in FUQARO_HUJJATLARI.items():
            nomi = doc.get("nomi", "").lower()
            jpk = doc.get("jpk", "").lower()
            if q in nomi or q in jpk or q in kod.lower():
                results[kod] = {
                    **doc,
                    "_tur": "fuqaro",
                    "_relevance": calculate_relevance(q, nomi + " " + jpk)
                }

    sorted_results = dict(sorted(
        results.items(),
        key=lambda x: x[1].get("_relevance", 0),
        reverse=True
    ))

    return {
        "query": q,
        "count": len(sorted_results),
        "results": sorted_results
    }


def calculate_relevance(query: str, text: str) -> int:
    """Qidiruv so'zining relevance ballini hisoblash"""
    count = text.count(query)
    if text.startswith(query):
        count += 5
    return count


def calculate_relevance_jk(query: str, text: str) -> int:
    """JK moddalari uchun relevance ballini hisoblash"""
    words = query.split()
    score = 0
    for word in words:
        if len(word) > 2:
            if word in text:
                score += 10
            if text.startswith(word):
                score += 5
    return score


# ============================================================
# CHAT ENDPOINT - ASOSIY
# ============================================================

@app.post("/chat")
async def chat(req: ChatRequest):
    """AI yordamchi bilan suhbat (hujjat asosida)"""
    logger.info(f"Chat so'rovi: {req.doc_kod}, savol: {req.question[:50]}...")

    if not OPENROUTER_API_KEY:
        return JSONResponse(
            status_code=503,
            content={
                "javob": "⚠️ OpenRouter API kaliti sozlanmagan. config.py faylida OPENROUTER_API_KEY ni tekshiring."
            }
        )

    doc = None
    if req.tur == "organ":
        doc = ORGAN_HUJJATLARI.get(req.doc_kod)
    elif req.tur == "fuqaro":
        doc = FUQARO_HUJJATLARI.get(req.doc_kod)
    else:
        if req.doc_kod.startswith("FQ-"):
            doc = FUQARO_HUJJATLARI.get(req.doc_kod)
            req.tur = "fuqaro"
        else:
            doc = ORGAN_HUJJATLARI.get(req.doc_kod)
            req.tur = "organ"

    if not doc:
        doc = ORGAN_HUJJATLARI.get(req.doc_kod) or FUQARO_HUJJATLARI.get(req.doc_kod)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Hujjat topilmadi: {req.doc_kod}")

    try:
        answer = await ai.ask(
            question=req.question,
            doc_info=doc,
            form_data=req.form_data,
            history=req.history
        )
        return {"javob": answer, "manba": "gemini"}
    except Exception as e:
        logger.error(f"Chat xatosi: {e}")
        return JSONResponse(
            status_code=500,
            content={"javob": f"Kechirasiz, texnik xatolik yuz berdi: {str(e)}"}
        )


# ============================================================
# JINOYAT HUQUQI CHATBOT ENDPOINT
# ============================================================

# jinoyat.txt bir marta o'qib xotiraga olinadi
_JINOYAT_TXT_PATH = Path(__file__).parent / "documents" / "chatbot" / "jinoyat.txt"
try:
    _JK_TEXT = _JINOYAT_TXT_PATH.read_text(encoding="utf-8")
    logger.info(f"✅ jinoyat.txt yuklandi: {len(_JK_TEXT):,} belgi")
except Exception as _e:
    _JK_TEXT = ""
    logger.warning(f"⚠️ jinoyat.txt o'qilmadi: {_e}")


@app.post("/chat/jinoyat")
async def chat_jinoyat(req: JinoyatChatRequest):
    """Jinoyat kodeksi — to'liq matn system prompt ichida, OpenRouter orqali"""
    logger.info(f"Jinoyat chat: {req.question[:60]}...")

    if not OPENROUTER_API_KEY:
        return {"javob": "⚠️ OpenRouter API kaliti sozlanmagan."}

    if not _JK_TEXT:
        return {"javob": "⚠️ jinoyat.txt fayli topilmadi. Backend/documents/chatbot/ papkasini tekshiring."}

    try:
        import httpx

        system_prompt = f"""Siz O'zbekiston Respublikasi Jinoyat kodeksi bo'yicha ekspert yuristsiz.

Quyida O'zbekiston Respublikasi Jinoyat kodeksining BARCHA moddalari (374 ta) keltirilgan.
Faqat shu ma'lumotlarga asoslanib javob bering. O'z bilimingizdan FOYDALANMANG.

====== JINOYAT KODEKSI MA'LUMOTLARI ======
{_JK_TEXT}
==========================================

QOIDALAR:
1. Faqat yuqoridagi moddalarga asoslaning
2. Modda raqami, dispozitsiya, jazo miqdori va kvalifikatsiyani aniq ko'rsating
3. Bir nechta modda tegishli bo'lsa, barchasini ko'rsating
4. Agar savol JK ga tegishli bo'lmasa: "Bu savol JK doirasidan tashqari" deng
5. Agar modda ma'lumotlarda bo'lmasa: "Bu modda bazada yo'q" deng
"""

        # Tarix (history) formati — OpenAI formatida
        messages = [{"role": "system", "content": system_prompt}]
        for msg in req.history[-6:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "model":
                role = "assistant"
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": req.question})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OPENROUTER_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_ID,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 2048,
                }
            )
            resp.raise_for_status()
            data = resp.json()
            javob = data["choices"][0]["message"]["content"]

        return {"javob": javob, "manba": "openrouter"}

    except Exception as e:
        logger.error(f"Jinoyat chat xatosi: {e}")
        return {"javob": f"Texnik xatolik: {str(e)}"}


# ============================================================
# TEST ENDPOINT - API KALITNI TEKSHIRISH
# ============================================================

@app.get("/test/api")
async def test_api():
    """OpenRouter API kalitini tekshirish"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{OPENROUTER_URL}/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            resp.raise_for_status()
        return {
            "status": "success",
            "message": "OpenRouter API to'g'ri sozlangan",
            "model": MODEL_ID,
            "jinoyat_kodeksi_count": len(jinoyat_jsonl_data)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# SERVERNI ISHGA TUSHIRISH
# ============================================================

if __name__ == "__main__":
    organ_soni = len(ORGAN_HUJJATLARI)
    fuqaro_soni = len(FUQARO_HUJJATLARI)
    jinoyat_soni = len(jinoyat_jsonl_data)

    organ_tayyor = sum(1 for kod in ORGAN_HUJJATLARI if kod.startswith(("JQ-", "JR-")))
    mehnat_soni = sum(1 for kod in FUQARO_HUJJATLARI if kod.startswith("FQ-MN"))
    uyjoy_soni = sum(1 for kod in FUQARO_HUJJATLARI if kod.startswith("FQ-UJ"))

    print("\n" + "=" * 80)
    print("🚀 HUQUQIY AI API v3.0 (JK MODDALARI)".center(80))
    print("=" * 80)

    if not OPENROUTER_API_KEY:
        print("⚠️  OPENROUTER_API_KEY sozlanmagan!")
    else:
        print(f"✅ OpenRouter API: Sozlangan")
        print(f"   Model: {MODEL_ID}\n")

    print(f"⚖️  JINOYAT KODEKSI: {jinoyat_soni} ta modda")
    if jinoyat_soni > 0:
        print(f"   ├─ JSONL fayl: {JINOYAT_JSONL_PATH.name}")
        print(f"   └─ Tayyor: {jinoyat_soni} ta modda ✅")
    print()

    print(f"📚 ORGAN HODIMLAR: {organ_soni} ta hujjat")
    print(f"   ├─ Tayyor: {organ_tayyor} ta")
    print(f"   └─ Tez kunda: {organ_soni - organ_tayyor} ta")
    print()

    print(f"👤 FUQAROLAR UCHUN: {fuqaro_soni} ta hujjat")
    if mehnat_soni > 0:
        print(f"   ├─ Mehnat: {mehnat_soni} ta ✅")
    if uyjoy_soni > 0:
        print(f"   ├─ Uy-joy: {uyjoy_soni} ta ✅")

    print()
    print(f"📊 JAMI: {organ_soni + fuqaro_soni + jinoyat_soni} ta ma'lumot")
    print(f"🌐 Server: http://localhost:{API_PORT}")
    print("=" * 80 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=True,
        log_level="info"
    )