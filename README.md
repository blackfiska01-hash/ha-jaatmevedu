# Eesti jäätmevedu for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/blackfiska01-hash/ha-jaatmevedu/actions/workflows/validate.yml/badge.svg)](https://github.com/blackfiska01-hash/ha-jaatmevedu/actions/workflows/validate.yml)

Waste collection days for Estonian homes in Home Assistant: a calendar plus date sensors for every waste type. It works with the carriers that publish schedules without a login, which together cover about 60 of Estonia's 79 municipalities.

[Eesti keeles](#eesti-keeles) · [На русском](#на-русском)

## Supported carriers

| Carrier | Where (organised waste collection, 2026) | You need |
|---|---|---|
| **Eesti Keskkonnateenused** | Most of Estonia, about 44 municipalities, among them Tallinn (Haabersti, Kristiine, Lasnamäe, Pirita, Põhja-Tallinn, Vanalinn), Maardu, Viimsi, Rae, Harku, Jõelähtme, Tartu linn, Viljandi, Võru, Valga, Haapsalu, Saaremaa, Hiiumaa | Contract number (*lepingu number*) |
| **Ragn-Sells** | Jõhvi, Kadrina, Kambja, Kose, Lääneranna, Lüganuse, Luunja, Narva-Jõesuu, Pärnu linn, Peipsiääre, Saue, Tapa, Tartu vald, Toila, Türi | Area, plus your address or client code (*kliendikood*) |
| **TJT** (Tallinna Jäätmete Taaskasutuskeskus) | Saku vald | Address |

**Not supported yet:** these carriers have no public schedule lookup.
- **TJT in Tallinn** (Kesklinn, Mustamäe, Nõmme): schedules are behind its ID-card login.
- **ENEST/Ekovir**: Narva, Kohtla-Järve, Sillamäe, Alutaguse, Jõgeva, Anija.
- **Lääne-Viru Jäätmekeskus**: Rakvere, Rakvere vald, Vinni, Väike-Maarja.

If your carrier publishes schedules somewhere public, please [open an issue](https://github.com/blackfiska01-hash/ha-jaatmevedu/issues).

## What you get

Entity IDs start with the carrier name, for example `eesti_keskkonnateenused_`, `ragn_sells_` or `tjt_`.

| Entity | Example | Notes |
|---|---|---|
| `calendar.<carrier>_collections` | all-day event "Mixed waste" | Works with calendar cards and calendar triggers |
| `sensor.<carrier>_next_collection` | `2026-10-28` | Next collection of any type; attributes `waste_types` and `days_until` |
| `sensor.<carrier>_days_until_next_collection` | `3` | Days left; `0` means today |
| `sensor.<carrier>_mixed_waste`, `…_packaging`, `…_biowaste`, … | `2026-10-28` | One per waste type; attributes `days_until`, `waste_type` (the carrier's name) and, when the carrier publishes them, `container`, `frequency_days` and `weekdays` |

Waste types are grouped into mixed waste, packaging, glass, paper and cardboard, biowaste, garden waste, bulky waste and hazardous waste, with names in English, Estonian and Russian. A type the integration does not recognise still gets a sensor under the carrier's own name.

**How far ahead you can see depends on the carrier.** Eesti Keskkonnateenused and Ragn-Sells publish only the **next** collection per container. TJT publishes about a month ahead. After each collection the next date appears automatically.

## Installation

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/blackfiska01-hash/ha-jaatmevedu`, category **Integration**.
2. Install **Eesti jäätmevedu** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Eesti jäätmevedu**, then pick your carrier.

Alternatively, copy `custom_components/jaatmevedu` into `config/custom_components/` and restart.

### Eesti Keskkonnateenused

Enter the contract number from your invoice or the [self-service portal](https://eteenindus.keskkonnateenused.ee/). You can check the number on the carrier's [Järgmine veopäev](https://www.keskkonnateenused.ee/klienditugi/j%C3%A4rgmine-veop%C3%A4ev) page.

### Ragn-Sells

Choose your area, then do one of these:
- type the start of your street name and pick your address from the list; or
- enter the client code (*kliendikood*) from a Ragn-Sells invoice.

For data-protection reasons Ragn-Sells shows only some addresses in its [public table](https://www.ragnsells.ee/klienditugi/kliendile/graafikud). If your house is not found, use the client code.

### TJT

Choose Saku vald, search for your address and pick it from the list.

Several homes or contracts? Add each one separately.

## Examples

### Reminder the evening before

```yaml
automation:
  - alias: "Waste collection tomorrow"
    triggers:
      - trigger: time
        at: "19:00:00"
    conditions:
      - condition: state
        entity_id: sensor.eesti_keskkonnateenused_days_until_next_collection
        state: "1"
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "Waste collection tomorrow"
          message: >
            {{ state_attr('sensor.eesti_keskkonnateenused_next_collection', 'waste_types') | join(', ') }}
            — put the container out tonight.
```

### Dashboard tile

```yaml
type: tile
entity: sensor.eesti_keskkonnateenused_next_collection
name: Next collection
```

## How it works

- The integration reads the same public pages the carriers offer on their websites: the EKT next-collection lookup, the Ragn-Sells schedule table and the TJT schedule search. No login or API key is involved.
- Data refreshes every 6 hours and shortly after midnight. A collection stays "today" for the whole day and disappears the next day.
- This is an unofficial integration and is not affiliated with any carrier.

## Privacy

Your contract number, client code or address is stored only in your Home Assistant config entry. It is sent only to your own carrier's lookup. **Download diagnostics** removes all of them from its output.

## Upgrading from 0.1 (Eesti Keskkonnateenused)

Version 0.1 was called *Eesti Keskkonnateenused* and used the domain `keskkonnateenused`. To upgrade:
1. Remove that integration entry.
2. Update in HACS and restart.
3. Add **Eesti jäätmevedu** with the same contract number.

Entity IDs stay the same, so your automations and cards keep working.

## Development

```bash
pip install -e '.[dev]'
ruff check custom_components tests && ruff format --check custom_components tests
mypy
pytest tests --cov=custom_components/jaatmevedu
```

---

## Eesti keeles

Jäätmeveo päevad Home Assistantis kalendri ja kuupäevaanduritena, iga jäätmeliigi kohta eraldi. Toetatud on vedajad, kelle graafikud on avalikud ilma sisselogimiseta:
- **Eesti Keskkonnateenused**: lepingu number;
- **Ragn-Sells**: piirkond ning aadress või kliendikood;
- **TJT**: ainult Saku vald, aadressi järgi.

Kokku katavad need umbes 60 omavalitsust 79-st. Paigaldus käib HACS-i kaudu kohandatud hoidlana (*Custom repositories*). Lisa on mitteametlik.

## На русском

Даты вывоза мусора в Home Assistant: календарь и сенсоры с датой по каждому виду отходов. Поддерживаются перевозчики, у которых графики открыты без входа в личный кабинет:
- **Eesti Keskkonnateenused**: по номеру договора;
- **Ragn-Sells**: район плюс адрес или код клиента;
- **TJT**: только Saku vald, по адресу.

Вместе они покрывают около 60 из 79 самоуправлений Эстонии. Устанавливается через HACS как пользовательский репозиторий (*Custom repositories*). Интеграция неофициальная.

## License

[MIT](LICENSE)
