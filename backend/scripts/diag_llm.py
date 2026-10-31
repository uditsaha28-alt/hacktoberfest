import asyncio
import time

import httpx

from app.config import settings

GEMINI = "https://generativelanguage.googleapis.com/v1beta"


async def main() -> None:
    print("GEMINI_MODEL =", settings.gemini_model, "| key set:", bool(settings.gemini_api_key))
    print("GROQ_MODEL   =", settings.groq_model, "| key set:", bool(settings.groq_api_key))

    async with httpx.AsyncClient(timeout=60) as client:
        print("\n--- Gemini: available models ---")
        try:
            res = await client.get(
                f"{GEMINI}/models",
                headers={"x-goog-api-key": settings.gemini_api_key},
                params={"pageSize": 200},
            )
            print("HTTP", res.status_code)
            if res.status_code == 200:
                names = [
                    m["name"].removeprefix("models/")
                    for m in res.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                print([n for n in names if "flash" in n])
            else:
                print(res.text[:300])
        except Exception as exc:
            print("NETWORK ERROR:", repr(exc))

        print("\n--- Gemini: one tiny request with your configured model ---")
        start = time.time()
        try:
            res = await client.post(
                f"{GEMINI}/models/{settings.gemini_model}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={"contents": [{"role": "user", "parts": [{"text": "Say hi in 3 words."}]}]},
            )
            print(f"HTTP {res.status_code} in {time.time() - start:.1f}s")
            print(res.text[:300])
        except Exception as exc:
            print(f"NETWORK ERROR after {time.time() - start:.1f}s:", repr(exc))

        print("\n--- Groq: available models ---")
        try:
            res = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            print("HTTP", res.status_code)
            if res.status_code == 200:
                print(sorted(m["id"] for m in res.json().get("data", [])))
            else:
                print(res.text[:300])
        except Exception as exc:
            print("NETWORK ERROR:", repr(exc))


if __name__ == "__main__":
    asyncio.run(main())