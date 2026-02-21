import os
from langchain_openai import ChatOpenAI


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Brak OPENAI_API_KEY")

    model = os.getenv("OPENAI_MODEL", "gpt-5")

    # Prosty model LangChain — bez tools
    llm = ChatOpenAI(
        model=model,
        temperature=0
    )

    prompt = """
    Podaj aktualną pogodę w Warszawie.
    Jeśli nie masz dostępu do aktualnych danych, podaj realistyczną przybliżoną pogodę
    typową dla obecnej pory roku w Warszawie oraz zaznacz, że to estymacja.

    Podaj:
    - temperatura °C
    - odczuwalna
    - wiatr
    - zachmurzenie / opady
    - prognoza na 12h
    """

    response = llm.invoke(prompt)

    print(response.content)


if __name__ == "__main__":
    main()