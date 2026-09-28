# Tradebot

Paper trading-bot (fejkpengar) för forex och aktier med full transaktionslogg,
riskregler, Telegram-notiser och årsexport i SEK för deklarationen.

Startkapital i simuleringen: 500 kr forex + 500 kr aktier (ändras i `config.py`).

## Kom igång

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fyll i Telegram om du vill ha notiser
python main.py once              # kör en runda
python main.py run               # kör i loop
```

## Kommandon

| Kommando | Vad det gör |
|---|---|
| `python main.py once` | En runda: hämtar priser, tar beslut, loggar |
| `python main.py run` | Loop, en runda per timme + daglig sammanfattning kl 22 |
| `python main.py summary` | Visar saldo och öppna positioner |
| `python main.py report --year 2026` | Skapar `exports/trades_2026.csv` och `exports/summary_2026.txt` |

## Vad som loggas

Allt hamnar i SQLite (`data/tradebot.db`): varje affär (datum, symbol, antal, pris,
avgift, valuta, växelkurs till SEK, ordernummer), varje beslut med motivering,
och kapitalkurvan över tid.

## Säkerhet

- Stop-loss 5 % per position, max 50 % av kapitalet per position.
- Daglig förlustgräns (10 %) och total förlustgräns (30 %).
- Kill switch: skapa en tom fil som heter `STOP` i projektmappen, så köper boten inget mer.
- API-nycklar ligger i `.env`, som ignoreras av git.

## Innan riktiga pengar

Kör på paper i 4-8 veckor. Byt sedan `PaperBroker` mot en riktig mäklarklass
(OANDA, Interactive Brokers) med samma metoder. Kolla mäklarens villkor för svenska kunder.

Detta är ett hobbyprojekt och ingen finansiell rådgivning. De flesta hemmabyggda botar förlorar pengar.
