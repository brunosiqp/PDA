# PDA · Automation Panel

🇧🇷 [Leia em português](README.md)

A local web panel for **Support and Monitoring** teams: automated alerts,
monitors, internal tools and a team community feed in one place. It is a
**pure** Python web server (`http.server`, no framework) embedded in a Tkinter
window, with scheduled jobs running in the background. Packaged with
PyInstaller, it runs on the operator's machine (it is not a hosted service).

The user interface, code comments and docs are in Brazilian Portuguese.

> **Privacy and LGPD.** This repository is public and is a **sanitized mirror**
> of the production source, which lives in a private repository. It contains
> **no sensitive data**: no credentials, tokens or signed URLs; no personal data
> (names, logins, e-mails, photos, job titles, feedback); no internal hosts,
> servers or network paths; no company tax IDs (CNPJ) and no customer names.
> Customers appear as pseudonyms (`ClienteA`, `cliente_b`...), people as
> fictitious names, e-mails on `@example.com`, IPs in the `192.0.2.0/24`
> documentation range, and images (logos, photos, screenshots) as placeholders.
> See [Privacy and LGPD](#privacy-and-lgpd). LGPD is Brazil's general data
> protection law.

## Features

**Monitoring and alerts**
- Scheduled tax-document alerts (`schedule` library), each in its own thread,
  with logs, status and a Microsoft Teams notice when a job keeps failing.
- SEFAZ contingency monitoring (SVC-AN / SVC-RS) per state, with Teams notices.
- Monitor hub: shortcuts to each customer's monitors and infrastructure,
  editable from the page itself.
- EmailPack log monitoring, automatic reprocessing of stuck CT-e documents,
  long file name cleanup, misuse monitoring and NNU automations
  (status 20 → 15), all starting paused and in simulation mode.

**Reports and data**
- Daily reports uploaded to SharePoint (Microsoft Graph), a monthly finance
  dataset for Power BI, and maintenance of alerts, rejections and reports
  directly in the database, with reusable connection strings.
- Movidesk indicators, hours worked per analyst, monthly indicators
  (effectiveness, NOC, satisfaction) and a change (GMUD) calendar.

**Team**
- Community (the home page): a feed with birthdays, promotions, badges,
  vacations, posts with photos, videos, files and polls, "claps" and comments,
  and notifications at the top of every page.
- Profile with career history and badges, feedback and alignment records,
  per-product rankings, a "claps" store and a vacation calendar.

**Access and security**
- Login with per-person and per-area permissions, mandatory change of the
  initial password, user sync with Movidesk.
- Sensitive credentials encrypted (Fernet, `config.dat`), one isolated log per
  automation with automatic zip archiving.

## Stack

Python 3, `http.server`, Tkinter, `schedule`, `requests`, `pyodbc`, `pandas`,
`xlsxwriter`, `cryptography`, Chart.js (CDN) and PyInstaller for the `.exe`.

## Layout

| Path | What it is |
|---|---|
| `alertas_gui.py` | Main app: jobs and scheduler, page assembly (`_montar_*_html`), HTTP routes and the Tkinter window. Version in `VERSAO_PDA`. |
| `areas/<area>/` | One folder per area, with `logica.py` (rules) and `tela.py` (HTML/CSS/JS). |
| `nucleo/` | Shared base: paths, configuration, users, sessions and permissions, teams, photos, notifications, Movidesk. Never imports `alertas_gui.py`. |
| `telas/` | HTML/CSS/JS for the general pages (home, login, alerts, logs, about, changelog...) and the shared CSS. Text only. |
| `core/`, `alerta_core/`, `features/` | Database, e-mail, configuration and encryption utilities, and the per-customer alert classes. |
| `validar.py`, `validar_execucao.py` | Validation checklist (see below). |
| `compilar.bat`, `PainelAlertas.spec`, `requirements.txt` | Build. |

## Running

```bash
pip install -r requirements.txt
python alertas_gui.py
```

With no configuration the panel still starts, and each integration shows on
screen what is missing (database, SMTP, Movidesk, Teams) instead of crashing.
On the first run a `usuarios.json` is created from the sample users in
`nucleo/usuarios.py` (password `troque-esta-senha`); change those passwords
right away.

## Configuration

No environment values ship with the code. Every credential follows a hybrid
pattern: the PDA first looks for a section in `CREDENCIAIS_CENTRALIZADAS.env`
(INI format) and, if it is missing, falls back to a legacy `.env.<name>` file.
Passwords and tokens can be stored encrypted in `config.dat` (key in
`chave.key`) through the "Configurações Seguras" page; see
[CRIPTOGRAFIA.md](CRIPTOGRAFIA.md) (in Portuguese). The EmailPack monitor also
reads environment variables, listed in [`.env.example`](.env.example). All of
these files are in `.gitignore`.

## Validation

```bash
python -X utf8 validar.py
```

Checks compilation, real syntax of every `<script>` block (via Node),
duplicate routes, orphan placeholders, definition order of the functions used
by `JOBS`, repeated card colors and local package imports. It then **runs the
PDA** in a temporary copy: builds every page, calls every GET route with an
admin session and validates the JS of the built pages (`--rapido` skips this
part). Conventions and versioning are in
[docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md) (in Portuguese).

## Privacy and LGPD

This repository is generated from the private one by a sanitizer that exports
only committed files, replaces real data with pseudonyms and **checks the
result** before publishing (the machine's credentials, names, logins,
e-mails, customers, IPs, servers, internal domains, signed URLs and literal
passwords). If the check finds anything, nothing is published.

Rules for contributors:

1. **Never** commit credentials, tokens, keys, signed URLs or connection
   strings. Use the local configuration files, which git ignores.
2. **Never** commit personal data: names, e-mails, photos, job titles,
   feedback, vacations, career history, logins or passwords, not even in
   comments, examples, tests or commit messages.
3. **Never** commit real infrastructure data (hosts, IPs, network shares,
   tenant, workflow or report IDs) or customer names or tax IDs: use the
   pseudonyms.
4. Runtime data files (`usuarios.json`, `feedbacks_usuarios.json`,
   `historico_carreira.json`, `ferias.json`, `mural_*.json`, photos,
   attachments and the like) stay out of the repository. In development and
   tests use **fictitious** data only (`exemplo@example.com`, `maria.souza`).
5. If sensitive data ever gets committed, treat it as a leak: revoke the
   credential and rewrite history. Deleting it in a new commit is not enough.

## License

Not defined yet. Without an explicit license, all rights remain reserved to
the author.
