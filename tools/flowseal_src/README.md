# Исходные .bat Flowseal

Здесь лежат исходные `.bat`-файлы проекта
[Flowseal/zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube)
(скопированы 2026-10-05). Они нужны как источник для
`tools/convert_flowseal_strategies.py --check`: скрипт механически конвертирует
командные строки `winws.exe` в стратегии менеджера и сверяет результат с
`files/strategy/`.

Ранее источник искался в `.dsh/tmp/flowseal/src`, но `.dsh/` не попадает в git,
поэтому в CI шаг «Flowseal conversion matches files/strategy» падал с кодом 2
(каталога нет). Теперь источник версионируется вместе с репозиторием, и проверка
работает одинаково локально и в CI.

Обновление стратегий: заменить `.bat` здесь на свежие из апстрима и выполнить

```bash
python3 tools/convert_flowseal_strategies.py --check   # сверить
python3 tools/convert_flowseal_strategies.py --write   # записать в files/strategy
```
