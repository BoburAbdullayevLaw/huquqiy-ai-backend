# ============================================================
# AI XIZMATI — OpenRouter orqali (hujjat chatbot uchun)
# ============================================================

from openai import AsyncOpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_URL, MODEL_ID
import logging

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_URL
)


class AIService:
    async def ask(self, question: str, doc_info: dict, form_data: dict, history: list = []) -> str:
        try:
            system = self._build_system(doc_info, form_data)
            messages = [{"role": "system", "content": system}]

            for msg in history[-8:]:
                role = msg.get("role", "")
                if role == "model":
                    role = "assistant"
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg.get("content", "")})

            messages.append({"role": "user", "content": question})

            response = await client.chat.completions.create(
                model=MODEL_ID,
                messages=messages,
                temperature=0.2,
                max_tokens=1800,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"AIService xatosi: {e}")
            return f"Texnik xatolik: {str(e)}"

    def _build_system(self, doc_info: dict, form_data: dict) -> str:
        doc_nomi    = doc_info.get("nomi", "")
        doc_jpk     = doc_info.get("jpk", "")
        doc_shablon = doc_info.get("shablon", "")
        doc_prompt  = doc_info.get("ai_prompt", "")
        forma_str   = "\n".join(f"  {k}: {v}" for k, v in form_data.items() if v)

        maxsus_qoida = doc_prompt if doc_prompt else (
            "- Shablon asosida forma ma'lumotlarini joylashtir\n"
            "- Hujjat matnini *** va *** orasiga ol\n"
            "- Rasmiy, aniq uslubda yoz"
        )

        return f"""Sen O'zbekiston Respublikasi huquq-tartibot organlarida ishlaydigan \
tergovchi va prokurorlar uchun AI yordamchisan.

━━━ ASOSIY QOIDALAR ━━━
1. FAQAT "{doc_nomi}" hujjati bo'yicha javob ber
2. Boshqa mavzu so'ralsa: "Bu bo'lim faqat {doc_nomi} uchun" de
3. Bilmagan narsani YOZMA — "Qo'lda tekshiring" de

━━━ HUJJAT TURI ━━━
{doc_nomi}
JPK asoslari: {doc_jpk}

━━━ FORMA MA'LUMOTLARI ━━━
{forma_str if forma_str else "Hali kiritilmagan"}

━━━ HUJJAT SHABLONI ━━━
{doc_shablon}

━━━ MAXSUS KO'RSATMA ━━━
{maxsus_qoida}"""