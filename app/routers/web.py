import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()
ENABLED_VALUES = {"1", "true", "yes", "on"}


def _env_status_label(name):
    return (
        "Attivo"
        if os.getenv(name, "0").strip().lower() in ENABLED_VALUES
        else "Disattivo"
    )


@router.get("/", response_class=HTMLResponse)
def web_home():
    html = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>OddSignal - Dashboard</title>
  <style>
    :root {
      --bg: #f5faf8;
      --panel: rgba(255, 255, 255, 0.72);
      --text: #0b2540;
      --muted: #526b80;
      --border: rgba(13, 31, 45, 0.10);
      --sidebar: rgba(255, 255, 255, 0.66);
      --sidebar-muted: #5f7487;
      --accent: #1f9d69;
      --accent-dark: #0b2540;
      --accent-soft: rgba(31, 157, 105, 0.12);
      --success-bg: #dcfce7;
      --warning-bg: #fef3c7;
    }

    * {
      box-sizing: border-box;
    }

    body {
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background:
        radial-gradient(circle at 12% 8%, rgba(31, 157, 105, 0.18), transparent 32%),
        radial-gradient(circle at 90% 12%, rgba(13, 31, 45, 0.10), transparent 30%),
        linear-gradient(135deg, #f8fffb 0%, var(--bg) 46%, #eef6f7 100%);
      color: var(--text);
    }

    h1, h2, h3 {
      margin-bottom: 8px;
      color: var(--accent-dark);
    }

    h1 {
      margin-top: 0;
      font-size: 38px;
      line-height: 1.1;
    }

    h2 {
      margin-top: 0;
      font-size: 24px;
    }

    h3 {
      font-size: 16px;
    }

    .app-shell {
      min-height: 100vh;
    }

    .sidebar {
      position: fixed;
      inset: 18px auto 18px 18px;
      width: 280px;
      background: var(--sidebar);
      color: var(--text);
      padding: 24px 16px;
      overflow-y: auto;
      border: 1px solid rgba(255, 255, 255, 0.72);
      border-radius: 28px;
      box-shadow: 0 24px 70px rgba(13, 31, 45, 0.14);
      backdrop-filter: blur(22px);
      -webkit-backdrop-filter: blur(22px);
    }

    .brand {
      display: block;
      margin: 2px 8px 30px;
    }

    .brand-logo {
      display: block;
      width: 205px;
      max-width: 100%;
      height: auto;
    }

    .sidebar-nav {
      display: grid;
      gap: 7px;
    }

    .sidebar-link {
      display: block;
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text);
      text-align: left;
      text-decoration: none;
      border-radius: 14px;
      padding: 10px 12px;
      font-size: 14px;
      font-weight: 650;
      box-shadow: none;
    }

    .sidebar-link:hover,
    .sidebar-link:focus,
    .sidebar-link.active {
      background: rgba(255, 255, 255, 0.72);
      border-color: rgba(31, 157, 105, 0.18);
      color: var(--accent-dark);
      outline: none;
    }

    .sidebar-link.active {
      box-shadow: inset 3px 0 0 var(--accent), 0 10px 24px rgba(13, 31, 45, 0.07);
    }

    .main-content {
      margin-left: 316px;
      padding: 28px;
    }

    .content-inner {
      max-width: 1280px;
      margin: 0 auto;
    }

    .page-section {
      display: none;
    }

    .page-section.active {
      display: block;
    }

    .glass-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 26px;
      padding: 24px;
      box-shadow: 0 22px 60px rgba(13, 31, 45, 0.10);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
    }

    .home-section {
      min-height: calc(100vh - 56px);
      display: none;
      align-content: start;
      gap: 18px;
    }

    .home-section.active {
      display: grid;
    }

    .home-hero {
      text-align: center;
      padding: 34px 28px 30px;
    }

    .home-logo {
      display: block;
      width: min(360px, 72vw);
      height: auto;
      margin: 0 auto 18px;
    }

    .home-dashboard {
      display: grid;
      gap: 12px;
    }

    .home-status-panel {
      padding: 18px;
    }

    .home-toolbar {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      text-align: left;
    }

    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .06em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }

    .lead {
      max-width: 760px;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.55;
      margin: 0 auto 18px;
    }

    .section-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }

    .section-header h2 {
      margin: 0 0 4px;
    }

    .section-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .section-stack {
      display: grid;
      gap: 18px;
    }

    .subsection {
      border-top: 1px solid var(--border);
      padding-top: 18px;
    }

    .subsection:first-child {
      border-top: 0;
      padding-top: 0;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }

    .status-grid {
      grid-template-columns: repeat(4, minmax(130px, 1fr));
    }

    .summary-card {
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 13px 14px;
      background: rgba(255, 255, 255, 0.64);
      box-shadow: 0 12px 30px rgba(13, 31, 45, 0.06);
    }

    .summary-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }

    .summary-value {
      margin-top: 5px;
      font-size: 18px;
      font-weight: 700;
      color: var(--accent-dark);
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      align-items: end;
    }

    .filter-row {
      display: grid;
      grid-template-columns: minmax(220px, 420px);
      gap: 8px;
      margin: 12px 0;
    }

    label {
      display: flex;
      flex-direction: column;
      gap: 5px;
      color: var(--accent-dark);
      font-size: 13px;
      font-weight: 700;
    }

    button {
      cursor: pointer;
      padding: 9px 13px;
      border-radius: 12px;
      border: 1px solid rgba(13, 31, 45, 0.12);
      background: rgba(255, 255, 255, 0.76);
      color: var(--text);
      font-weight: 700;
      box-shadow: 0 8px 20px rgba(13, 31, 45, 0.06);
    }

    button:hover {
      border-color: var(--accent);
      color: var(--accent-dark);
      background: rgba(255, 255, 255, 0.92);
    }

    button.primary {
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }

    button.primary:hover {
      background: var(--accent-dark);
      color: white;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: .55;
    }

    button.compact {
      padding: 6px 10px;
      font-size: 13px;
    }

    input, select {
      padding: 9px 10px;
      border-radius: 12px;
      border: 1px solid rgba(13, 31, 45, 0.14);
      min-width: 0;
      background: rgba(255, 255, 255, 0.76);
      color: var(--text);
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 18px;
      margin-top: 12px;
      background: rgba(255, 255, 255, 0.50);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: transparent;
    }

    th, td {
      border-bottom: 1px solid rgba(13, 31, 45, 0.08);
      padding: 11px 10px;
      text-align: left;
      font-size: 14px;
      vertical-align: top;
      color: var(--text);
    }

    tr:last-child td {
      border-bottom: 0;
    }

    th {
      background: rgba(255, 255, 255, 0.58);
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }

    .muted {
      color: var(--muted);
      font-size: 13px;
    }

    .badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      background: #e5e7eb;
      font-size: 12px;
      font-weight: 700;
      color: var(--accent-dark);
    }

    .ok {
      background: var(--success-bg);
    }

    .warn {
      background: var(--warning-bg);
    }

    .feedback {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #f3f4f6;
      border: 1px solid #e5e7eb;
      font-size: 14px;
      color: var(--text);
    }
    .feedback.success {
      background: #ecfdf5;
      border-color: #bbf7d0;
      color: #166534;
    }
    .feedback.error {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }

    .info-box {
      background: rgba(255, 255, 255, 0.62);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 12px;
      margin: 10px 0;
    }

    .secondary-text {
      color: var(--muted);
      font-size: 12px;
    }

    .market-name {
      font-weight: 700;
    }

    .future-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }

    .inline-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0;
    }

    details {
      background: rgba(255, 255, 255, 0.58);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 10px 12px;
    }

    .technical-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    summary {
      cursor: pointer;
      color: var(--accent-dark);
      font-size: 14px;
      font-weight: 700;
    }

    pre {
      white-space: pre-wrap;
      background: #111827;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      max-height: 420px;
    }

    @media (max-width: 980px) {
      .sidebar {
        position: static;
        width: auto;
        min-height: 0;
        margin: 12px;
      }

      .main-content {
        margin-left: 0;
        padding: 18px;
      }

      .sidebar-nav {
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      }

      .status-grid {
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      }

      .home-toolbar {
        display: grid;
      }
    }
  </style>
