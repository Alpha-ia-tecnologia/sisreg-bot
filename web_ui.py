import datetime
import threading
import webbrowser
from flask import Flask, jsonify, Response

from bot_state import state
from db import finish_execution, get_executions, get_execution_detail

app = Flask(__name__)
_bot_runner = None  # Set by start_web_ui

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SISREG Bot</title>
<style>
  :root {
    --bg: #0f172a;
    --surface: #1e293b;
    --border: #334155;
    --cyan: #22d3ee;
    --green: #4ade80;
    --red: #f87171;
    --yellow: #facc15;
    --text: #e2e8f0;
    --muted: #94a3b8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* Header */
  .header {
    background: linear-gradient(135deg, #0e1726, #1a2744);
    border-bottom: 1px solid var(--border);
    padding: 1.25rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header h1 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--cyan);
  }
  .header h1 span { color: var(--muted); font-weight: 400; }
  .header-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .pulse {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--green);
    animation: pulse 1.5s infinite;
  }
  .pulse.done { background: var(--cyan); animation: none; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
  }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .card-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 1rem;
  }

  /* Pipeline */
  .pipeline { grid-column: 1 / -1; }
  .steps {
    display: flex;
    gap: 0;
    position: relative;
  }
  .step-item {
    flex: 1;
    text-align: center;
    position: relative;
    padding: 0 0.5rem;
  }
  .step-circle {
    width: 36px; height: 36px;
    border-radius: 50%;
    border: 2px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.5rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--muted);
    background: var(--bg);
    transition: all 0.3s;
  }
  .step-item.done .step-circle {
    border-color: var(--green);
    background: rgba(74, 222, 128, 0.15);
    color: var(--green);
  }
  .step-item.active .step-circle {
    border-color: var(--cyan);
    background: rgba(34, 211, 238, 0.15);
    color: var(--cyan);
    box-shadow: 0 0 12px rgba(34, 211, 238, 0.3);
  }
  .step-label {
    font-size: 0.75rem;
    color: var(--muted);
    transition: color 0.3s;
  }
  .step-item.active .step-label { color: var(--cyan); }
  .step-item.done .step-label { color: var(--green); }
  .step-connector {
    position: absolute;
    top: 18px;
    left: calc(50% + 22px);
    right: calc(-50% + 22px);
    height: 2px;
    background: var(--border);
    z-index: 0;
  }
  .step-item.done .step-connector { background: var(--green); }
  .step-item:last-child .step-connector { display: none; }

  /* Stats */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
  .stat {
    text-align: center;
    padding: 0.75rem;
    background: var(--bg);
    border-radius: 8px;
  }
  .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .stat-label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    margin-top: 0.25rem;
  }
  .stat-sent .stat-value { color: var(--green); }
  .stat-failed .stat-value { color: var(--red); }
  .stat-total .stat-value { color: var(--cyan); }

  /* Progress bar */
  .progress-section { margin-top: 1rem; }
  .progress-bar-bg {
    height: 8px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--cyan), var(--green));
    border-radius: 4px;
    transition: width 0.5s ease;
  }
  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.35rem;
  }

  /* Activity log */
  .log-area {
    max-height: 165px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .log-entry {
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    padding: 0.3rem 0.5rem;
    border-radius: 4px;
    background: var(--bg);
    display: flex;
    gap: 0.75rem;
  }
  .log-time { color: var(--muted); flex-shrink: 0; }
  .log-msg { color: var(--text); }
  .log-entry.step .log-msg { color: var(--cyan); font-weight: 600; }
  .log-entry.done .log-msg { color: var(--green); }
  .log-entry.error .log-msg { color: var(--red); }
  .log-entry.info .log-msg { color: var(--muted); }

  /* Records table */
  .records-section { grid-column: 1 / -1; }
  .table-wrap {
    max-height: 350px;
    overflow-y: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  th {
    text-align: left;
    padding: 0.6rem 0.75rem;
    color: var(--cyan);
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--surface);
  }
  td {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(51, 65, 85, 0.5);
    color: var(--text);
  }
  tr:hover td { background: rgba(34, 211, 238, 0.03); }
  .empty-msg {
    text-align: center;
    padding: 2rem;
    color: var(--muted);
    font-size: 0.85rem;
  }

  /* No records banner */
  .no-records-banner {
    grid-column: 1 / -1;
    text-align: center;
    padding: 2rem;
    border: 1px solid var(--yellow);
    border-radius: 12px;
    background: rgba(250, 204, 21, 0.05);
  }
  .no-records-banner .icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
  .no-records-banner .title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--yellow);
    margin-bottom: 0.35rem;
  }
  .no-records-banner .subtitle { color: var(--muted); font-size: 0.85rem; }

  /* Message status badges */
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .status-badge.sent { background: rgba(74, 222, 128, 0.15); color: var(--green); }
  .status-badge.failed { background: rgba(248, 113, 113, 0.15); color: var(--red); }
  .status-badge.pending { background: rgba(148, 163, 184, 0.1); color: var(--muted); }

  /* Current action */
  .current-action {
    grid-column: 1 / -1;
    text-align: center;
    padding: 0.75rem;
    font-size: 0.95rem;
    color: var(--cyan);
    border: 1px dashed var(--border);
    border-radius: 8px;
    background: rgba(34, 211, 238, 0.03);
  }
  .current-action .detail { color: var(--muted); font-size: 0.8rem; margin-top: 0.25rem; }

  /* Browser view */
  .browser-section { grid-row: span 2; }
  .browser-frame {
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--bg);
    position: relative;
  }
  .browser-toolbar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .browser-dot {
    width: 10px; height: 10px; border-radius: 50%;
  }
  .browser-dot.r { background: #f87171; }
  .browser-dot.y { background: #facc15; }
  .browser-dot.g { background: #4ade80; }
  .browser-url {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.6rem;
    font-size: 0.75rem;
    color: var(--muted);
    font-family: monospace;
  }
  .browser-img-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 450px;
  }
  .browser-img-wrap img {
    width: 100%;
    display: block;
  }
  .browser-placeholder {
    color: var(--muted);
    font-size: 0.85rem;
    padding: 3rem;
  }
  .browser-fullscreen-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--muted);
    cursor: pointer;
    padding: 0.2rem 0.4rem;
    font-size: 0.85rem;
    line-height: 1;
    transition: color 0.2s, border-color 0.2s;
  }
  .browser-fullscreen-btn:hover {
    color: var(--cyan);
    border-color: var(--cyan);
  }
  .browser-frame:fullscreen {
    background: #000;
  }
  .browser-frame:fullscreen .browser-img-wrap {
    min-height: 0;
    height: calc(100vh - 36px);
  }
  .browser-frame:fullscreen .browser-img-wrap img {
    width: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  /* Tab bar */
  .tab-bar {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    padding: 0 2rem;
  }
  .tab-btn {
    background: none; border: none; color: var(--muted);
    padding: 0.75rem 1.5rem; cursor: pointer;
    font-size: 0.85rem; font-weight: 600;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--cyan); border-bottom-color: var(--cyan); }

  /* History */
  .history-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
  }
  .history-table-wrap {
    max-height: 70vh;
    overflow-y: auto;
  }
  .history-table tr { cursor: pointer; }
  .history-table tr:hover td { background: rgba(34, 211, 238, 0.06); }
  .back-btn {
    background: none; border: 1px solid var(--border); color: var(--muted);
    border-radius: 6px; padding: 0.4rem 1rem; cursor: pointer;
    font-size: 0.8rem; margin-bottom: 1rem; transition: all 0.2s;
  }
  .back-btn:hover { color: var(--cyan); border-color: var(--cyan); }
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
  }
  .detail-full { grid-column: 1 / -1; }

  .elapsed-badge {
    background: var(--bg);
    padding: 0.3rem 0.75rem;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--cyan);
  }

  .start-btn {
    background: var(--green);
    color: var(--bg);
    border: none;
    border-radius: 6px;
    padding: 0.4rem 1rem;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s, background 0.2s;
    letter-spacing: 0.03em;
  }
  .start-btn:hover { opacity: 0.85; }
  .start-btn:disabled {
    background: var(--border);
    color: var(--muted);
    cursor: not-allowed;
    opacity: 0.7;
  }
