# ANY-784: решение по зависимостям Mailpit

Дата: 1 ноября 2026. Область: локальный Mailpit; production Dokploy его не включает.
Решение: заменить официальный стабильный образ 1.32.0 на **1.33.0**, сохранив
digest pin и существующие сетевые/retention ограничения. Собственный patched image
и `latest`/`edge` не используются. Разрешение на исправление дал пользователь
после приёмки ANY-758; публикация статуса Linear в это поручение не входит.

## Проверенный образ

- Официальный [release 1.33.0](https://github.com/axllent/mailpit/releases/tag/v1.33.0).
- Index digest: `sha256:9b3a463be15354c0f0eba91697d80e3e0d8a5623ef0e627cacc836bc17fd5231`.
- Проверенная платформа: `linux/amd64`; manifest:
  `sha256:18156f9ee243aa339170ac33d09d6d5a80b10d9e06b265f90f223a777a8f4b73`.
- Извлечённый из фактического Compose-контейнера бинарник: Go **1.27.3**,
  `golang.org/x/net v0.62.0`, `golang.org/x/crypto v0.58.0`, CGO=0.
  VCS revision: `364916b15e80a8bac1e7b0ab66a4f2b3d7d745c2`.
- Trivy **0.74.0**, scan 2026-11-01 19:23 Asia/Novosibirsk. DB UpdatedAt:
  `2026-11-01T07:08:40.846369079Z`, DownloadedAt:
  `2026-11-01T08:03:33.5410007Z`. Повторное выполнение использует актуальную на
  дату проверки базу; тот же DB snapshot использовался в первоначальной приёмке.

## HTML advisories

[GO-2026-6860 / CVE-2026-78661](https://pkg.go.dev/vuln/GO-2026-6860) и
[GO-2026-6866 / CVE-2026-97045](https://pkg.go.dev/vuln/GO-2026-6866) исправлены
в `x/net v0.62.0`. Зависимость проверена в бинарнике и
[go.mod официального тега](https://github.com/axllent/mailpit/blob/v1.33.0/go.mod).
Обе находки отсутствуют в новом Trivy scan и Go-aware binary scan. Старый pin
1.32.0 содержал v0.61.0 и обе находки; артефакты первоначальной приёмки сохранены.

Путь обработки входящего HTML остаётся реальным: SMTP SaveToDatabase →
storage.Store → createSearchText → html2text.Strip → html.Parse; HTTP-преобразование
в `internal/tools/html.go` вызывает ParseWithOptions/Render. Обновление закрывает
уязвимую версию зависимости на этих путях. Exhausting PoC и XSS/эксфильтрация не
запускались и не заявляются доказанными.

## Остаточная находка OpenPGP

Trivy продолжает выдавать **GO-2026-5932**, severity **UNKNOWN**, на уровне модуля
`golang.org/x/crypto v0.58.0`. [Первичный advisory](https://pkg.go.dev/vuln/GO-2026-5932)
относится к пакетам **openpgp**; он не означает, что любая функция модуля x/crypto
уязвима. Исправленной версии OpenPGP в этом модуле advisory не указывает.

Обоснование неприменимости к стандартной проверенной сборке:

1. Из официального тега v1.33.0 получен полный `go list -deps -json .` для
   **GOOS=linux, GOARCH=amd64, CGO_ENABLED=0, Go 1.27.3**. Все 403 пакета
   загружены без Error/Incomplete. Ни один `golang.org/x/crypto/openpgp` или его
   подпакет не импортируется. Из x/crypto импортируются только **bcrypt и blowfish**.
2. `govulncheck v1.1.4 -mode=source -scan=package` для той же платформы сообщает
   GO-2026-5932 только на уровне модуля, без затронутого импортируемого пакета.
3. Binary scan той же версией инструмента оставляет module/package wildcard
   findings без вызывающего прикладного пути. Они сохранены в исходном виде и
   не используются как доказательство достижимого OpenPGP-вызова. Source import
   graph даёт более точное основание оценки применимости этой находки.

Решение: находку сохранить в отчёте как **module-level, affected OpenPGP packages
not imported в проверенном release graph**. Глобального ignore/suppression нет.
При обновлении Mailpit, изменении build tags/платформы или появлении OpenPGP
оценку повторить. Это не обещание отсутствия всех уязвимостей в образе.

## Проверка внедрения и границы

Новый pin используется в `deploy/compose/mailpit.yaml`, а не только в отдельном
candidate fixture. Проверки привязаны к HEAD `ea1cfc942a96239543029cd70bd0c3ac5fbee3d1`
с локальным patch, указанным в manifest повторной приёмки. Образ приложения не
изменяет schema startup и не выполняет downgrade.

Сохраняются loopback UI, отсутствие host SMTP, relay/forwarding и внешнего прокси,
project-scoped SQLite, 500 сообщений / 7 дней. Mailpit не должен получать
недоверенный внешний поток. Ограничения сети/retention не считаются исправлением
HTML-парсера и не ограничивают стоимость обработки одного сообщения.

Сырые материалы: `output/any758-fixes/20261101-2cc4fc06/` — manifest/pull,
Trivy JSON/log/version, `mailpit-binary-info.txt`, Go-aware binary/source scans,
полный `mailpit-linux-deps.json` и сводка `mailpit-reachability.json`.
Результаты SMTP/API/restart/network и коротких application journeys вынесены в
отдельный отчёт повторной приёмки ANY-758. Базы существующих установок не менялись.