</head>
<body>
  <div class="app-shell">
  <aside class="sidebar">
    <div class="brand">
      <img class="brand-logo" src="/static/brand/oddsignal-horizontal.png" alt="OddSignal">
    </div>
    <nav class="sidebar-nav" aria-label="Navigazione dashboard">
      <button type="button" class="sidebar-link active" data-page="overview" onclick="showPage('overview', event)">Home</button>
      <button type="button" class="sidebar-link" data-page="automation" onclick="showPage('automation', event)">Automazione</button>
      <button type="button" class="sidebar-link" data-page="readiness" onclick="showPage('readiness', event)">Sistema</button>
      <button type="button" class="sidebar-link" data-page="competitions" onclick="showPage('competitions', event)">Campionati</button>
      <button type="button" class="sidebar-link" data-page="markets" onclick="showPage('markets', event)">Mercati</button>
      <button type="button" class="sidebar-link" data-page="recent-alerts" onclick="showPage('recent-alerts', event)">Alert</button>
      <button type="button" class="sidebar-link" data-page="provider-bookmakers" onclick="showPage('provider-bookmakers', event)">Bookmaker</button>
      <button type="button" class="sidebar-link" data-page="provider-plan" onclick="showPage('provider-plan', event)">Piano API</button>
      <button type="button" class="sidebar-link" data-page="recipients" onclick="showPage('recipients', event)">Telegram</button>
      <button type="button" class="sidebar-link" data-page="notification-logs-section" onclick="showPage('notification-logs-section', event)">Storico / Log</button>
      <button type="button" class="sidebar-link" data-page="technical-area" onclick="showPage('technical-area', event)">Area tecnica</button>
      <a class="sidebar-link" href="/logout">Esci</a>
    </nav>
  </aside>

  <main class="main-content">
  <div class="content-inner">
  <section id="overview" class="page-section home-section active">
    <div class="home-hero glass-card">
      <img class="home-logo" src="/static/brand/oddsignal-horizontal.png" alt="OddSignal">
      <div class="eyebrow">Dashboard operativa</div>
      <h1>Benvenuto in OddSignal</h1>
      <p class="lead">Software informativo per monitorare variazioni significative delle quote calcio, con alert configurabili, storico, notifiche Telegram e controlli sui limiti API.</p>
    </div>
    <div class="home-dashboard glass-card home-status-panel">
      <div class="home-toolbar">
        <div>
          <h2>Riepilogo operativo</h2>
          <p class="muted">Stato corrente del sistema e delle configurazioni principali.</p>
        </div>
        <div class="section-actions">
          <button onclick="loadStatus()">Aggiorna stato</button>
          <button onclick="loadReadiness()">Ricarica sistema</button>
          <button onclick="loadProviderUsage()">Ricarica consumo API locale</button>
        </div>
      </div>
      <div id="dashboard-summary" class="summary-grid status-grid">
        <div class="summary-card"><div class="summary-label">Sistema</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Monitoraggio</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Consumo API</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Telegram</div><div class="summary-value">...</div></div>
      </div>
      <div id="overview-metrics" class="summary-grid">
        <div class="summary-card"><div class="summary-label">Campionati attivi</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Mercati attivi</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Alert recenti</div><div class="summary-value">...</div></div>
        <div class="summary-card"><div class="summary-label">Log notifiche</div><div class="summary-value">...</div></div>
      </div>
    </div>
  </section>

  <section id="readiness" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Sistema</h2>
        <p class="muted">Riepilogo operativo per capire se il sistema è pronto a monitorare senza controllare manualmente tutte le sezioni.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadReadiness()">Ricarica sistema</button>
      </div>
    </div>
    <div id="readiness-summary" class="info-box">Caricamento sistema...</div>
    <div id="readiness-feedback" class="feedback muted">Caricamento sistema...</div>
  </section>

  <section id="recent-alerts" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Alert</h2>
        <p class="muted">Soglie, cooldown e storico degli alert generati dal monitoraggio quote.</p>
      </div>
    </div>
    <div class="section-stack">
      <div id="alert-settings" class="subsection">
        <div class="section-header">
          <div>
            <h3>Soglie alert e cooldown</h3>
            <p class="muted">Configura le soglie. Telegram notifica solo i cali quota: Standard tra min/max, Critico oltre la soglia critica.</p>
          </div>
        </div>
        <div class="form-grid">
          <label>Min %
            <input id="alert-min-percent" type="number" step="0.01" placeholder="8">
          </label>
          <label>Max %
            <input id="alert-max-percent" type="number" step="0.01" placeholder="15">
          </label>
          <label>Critico %
            <input id="alert-critical-percent" type="number" step="0.01" placeholder="15">
          </label>
          <label>Dedup minuti
            <input id="alert-deduplication-minutes" type="number" step="1" placeholder="30">
          </label>
          <button class="primary" onclick="saveAlertSettings()">Salva soglie</button>
          <button onclick="loadAlertSettings()">Ricarica</button>
        </div>
        <div class="info-box">
          <strong>Dedup minuti</strong>
          <p class="muted">Indica per quanti minuti il sistema evita di generare alert duplicati sulla stessa combinazione evento, mercato, selezione, bookmaker e provider.</p>
          <p class="muted">Serve a non ricevere notifiche ripetute per lo stesso movimento quota. Esempio: se dedup minuti = 30, lo stesso alert non viene ripetuto per 30 minuti.</p>
        </div>
        <div id="alert-settings-feedback" class="feedback muted">Caricamento impostazioni...</div>
      </div>

      <div class="subsection">
        <div class="section-header">
          <div>
            <h3>Alert recenti</h3>
            <p class="muted">Storico completo degli alert. Gli aumenti restano nello storico, ma non vengono notificati via Telegram.</p>
          </div>
          <div class="section-actions">
            <select id="alerts-filter" onchange="renderAlertsTable()">
              <option value="all">Tutti</option>
              <option value="notifiable">Solo cali notificabili</option>
              <option value="increases">Aumenti non notificati</option>
              <option value="critical">Critici</option>
            </select>
            <button onclick="loadAlerts()">Aggiorna alert</button>
            <button onclick="clearRecentAlerts()">Cancella alert recenti</button>
          </div>
        </div>
        <div id="alerts-filter-feedback" class="feedback muted">Gli alert Telegram vengono inviati solo sui cali quota.</div>
        <div id="alerts"></div>
      </div>
    </div>
  </section>

  <section id="competitions" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Campionati da monitorare</h2>
        <p class="muted">Scegli i campionati su cui vuoi ricevere alert. Puoi aggiornare l’elenco in base agli eventi disponibili dal provider.</p>
      </div>
      <div class="section-actions">
        <button class="primary" onclick="refreshProviderLeagues()">Aggiorna leghe/slug dal provider</button>
        <button onclick="refreshProviderCompetitions()">Aggiorna campionati da eventi</button>
        <button onclick="loadCompetitions()">Aggiorna campionati</button>
      </div>
    </div>
    <div class="info-box">
      <strong>Come usare questa sezione</strong>
      <p class="muted">Attiva solo i campionati che vuoi monitorare. I campionati non attivi restano disponibili, ma non vengono usati nel controllo quote.</p>
    </div>
    <div class="filter-row">
      <label>Cerca campionati
        <input id="competition-search" type="search" placeholder="Cerca per nome, paese, slug o stato" oninput="renderCompetitionsTable()">
      </label>
    </div>
    <div id="competitions-summary" class="summary-grid"></div>
    <div id="competitions-feedback" class="feedback muted">Caricamento campionati...</div>
    <div id="competitions-table"></div>
  </section>

  <section id="markets" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Mercati</h2>
        <p class="muted">Seleziona i mercati MVP supportati da monitorare.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadMonitoredMarkets()">Aggiorna mercati</button>
        <button onclick="addSuggestedMarkets()">Carica mercati suggeriti</button>
      </div>
    </div>
    <div id="markets-feedback" class="feedback muted">Caricamento mercati...</div>
    <div id="monitored-markets"></div>
  </section>

  <section id="provider-bookmakers" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Bookmaker</h2>
        <p class="muted">Configura i bookmaker selezionati su Odds-API.io senza modificare file .env o codice.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadProviderBookmakerSettings()">Ricarica bookmaker</button>
      </div>
    </div>
    <div id="provider-bookmakers-summary" class="info-box">Caricamento bookmaker...</div>
    <div class="form-grid">
      <label>Bookmaker configurati
        <input id="provider-bookmakers-csv" type="text" placeholder="Stake,Sbobet">
      </label>
      <button class="primary" onclick="saveProviderBookmakerSettings()">Salva bookmaker</button>
    </div>
    <div id="provider-bookmakers-feedback" class="feedback muted">Caricamento bookmaker...</div>
  </section>

  <section id="provider-plan" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Piano API</h2>
        <p class="muted">Configura i limiti del piano Odds-API.io. Se la configurazione stimata supera il limite, l'attivazione dello scheduler viene bloccata.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadProviderPlanSettings()">Ricarica piano API</button>
      </div>
    </div>
    <div id="provider-plan-estimate" class="info-box">Caricamento piano API...</div>
    <div class="form-grid">
      <label>Preset piano
        <select id="provider-plan-preset" onchange="applyProviderPlanPreset()">
          <option value="custom">Custom</option>
          <option value="free-plan">Free Plan</option>
          <option value="starter">Starter</option>
          <option value="growth">Growth</option>
          <option value="pro">Pro</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </label>
      <label>Nome piano
        <input id="provider-plan-name" type="text" placeholder="Free">
      </label>
      <label>Limite richieste/ora
        <input id="provider-hourly-request-limit" type="number" min="0" step="1" placeholder="100">
      </label>
      <label>Bookmaker massimi
        <input id="provider-max-bookmakers" type="number" min="1" max="100" step="1" placeholder="2">
      </label>
      <button class="primary" onclick="saveProviderPlanSettings()">Salva piano API</button>
    </div>
    <div id="provider-plan-feedback" class="feedback muted">Caricamento piano API...</div>

    <div id="provider-usage" class="subsection">
      <div class="section-header">
        <div>
          <h3>Consumo API locale</h3>
          <p class="muted">Questo contatore mostra solo le chiamate registrate localmente da OddSignal nell’ultima ora. Il dato può differire dal pannello ufficiale Odds-API.io, che resta la fonte ufficiale del consumo del piano.</p>
          <p class="muted">I dati della dashboard si aggiornano automaticamente ogni 5 minuti quando la pagina è aperta.</p>
        </div>
        <div class="section-actions">
          <button onclick="loadProviderUsage()">Ricarica consumo API locale</button>
        </div>
      </div>
      <div id="provider-usage-summary" class="info-box">Caricamento consumo API locale...</div>
      <div id="provider-usage-last-updated" class="feedback muted">Ultimo aggiornamento: n/d</div>
      <div id="provider-usage-feedback" class="feedback muted">Caricamento consumo API locale...</div>
    </div>
  </section>

  <section id="automation" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Automazione</h2>
        <p class="muted">Definisce ogni quanto controllare le quote. Se la stima supera il Piano API, lo scheduler non può essere attivato.</p>
      </div>
    </div>
    <div class="section-stack">
      <div class="subsection">
        <div id="scheduler-status"></div>
      </div>

      <div class="subsection">
        <h3>Configurazione automazione</h3>
        <div id="automation-status" class="info-box">Caricamento automazione...</div>
        <div class="form-grid">
          <label>Controllo automatico
            <select id="scheduler-enabled">
              <option value="false">Spento</option>
              <option value="true">Attivo</option>
            </select>
          </label>
          <label>Frequenza controllo
            <select id="scheduler-poll-interval-seconds">
              <option value="3">3 secondi</option>
              <option value="30">30 secondi</option>
              <option value="60">1 minuto</option>
              <option value="300">5 minuti - consigliato</option>
              <option value="900">15 minuti</option>
            </select>
          </label>
          <label>Eventi per ciclo
            <input id="scheduler-event-limit" type="number" min="1" max="10" step="1" placeholder="1">
          </label>
          <button class="primary" onclick="saveSchedulerSettings()">Salva automazione</button>
          <button onclick="loadSchedulerSettings()">Ricarica automazione</button>
        </div>
        <div id="scheduler-settings-feedback" class="feedback muted">Caricamento automazione...</div>
      </div>

      <div id="manual-check" class="subsection">
        <div class="section-header">
          <div>
            <h3>Controllo quote manuale</h3>
            <p class="muted">Esegue subito un controllo quote sui campionati attivi.</p>
          </div>
          <div class="section-actions">
            <button class="primary" onclick="runManualOddsCheck()">Esegui controllo quote ora</button>
          </div>
        </div>
        <div id="manual-odds-check-feedback" class="feedback muted">Nessun controllo eseguito.</div>
      </div>
    </div>
  </section>

  <section id="recipients" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Telegram</h2>
        <p class="muted">Rileva gli account che hanno scritto al bot. Solo gli account attivati manualmente ricevono alert.</p>
      </div>
    </div>
    <div class="info-box">
      <strong>Come collegare Telegram</strong>
      <p class="muted">Apri il bot Telegram configurato per il software, premi Start o invia un messaggio, poi clicca “Rileva account Telegram”.</p>
      <p class="muted">Il codice tecnico della chat viene salvato automaticamente e non deve essere inserito manualmente.</p>
    </div>
    <div class="form-grid">
      <button class="primary" onclick="syncTelegramRecipients()">Rileva account Telegram</button>
      <button onclick="sendTelegramTestMessage()">Invia test Telegram</button>
      <button onclick="loadRecipients()">Aggiorna Telegram</button>
    </div>
    <div id="recipients-feedback" class="feedback muted">Caricamento destinatari...</div>
    <div id="recipients-last-updated" class="feedback muted">Ultimo aggiornamento: n/d</div>
    <div id="recipients-table"></div>
  </section>

  <section id="notification-logs-section" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Storico / Log</h2>
        <p class="muted">Esiti recenti degli invii verso destinatari configurati.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadNotificationLogs()">Aggiorna log</button>
      </div>
    </div>
    <div id="notification-logs"></div>
  </section>

  <section id="technical-area" class="page-section glass-card">
    <div class="section-header">
      <div>
        <h2>Area tecnica</h2>
        <p class="muted">JSON, risposte tecniche e dettagli diagnostici separati dalle pagine operative.</p>
      </div>
    </div>
    <div class="info-box">
      <h3>Automazioni automatiche</h3>
      <div class="summary-grid">
        <div class="summary-card"><div class="summary-label">Dashboard auto refresh</div><div class="summary-value">Attivo</div></div>
        <div class="summary-card"><div class="summary-label">Telegram auto sync</div><div class="summary-value">__TELEGRAM_AUTO_SYNC_STATUS__</div></div>
        <div class="summary-card"><div class="summary-label">Provider competitions auto refresh</div><div class="summary-value">__PROVIDER_COMPETITIONS_AUTO_REFRESH_STATUS__</div></div>
        <div class="summary-card"><div class="summary-label">Odds scheduler</div><div class="summary-value">Separato</div></div>
      </div>
      <p class="muted">I dati della dashboard si aggiornano automaticamente ogni 5 minuti quando la pagina è aperta. Il refresh automatico della dashboard usa solo endpoint locali e non esegue controlli quote.</p>
      <div id="dashboard-auto-refresh-feedback" class="feedback muted">Auto refresh dashboard attivo ogni 5 minuti.</div>
    </div>
    <div class="technical-grid">
      <details>
        <summary>Dettagli tecnici sistema</summary>
        <pre id="system-status">Caricamento...</pre>
      </details>
      <details>
        <summary>JSON tecnico prontezza</summary>
        <pre id="readiness-result">Caricamento...</pre>
      </details>
      <details>
        <summary>JSON tecnico piano API</summary>
        <pre id="provider-plan-result">Caricamento...</pre>
      </details>
      <details>
        <summary>JSON tecnico consumo API locale</summary>
        <pre id="provider-usage-result">Caricamento...</pre>
      </details>
      <details>
        <summary>JSON tecnico bookmaker</summary>
        <pre id="provider-bookmakers-result">Caricamento...</pre>
      </details>
      <details>
        <summary>Risposta tecnica ultimo controllo</summary>
        <div id="manual-odds-check-executed-at" class="feedback muted">Ultimo controllo eseguito: n/d</div>
        <div id="manual-odds-check-summary" class="info-box">
          <div class="summary-grid">
            <div class="summary-card"><div class="summary-label">Quote ricevute</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Quote processate</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Quote escluse per mercati non ancora supportati</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Snapshot inseriti</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Quote invariate</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Alert generati</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Notifiche Telegram create</div><div class="summary-value">n/d</div></div>
            <div class="summary-card"><div class="summary-label">Duplicati alert evitati</div><div class="summary-value">n/d</div></div>
          </div>
          <p class="secondary-text">Le quote escluse non sono errori: indicano mercati ricevuti dal provider ma non ancora supportati o volutamente non monitorati.</p>
          <p class="secondary-text">Mercati esclusi principali: n/d</p>
        </div>
        <pre id="manual-odds-check-result">Nessun controllo eseguito.</pre>
      </details>
      <details>
        <summary>JSON tecnico impostazioni alert</summary>
        <pre id="alert-settings-result">Caricamento...</pre>
      </details>
    </div>
  </section>

