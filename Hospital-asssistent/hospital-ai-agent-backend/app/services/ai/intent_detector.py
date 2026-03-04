import json
import re
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, date, timezone

from openai import AsyncOpenAI
from app.core.config import settings


class IntentDetector:

    # =====================================================
    # CLIENT INITIALIZATION
    # =====================================================
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    # =====================================================
    # PUBLIC METHOD (MAIN ENTRY)
    # =====================================================
    @staticmethod
    async def detect(text: str, current_state: dict = None) -> Dict[str, Any]:
        # Agar state nahi hai toh default initialize karein
        if not current_state:
            current_state = {"stage": "START", "last_intent": "general"}

        # context ke saath detect karein
        data = await IntentDetector._detect_all(text, current_state)
        
        print("sandeep_data",data,text)
        
        intent = data.get("intent", "general")

        if intent not in [
            "book_appointment",
            "cancel_booking",
            "confirm_booking",
            "general",
        ]:
            intent = "general"

        # If not booking intent → return early
        if intent != "book_appointment":
            return IntentDetector._empty_response(intent)

        department = None
        date_str = None
        time_str = None

        # Normalize Department
        if data.get("department"):
            department = await IntentDetector._normalize_department(
                data["department"]
            )

        # Resolve Date
        if data.get("date_text"):
            date_str = await IntentDetector._resolve_date(
                data["date_text"]
            )

        # Resolve Time
        if data.get("time_text"):
            time_str = await IntentDetector._resolve_time(
                data["time_text"]
            )

        return IntentDetector._finalize_response(
            intent=intent,
            department=department,
            doctor_name=data.get("doctor_name"),
            date_str=date_str,
            time_str=time_str,
            patient_name=data.get("patient_name"),
            phone_number=data.get("phone_number"),
        )

    # =====================================================
    # SINGLE LLM CALL (Intent + Entities)
    # =====================================================
#     @staticmethod
#     async def _detect_all(text: str) -> Dict[str, Any]:

#         prompt = f"""
# You are a hospital appointment assistant.

# Today's date is: {datetime.now(timezone.utc).date()}

# Return ONLY valid JSON:

# {{
#   "intent": "book_appointment or cancel_booking or confirm_booking or general",
#   "department": "string or null",
#   "doctor_name": "string or null",
#   "date_text": "original date words or null",
#   "time_text": "original time words or null",
#   "patient_name": "string or null",
#   "phone_number": "string or null"
# }}

# Rules:
# - Fix spelling mistakes.
# - Convert Hinglish properly.
# - Extract raw date/time words only.
# - Do NOT normalize date/time here.
# """