</style>
</head>
<body>

<div class="header">
  <h1>SISREG Bot</h1>
  <div class="header-status">
    <button class="start-btn" id="startBtn" onclick="startBot()">&#9654; Iniciar Bot</button>
    <div class="pulse" id="statusPulse" style="display:none"></div>
    <span id="statusText"></span>
    <span class="elapsed-badge" id="elapsed" style="display:none">0s</span>
  </div>
</div>

<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab('dashboard')">Dashboard</button>
  <button class="tab-btn" onclick="switchTab('history')">Hist&oacute;rico</button>
</div>

<div id="tab-dashboard">
<div class="container">

  <!-- Pipeline -->
  <div class="card pipeline">
    <div class="card-title">Pipeline de Execu&ccedil;&atilde;o</div>
    <div class="steps" id="stepsContainer">
      <div class="step-item" data-step="1">
        <div class="step-connector"></div>
        <div class="step-circle">1</div>
        <div class="step-label">Autentica&ccedil;&atilde;o</div>
      </div>
      <div class="step-item" data-step="2">
        <div class="step-connector"></div>
        <div class="step-circle">2</div>
        <div class="step-label">Extra&ccedil;&atilde;o</div>
      </div>
      <div class="step-item" data-step="3">
        <div class="step-connector"></div>
        <div class="step-circle">3</div>
        <div class="step-label">Processamento</div>
      </div>
      <div class="step-item" data-step="4">
        <div class="step-connector"></div>
        <div class="step-circle">4</div>
        <div class="step-label">Envio</div>
      </div>
    </div>
  </div>

  <!-- Current action -->
  <div class="current-action" id="currentAction">
    <div id="actionLabel">Aguardando in&iacute;cio...</div>
    <div class="detail" id="actionDetail"></div>
  </div>

  <!-- Browser view (left column, spans 2 rows) -->
  <div class="card browser-section">
    <div class="card-title">Navegador do Bot</div>
    <div class="browser-frame">
      <div class="browser-toolbar">
        <div class="browser-dot r"></div>
        <div class="browser-dot y"></div>
        <div class="browser-dot g"></div>
        <div class="browser-url">sisregiii.saude.gov.br</div>
        <button class="browser-fullscreen-btn" onclick="toggleFullscreen()" title="Tela cheia">&#x26F6;</button>
      </div>
      <div class="browser-img-wrap" id="browserWrap">
        <div class="browser-placeholder" id="browserPlaceholder">Clique em "Iniciar Bot" para come&ccedil;ar</div>
        <img id="browserImg" src="" alt="Browser screenshot" style="display:none">
      </div>
    </div>
  </div>

  <!-- Log (right column, row 1) -->
  <div class="card">
    <div class="card-title">Atividade Recente</div>
    <div class="log-area" id="logArea"></div>
  </div>

  <!-- Stats (right column, row 2) -->
  <div class="card">
    <div class="card-title">Mensagens</div>
    <div class="stats-grid">
      <div class="stat stat-total">
        <div class="stat-value" id="statTotal">0</div>
        <div class="stat-label">Total</div>
      </div>
      <div class="stat stat-sent">
        <div class="stat-value" id="statSent">0</div>
        <div class="stat-label">Enviadas</div>
      </div>
      <div class="stat stat-failed">
        <div class="stat-value" id="statFailed">0</div>
        <div class="stat-label">Falhas</div>
      </div>
    </div>
    <div class="progress-section">
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progressBar" style="width: 0%"></div>
      </div>
      <div class="progress-label">
        <span id="progressPct">0%</span>
        <span id="progressCount">0 / 0</span>
      </div>
    </div>
  </div>

  <!-- No records banner -->
  <div class="no-records-banner" id="noRecordsBanner" style="display:none">
    <div class="icon">&#128269;</div>
    <div class="title">Nenhum agendamento pendente de notifica&ccedil;&atilde;o encontrado</div>
    <div class="subtitle">A busca foi conclu&iacute;da, mas n&atilde;o h&aacute; registros para notificar neste per&iacute;odo.</div>
  </div>

  <!-- Records -->
  <div class="card records-section" id="recordsCard" style="display:none">
    <div class="card-title">Agendamentos Extra&iacute;dos (<span id="recordCount">0</span>)</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Paciente</th>
            <th>Procedimento</th>
            <th>Local</th>
            <th>Data</th>
            <th>Hora</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="recordsBody"></tbody>
      </table>
    </div>
  </div>

