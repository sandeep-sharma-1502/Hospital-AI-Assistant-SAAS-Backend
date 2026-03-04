class BookingContextManager:

    FIELD_ORDER = [
        "department",
        "date",
        "time",
        "patient_name",
        "phone_number"
    ]

    @staticmethod
    def merge(state, extracted):
        for field in BookingContextManager.FIELD_ORDER:
            if extracted.get(field):
                setattr(state, field, extracted[field])
        return state

    @staticmethod
    def get_missing_field(state):
        for field in BookingContextManager.FIELD_ORDER:
            if not getattr(state, field):
                return field
        return None

    @staticmethod
    def ask_question(field):
        questions = {
            "department": "Kaunsa department chahiye?",
            "date": "Kis date ka appointment chahiye?",
            "time": "Kis time ka slot chahiye?",
            "patient_name": "Aapka naam batayein?",
            "phone_number": "Mobile number batayein?",
        }
        return questions.get(field)