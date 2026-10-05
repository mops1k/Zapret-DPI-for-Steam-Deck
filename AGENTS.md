# Правила проекта Zapret DPI Manager 2.0

## Сборка и релиз

- Сборка пакетов: `tools/build_release.sh` → `dist/Zapret_DPI_Manager.tar.gz` (полный пакет)
  и `dist/zapret_updater.tar.gz` (автообновление, без `config.txt` и `files/lists/*_user.txt`);
  из `installer/install_zapret.sh` пересобирается `install_zapret.tar.gz`.
- Версия хранится в `version.txt` (строка 1) и дублируется в `core/manager_config.py`
  (`current_version`) — менять синхронно. Строка 2 `version.txt` — URL архива обновления.
- Релиз публикуется workflow `.github/workflows/release.yml` (тег `v*` или ручной запуск);
  тег обязан совпадать с `version.txt`. В релиз входят оба архива и `SHA256SUMS`.
- Пуш и публикация релиза — только по прямой просьбе пользователя.

## Проверки перед коммитом

```bash
python3 -m compileall -q core ui tools main.py
bash -n zapret/system/starter.sh zapret/system/stopper.sh installer/install_zapret.sh
python3 tools/validate_strategies.py --dry-run     # плейсхолдеры, формат, nfqws --dry-run
python3 tools/convert_flowseal_strategies.py --check
ruff check core ui tools main.py                   # конфиг в pyproject.toml
XAUTHORITY=$(ls /run/user/1000/xauth_* | head -1) python3 tools/smoke_ui_material.py  # дымовой тест всех окон
```

CI (`.github/workflows/ci.yml`) выполняет те же шаги, кроме дымового теста окон.

## Оформление (Material 3)

- Единая тема: `ui/theme/` (`theme.color(role)`, `theme.font(role)`, `theme.text(...)`,
  `theme.space(step)`, `theme.radius(name)`, `theme.px(dp)`); режим dark/light хранится
  в `utils/theme.txt`, переключается в меню настроек главного окна (`MainWindow.rebuild_ui()`).
- Компоненты: `ui/components/material/` (кнопки, карточки, switch/checkbox/radio,
  поля, списки и таблицы, диалоги, snackbar, прогресс, top app bar, тонкий скроллбар).
- Хардкод-цвета в окнах запрещены: цвета берутся только из ролей темы. Прежние API
  (`create_hover_button`, `custom_messagebox`, `_font` в больших окнах) сохранены.
- Отчёт тестера стратегий открывается окном `ui/windows/report_window.py` (данные —
  `utils/reports/*.json`, рядом с HTML; для старых отчётов работает разбор HTML),
  в браузер ничего не открывается автоматически.

## Архитектура (кратко)

- `main.py` → `MainWindow` (миксины в `ui/windows/main/`) → `core/` → `config.txt`
  → `/opt/zapret/starter.sh` → `nfqws --qnum=200` + правила NFQUEUE.
- Служба: `/etc/systemd/system/zapret.service`, `Type=oneshot`, `RemainAfterExit=yes`,
  `ExecStart=/bin/bash /opt/zapret/starter.sh`, `ExecStop=/bin/bash /opt/zapret/stopper.sh`.
- FWTYPE — единый источник истины `core/platform_info.detect_fwtype()` (nft → `nftables`,
  иначе `iptables`). Правила живут в собственной цепочке `ZAPRET` / таблице `inet zapret`,
  чужие правила (Docker/VPN/firewalld) не трогаются.
- Все привилегированные команды — только через `core/sudo_helper.run_sudo` (`sudo -A` +
  `core/askpass.py`). Пароль приложение не хранит, кроме явного кэша 0600
  (`~/.cache/zapret_dpi_manager/sudo.cred`) по галочке «Запомнить».
- Плейсхолдеры `{...}` в `config.txt` раскрывает `zapret/system/starter.sh`; набор
  поддерживаемых плейсхолдеров проверяет `tools/validate_strategies.py`.
- Логи ошибок: `~/.local/state/zapret_dpi_manager/error.log` (0600, ротация).

## Данные

- `files/strategy/` — готовые стратегии (по строке на правило, `--new` в конце строки).
- `files/lists/` — домены/IP; `*_user.txt` — пользовательские, обновление их не перезаписывает.
- `files/bin/` — payload-бинарники; `zapret/bins/<arch>/nfqws` — движок (исполняемый бит обязателен).
- `core/strategy_data.py` (`STRATEGY_OPTIONS`) — варианты конструктора стратегии;
  `core/game_presets.py` (`GAME_PRESETS`) — игровые пресеты.