<script>
function showPage(pageId, event) {
  if (event && typeof event.preventDefault === "function") {
    event.preventDefault();
  }

  const target = document.getElementById(pageId);
  if (!target) {
    return;
  }

  document.querySelectorAll(".page-section").forEach((section) => {
    section.classList.remove("active");
  });
  target.classList.add("active");

  document.querySelectorAll(".sidebar-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === pageId);
  });
}

async function api(path, options) {
  const response = await fetch(path, options || {});
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const payload = JSON.parse(text);
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload.detail && payload.detail.message) {
        message = payload.detail.message;
      }
    } catch (error) {
      message = text;
    }
    throw new Error(response.status + " " + message);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const dashboardState = {
  system: {},
  readiness: null,
  providerUsage: null,
  competitions: [],
  activeCompetitions: "...",
  activeMarkets: "...",
  activeRecipients: "...",
  lastManualCheck: "Nessuno"
};

const DASHBOARD_AUTO_REFRESH_INTERVAL_MS = 300000;
const PROVIDER_USAGE_AUTO_REFRESH_INTERVAL_MS = 300000;
let dashboardAutoRefreshIntervalId = null;

const suggestedFootballMarkets = [
  "1X2",
  "Doppia chance",
  "Pareggio escluso",
  "Goal/No Goal",
  "Handicap asiatico",
  "Over/Under 0.5",
  "Over/Under 1.5",
  "Over/Under 2.5",
  "Over/Under 3.5",
  "Handicap europeo",
  "Risultato esatto",
  "Risultato primo tempo",
  "Primo tempo/finale",
  "Totale corner",
  "Handicap corner",
  "Totale cartellini",
  "Marcatori",
  "Primo marcatore",
  "Entrambe segnano nel primo tempo"
];

const activeSuggestedFootballMarkets = new Set([
  "1X2",
  "Doppia chance",
  "Pareggio escluso",
  "Goal/No Goal",
  "Handicap asiatico",
  "Over/Under 0.5",
  "Over/Under 1.5",
  "Over/Under 2.5",
  "Over/Under 3.5"
]);

function setFeedback(elementId, message, type) {
  const element = document.getElementById(elementId);
  if (!element) {
    return;
  }

  element.className = "feedback" + (type ? " " + type : " muted");
  element.textContent = message;
}