</div>
</div><!-- /tab-dashboard -->

<div id="tab-history" style="display:none">
<div class="history-container">

  <!-- History list -->
  <div id="historyList">
    <div class="card">
      <div class="card-title">Hist&oacute;rico de Execu&ccedil;&otilde;es</div>
      <div class="history-table-wrap">
        <table class="history-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Data/Hora</th>
              <th>Dura&ccedil;&atilde;o</th>
              <th>Registros</th>
              <th>Enviadas</th>
              <th>Falhas</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="historyListBody"></tbody>
        </table>
        <div class="empty-msg" id="historyEmpty">Nenhuma execu&ccedil;&atilde;o registrada ainda.</div>
      </div>
    </div>
  </div>

  <!-- History detail -->
  <div id="historyDetail" style="display:none">
    <button class="back-btn" onclick="backToHistoryList()">&#8592; Voltar ao hist&oacute;rico</button>
    <div class="detail-grid">
      <div class="card detail-full">
        <div class="card-title">Resumo da Execu&ccedil;&atilde;o #<span id="detailId"></span></div>
        <div class="stats-grid">
          <div class="stat stat-total">
            <div class="stat-value" id="detailTotal">0</div>
            <div class="stat-label">Total</div>
          </div>
          <div class="stat stat-sent">
            <div class="stat-value" id="detailSent">0</div>
            <div class="stat-label">Enviadas</div>
          </div>
          <div class="stat stat-failed">
            <div class="stat-value" id="detailFailed">0</div>
            <div class="stat-label">Falhas</div>
          </div>
        </div>
        <div style="margin-top:1rem;font-size:0.8rem;color:var(--muted)">
          <span>Inicio: <span id="detailStart" style="color:var(--text)"></span></span>
          <span style="margin-left:1.5rem">Fim: <span id="detailEnd" style="color:var(--text)"></span></span>
          <span style="margin-left:1.5rem">Dura&ccedil;&atilde;o: <span id="detailDuration" style="color:var(--cyan)"></span></span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Logs</div>
        <div class="log-area" id="detailLogArea" style="max-height:300px"></div>
      </div>

      <div class="card">
        <div class="card-title">Agendamentos (<span id="detailRecordCount">0</span>)</div>
        <div class="table-wrap" style="max-height:300px">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Paciente</th>
                <th>Procedimento</th>
                <th>Local</th>
                <th>Data</th>
                <th>Hora</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody id="detailRecordsBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

