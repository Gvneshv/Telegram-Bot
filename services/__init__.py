"""
AI backend implementations.
 
Public API (the only names the rest of the bot should import):
    - ``AIService``         — abstract interface (services.base)
    - ``create_ai_service`` — factory function  (services.factory)
 
Concrete service classes (``OpenAIService``, etc.) should not be imported
directly outside this package. Use the factory instead.
"""