function summaryCard(label, value) {
  return `
    <div class="summary-card">
      <div class="summary-label">${escapeHtml(label)}</div>
      <div class="summary-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function humanizeSeconds(seconds) {
  const value = Number(seconds || 0);
  if (value >= 3600) {
    return `${Math.round(value / 3600)} ore`;
  }
  if (value >= 60) {
    return `${Math.round(value / 60)} minuti`;
  }
  return `${value} secondi`;
}

function readableMarketName(marketName) {
  if (!marketName) {
    return "Mercato non specificato";
  }

  if (marketName === "ML") {
    return "1X2";
  }

  if (marketName.startsWith("Totals")) {
    const suffix = marketName.replace("Totals", "").trim();
    return "Over/Under" + (suffix ? ` ${suffix}` : "");
  }

  if (marketName.startsWith("Both Teams To Score")) {
    return "Goal/No Goal";
  }

  if (marketName.startsWith("Spread")) {
    const suffix = marketName.replace("Spread", "").trim();
    return "Handicap asiatico" + (suffix ? ` ${suffix}` : "");
  }

  if (marketName === "Double Chance") {
    return "Doppia chance";
  }

  if (marketName === "Draw No Bet") {
    return "Pareggio escluso";
  }

  if (marketName.startsWith("European Handicap")) {
    const suffix = marketName.replace("European Handicap", "").trim();
    return "Handicap europeo" + (suffix ? ` ${suffix}` : "");
  }

  return marketName;
}


function readableAlertType(alertType) {
  if (alertType === "critical_alert") {
    return "Critico";
  }

  if (alertType === "standard_alert") {
    return "Standard";
  }

  return alertType || "n/d";
}

function alertTypeBadgeClass(alertType) {
  return alertType === "critical_alert" ? "badge warn" : "badge ok";
}

function readableNotificationStatus(status) {
  if (status === "sent") {
    return "Inviato";
  }

  if (status === "skipped") {
    return "Non inviato";
  }

  if (status === "failed") {
    return "Errore";
  }

  return status || "n/d";
}

function notificationStatusBadgeClass(status) {
  if (status === "sent") {
    return "badge ok";
  }

  if (status === "failed") {
    return "badge warn";
  }

  return "badge";
}

function formatDateTime(value) {
  if (!value) {
    return "n/d";
  }

  return String(value).replace("T", " ").slice(0, 19);
}

function formatLocalDateTime(value) {
  if (!value) {
    return "n/d";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return formatDateTime(value);
  }

  return parsed.toLocaleString("it-IT");
}

function renderManualOddsCheckSummary(data) {
  const summaryBox = document.getElementById("manual-odds-check-summary");
  if (!summaryBox) {
    return;
  }

  const safeData = data || {};
  const metrics = [
    ["Quote ricevute", safeData.odds_received ?? "n/d"],
    ["Quote processate", safeData.odds_processed ?? "n/d"],
    ["Quote escluse per mercati non ancora supportati", safeData.odds_excluded ?? "n/d"],
    ["Snapshot inseriti", safeData.snapshots_inserted ?? "n/d"],
    ["Quote invariate", safeData.snapshots_unchanged ?? "n/d"],
    ["Alert generati", safeData.alerts_created ?? "n/d"],
    ["Notifiche Telegram create", safeData.notification_logs_created ?? "n/d"],
    ["Duplicati alert evitati", safeData.duplicate_alerts_skipped ?? "n/d"]
  ];
  const unsupportedMarkets = Object.entries(
    safeData.excluded_market_breakdown_by_name?.unsupported_market || {}
  )
    .sort((left, right) => right[1] - left[1])
    .slice(0, 8)
    .map(([marketName]) => marketName);
  const excludedMarketsText = unsupportedMarkets.length ? unsupportedMarkets.join(", ") : "n/d";

  summaryBox.innerHTML = `
    <div class="summary-grid">
      ${metrics.map(([label, value]) => summaryCard(label, value)).join("")}
    </div>
    <p class="secondary-text">Le quote escluse non sono errori: indicano mercati ricevuti dal provider ma non ancora supportati o volutamente non monitorati.</p>
    <p class="secondary-text">Mercati esclusi principali: ${escapeHtml(excludedMarketsText)}</p>
  `;
}

function renderDashboardSummary(data) {
  if (data) {
    dashboardState.system = data;
  }

  const system = dashboardState.system || {};
  const scheduler = system.scheduler || {};
  const counts = system.database_counts || {};
  const schedulerValue = scheduler.enabled === true ? "Attivo" : "Spento";
  const readiness = dashboardState.readiness;
  const readinessValue = readiness
    ? (readiness.ready ? "Pronto" : "Da verificare")
    : "...";
  const providerUsage = dashboardState.providerUsage;
  let providerUsageValue = "...";

  if (providerUsage) {
    if (providerUsage.cooldown_active) {
      providerUsageValue = "Cooldown";
    } else if (providerUsage.limit_reached) {
      providerUsageValue = "Limite raggiunto";
    } else {
      providerUsageValue = "OK";
    }
  }

  const telegramValue = dashboardState.activeRecipients === "..."
    ? "..."
    : `${dashboardState.activeRecipients} attivi`;

  const dashboardSummary = document.getElementById("dashboard-summary");
  if (dashboardSummary) {
    dashboardSummary.innerHTML = [
      summaryCard("Sistema", readinessValue),
      summaryCard("Monitoraggio", schedulerValue),
      summaryCard("API locale", providerUsageValue),
      summaryCard("Telegram", telegramValue)
    ].join("");
  }

  const overviewMetrics = document.getElementById("overview-metrics");
  if (overviewMetrics) {
    overviewMetrics.innerHTML = [
      summaryCard("Campionati attivi", dashboardState.activeCompetitions),
      summaryCard("Mercati attivi", dashboardState.activeMarkets),
      summaryCard("Ultimo controllo", dashboardState.lastManualCheck),
      summaryCard("Alert recenti", counts.alerts ?? 0),
      summaryCard("Log notifiche", counts.notification_logs ?? 0)
    ].join("");
  }
}

function renderAutomationStatus(data) {
  const scheduler = data.scheduler || {};
  const alerts = data.alerts || {};
  const schedulerEnabled = scheduler.enabled === true;
  const intervalLabel = humanizeSeconds(scheduler.poll_interval_seconds);
  const eventLimit = scheduler.event_limit ?? "n/d";
  const cooldownMinutes = alerts.deduplication_minutes ?? "n/d";

  document.getElementById("automation-status").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Controllo automatico", schedulerEnabled ? "Attivo" : "Spento")}
      ${summaryCard("Frequenza controllo", intervalLabel)}
      ${summaryCard("Eventi per ciclo", eventLimit)}
      ${summaryCard("Cooldown notifiche", `${cooldownMinutes} min`)}
    </div>
  `;

  document.getElementById("scheduler-status").innerHTML = `
    <div class="info-box">
      <strong>Come funziona</strong>
      <p class="muted">
        Lo scheduler controlla periodicamente le quote e confronta i nuovi valori con lo storico salvato.
      </p>
      <p class="muted">
        La frequenza controllo indica ogni quanti secondi o minuti viene eseguito il ciclo; eventi per ciclo indica quanti eventi vengono analizzati a ogni ciclo di controllo.
      </p>
      <p class="muted">
        Aumentare eventi per ciclo aumenta il consumo API. Con Free Plan conviene tenere pochi eventi per ciclo.
      </p>
      <p class="muted">
        Se lo scheduler è spento non partono controlli automatici e non vengono generate notifiche automatiche.
      </p>
      <p class="muted">
        Il controllo quote manuale serve per test o verifiche occasionali e può consumare richieste API.
      </p>
      <p class="muted">
        Stato attuale: ${schedulerEnabled
          ? `attivo, fino a ${escapeHtml(eventLimit)} evento/i ogni ${escapeHtml(intervalLabel)}.`
          : "spento."}
        Cooldown notifiche: ${escapeHtml(cooldownMinutes)} minuti.
      </p>
    </div>
  `;
}

async function loadStatus() {
  const data = await api("/system/status");

  renderDashboardSummary(data);
  renderAutomationStatus(data);

  document.getElementById("system-status").textContent = JSON.stringify(data, null, 2);
}

async function runManualOddsCheck() {
  const resultBox = document.getElementById("manual-odds-check-result");
  const executedAtBox = document.getElementById("manual-odds-check-executed-at");
  setFeedback("manual-odds-check-feedback", "Controllo quote in corso...", "");
  resultBox.textContent = "Controllo in corso...";
  executedAtBox.textContent = "Ultimo controllo eseguito: controllo in corso...";
  renderManualOddsCheckSummary({
    odds_received: "...",
    odds_processed: "...",
    odds_excluded: "...",
    snapshots_inserted: "...",
    snapshots_unchanged: "...",
    alerts_created: "...",
    notification_logs_created: "...",
    duplicate_alerts_skipped: "..."
  });

  try {
    const data = await api("/api/odds-provider/ingest-sample?limit=1", {
      method: "POST"
    });

    resultBox.textContent = JSON.stringify(data, null, 2);
    executedAtBox.textContent = `Ultimo controllo eseguito: ${formatLocalDateTime(data.executed_at)}`;
    renderManualOddsCheckSummary(data);
    dashboardState.lastManualCheck = "OK";
    renderDashboardSummary();
    setFeedback("manual-odds-check-feedback", "Controllo quote completato. Dashboard aggiornata.", "success");

    await loadStatus();
    await loadAlerts();
    await loadNotificationLogs();
  } catch (error) {
    resultBox.textContent = "Errore controllo quote: " + error.message;
    executedAtBox.textContent = "Ultimo controllo eseguito: errore";
    renderManualOddsCheckSummary({
      odds_received: "errore",
      odds_processed: "errore",
      odds_excluded: "errore",
      snapshots_inserted: "errore",
      snapshots_unchanged: "errore",
      alerts_created: "errore",
      notification_logs_created: "errore",
      duplicate_alerts_skipped: "errore"
    });
    dashboardState.lastManualCheck = "Errore";
    renderDashboardSummary();
    setFeedback("manual-odds-check-feedback", "Controllo quote non completato. " + error.message, "error");
  }
}