</div>
</div><!-- /tab-history -->

<script>
let lastLogCount = 0;

async function poll() {
  try {
    const res = await fetch('/api/status');
    const d = await res.json();

    // Steps
    document.querySelectorAll('.step-item').forEach(el => {
      const s = parseInt(el.dataset.step);
      el.classList.remove('active', 'done');
      if (s < d.current_step) el.classList.add('done');
      else if (s === d.current_step) el.classList.add('active');
    });

    // Current action
    document.getElementById('actionLabel').textContent = d.step_label;
    document.getElementById('actionDetail').textContent = d.step_detail;

    // Stats
    document.getElementById('statTotal').textContent = d.total_messages;
    document.getElementById('statSent').textContent = d.sent_messages;
    document.getElementById('statFailed').textContent = d.failed_messages;

    const processed = d.sent_messages + d.failed_messages;
    const pct = d.total_messages > 0 ? Math.round((processed / d.total_messages) * 100) : 0;
    document.getElementById('progressBar').style.width = pct + '%';
    document.getElementById('progressPct').textContent = pct + '%';
    document.getElementById('progressCount').textContent = processed + ' / ' + d.total_messages;

    // Elapsed
    document.getElementById('elapsed').textContent = d.elapsed;

    // Status & Start button
    const pulse = document.getElementById('statusPulse');
    const statusText = document.getElementById('statusText');
    const startBtn = document.getElementById('startBtn');
    const elapsedEl = document.getElementById('elapsed');

    if (d.running || d.finished) {
      startBtn.style.display = 'none';
      pulse.style.display = '';
      elapsedEl.style.display = '';
    }

    if (d.finished) {
      pulse.classList.add('done');
      if (d.records.length === 0 && d.total_messages === 0) {
        statusText.textContent = 'Finalizado — Sem registros';
        document.getElementById('noRecordsBanner').style.display = '';
      } else {
        statusText.textContent = 'Finalizado';
      }
      startBtn.style.display = '';
      startBtn.disabled = false;
      startBtn.innerHTML = '&#9654; Iniciar Novamente';
      document.querySelectorAll('.step-item').forEach(el => el.classList.add('done'));
      document.querySelectorAll('.step-item').forEach(el => el.classList.remove('active'));
      stopPolling();
    } else if (d.running) {
      statusText.textContent = 'Executando...';
    }

    // Logs
    if (d.logs.length > lastLogCount) {
      const logArea = document.getElementById('logArea');
      for (let i = lastLogCount; i < d.logs.length; i++) {
        const entry = d.logs[i];
        const div = document.createElement('div');
        div.className = 'log-entry ' + entry.level;
        div.innerHTML = '<span class="log-time">' + entry.time + '</span><span class="log-msg">' +
          entry.message.replace(/</g, '&lt;') + '</span>';
        logArea.appendChild(div);
      }
      logArea.scrollTop = logArea.scrollHeight;
      lastLogCount = d.logs.length;
    }

    // Records
    if (d.records.length > 0) {
      document.getElementById('recordsCard').style.display = '';
      document.getElementById('recordCount').textContent = d.records.length;
      const tbody = document.getElementById('recordsBody');
      const ms = d.message_status || {};
      if (tbody.children.length !== d.records.length) {
        tbody.innerHTML = '';
        d.records.forEach((r, i) => {
          const tr = document.createElement('tr');
          tr.dataset.codigo = r.codigo_solicitacao;
          tr.innerHTML = '<td>' + (i+1) + '</td><td>' + esc(r.nome) + '</td><td>' +
            esc(r.procedimento) + '</td><td>' + esc(r.local) + '</td><td>' +
            r.data + '</td><td>' + r.hora + '</td><td>' + statusBadge(ms[r.codigo_solicitacao]) + '</td>';
          tbody.appendChild(tr);
        });
      } else {
        // Update status column only
        tbody.querySelectorAll('tr').forEach(tr => {
          const codigo = tr.dataset.codigo;
          const lastTd = tr.querySelector('td:last-child');
          if (codigo && lastTd) {
            lastTd.innerHTML = statusBadge(ms[codigo]);
          }
        });
      }
    }

  } catch(e) { /* ignore */ }
}

