from datetime import date as dt_date
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid

from app.services.ai.intent_detector import IntentDetector
from sqlalchemy.orm.attributes import flag_modified
from app.services.appointments.slot_service import SlotService
from app.services.appointments.appointment_service import AppointmentService

logger = logging.getLogger(__name__)


class AIOrchestrator:

    ASK_DEPARTMENT = "ASK_DEPARTMENT"
    ASK_DATE = "ASK_DATE"
    ASK_TIME = "ASK_TIME"
    ASK_NAME = "ASK_NAME"
    ASK_PHONE = "ASK_PHONE"
    CONFIRM = "CONFIRM"

    @staticmethod
    async def handle_message(text: str, db: AsyncSession, session):

        text = text.strip()

        if not text:
            return "Kripya kuch likhiye."

        # =============================
        # AI DETECTION
        # =============================
        state = {
            "stage": session.booking_stage,
            "last_intent": "book_appointment" if session.booking_stage else "general"
        }

        extracted = await IntentDetector.detect(text, current_state=state)
        intent = extracted.get("intent")

        logger.warning(
            f"[DEBUG] Intent: {intent}, Stage: {session.booking_stage}, Text: {text}"
        )

        # Cancel handling
        if intent == "cancel_booking":
            session.booking_data = {}
            session.booking_stage = AIOrchestrator.ASK_DEPARTMENT
            return "Aapki booking cancel kar di gayi hai."

        text_lower = text.lower()

        manual_confirm = text_lower in [
            "yes", "ha", "haan", "h", "ok", "okay",
            "confirm", "kar do", "theek hai", "haan ji"
        ]

        confirm_intent = intent == "confirm_booking" or manual_confirm

        # =============================
        # FLOW PROTECTION
        # =============================
        if intent not in ["book_appointment", "confirm_booking"]:
            if session.booking_stage and session.booking_stage in {
                AIOrchestrator.ASK_DEPARTMENT,
                AIOrchestrator.ASK_DATE,
                AIOrchestrator.ASK_TIME,
                AIOrchestrator.ASK_NAME,
                AIOrchestrator.ASK_PHONE,
                AIOrchestrator.CONFIRM,
            }:
                intent = "book_appointment"
                logger.warning("[FLOW FIX] Intent forced to book_appointment")
            else:
                return None

        if intent not in ["book_appointment", "confirm_booking"]:
            return None

        # =============================
        # MERGE EXTRACTED DATA
        # =============================
        session.booking_data = session.booking_data or {}

        for field in [
            "department",
            "date",
            "time",
            "patient_name",
            "phone_number",
            "doctor_name",
        ]:

            if field not in extracted:
                continue

            value = extracted[field]

            if value is None:
                continue

            if isinstance(value, str):
                value = value.strip()

                if value == "":
                    continue

                if value.lower() in ["null", "none", "n/a"]:
                    continue

            session.booking_data[field] = value


        # 🔥 VERY IMPORTANT (JSON mutation fix)
        flag_modified(session, "booking_data")
        print("Sandeep sssss",session.booking_data)

        stage = session.booking_stage

        # Start booking flow only if intent is booking
        if not stage and intent == "book_appointment":
            stage = AIOrchestrator.ASK_DEPARTMENT

        # ============================================================
        # 🔥 FALL-THROUGH STAGE ENGINE
        # ============================================================
        while True:
            
            department = session.booking_data.get("department")
            date_str = session.booking_data.get("date")
            time_str = session.booking_data.get("time")
            patient_name = session.booking_data.get("patient_name")
            phone = session.booking_data.get("phone_number")
            doctor_name = session.booking_data.get("doctor_name")

            print("Sandeep sharma", session.booking_data)

            # =====================================================
            # STAGE 1 — DEPARTMENT
            # =====================================================
            if stage == AIOrchestrator.ASK_DEPARTMENT:

                if not department:
                    session.booking_stage = AIOrchestrator.ASK_DEPARTMENT
                    return "Kaunsa department chahiye?"

                stage = AIOrchestrator.ASK_DATE
                session.booking_stage = stage
                continue

            # =====================================================
            # STAGE 2 — DATE
            # =====================================================
            if stage == AIOrchestrator.ASK_DATE:

                if not date_str:
                    session.booking_stage = AIOrchestrator.ASK_DATE
                    return "Kis date ka appointment chahiye?"

                try:
                    parsed_date = dt_date.fromisoformat(date_str)
                    if parsed_date < dt_date.today():
                        return "Ye date past me hai. Nayi date batayein."
                except Exception:
                    return "Date samajh nahi aayi. Dobara batayein."

                stage = AIOrchestrator.ASK_TIME
                session.booking_stage = stage
                continue

            # =====================================================
            # STAGE 3 — TIME
            # =====================================================
            if stage == AIOrchestrator.ASK_TIME:

                if not department:
                    stage = AIOrchestrator.ASK_DEPARTMENT
                    session.booking_stage = stage
                    continue

                if not date_str:
                    stage = AIOrchestrator.ASK_DATE
                    session.booking_stage = stage
                    continue

                target_date = dt_date.fromisoformat(date_str)

                doctor, slots = await SlotService.get_available_slots_by_department(
                    db=db,
                    department=department,
                    target_date=target_date,
                )

                if not doctor:
                    return "Is department ka doctor available nahi hai."

                if not slots:
                    return "Is date par koi slot available nahi hai."
                
                # handle ambiguous time like "12"
                if isinstance(time_str, dict) and "ambiguous_hour" in time_str:

                    hour = time_str["ambiguous_hour"]

                    text_lower = text.lower()

                    # night case
                    if any(x in text_lower for x in ["raat", "night"]):

                        if hour == 12:
                            time_str = "00:00"
                        else:
                            time_str = f"{hour+12:02d}:00"

                    # default behaviour → daytime
                    else:

                        if hour == 12:
                            time_str = "12:00"
                        else:
                            time_str = f"{hour:02d}:00"

                    session.booking_data["time"] = time_str

                if not time_str:
                    sorted_times = sorted(
                        [s.start_time.strftime("%H:%M") for s in slots]
                    )
                    slot_list = "\n".join(
                        [f"{i+1}️⃣ {t}" for i, t in enumerate(sorted_times[:5])]
                    )
                    return f"Available slots:\n{slot_list}\nNumber choose karein."

                available_times = [
                    s.start_time.strftime("%H:%M") for s in slots
                ]

                if time_str not in available_times:
                    return "Ye time available nahi hai."

                stage = AIOrchestrator.ASK_NAME
                session.booking_stage = stage
                continue

            # =====================================================
            # STAGE 4 — NAME
            # =====================================================
            if stage == AIOrchestrator.ASK_NAME:

                if not patient_name:
                    session.booking_stage = AIOrchestrator.ASK_NAME
                    return "Aapka naam batayein."

                stage = AIOrchestrator.ASK_PHONE
                session.booking_stage = stage
                continue


            # =====================================================
            # STAGE 5 — PHONE
            # =====================================================
            if stage == AIOrchestrator.ASK_PHONE:

                if not phone or len(phone) != 10 or not phone.isdigit():
                    session.booking_stage = AIOrchestrator.ASK_PHONE
                    return "Sahi 10 digit mobile number batayein."

                stage = AIOrchestrator.CONFIRM
                session.booking_stage = stage
                continue


            # =====================================================
            # STAGE 6 — CONFIRM
            # =====================================================
            if stage == AIOrchestrator.CONFIRM:

                if not department or not date_str or not time_str:
                    session.booking_data = {}
                    session.booking_stage = None
                    return "Session expire ho gaya hai. Dobara shuru karte hain."

                # If user did not confirm explicitly
                if not confirm_intent:
                    return (
                        f"Aap {department} me {date_str} ko {time_str} ka "
                        f"appointment confirm karna chahte hain?"
                    )

                # Idempotency protection
                if session.booking_data.get("booking_token"):
                    return "Booking already processed."

                target_date = dt_date.fromisoformat(date_str)

                doctor, slots = await SlotService.get_available_slots_by_department(
                    db=db,
                    department=department,
                    target_date=target_date,
                )

                selected_slot = next(
                    (s for s in slots if s.start_time.strftime("%H:%M") == time_str),
                    None,
                )

                if not selected_slot:
                    return "Ye slot ab available nahi hai."

                session.booking_data["booking_token"] = str(uuid.uuid4())

                try:
                    appointment = await AppointmentService.create_atomic_booking(
                        db=db,
                        slot_id=selected_slot.id,
                        doctor_id=doctor.id,
                        patient_name=patient_name,
                        phone_number=phone,
                    )

                    logger.info(
                        f"BOOKING | Doctor:{doctor.id} | Slot:{selected_slot.id} | Phone:{phone}"
                    )

                except Exception:
                    logger.exception("Atomic booking failed")
                    return "Ye slot ab available nahi hai."

                # Reset session after success
                session.booking_data = {}
                session.booking_stage = None

                return (
                    f"Aapka appointment confirm ho gaya hai.\n"
                    f"Doctor: {doctor.name}\n"
                    f"Date: {date_str}\n"
                    f"Time: {time_str}\n"
                    f"Appointment ID: {appointment.id}"
                )

            # Safety fallback
            session.booking_stage = AIOrchestrator.ASK_DEPARTMENT
            return "Dobara shuru karte hain. Kaunsa department chahiye?"