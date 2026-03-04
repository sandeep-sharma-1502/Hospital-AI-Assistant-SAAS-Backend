# from app.services.llm_service import LLMService


# class TimeParser:

#     @staticmethod
#     async def extract_time_from_text(text: str) -> str | None:
#         prompt = f"""
# Extract time in 24-hour HH:MM format from this sentence.
# Return ONLY time.

# Sentence: "{text}"
# """

#         response = await LLMService.generate(prompt)

#         cleaned = response.strip()

#         # Basic safety validation
#         if ":" in cleaned and len(cleaned) == 5:
#             return cleaned

#         return None