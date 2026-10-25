# Eesti Keskkonnateenused for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/blackfiska01-hash/ha-keskkonnateenused/actions/workflows/validate.yml/badge.svg)](https://github.com/blackfiska01-hash/ha-keskkonnateenused/actions/workflows/validate.yml)

Waste collection days from [Eesti Keskkonnateenused](https://www.keskkonnateenused.ee) in Home Assistant: a calendar plus date sensors for each waste type on your contract. Setup asks only for your contract number. No login is needed.

[Eesti keeles](#eesti-keeles) · [На русском](#на-русском)

## What you get

| Entity | Example | Notes |
|---|---|---|
| `calendar.eesti_keskkonnateenused_collections` | all-day event "Mixed waste" | Works with the calendar card and calendar triggers |
| `sensor.eesti_keskkonnateenused_next_collection` | `2026-10-28` | Next collection of any type; attributes `waste_types` and `days_until` |
| `sensor.eesti_keskkonnateenused_days_until_next_collection` | `3` | Days left; `0` means today |
| `sensor.eesti_keskkonnateenused_mixed_waste`, `…_packaging`, … | `2026-10-28` | One per waste type on your contract; attributes `container`, `days_until` and `waste_type` (the provider's own name) |

The provider's waste names are mapped to mixed waste, packaging, glass, paper and cardboard, biowaste, garden waste, bulky waste and hazardous waste. These are translated into English, Estonian and Russian. A type the integration does not recognise still gets a sensor, under the provider's own name. Sensors for new waste types appear by themselves when your contract gains one.

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/blackfiska01-hash/ha-keskkonnateenused`, category **Integration**.
2. Install **Eesti Keskkonnateenused** and restart Home Assistant.

### Manual

Copy `custom_components/keskkonnateenused` into your `config/custom_components/` folder and restart.

## Setup

**Settings → Devices & services → Add integration → Eesti Keskkonnateenused**, then enter your contract number (*lepingu number*). You can find it on your invoice or in the [self-service portal](https://eteenindus.keskkonnateenused.ee/). To check the number, enter it on the provider's [Järgmine veopäev](https://www.keskkonnateenused.ee/klienditugi/j%C3%A4rgmine-veop%C3%A4ev) page. If you have several contracts, add each one separately.

## How it works and its limits

- The integration uses the same public lookup as the provider's "Järgmine veopäev" page.
- The provider publishes only the **next** collection day per container, not a full schedule. So the calendar shows one upcoming event per waste type, and after each collection the next date replaces it.
- Data is refreshed every 6 hours and shortly after midnight. A collection stays "today" all day and disappears the next day.
- This is an unofficial integration and is not affiliated with Eesti Keskkonnateenused AS.

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

## Privacy

Your contract number is stored only in your Home Assistant config entry and sent only to the provider's lookup. **Download diagnostics** removes the contract number and your address from its output.

## Development

```bash
pip install -e '.[dev]'
ruff check custom_components tests && ruff format --check custom_components tests
mypy
pytest tests --cov=custom_components/keskkonnateenused
```

---

## Eesti keeles

Eesti Keskkonnateenuste jäätmeveo päevad Home Assistantis: kalender ja kuupäevaandurid iga jäätmeliigi kohta. Seadistamiseks on vaja ainult lepingu numbrit, mille leiate arvelt või [iseteenindusest](https://eteenindus.keskkonnateenused.ee/). Paigaldus käib HACS-i kaudu kohandatud hoidlana (*Custom repositories*). Teenusepakkuja avaldab ainult **järgmise** veopäeva, seega näitab kalender iga jäätmeliigi kohta ühte eelseisvat vedu. Tegemist on mitteametliku lisaga.

## На русском

Даты вывоза мусора от Eesti Keskkonnateenused в Home Assistant: календарь и сенсоры с датой по каждому виду отходов. Для настройки нужен только номер договора (*lepingu number*), он есть на счёте и в [e-teenindus](https://eteenindus.keskkonnateenused.ee/). Устанавливается через HACS как пользовательский репозиторий (*Custom repositories*). Перевозчик публикует только **ближайшую** дату вывоза, поэтому в календаре по каждому виду отходов видно одно следующее событие. Интеграция неофициальная.

## License

[MIT](LICENSE)