function esc(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function statusBadge(status) {
  if (status === 'sent') return '<span class="status-badge sent">&#10003; Enviada</span>';
  if (status === 'failed') return '<span class="status-badge failed">&#10007; Falha</span>';
  return '<span class="status-badge pending">&#8226; Pendente</span>';
}

async function startBot() {
  const btn = document.getElementById('startBtn');
  btn.disabled = true;
  btn.innerHTML = '&#9203; Iniciando...';
  try {
    const res = await fetch('/api/start', { method: 'POST' });
    const d = await res.json();
    if (!d.ok) {
      btn.innerHTML = '&#9654; Iniciar Bot';
      btn.disabled = false;
      alert(d.error);
    } else {
      lastLogCount = 0;
      startPolling();
    }
  } catch(e) {
    btn.innerHTML = '&#9654; Iniciar Bot';
    btn.disabled = false;
  }
}

function toggleFullscreen() {
  const frame = document.querySelector('.browser-frame');
  if (!document.fullscreenElement) {
    frame.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
}

function refreshScreenshot() {
  const img = document.getElementById('browserImg');
  const placeholder = document.getElementById('browserPlaceholder');
  const newImg = new Image();
  newImg.onload = function() {
    img.src = newImg.src;
    img.style.display = '';
    placeholder.style.display = 'none';
  };
  newImg.src = '/api/screenshot?' + Date.now();
}

// ─── Tabs ─────────────────────────────────────────────────────────
let currentTab = 'dashboard';

function switchTab(tab) {
  currentTab = tab;
  document.getElementById('tab-dashboard').style.display = tab === 'dashboard' ? '' : 'none';
  document.getElementById('tab-history').style.display = tab === 'history' ? '' : 'none';
  document.querySelectorAll('.tab-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === (tab === 'dashboard' ? 0 : 1));
  });
  if (tab === 'history') loadHistory();
}

// ─── History ──────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    const tbody = document.getElementById('historyListBody');
    const empty = document.getElementById('historyEmpty');
    tbody.innerHTML = '';
    if (data.length === 0) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    data.forEach(exec => {
      const tr = document.createElement('tr');
      tr.onclick = () => loadHistoryDetail(exec.id);
      const start = new Date(exec.started_at);
      const end = exec.finished_at ? new Date(exec.finished_at) : null;
      const duration = end ? fmtDuration(end - start) : '-';
      tr.innerHTML =
        '<td>' + exec.id + '</td>' +
        '<td>' + start.toLocaleString('pt-BR') + '</td>' +
        '<td>' + duration + '</td>' +
        '<td>' + exec.total_messages + '</td>' +
        '<td style="color:var(--green)">' + exec.sent_messages + '</td>' +
        '<td style="color:var(--red)">' + exec.failed_messages + '</td>' +
        '<td>' + execStatusBadge(exec.status) + '</td>';
      tbody.appendChild(tr);
    });
  } catch(e) {}
}

