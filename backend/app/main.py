from .flights import get_flights_data
from .hotels import get_hotels_data

if __name__ == "__main__":
    # Hotel w Berlinie, 2 osoby, 2 noce, 2026-05-02 - 2026-05-05
    BERLIN = "https://www.booking.com/hotel/de/maritimberlin.pl.html?label=gen173nr-10CAEoggI46AdIM1gEaLYBiAEBmAEzuAEXyAEM2AED6AEB-AEBiAIBqAIBuAKJ5ubMBsACAdICJDliMWZmMjZkLTY5ZGQtNDc5Ny04MDUxLTMyYzRmNjBlYjUzYtgCAeACAQ&sid=4b51bbf7a01a958f4b2fda85c35c5d56&aid=304142&ucfs=1&arphpl=1&checkin=2026-05-02&checkout=2026-05-05&group_adults=2&req_adults=2&no_rooms=1&group_children=0&req_children=0&all_sr_blocks=6037402_418238029_0_34_0&highlighted_blocks=6037402_418238029_0_34_0&matching_block_id=6037402_418238029_0_34_0&sr_pri_blocks=6037402_418238029_0_34_0&from_list=1&selected_currency=EUR"

    QUESTION = f"""Daj mi cenę pokoju Pokój Dwuosobowy typu Classic i Pokój Dwuosobowy typu Comfort, oba ze śniadaniem i bez śniadania. Daj ceny w EUR"""

    get_hotels_data(BERLIN, QUESTION) 

    # Loty Warszawa - Malta i Malta - Warszawa, 2026-07-13
    WARSAW_TO_MALTA = "https://www.fru.pl/search_results?from=CITY:WAW&to=CITY:MLA&dd=2026-07-13&ad=1&ow=1&cc=ECONOMY"
    
    QUESTION = f"""Daj mi ceny wszystkich bezpośrednich lotów z Warszawy do Malty lotnisko Malta International, z lotniska Warszawa Chopin i z lotniska Warszawa Modlin razem z godzinami odlotów.
 To ma być cena Regular Price. Daj ceny w PLN. Ceny mają dużą czcionkę, są pogrubione i NIE są przekreślone. Ceny mogą się powtarzać. Loty tylko bezpośrednie. Nazwy lotnisk odlotów w formacie "Warszawa Chopin" i "Warszawa Modlin"."""
    
    get_flights_data(WARSAW_TO_MALTA, QUESTION)

    MALTA_TO_WARSAW = "https://www.fru.pl/search_results?from=AIRPORT:MLA&to=CITY:WAW&dd=2026-07-13&ad=1&ow=1&cc=ECONOMY"

    QUESTION = f"""Daj mi ceny wszystkich bezpośrednich lotów z Malty do Warszawy Chopin lub Warszawa Modlin, z lotniska Malta International razem z godzinami odlotów.
 To ma być cena Regular Price. Daj ceny w PLN. Ceny mają dużą czcionkę, są pogrubione i NIE są przekreślone. Ceny mogą się powtarzać. Loty tylko bezpośrednie. Nazwy lotnisk przylotów w formacie "Warszawa Chopin" i "Warszawa Modlin"."""
    
    get_flights_data(MALTA_TO_WARSAW, QUESTION)

    

    # https://github.com/VectifyAI/PageIndex -> do przemyślenia, może uprościć RAG i dać więcej kontroli nad chunkowaniem i embeddingiem