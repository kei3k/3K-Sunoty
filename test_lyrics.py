from google import genai
from google.genai import types

client = genai.Client(api_key='AIzaSyCTXmDUJbj8HX1xKS02w66c7IgT2AZ3ym4')

prompt = """Find the complete original lyrics for the song "Sabrina Carpenter - Tears".

Rules:
- Return ONLY the lyrics text, nothing else
- Include section markers like [Verse 1], [Chorus], [Bridge] etc.
- Do NOT include any explanation, commentary, or notes
- If you cannot find the lyrics, return exactly: LYRICS_NOT_FOUND
- Keep the original language of the song"""

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
)
print(response.text)
