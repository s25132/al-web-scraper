import os
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from bs4 import BeautifulSoup

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever


DEFAULT_URL = "https://www.booking.com/hotel/de/maritimberlin.pl.html?label=gen173nr-10CAEoggI46AdIM1gEaLYBiAEBmAEzuAEXyAEM2AED6AEB-AEBiAIBqAIBuAKJ5ubMBsACAdICJDliMWZmMjZkLTY5ZGQtNDc5Ny04MDUxLTMyYzRmNjBlYjUzYtgCAeACAQ&sid=4b51bbf7a01a958f4b2fda85c35c5d56&aid=304142&ucfs=1&arphpl=1&checkin=2026-05-02&checkout=2026-05-05&group_adults=2&req_adults=2&no_rooms=1&group_children=0&req_children=0&all_sr_blocks=6037402_418238029_0_34_0&highlighted_blocks=6037402_418238029_0_34_0&matching_block_id=6037402_418238029_0_34_0&sr_pri_blocks=6037402_418238029_0_34_0&from_list=1&selected_currency=EUR"


def _try_accept_cookies(page) -> None:
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button:has-text("Akceptuj")',
        'button:has-text("Zaakceptuj")',
        'button:has-text("Zgadzam")',
        'button:has-text("Accept")',
        'button:has-text("I accept")',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=1500)
                page.wait_for_timeout(500)
                return
        except Exception:
            pass

def get_page_content(url: str) -> str:

    headless = os.getenv("HEADLESS", "1") != "0"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        context = browser.new_context(
            locale="pl-PL",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        _try_accept_cookies(page)

        try:
            page.wait_for_selector("tr[data-hotel-rounded-price]", timeout=30000)
        except PWTimeoutError:
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_selector("tr[data-hotel-rounded-price]", timeout=30000)   
            
        return page.content()


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # usuń niepotrzebne tagi
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # usuń puste linie
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)


def build_rag_from_html(html: str):
    clean_text = clean_html(html)

    # Document LangChain
    docs = [Document(page_content=clean_text)]

    # podziel na chunki
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)

    print(f"Chunks: {len(chunks)}")

    # embedding model
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    # vector store w pamięci
    vector_store = FAISS.from_documents(
        chunks,
        embeddings
    )
    
        # +++ BM25 na chunkach +++
    bm25 = BM25Retriever.from_documents(chunks)


    return vector_store, bm25


def ask_rag(vector_store, bm25, question: str):
    bm25.k = 10
    bm_docs = bm25.invoke(question) 

    vs_docs = vector_store.as_retriever(search_kwargs={"k": 10}).invoke(question)

    merged = []
    seen = set()
    for d in bm_docs + vs_docs:
        key = d.page_content[:1000]
        if key not in seen:
            seen.add(key)
            merged.append(d)

    # Prosty rerank: premiuj chunki zawierające "Classic" i "€" / "EUR"
    def score(doc: Document) -> int:
        t = doc.page_content.lower()
        s = 0
        if "classic" in t:
            s += 5
        if "€" in t or " eur" in t:
            s += 2
        if "śniad" in t or "breakfast" in t:
            s += 1
        return s

    merged.sort(key=score, reverse=True)

    context = "\n\n".join(d.page_content for d in merged[:10])

    llm = ChatOpenAI(model="gpt-5", temperature=0)

    prompt = f"""
Jesteś systemem ekstrakcji danych. Twoim zadaniem jest wyciągnąć informacje o cenach pokoi z kontekstu.

ZASADY:
- Odpowiadaj WYŁĄCZNIE w formacie JSON.
- NIE dodawaj żadnego tekstu poza JSON.
- NIE dodawaj komentarzy.
- Wszystkie ceny muszą być liczbami (bez symboli walut).

Format JSON:
{{
  "rooms": [
    {{
      "room_type": "string",
      "breakfast_included": true,
      "price_eur": number
    }},
    {{
      "room_type": "string",
      "breakfast_included": false,
      "price_eur": number
    }}
  ]
}}

Kontekst:
{context}

Pytanie:
{question}

Zwróć wyłącznie JSON.
""".strip()

    response = llm.invoke(prompt)
    return response.content


def main() -> None:
    html = get_page_content(DEFAULT_URL)

    vector_store, bm25 = build_rag_from_html(html)

    answer = ask_rag(
        vector_store,
        bm25,
        "Daj mi cenę pokoju Pokój Dwuosobowy typu Classic i tylko Classic ze śniadaniem i bez śniadania. Daj ceny w EUR"
    )

    print(answer)




if __name__ == "__main__":
    main()