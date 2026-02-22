create table if not exists public.room_prices ( 

  id bigserial primary key, 

  scraped_at timestamptz not null default now(), 

  room_type text not null, 

  breakfast_included boolean not null, 

  price numeric not null, 

  currency text not null default 'EUR' 

) 


taskschd.msc 

C:\Windows\System32\cmd.exe 

/c docker compose run --rm al-web-scraper 

C:\home\github\al-web-scraper\backend 



k - liczba najbardziej podobnych chunków 

chunk_size ~ len(clean_text)/k 