#         try:
#             return await IntentDetector._call_llm(prompt, text)
#         except Exception:
#             return {}

    @staticmethod
    async def _detect_all(text: str, current_state: dict) -> Dict[str, Any]:
        stage = current_state.get("stage", "START")
        last_intent = current_state.get("last_intent", "general")

        prompt = f"""
        You are an expert Hospital System Orchestrator.

        [SYSTEM CONTEXT]
        - Current Flow Stage: {stage}
        - Previous Intent: {last_intent}
        - Today's Date: {datetime.now(timezone.utc).date()}

        [CORE RULES]

        1. INTENT DETECTION
        Detect intent as one of:
        - book_appointment
        - cancel_booking
        - confirm_booking
        - general

        2. INTENT PERSISTENCE
        If the conversation is already in appointment booking flow and user answers the asked question, KEEP intent as "book_appointment".

        3. INTENT SWITCHING
        If user clearly cancels or stops booking, set intent to "cancel_booking".

        4. STRICT SELECTIVE EXTRACTION (VERY IMPORTANT)

        Extract ONLY the information that appears in THIS user message.

        If a field is NOT mentioned in the message, return null.

        DO NOT guess.
        DO NOT repeat old values.
        DO NOT fill fields just because they were asked earlier.

        Examples:

        User: "09:30"
        Return:
        {{
        "intent": "book_appointment",
        "department": null,
        "doctor_name": null,
        "date_text": null,
        "time_text": "09:30",
        "patient_name": null,
        "phone_number": null
        }}

        User: "Cardiology"
        Return:
        {{
        "intent": "book_appointment",
        "department": "Cardiology",
        "doctor_name": null,
        "date_text": null,
        "time_text": null,
        "patient_name": null,
        "phone_number": null
        }}

        5. MEDICAL MAPPING

        If user mentions body part or symptom, map it to department.

        Examples:
        heart / dil → Cardiology
        bone / haddi → Orthopedics
        skin → Dermatology
        child → Pediatrics

        Return ONLY valid JSON:

        {{
        "intent": "book_appointment | cancel_booking | confirm_booking | general",
        "department": "string or null",
        "doctor_name": "string or null",
        "date_text": "string or null",
        "time_text": "string or null",
        "patient_name": "string or null",
        "phone_number": "string or null"
        }}
        """
        try:
            return await IntentDetector._call_llm(prompt, text)
        except Exception:
            return {}

    # =====================================================
    # DATE RESOLUTION
    # =====================================================
    @staticmethod
    async def _resolve_date(date_text: str) -> Optional[str]:
        try:
            prompt = f"""
    Today's date is {datetime.now(timezone.utc).date()}.

    Convert the user's date expression into YYYY-MM-DD.

    Examples:
    kal → tomorrow
    parso → day after tomorrow
    today → today

    Return JSON:
    {{
    "date": "YYYY-MM-DD or null"
    }}

    Prevent past dates.
    """

            data = await IntentDetector._call_llm(prompt, date_text)
            date_str = data.get("date")

            if date_str:
                parsed = date.fromisoformat(date_str)
                if parsed >= date.today():
                    return parsed.isoformat()

            return None
        except Exception:
            return None

    # =====================================================
    # TIME RESOLUTION
    # =====================================================
    @staticmethod
    async def _resolve_time(time_text: str) -> Optional[Any]:

        parsed_time, ambiguous = IntentDetector._rule_based_time_parser(time_text)

        if parsed_time and not ambiguous:
            return parsed_time

        if ambiguous:
            return {"ambiguous_hour": parsed_time}

        try:
            prompt = f"""
Convert to 24-hour HH:MM.

Input: "{time_text}"

Return JSON:
{{
  "time": "HH:MM or null"
}}
"""
            data = await IntentDetector._call_llm(prompt,time_text)
            time_str = data.get("time")

            if time_str:
                datetime.strptime(time_str, "%H:%M")
                return time_str

            return None
        except Exception:
            return None

    # =====================================================
    # DEPARTMENT NORMALIZATION
    # =====================================================
    @staticmethod
    async def _normalize_department(department: str) -> Optional[str]:
        try:
            prompt = f"""
Normalize hospital department.

Input: "{department}"

Return JSON:
{{
  "department": "normalized department or null"
}}
"""
            data = await IntentDetector._call_llm(prompt, department)
            return data.get("department")
        except Exception:
            return None

    # =====================================================
    # RULE-BASED TIME PARSER
    # =====================================================
    @staticmethod
    def _rule_based_time_parser(text: str):

        text = text.lower().strip()

        # fix common speech spelling
        text = text.replace("bje", "baje").replace("bj", "baje").replace("bja", "baje")

        # ---------------------------------------------
        # 1️⃣ HH:MM or HH.MM  (10:30 , 17.00)
        # ---------------------------------------------
        match = re.search(r"\b(\d{1,2})[:\.](\d{2})\b", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}", False


        # ---------------------------------------------
        # 2️⃣ AM / PM format
        # ---------------------------------------------
        match = re.search(r"\b(\d{1,2})\s?(am|pm)\b", text)
        if match:
            hour = int(match.group(1))
            period = match.group(2)

            if period == "pm" and hour != 12:
                hour += 12

            if period == "am" and hour == 12:
                hour = 0

            return f"{hour:02d}:00", False


        # ---------------------------------------------
        # 3️⃣ Hindi spoken times
        # ---------------------------------------------

        # sawa 10  → 10:15
        match = re.search(r"sawa\s*(\d{1,2})", text)
        if match:
            hour = int(match.group(1))
            return f"{hour:02d}:15", False


        # aadhe 10 → 10:30
        match = re.search(r"aadhe\s*(\d{1,2})", text)
        if match:
            hour = int(match.group(1))
            return f"{hour:02d}:30", False


        # paune 11 → 10:45
        match = re.search(r"paune\s*(\d{1,2})", text)
        if match:
            hour = int(match.group(1)) - 1
            if hour < 0:
                hour = 0
            return f"{hour:02d}:45", False


        # ---------------------------------------------
        # 4️⃣ Hindi / English context time
        # ---------------------------------------------
        match = re.search(r"\b(\d{1,2})\s?(baje)?\b", text)

        if match:

            hour = int(match.group(1))

            if hour > 23:
                return None, False

            # evening / night
            if any(x in text for x in ["shaam", "evening", "raat", "night"]):
                if hour < 12:
                    hour += 12
                return f"{hour:02d}:00", False

            # morning
            if any(x in text for x in ["subah", "morning"]):
                return f"{hour:02d}:00", False

            # afternoon
            if any(x in text for x in ["dopahar", "afternoon"]):
                if hour < 12:
                    hour += 12
                return f"{hour:02d}:00", False

            # ambiguous like "10"
            return hour, True


        # ---------------------------------------------
        # No rule matched
        # ---------------------------------------------
        return None, False

    # =====================================================
    # FINAL RESPONSE NORMALIZATION
    # =====================================================
    @staticmethod
    def _finalize_response(
        intent: str,
        department: Optional[str],
        doctor_name: Optional[str],
        date_str: Optional[str],
        time_str: Optional[Any],
        patient_name: Optional[str],
        phone_number: Optional[str],
    ) -> Dict[str, Any]:

        if phone_number:
            phone_number = re.sub(r"\D", "", phone_number)
            if len(phone_number) > 10:
                phone_number = phone_number[-10:]

        return {
            "intent": intent,
            "department": department,
            "doctor_name": doctor_name,
            "date": date_str,
            "time": time_str,
            "patient_name": patient_name,
            "phone_number": phone_number,
        }

    # =====================================================
    # EMPTY RESPONSE
    # =====================================================
    @staticmethod
    def _empty_response(intent: str) -> Dict[str, Any]:
        return {
            "intent": intent,
            "department": None,
            "doctor_name": None,
            "date": None,
            "time": None,
            "patient_name": None,
            "phone_number": None,
        }

    # =====================================================
    # LLM CALL WRAPPER WITH TIMEOUT
    # =====================================================
    @staticmethod
    async def _call_llm(system_prompt: str, user_input: str) -> Dict[str, Any]:

        try:
            response = await asyncio.wait_for(
                IntentDetector.client.chat.completions.create(
                    model=settings.llm_model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                ),
                timeout=5,
            )

            content = response.choices[0].message.content
            print("sandeep 1",json.loads(content))
            return json.loads(content)

        except Exception:
            return {}