async function loadHistoryDetail(id) {
  try {
    const res = await fetch('/api/history/' + id);
    const d = await res.json();
    document.getElementById('historyList').style.display = 'none';
    document.getElementById('historyDetail').style.display = '';
    document.getElementById('detailId').textContent = d.id;
    document.getElementById('detailTotal').textContent = d.total_messages;
    document.getElementById('detailSent').textContent = d.sent_messages;
    document.getElementById('detailFailed').textContent = d.failed_messages;
    const start = new Date(d.started_at);
    const end = d.finished_at ? new Date(d.finished_at) : null;
    document.getElementById('detailStart').textContent = start.toLocaleString('pt-BR');
    document.getElementById('detailEnd').textContent = end ? end.toLocaleString('pt-BR') : '-';
    document.getElementById('detailDuration').textContent = end ? fmtDuration(end - start) : '-';

    // Logs
    const logArea = document.getElementById('detailLogArea');
    logArea.innerHTML = '';
    (d.logs || []).forEach(entry => {
      const div = document.createElement('div');
      div.className = 'log-entry ' + entry.level;
      div.innerHTML = '<span class="log-time">' + entry.time + '</span><span class="log-msg">' +
        entry.message.replace(/</g, '&lt;') + '</span>';
      logArea.appendChild(div);
    });

    // Records
    const records = d.records || [];
    document.getElementById('detailRecordCount').textContent = records.length;
    const tbody = document.getElementById('detailRecordsBody');
    tbody.innerHTML = '';
    records.forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (i+1) + '</td>' +
        '<td>' + esc(r.nome) + '</td>' +
        '<td>' + esc(r.procedimento) + '</td>' +
        '<td>' + esc(r.local) + '</td>' +
        '<td>' + (r.data || '') + '</td>' +
        '<td>' + (r.hora || '') + '</td>' +
        '<td>' + statusBadge(r.message_status) + '</td>';
      tbody.appendChild(tr);
    });
  } catch(e) {}
}

function backToHistoryList() {
  document.getElementById('historyDetail').style.display = 'none';
  document.getElementById('historyList').style.display = '';
}

function fmtDuration(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? m + 'm ' + (s % 60) + 's' : s + 's';
}

function execStatusBadge(status) {
  if (status === 'finished') return '<span class="status-badge sent">Conclu&iacute;do</span>';
  if (status === 'error') return '<span class="status-badge failed">Erro</span>';
  return '<span class="status-badge pending">Em execu&ccedil;&atilde;o</span>';
}

let pollTimer = null;
let screenshotTimer = null;

function startPolling() {
  stopPolling();
  pollTimer = setInterval(poll, 1000);
  screenshotTimer = setInterval(refreshScreenshot, 2000);
  poll();
  refreshScreenshot();
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  if (screenshotTimer) { clearInterval(screenshotTimer); screenshotTimer = null; }
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return Response(DASHBOARD_HTML, content_type="text/html")


@app.route("/api/status")
def status():
    return jsonify(state.to_dict())


@app.route("/api/start", methods=["POST"])
def start_bot():
    if state.running:
        return jsonify({"ok": False, "error": "Bot já está em execução"}), 409
    if _bot_runner is None:
        return jsonify({"ok": False, "error": "Bot runner não configurado"}), 500

    def wrapper():
        state.set_running(True)
        try:
            _bot_runner()
        except Exception as e:
            state.add_log("error", f"Erro: {e}")
            state.set_finished()
            if state.execution_id is not None:
                finish_execution(
                    execution_id=state.execution_id,
                    finished_at=datetime.datetime.now().isoformat(),
                    total=state.total_messages,
                    sent=state.sent_messages,
                    failed=state.failed_messages,
                    status="error",
                    logs=state.logs.copy(),
                    records=state.records.copy(),
                    message_status=dict(state.message_status),
                )

    threading.Thread(target=wrapper, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/history")
def history():
    return jsonify(get_executions())


@app.route("/api/history/<int:execution_id>")
def history_detail(execution_id):
    detail = get_execution_detail(execution_id)
    if detail is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(detail)


@app.route("/api/screenshot")
def screenshot():
    data = state.get_screenshot()
    if data is None:
        return Response("", status=204)
    return Response(data, content_type="image/png")


def start_web_ui(port: int = 5050, bot_runner=None):
    """Start the dashboard server in a background daemon thread."""
    global _bot_runner
    _bot_runner = bot_runner

    def run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    webbrowser.open(f"http://localhost:{port}")
    return thread