async function loadAlertSettings() {
  const data = await api("/configuration/alert-settings");

  document.getElementById("alert-min-percent").value = data.min_percent;
  document.getElementById("alert-max-percent").value = data.max_percent;
  document.getElementById("alert-critical-percent").value = data.critical_percent;
  document.getElementById("alert-deduplication-minutes").value = data.deduplication_minutes;
  document.getElementById("alert-settings-result").textContent = JSON.stringify(data, null, 2);
  setFeedback("alert-settings-feedback", "Impostazioni alert caricate.", "success");
  if (dashboardState.system.alerts) {
    dashboardState.system.alerts.deduplication_minutes = data.deduplication_minutes;
    renderAutomationStatus(dashboardState.system);
  }
}

async function loadSchedulerSettings() {
  const data = await api("/configuration/scheduler-settings");

  document.getElementById("scheduler-enabled").value = String(data.enabled);
  document.getElementById("scheduler-poll-interval-seconds").value = String(data.poll_interval_seconds);
  document.getElementById("scheduler-event-limit").value = data.event_limit;
  setFeedback("scheduler-settings-feedback", "Impostazioni automazione caricate.", "success");

  await loadStatus();
}


async function saveSchedulerSettings() {
  const payload = {
    enabled: document.getElementById("scheduler-enabled").value === "true",
    poll_interval_seconds: Number(document.getElementById("scheduler-poll-interval-seconds").value),
    event_limit: Number(document.getElementById("scheduler-event-limit").value)
  };

  setFeedback("scheduler-settings-feedback", "Salvataggio automazione...", "");

  try {
    await api("/configuration/scheduler-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    setFeedback("scheduler-settings-feedback", "Automazione salvata. Le nuove impostazioni vengono applicate dal prossimo ciclo scheduler.", "success");
    await loadSchedulerSettings();
  } catch (error) {
    if (String(error.message).includes("troppo aggressiva per il piano API")) {
      setFeedback(
        "scheduler-settings-feedback",
        "Scheduler non attivato: la configurazione supera il limite richieste del Piano API. Riduci eventi per ciclo, aumenta l’intervallo di controllo oppure aggiorna il Piano API. Dettaglio tecnico: " + error.message,
        "error"
      );
      await loadProviderPlanSettings();
      return;
    }

    if (String(error.message).includes("Configurazione bookmaker non compatibile")) {
      setFeedback(
        "scheduler-settings-feedback",
        "Scheduler non attivato: i bookmaker configurati superano il limite del Piano API. Riduci i bookmaker nella sezione Bookmaker provider oppure seleziona un piano superiore. Dettaglio tecnico: " + error.message,
        "error"
      );
      await loadProviderPlanSettings();
      await loadProviderBookmakerSettings();
      return;
    }

    setFeedback("scheduler-settings-feedback", "Automazione non salvata: " + error.message, "error");
  }
}



function applyProviderPlanPreset() {
  const preset = document.getElementById("provider-plan-preset").value;

  if (preset === "free-plan") {
    document.getElementById("provider-plan-name").value = "Free Plan";
    document.getElementById("provider-hourly-request-limit").value = "100";
    document.getElementById("provider-max-bookmakers").value = "2";
  } else if (preset === "starter") {
    document.getElementById("provider-plan-name").value = "Starter";
    document.getElementById("provider-hourly-request-limit").value = "5000";
    document.getElementById("provider-max-bookmakers").value = "5";
  } else if (preset === "growth") {
    document.getElementById("provider-plan-name").value = "Growth";
    document.getElementById("provider-hourly-request-limit").value = "5000";
    document.getElementById("provider-max-bookmakers").value = "10";
  } else if (preset === "pro") {
    document.getElementById("provider-plan-name").value = "Pro";
    document.getElementById("provider-hourly-request-limit").value = "5000";
    document.getElementById("provider-max-bookmakers").value = "15";
  } else if (preset === "enterprise") {
    document.getElementById("provider-plan-name").value = "Enterprise";
    document.getElementById("provider-hourly-request-limit").value = "0";
    document.getElementById("provider-max-bookmakers").value = "100";
  }
}


function renderProviderPlanEstimate(data) {
  const estimate = data.usage_estimate;
  const limitLabel = data.hourly_request_limit === null ? "Illimitato" : `${data.hourly_request_limit}/h`;
  const statusClass = estimate.exceeds_hourly_limit ? "badge warn" : "badge ok";
  const statusLabel = estimate.exceeds_hourly_limit ? "Supera limite" : "OK";

  document.getElementById("provider-plan-estimate").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Piano", data.plan_name)}
      ${summaryCard("Limite richieste", limitLabel)}
      ${summaryCard("Bookmaker max", data.max_bookmakers)}
      ${summaryCard("Stima richieste/h", estimate.estimated_requests_per_hour)}
    </div>
    <p><span class="${statusClass}">${statusLabel}</span></p>
    <p class="muted">
      Campionati attivi mappati: ${escapeHtml(estimate.active_mapped_competitions_count)}.
      Eventi per ciclo: ${escapeHtml(estimate.event_limit)}.
      Cicli/ora stimati: ${escapeHtml(estimate.cycles_per_hour)}.
      Richieste/ciclo stimate: ${escapeHtml(estimate.estimated_requests_per_cycle)}.
    </p>
    <p class="muted">${escapeHtml(estimate.recommendation)}</p>
  `;
}


function syncProviderPlanPreset(data) {
  if (data.plan_name === "Free Plan" && data.hourly_request_limit === 100 && data.max_bookmakers === 2) {
    document.getElementById("provider-plan-preset").value = "free-plan";
  } else if (data.plan_name === "Starter" && data.hourly_request_limit === 5000 && data.max_bookmakers === 5) {
    document.getElementById("provider-plan-preset").value = "starter";
  } else if (data.plan_name === "Growth" && data.hourly_request_limit === 5000 && data.max_bookmakers === 10) {
    document.getElementById("provider-plan-preset").value = "growth";
  } else if (data.plan_name === "Pro" && data.hourly_request_limit === 5000 && data.max_bookmakers === 15) {
    document.getElementById("provider-plan-preset").value = "pro";
  } else if (data.plan_name === "Enterprise" && data.hourly_request_limit === null) {
    document.getElementById("provider-plan-preset").value = "enterprise";
  } else {
    document.getElementById("provider-plan-preset").value = "custom";
  }
}


async function loadProviderPlanSettings() {
  const data = await api("/configuration/provider-plan-settings");

  syncProviderPlanPreset(data);
  document.getElementById("provider-plan-name").value = data.plan_name;
  document.getElementById("provider-hourly-request-limit").value = data.hourly_request_limit === null ? "0" : data.hourly_request_limit;
  document.getElementById("provider-max-bookmakers").value = data.max_bookmakers;
  document.getElementById("provider-plan-result").textContent = JSON.stringify(data, null, 2);
  renderProviderPlanEstimate(data);
  setFeedback("provider-plan-feedback", "Piano API caricato.", "success");
}


async function saveProviderPlanSettings() {
  const rawLimit = Number(document.getElementById("provider-hourly-request-limit").value);
  const payload = {
    plan_name: document.getElementById("provider-plan-name").value,
    hourly_request_limit: rawLimit <= 0 ? null : rawLimit,
    max_bookmakers: Number(document.getElementById("provider-max-bookmakers").value)
  };

  setFeedback("provider-plan-feedback", "Salvataggio piano API...", "");

  try {
    const data = await api("/configuration/provider-plan-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    document.getElementById("provider-plan-result").textContent = JSON.stringify(data, null, 2);
    renderProviderPlanEstimate(data);
    syncProviderPlanPreset(data);
    await loadProviderUsage();
    await loadProviderBookmakerSettings();
    setFeedback("provider-plan-feedback", "Piano API salvato.", "success");
  } catch (error) {
    setFeedback("provider-plan-feedback", "Piano API non salvato: " + error.message, "error");
  }
}





function readinessBadge(ok) {
  return ok ? '<span class="badge ok">OK</span>' : '<span class="badge warn">Da verificare</span>';
}


function renderReadiness(data) {
  const readyStatus = data.ready ? '<span class="badge ok">Sistema pronto</span>' : '<span class="badge warn">Sistema non pronto</span>';
  const autoStatus = data.automatic_monitoring_ready
    ? '<span class="badge ok">Monitoraggio automatico attivo</span>'
    : '<span class="badge warn">Monitoraggio automatico non attivo</span>';

  const checks = data.checks || {};
  const issues = data.issues || [];
  const warnings = data.warnings || [];

  const issueHtml = issues.length
    ? `<ul>${issues.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : '<p class="muted">Nessun problema bloccante.</p>';

  const warningHtml = warnings.length
    ? `<ul>${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : '<p class="muted">Nessun avviso.</p>';

  document.getElementById("readiness-summary").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Sistema", data.ready ? "Pronto" : "Non pronto")}
      ${summaryCard("Monitoraggio", data.automatic_monitoring_ready ? "Attivo" : "Non attivo")}
      ${summaryCard("Scheduler", data.scheduler_enabled ? "Acceso" : "Spento")}
    </div>
    <p>${readyStatus} ${autoStatus}</p>

    <table>
      <thead>
        <tr>
          <th>Controllo</th>
          <th>Stato</th>
          <th>Messaggio</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Consumo API locale</td>
          <td>${readinessBadge(checks.provider_usage && checks.provider_usage.ok)}</td>
          <td>${escapeHtml(checks.provider_usage ? checks.provider_usage.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Piano API</td>
          <td>${readinessBadge(checks.provider_plan && checks.provider_plan.ok)}</td>
          <td>${escapeHtml(checks.provider_plan ? checks.provider_plan.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Bookmaker</td>
          <td>${readinessBadge(checks.bookmakers && checks.bookmakers.ok)}</td>
          <td>${escapeHtml(checks.bookmakers ? checks.bookmakers.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Campionati</td>
          <td>${readinessBadge(checks.competitions && checks.competitions.ok)}</td>
          <td>${escapeHtml(checks.competitions ? checks.competitions.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Mercati</td>
          <td>${readinessBadge(checks.markets && checks.markets.ok)}</td>
          <td>${escapeHtml(checks.markets ? checks.markets.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Telegram</td>
          <td>${readinessBadge(checks.telegram && checks.telegram.ok)}</td>
          <td>${escapeHtml(checks.telegram ? checks.telegram.message : "n/d")}</td>
        </tr>
        <tr>
          <td>Scheduler</td>
          <td>${readinessBadge(checks.scheduler && checks.scheduler.enabled)}</td>
          <td>${escapeHtml(checks.scheduler ? checks.scheduler.message : "n/d")}</td>
        </tr>
      </tbody>
    </table>

    <h3>Problemi bloccanti</h3>
    ${issueHtml}
    <h3>Avvisi</h3>
    ${warningHtml}
  `;
}


async function loadReadiness() {
  try {
    const data = await api("/system/readiness");

    dashboardState.readiness = data;
    document.getElementById("readiness-result").textContent = JSON.stringify(data, null, 2);
    renderReadiness(data);
    renderDashboardSummary();
    setFeedback("readiness-feedback", "Sistema caricato.", "success");
  } catch (error) {
    setFeedback("readiness-feedback", "Sistema non caricato: " + error.message, "error");
  }
}


function renderProviderUsage(data) {
  const limitLabel = data.hourly_request_limit === null ? "Illimitato" : `${data.hourly_request_limit}/h`;
  const usedLabel = data.hourly_request_limit === null
    ? `${data.requests_used_last_hour}`
    : `${data.requests_used_last_hour}/${data.hourly_request_limit}`;
  const remainingLabel = data.requests_remaining === null ? "n/d" : data.requests_remaining;
  const cooldownLabel = data.cooldown_active ? "Attivo" : "Non attivo";

  let statusClass = "badge ok";
  let statusLabel = "OK";

  if (data.cooldown_active) {
    statusClass = "badge warn";
    statusLabel = "Cooldown provider attivo";
  } else if (data.limit_reached) {
    statusClass = "badge warn";
    statusLabel = "Limite raggiunto";
  }

  const cooldownDetails = data.cooldown_active
    ? `<p class="muted"><strong>Cooldown fino a:</strong> ${escapeHtml(data.cooldown_until || "n/d")}</p>
       <p class="muted"><strong>Motivo:</strong> ${escapeHtml(data.cooldown_reason || "n/d")}</p>`
    : "";

  document.getElementById("provider-usage-summary").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Provider", data.provider)}
      ${summaryCard("Usate ultima ora", usedLabel)}
      ${summaryCard("Residue", remainingLabel)}
      ${summaryCard("Limite piano", limitLabel)}
      ${summaryCard("Cooldown", cooldownLabel)}
    </div>
    <p><span class="${statusClass}">${statusLabel}</span></p>
    <p class="muted">${escapeHtml(data.message)}</p>
    ${cooldownDetails}
  `;
}


async function loadProviderUsage(options) {
  const isAutoRefresh = options && options.auto === true;

  try {
    const data = await api("/system/provider-usage");

    dashboardState.providerUsage = data;
    document.getElementById("provider-usage-result").textContent = JSON.stringify(data, null, 2);
    renderProviderUsage(data);
    renderDashboardSummary();
    document.getElementById("provider-usage-last-updated").textContent =
      `Ultimo aggiornamento: ${new Date().toLocaleString("it-IT")}`;
    setFeedback(
      "provider-usage-feedback",
      isAutoRefresh
        ? "Consumo API locale aggiornato automaticamente."
        : "Consumo API locale caricato.",
      "success"
    );
  } catch (error) {
    setFeedback(
      "provider-usage-feedback",
      isAutoRefresh
        ? "Aggiornamento automatico consumo API locale non completato: " + error.message
        : "Consumo API locale non caricato: " + error.message,
      "error"
    );
  }
}


function startProviderUsageAutoRefresh() {
  startDashboardAutoRefresh();
}


async function refreshDashboardDataAutomatically() {
  const refreshTasks = [
    loadStatus(),
    loadReadiness(),
    loadProviderUsage({auto: true}),
    loadAlertSettings(),
    loadSchedulerSettings(),
    loadProviderPlanSettings(),
    loadProviderBookmakerSettings(),
    loadCompetitions(),
    loadMonitoredMarkets(),
    loadRecipients(),
    loadAlerts(),
    loadNotificationLogs()
  ];

  const results = await Promise.allSettled(refreshTasks);
  const failures = results.filter((item) => item.status === "rejected");

  if (failures.length > 0) {
    setFeedback(
      "dashboard-auto-refresh-feedback",
      `Auto refresh dashboard completato con ${failures.length} errori non bloccanti.`,
      "error"
    );
    return;
  }

  setFeedback(
    "dashboard-auto-refresh-feedback",
    `Auto refresh dashboard completato: ${new Date().toLocaleString("it-IT")}.`,
    "success"
  );
}


function startDashboardAutoRefresh() {
  if (dashboardAutoRefreshIntervalId !== null) {
    return;
  }

  dashboardAutoRefreshIntervalId = window.setInterval(() => {
    refreshDashboardDataAutomatically();
  }, DASHBOARD_AUTO_REFRESH_INTERVAL_MS);
}


function renderProviderBookmakerSettings(data) {
  const statusClass = data.exceeds_bookmaker_limit ? "badge warn" : "badge ok";
  const statusLabel = data.exceeds_bookmaker_limit ? "Supera limite" : "OK";

  document.getElementById("provider-bookmakers-summary").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Bookmaker configurati", data.bookmaker_count)}
      ${summaryCard("Limite piano", data.max_bookmakers)}
      ${summaryCard("Stato", statusLabel)}
    </div>
    <p><span class="${statusClass}">${statusLabel}</span></p>
    <p class="muted">
      Bookmaker attivi: ${escapeHtml(data.bookmakers.join(", ") || "n/d")}.
    </p>
  `;
}


async function loadProviderBookmakerSettings() {
  const data = await api("/configuration/provider-bookmaker-settings");

  document.getElementById("provider-bookmakers-csv").value = data.bookmakers_csv;
  document.getElementById("provider-bookmakers-result").textContent = JSON.stringify(data, null, 2);
  renderProviderBookmakerSettings(data);
  setFeedback("provider-bookmakers-feedback", "Bookmaker provider caricati.", "success");
}


async function saveProviderBookmakerSettings() {
  const payload = {
    bookmakers_csv: document.getElementById("provider-bookmakers-csv").value
  };

  setFeedback("provider-bookmakers-feedback", "Salvataggio bookmaker provider...", "");

  try {
    const data = await api("/configuration/provider-bookmaker-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    document.getElementById("provider-bookmakers-result").textContent = JSON.stringify(data, null, 2);
    document.getElementById("provider-bookmakers-csv").value = data.bookmakers_csv;
    renderProviderBookmakerSettings(data);
    await loadStatus();
    setFeedback("provider-bookmakers-feedback", "Bookmaker provider salvati.", "success");
  } catch (error) {
    setFeedback(
      "provider-bookmakers-feedback",
      "Bookmaker provider non salvati: " + error.message,
      "error"
    );
  }
}


async function saveAlertSettings() {
  setFeedback("alert-settings-feedback", "Salvataggio impostazioni alert...", "");

  const payload = {
    min_percent: Number(document.getElementById("alert-min-percent").value),
    max_percent: Number(document.getElementById("alert-max-percent").value),
    critical_percent: Number(document.getElementById("alert-critical-percent").value),
    deduplication_minutes: Number(document.getElementById("alert-deduplication-minutes").value)
  };

  try {
    const data = await api("/configuration/alert-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    document.getElementById("alert-settings-result").textContent = JSON.stringify(data, null, 2);
    setFeedback("alert-settings-feedback", "Impostazioni alert salvate.", "success");
    await loadStatus();
  } catch (error) {
    document.getElementById("alert-settings-result").textContent = "Errore impostazioni alert: " + error.message;
    setFeedback("alert-settings-feedback", "Impostazioni alert non salvate: " + error.message, "error");
  }
}

async function loadCompetitions() {
  const data = await api("/configuration/available-competitions");
  dashboardState.competitions = data;
  const activeCompetitions = data.filter((item) => item.is_active);
  const inactiveCompetitions = data.filter((item) => !item.is_active);

  dashboardState.activeCompetitions = activeCompetitions.length;
  renderDashboardSummary();

  document.getElementById("competitions-summary").innerHTML = [
    summaryCard("Campionati attivi", activeCompetitions.length),
    summaryCard("Campionati disponibili", data.length),
    summaryCard("Non attivi", inactiveCompetitions.length)
  ].join("");

  renderCompetitionsTable();
  setFeedback("competitions-feedback", `Campionati disponibili: ${data.length}. Attivi: ${activeCompetitions.length}.`, "success");
}

function renderCompetitionsTable() {
  const data = dashboardState.competitions || [];
  const query = (document.getElementById("competition-search")?.value || "").trim().toLowerCase();
  const activeCompetitions = data.filter((item) => item.is_active);
  const inactiveCompetitions = data.filter((item) => !item.is_active);
  const orderedCompetitions = activeCompetitions.concat(inactiveCompetitions);
  const filteredCompetitions = orderedCompetitions.filter((item) => {
    const isMapped = Boolean(item.provider_league_slug);
    const status = isMapped ? (item.is_active ? "Attivo" : "Non attivo") : "Non monitorabile";
    const normalizedCountry = item.country && item.country !== "Unknown"
      ? item.country
      : ((item.name || "").includes(" - ") ? (item.name || "").split(" - ")[0] : "");
    const searchable = [
      item.name,
      normalizedCountry,
      item.provider_league_slug,
      status
    ].join(" ").toLowerCase();

    return !query || searchable.includes(query);
  });

  let html = "<div class='table-wrap'><table><thead><tr><th>Campionato</th><th>Paese</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";

  for (const item of filteredCompetitions) {
    const isMapped = Boolean(item.provider_league_slug);
    const active = isMapped ? (item.is_active ? "Attivo" : "Non attivo") : "Non monitorabile";
    const badgeClass = item.is_active && isMapped ? "badge ok" : "badge";
    const actionLabel = item.is_active ? "Disattiva" : "Attiva";
    const nextState = item.is_active ? "false" : "true";
    const nameArg = JSON.stringify(item.name || "");
    const normalizedCountry = item.country && item.country !== "Unknown"
      ? item.country
      : ((item.name || "").includes(" - ") ? (item.name || "").split(" - ")[0] : "");
    const countryArg = JSON.stringify(normalizedCountry || "");
    const slugArg = JSON.stringify(item.provider_league_slug || "");
    const mappingInputId = `competition-mapping-${item.name.replace(/[^a-zA-Z0-9]/g, "-")}`;
    const mappingInputIdArg = JSON.stringify(mappingInputId);
    const providerDetail = isMapped
      ? `<details><summary>Provider mappato</summary><span class="secondary-text">${escapeHtml(item.provider_league_slug)}</span></details>`
      : `<div class="inline-actions">
          <input id="${escapeHtml(mappingInputId)}" type="text" placeholder="provider-league-slug">
          <button class="compact" onclick='saveCompetitionProviderMapping(${nameArg}, ${countryArg}, ${mappingInputIdArg})'>Salva mapping</button>
        </div>
        <span class="secondary-text">Inserisci lo slug provider corretto per rendere il campionato monitorabile.</span>`;

    html += `<tr>
      <td>
        <strong>${escapeHtml(item.name)}</strong><br>
        ${providerDetail}
      </td>
      <td>${escapeHtml(normalizedCountry || "n/d")}</td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        ${isMapped
          ? `<button class="compact ${item.is_active ? "" : "primary"}" onclick='monitorCompetition(${nameArg}, ${countryArg}, ${slugArg}, ${nextState})'>${actionLabel}</button>`
          : `<button class="compact" disabled>Non mappato</button>`}
      </td>
    </tr>`;
  }

  html += "</tbody></table></div>";
  document.getElementById("competitions-table").innerHTML = html;

  if (query) {
    setFeedback("competitions-feedback", `Filtro campionati: ${filteredCompetitions.length} risultati su ${data.length}.`, "");
  }
}

async function monitorCompetition(name, country, slug, isActive) {
  setFeedback("competitions-feedback", `${isActive ? "Attivazione" : "Disattivazione"} campionato in corso...`, "");

  try {
    await api("/configuration/monitored-competitions", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        competition_name: name,
        country: country || null,
        provider: "odds_api_io",
        provider_league_slug: slug || null,
        is_active: isActive
      })
    });
    await loadCompetitions();
    setFeedback("competitions-feedback", `Campionato ${isActive ? "attivato" : "disattivato"}: ${name}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("competitions-feedback", "Operazione campionato non completata: " + error.message, "error");
  }
}


async function saveCompetitionProviderMapping(name, country, inputId) {
  const input = document.getElementById(inputId);
  const providerLeagueSlug = input ? input.value.trim() : "";

  if (!providerLeagueSlug) {
    setFeedback("competitions-feedback", "Inserisci uno slug provider prima di salvare il mapping.", "error");
    return;
  }

  setFeedback("competitions-feedback", `Salvataggio mapping provider per ${name}...`, "");

  try {
    await api("/configuration/competitions/provider-mapping", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        competition_name: name,
        country: country || null,
        provider_league_slug: providerLeagueSlug
      })
    });

    await loadCompetitions();
    await loadProviderPlanSettings();
    setFeedback("competitions-feedback", `Mapping provider salvato per ${name}. Ora il campionato è monitorabile.`, "success");
  } catch (error) {
    setFeedback("competitions-feedback", "Mapping provider non salvato: " + error.message, "error");
  }
}

async function refreshProviderCompetitions() {
  setFeedback("competitions-feedback", "Aggiornamento campionati dal provider in corso...", "");

  try {
    const data = await api("/configuration/provider-competitions/refresh?limit=10", {
      method: "POST"
    });

    await loadCompetitions();
    await loadStatus();
    setFeedback(
      "competitions-feedback",
      `Campionati rilevati dagli eventi disponibili ora: ${data.competitions_found} da ${data.events_received} eventi.`,
      "success"
    );
  } catch (error) {
    setFeedback("competitions-feedback", "Aggiornamento campionati non completato. " + error.message, "error");
  }
}


async function refreshProviderLeagues() {
  setFeedback("competitions-feedback", "Aggiornamento leghe e slug dal provider in corso...", "");

  try {
    const data = await api("/configuration/provider-leagues/refresh", {
      method: "POST"
    });

    await loadCompetitions();
    await loadProviderPlanSettings();
    await loadStatus();
    setFeedback(
      "competitions-feedback",
      `Leghe provider aggiornate: ${data.leagues_upserted}. Campionati monitorati aggiornati: ${data.monitored_updated}.`,
      "success"
    );
  } catch (error) {
    setFeedback("competitions-feedback", "Aggiornamento leghe provider non completato. " + error.message, "error");
  }
}

async function loadMonitoredMarkets() {
  const data = await api("/configuration/monitored-markets");
  const existingNames = new Set(data.map((item) => item.market_name));
  const missingSuggestedMarkets = suggestedFootballMarkets.filter((marketName) => !existingNames.has(marketName));
  dashboardState.activeMarkets = data.filter((item) => item.is_active).length;
  renderDashboardSummary();

  let html = "<div class='table-wrap'><table><thead><tr><th>Mercato</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of data) {
    const active = item.is_active ? "Attivo" : "In attesa di attivazione";
    const badgeClass = item.is_active ? "badge ok" : "badge";
    html += `<tr>
      <td><span class="market-name">${escapeHtml(readableMarketName(item.market_name))}</span></td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button class="compact" onclick="toggleMonitoredMarket(${item.id}, true)">Attiva</button>
        <button class="compact" onclick="toggleMonitoredMarket(${item.id}, false)">Disattiva</button>
      </td>
    </tr>`;
  }

  for (const marketName of missingSuggestedMarkets) {
    html += `<tr>
      <td><span class="market-name">${escapeHtml(readableMarketName(marketName))}</span></td>
      <td><span class="badge">Da caricare</span></td>
      <td><button class="compact" onclick="addSuggestedMarkets()">Carica mercati suggeriti</button></td>
    </tr>`;
  }

  html += "</tbody></table></div>";
  document.getElementById("monitored-markets").innerHTML = html;
  setFeedback("markets-feedback", `Mercati configurati: ${data.length}. Suggeriti da caricare: ${missingSuggestedMarkets.length}.`, "success");
}

async function addSuggestedMarkets() {
  setFeedback("markets-feedback", "Caricamento mercati suggeriti...", "");

  try {
    const currentMarkets = await api("/configuration/monitored-markets");
    const existingNames = new Set(currentMarkets.map((item) => item.market_name));
    const marketsToCreate = suggestedFootballMarkets.filter((marketName) => !existingNames.has(marketName));

    for (const marketName of marketsToCreate) {
      await api("/configuration/monitored-markets", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          market_name: marketName,
          is_active: activeSuggestedFootballMarkets.has(marketName)
        })
      });
    }

    await loadMonitoredMarkets();
    setFeedback("markets-feedback", `Mercati suggeriti caricati: ${marketsToCreate.length}. I mercati consigliati sono attivi, gli altri restano in attesa.`, "success");
  } catch (error) {
    setFeedback("markets-feedback", "Mercati suggeriti non caricati: " + error.message, "error");
  }
}

async function toggleMonitoredMarket(marketId, isActive) {
  setFeedback("markets-feedback", `${isActive ? "Attivazione" : "Disattivazione"} mercato in corso...`, "");

  try {
    await api(`/configuration/monitored-markets/${marketId}/toggle?is_active=${isActive}`, {
      method: "PATCH"
    });

    await loadMonitoredMarkets();
    setFeedback("markets-feedback", `Mercato ${isActive ? "attivato" : "disattivato"}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("markets-feedback", "Operazione mercato non completata: " + error.message, "error");
  }
}

async function sendTelegramTestMessage() {
  setFeedback("recipients-feedback", "Invio test Telegram in corso...", "");

  try {
    const data = await api("/configuration/telegram-test-message", {
      method: "POST"
    });

    await loadRecipients();
    await loadStatus();

    const sent = Number(data.sent || 0);
    const failed = Number(data.failed || 0);
    const recipientsCount = Number(data.recipients_count || 0);

    if (sent > 0) {
      setFeedback(
        "recipients-feedback",
        `Test Telegram inviato correttamente. Inviati: ${sent}. Falliti: ${failed}. Destinatari: ${recipientsCount}.`,
        "success"
      );
      return;
    }

    setFeedback(
      "recipients-feedback",
      `Test Telegram completato ma nessun messaggio risulta inviato. Falliti: ${failed}. Destinatari: ${recipientsCount}.`,
      "error"
    );
  } catch (error) {
    await loadRecipients();
    setFeedback("recipients-feedback", "Test Telegram non inviato: " + error.message, "error");
  }
}


async function syncTelegramRecipients() {
  setFeedback("recipients-feedback", "Rilevamento account Telegram in corso...", "");

  try {
    const data = await api("/configuration/telegram-recipients/sync", {
      method: "POST"
    });

    await loadRecipients();
    await loadStatus();

    const newRecipientsCount = Number(data.new_recipients_count || 0);

    if (newRecipientsCount === 0) {
      setFeedback(
        "recipients-feedback",
        "Nessun nuovo account Telegram rilevato. Gli account già configurati restano invariati.",
        "success"
      );
      return;
    }

    setFeedback(
      "recipients-feedback",
      `Nuovi account Telegram rilevati: ${newRecipientsCount}. Attivali manualmente per abilitarli alle notifiche.`,
      "success"
    );
  } catch (error) {
    setFeedback("recipients-feedback", "Rilevamento Telegram non completato: " + error.message, "error");
  }
}


async function loadRecipients() {
  const data = await api("/configuration/notification-recipients");
  const telegramRecipients = data.filter((item) => item.channel === "telegram");
  const activeRecipients = telegramRecipients.filter((item) => item.status === "active");
  const pendingRecipients = telegramRecipients.filter((item) => item.status === "pending");
  const disabledRecipients = telegramRecipients.filter((item) => item.status === "disabled");
  const orderedRecipients = pendingRecipients.concat(activeRecipients, disabledRecipients);

  dashboardState.activeRecipients = activeRecipients.length;
  renderDashboardSummary();
  document.getElementById("recipients-last-updated").textContent =
    `Ultimo aggiornamento: ${new Date().toLocaleString("it-IT")}`;

  if (telegramRecipients.length === 0) {
    document.getElementById("recipients-table").innerHTML = "<p class='muted'>Nessun destinatario Telegram configurato.</p>";
    setFeedback("recipients-feedback", "Apri il bot Telegram, premi Start e clicca Rileva account Telegram.", "");
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Account Telegram</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of orderedRecipients) {
    const statusLabels = {
      pending: "In attesa di attivazione",
      active: "Attivo",
      disabled: "Disattivato"
    };
    const active = statusLabels[item.status] || "In attesa di attivazione";
    const badgeClass = item.status === "active" ? "badge ok" : "badge";
    const actionLabel = item.status === "active" ? "Disattiva" : "Attiva notifiche";
    const nextState = item.status === "active" ? "false" : "true";

    html += `<tr>
      <td><strong>${escapeHtml(item.label || "Telegram")}</strong><br><span class="secondary-text">ID tecnico salvato automaticamente</span></td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button class="compact ${item.is_active ? "" : "primary"}" onclick="toggleRecipient(${item.id}, ${nextState})">${actionLabel}</button>
      </td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("recipients-table").innerHTML = html;
  setFeedback("recipients-feedback", `Account Telegram: ${telegramRecipients.length}. Attivi: ${activeRecipients.length}. In attesa: ${pendingRecipients.length}. Disattivati: ${disabledRecipients.length}.`, "success");
}

async function toggleRecipient(recipientId, isActive) {
  setFeedback("recipients-feedback", `${isActive ? "Attivazione" : "Disattivazione"} destinatario Telegram in corso...`, "");

  try {
    await api(`/configuration/notification-recipients/${recipientId}/toggle?is_active=${isActive}`, {
      method: "PATCH"
    });

    await loadRecipients();
    setFeedback("recipients-feedback", `Destinatario Telegram ${isActive ? "attivato" : "disattivato"}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("recipients-feedback", "Operazione destinatario Telegram non completata: " + error.message, "error");
  }
}

async function loadAlerts() {
  const data = await api("/alerts?limit=20");
  dashboardState.recentAlerts = data;
  renderDashboardSummary();
  renderAlertsTable();
}


function renderAlertsTable() {
  const filterElement = document.getElementById("alerts-filter");
  const filter = filterElement ? filterElement.value : "all";
  const data = dashboardState.recentAlerts || [];

  let filtered = data;
  if (filter === "notifiable") {
    filtered = data.filter((item) => item.direction === "decrease");
  } else if (filter === "increases") {
    filtered = data.filter((item) => item.direction === "increase");
  } else if (filter === "critical") {
    filtered = data.filter((item) => item.alert_type === "critical_alert");
  }

  if (filtered.length === 0) {
    document.getElementById("alerts").innerHTML = "<p class='muted'>Nessun alert per il filtro selezionato.</p>";
    setFeedback("alerts-filter-feedback", `Filtro applicato: ${filtered.length} alert visualizzati su ${data.length}.`, "");
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Evento</th><th>Bookmaker</th><th>Mercato</th><th>Selezione</th><th>Variazione</th><th>Notifica</th><th>Tipo</th><th>Data</th></tr></thead><tbody>";
  for (const item of filtered) {
    const variation = `${item.variation_percent}%`;
    const alertLabel = readableAlertType(item.alert_type);
    const alertBadgeClass = alertTypeBadgeClass(item.alert_type);
    const notificationLabel = item.direction === "decrease" ? "Telegram" : "Solo storico";
    const notificationBadgeClass = item.direction === "decrease" ? "badge ok" : "badge";

    html += `<tr>
      <td><strong>${escapeHtml(item.event)}</strong></td>
      <td>${escapeHtml(item.bookmaker)}</td>
      <td>${escapeHtml(readableMarketName(item.market))}</td>
      <td>${escapeHtml(item.selection)}</td>
      <td><strong>${escapeHtml(variation)}</strong></td>
      <td><span class="${notificationBadgeClass}">${escapeHtml(notificationLabel)}</span></td>
      <td><span class="${alertBadgeClass}">${escapeHtml(alertLabel)}</span></td>
      <td><span class="secondary-text">${escapeHtml(formatDateTime(item.created_at))}</span></td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("alerts").innerHTML = html;
  setFeedback("alerts-filter-feedback", `Filtro applicato: ${filtered.length} alert visualizzati su ${data.length}.`, "success");
}

async function clearRecentAlerts() {
  const confirmed = window.confirm("Cancellare gli alert recenti visualizzati? Quote, configurazioni e log notifiche non verranno cancellati.");
  if (!confirmed) {
    return;
  }

  setFeedback("alerts-filter-feedback", "Cancellazione alert recenti...", "");

  try {
    const data = await api("/alerts/recent?limit=20", {
      method: "DELETE"
    });

    await loadAlerts();
    await loadStatus();
    setFeedback("alerts-filter-feedback", `Alert recenti cancellati: ${data.deleted_count}.`, "success");
  } catch (error) {
    setFeedback("alerts-filter-feedback", "Alert recenti non cancellati: " + error.message, "error");
  }
}

async function loadNotificationLogs() {
  const data = await api("/notification-logs?limit=20");
  if (data.length === 0) {
    document.getElementById("notification-logs").innerHTML = "<p class='muted'>Nessun log notifica recente.</p>";
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Canale</th><th>Stato</th><th>Destinatario</th><th>Dettaglio</th><th>Data</th></tr></thead><tbody>";
  for (const item of data) {
    const statusLabel = readableNotificationStatus(item.status);
    const statusBadgeClass = notificationStatusBadgeClass(item.status);
    const errorDetail = item.error_message ? item.error_message : "Nessun errore";

    html += `<tr>
      <td>Telegram</td>
      <td><span class="${statusBadgeClass}">${escapeHtml(statusLabel)}</span></td>
      <td>${escapeHtml(item.recipient || "n/d")}</td>
      <td><span class="secondary-text">${escapeHtml(errorDetail)}</span></td>
      <td><span class="secondary-text">${escapeHtml(formatDateTime(item.sent_at))}</span></td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("notification-logs").innerHTML = html;
}

loadStatus();
loadAlertSettings();
loadSchedulerSettings();
loadProviderPlanSettings();
loadProviderUsage();
startDashboardAutoRefresh();
loadProviderBookmakerSettings();
loadCompetitions();
loadMonitoredMarkets();
loadRecipients();
loadAlerts();
loadNotificationLogs();
</script>
  </div>
  </main>
  </div>
</body>
</html>
"""
    return (
        html
        .replace("__TELEGRAM_AUTO_SYNC_STATUS__", _env_status_label("TELEGRAM_AUTO_SYNC_ENABLED"))
        .replace(
            "__PROVIDER_COMPETITIONS_AUTO_REFRESH_STATUS__",
            _env_status_label("PROVIDER_COMPETITIONS_AUTO_REFRESH_ENABLED"),
        )
    )
