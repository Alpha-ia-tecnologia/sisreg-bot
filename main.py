from playwright.sync_api import sync_playwright
from time import sleep
import time
from dotenv import load_dotenv
import os
import datetime
from message_sender import MessageSender
from bot_state import state
from db import init_db, clear_records, insert_records, get_all_records, create_execution, finish_execution

NAV_TIMEOUT = int(os.getenv("NAV_TIMEOUT", "120000"))   # ms – default 2 min
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


def goto_with_retry(page, url, state_obj=None):
    """Navigate to *url* with retry + exponential back-off."""
    for attempt in range(1, MAX_RETRIES + 1):
        timeout = NAV_TIMEOUT + (attempt - 1) * 60_000      # +60 s each retry
        try:
            if state_obj:
                state_obj.add_log("info", f"Navegando para {url} (tentativa {attempt}/{MAX_RETRIES}, timeout {timeout // 1000}s)")
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return  # success
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise  # give up after last attempt
            wait_secs = 10 * attempt
            if state_obj:
                state_obj.add_log("error", f"Tentativa {attempt} falhou: {exc}. Aguardando {wait_secs}s…")
            sleep(wait_secs)
from web_ui import start_web_ui
from console_ui import (
    show_banner,
    show_config_summary,
    step_header,
    step_done,
    step_info,
    step_error,
    spinner,
    show_data_table,
    create_send_progress,
    show_summary,
    show_no_records,
    show_goodbye,
)

load_dotenv()


def capture(pw_page):
    """Take a screenshot and push it to the dashboard."""
    try:
        state.set_screenshot(pw_page.screenshot())
    except Exception:
        pass


def run_bot():
    """Main bot logic — runs in a separate thread triggered by the dashboard."""
    # ─── Leitura das variáveis no momento da execução ─────────────────────
    login_user = os.getenv("LOGIN_USER")
    login_password = os.getenv("LOGIN_PASSWORD")
    evolution_api_key = os.getenv("EVOLUTION_API_KEY")
    evolution_base_url = os.getenv("EVOLUTION_BASE_URL")
    instance_name = os.getenv("INSTANCE_NAME")
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")

    state.reset()
    bot_start_time = time.time()
    init_db()
    state.execution_id = create_execution(datetime.datetime.now().isoformat())

    # ─── Banner ───────────────────────────────────────────────────────────
    show_banner()

    if not login_user or not login_password:
        step_error("Variáveis LOGIN_USER e LOGIN_PASSWORD não configuradas no .env")
        state.add_log("error", "LOGIN_USER e LOGIN_PASSWORD não configuradas")
        state.set_finished()
        return

    if not evolution_api_key or not evolution_base_url or not instance_name:
        step_error("Variáveis da Evolution API não configuradas no .env")
        state.add_log("error", "Variáveis da Evolution API não configuradas")
        state.set_finished()
        return

    show_config_summary(
        user=login_user,
        date_range=current_date,
        instance=instance_name,
    )

    # ─── Etapa 1: Autenticação ────────────────────────────────────────────
    state.set_step(1, "Autenticação no SISREG", "Conectando ao sistema de regulação...")
    step_header(1, "Autenticação no SISREG", "Conectando ao sistema de regulação...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-extensions",
                "--dns-prefetch-disable",
                "--no-first-run",
                "--ignore-certificate-errors",
            ]
        )
        try:
            page = browser.new_page()

            state.set_detail("Acessando portal SISREG...")
            with spinner("Acessando portal SISREG..."):
                goto_with_retry(page, "https://sisregiii.saude.gov.br/cgi-bin/index#", state)
            capture(page)
            state.add_log("done", "Portal carregado")
            step_done("Portal carregado")

            state.set_detail("Realizando login...")
            with spinner("Realizando login..."):
                user_locator = page.locator("xpath=/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[2]/input")
                user_locator.wait_for(state="visible", timeout=10000)
                user_locator.fill(login_user)

                password_locator = page.locator("xpath=/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[5]/input")
                password_locator.wait_for(state="visible", timeout=10000)
                password_locator.fill(login_password)

                sign_button = page.locator("xpath=/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[8]/input")
                sign_button.wait_for(state="visible", timeout=10000)
                sign_button.click()
                sleep(3)
            capture(page)
            state.add_log("done", f"Login efetuado como {login_user}")
            step_done(f"Login efetuado como [bold cyan]{login_user}[/]")

            # ─── Etapa 2: Extração de Dados ──────────────────────────────────────
            state.set_step(2, "Extração de Dados", "Consultando fila de espera no SISREG...")
            step_header(2, "Extração de Dados", "Consultando fila de espera no SISREG...")

            state.set_detail("Navegando para fila de espera...")
            with spinner("Navegando para fila de espera..."):
                goto_with_retry(page, "https://sisregiii.saude.gov.br/cgi-bin/cons_fila_espera", state)
            capture(page)
            state.add_log("done", "Página da fila de espera carregada")
            step_done("Página da fila de espera carregada")

            state.set_detail("Configurando filtros de busca...")
            with spinner("Configurando filtros de busca..."):
                auth_box = page.locator("xpath=/html/body/center/div[2]/form/center/table/tbody/tr[8]/td[2]/input[2]")
                auth_box.wait_for(state="visible", timeout=10000)
                auth_box.click()

                init_date_locator = page.locator("xpath=/html/body/center/div[2]/form/center/table/tbody/tr[9]/td[2]/input[1]")
                init_date_locator.wait_for(state="visible", timeout=10000)
                init_date_locator.fill("22/02/2026")

                end_date_locator = page.locator("xpath=/html/body/center/div[2]/form/center/table/tbody/tr[9]/td[2]/input[2]")
                end_date_locator.wait_for(state="visible", timeout=10000)
                end_date_locator.fill("22/02/2026")

                search_button = page.locator("xpath=/html/body/center/div[2]/form/center/table/tbody/tr[10]/td/input[1]")
                search_button.wait_for(state="visible", timeout=10000)
                search_button.click()
            capture(page)
            state.add_log("done", "Filtros aplicados — buscando resultados...")
            step_done("Filtros aplicados — buscando resultados...")

            not_notified = []
            page_count = 0

            while True:
                sleep(5)
                page_count += 1
                state.set_detail(f"Processando página {page_count}...")
                step_info(f"Processando página {page_count}...")
                capture(page)

                lines = page.locator("table.table_listagem tr.linha_selecionavel").all()

                if lines is None or len(lines) == 0:
                    break

                for line in lines:
                    checkbox = line.locator("input[type='checkbox']")

                    if not checkbox.is_checked():
                        codigo_solicitacao = line.locator("td:nth-child(1)").inner_text()
                        nome = line.locator("td:nth-child(3)").inner_text()
                        local = line.locator("td:nth-child(8)").inner_text()
                        telefone = line.locator("td:nth-child(5)").inner_text()
                        procedimento = line.locator("td:nth-child(6)").inner_text()
                        data = line.locator("td:nth-child(9)").inner_text()
                        hora = line.locator("td:nth-child(10)").inner_text()

                        not_notified.append({
                            "codigo_solicitacao": codigo_solicitacao,
                            "nome": nome,
                            "telefone": telefone.replace("\n", " "),
                            "procedimento": procedimento,
                            "local": local,
                            "data": data,
                            "hora": hora,
                        })

                state.add_log("info", f"Página {page_count} — {len(not_notified)} registro(s) acumulados")
                state.set_records(not_notified.copy())
                step_info(f"Página {page_count} — {len(not_notified)} registro(s) acumulados")

                next_page_button = page.locator("img[src='/imagens/seta_direita.png']")

                if next_page_button.count() == 0:
                    break

                if not next_page_button.is_visible():
                    try:
                        next_page_button.wait_for(state="visible", timeout=5000)
                    except Exception:
                        break

                try:
                    next_page_button.click(no_wait_after=True, timeout=10000)
                except Exception:
                    break

                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
        finally:
            browser.close()

    if len(not_notified) == 0:
        state.add_log("info", "Nenhum agendamento pendente de notificação encontrado")
        state.set_finished()
        finish_execution(
            execution_id=state.execution_id,
            finished_at=datetime.datetime.now().isoformat(),
            total=0, sent=0, failed=0,
            status="finished",
            logs=state.logs.copy(),
            records=[],
            message_status={},
        )
        show_no_records()
        show_goodbye()
        return

    state.add_log("done", f"Extração concluída — {len(not_notified)} agendamento(s) encontrado(s)")
    state.set_records(not_notified)
    step_done(f"Extração concluída — [bold cyan]{len(not_notified)}[/] agendamento(s) encontrado(s)")

    # ─── Etapa 3: Processamento ──────────────────────────────────────────
    state.set_step(3, "Processamento de Dados", "Organizando registros extraídos...")
    step_header(3, "Processamento de Dados", "Organizando registros extraídos...")

    with spinner("Salvando dados no banco SQLite..."):
        init_db()
        clear_records()
        insert_records(not_notified)
        sleep(0.5)
    state.add_log("done", "Dados salvos no banco SQLite")
    step_done("Dados salvos no [bold cyan]banco SQLite[/]")

    show_data_table(not_notified)

    # ─── Etapa 4: Envio de Mensagens ─────────────────────────────────────
    state.set_step(4, "Envio de Notificações via WhatsApp", "Enviando mensagens aos pacientes...")
    step_header(4, "Envio de Notificações via WhatsApp", "Enviando mensagens aos pacientes...")

    solicitation = get_all_records()
    message_sender = MessageSender(
        base_url=evolution_base_url,
        instance=instance_name,
        api_key=evolution_api_key,
    )

    total = len(solicitation)
    state.set_total_messages(total)
    sent = 0
    failed = 0

    progress = create_send_progress(total)
    with progress:
        task = progress.add_task("    Enviando notificações", total=total)

        for row in solicitation:
            message = (
                f"Olá {row['nome']}, você tem um agendamento confirmado!\n\n"
                f"📋 *Código de Solicitação:* {row['codigo_solicitacao']}\n"
                f"🩺 *Procedimento:* {row['procedimento']}\n"
                f"🏥 *Local:* {row['local']}\n"
                f"📅 *Data:* {row['data']}\n"
                f"🕐 *Hora:* {row['hora']}\n\n"
                f"Por favor, compareça no local e horário indicados. "
                f"Em caso de dúvidas ou impossibilidade de comparecimento, "
                f"entre em contato conosco."
            )

            phone = str(row["telefone"]).replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
            sleep(5)
            success = message_sender.send_message(
                remote_jid='559889203822',
                message=message,
                name=row["nome"],
            )

            codigo = str(row["codigo_solicitacao"])
            if success:
                sent += 1
                state.increment_sent(codigo)
                state.add_log("done", f"Enviada → {row['nome']}")
            else:
                failed += 1
                state.increment_failed(codigo)
                state.add_log("error", f"Falha → {row['nome']}")

            progress.update(task, advance=1)
            sleep(1)

    # ─── Relatório Final ─────────────────────────────────────────────────
    elapsed = time.time() - bot_start_time
    show_summary(total=total, sent=sent, failed=failed, elapsed=elapsed)
    state.set_finished()
    finish_execution(
        execution_id=state.execution_id,
        finished_at=datetime.datetime.now().isoformat(),
        total=total, sent=sent, failed=failed,
        status="finished",
        logs=state.logs.copy(),
        records=state.records.copy(),
        message_status=dict(state.message_status),
    )
    show_goodbye()


# ─── Entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    start_web_ui(port=port, bot_runner=run_bot)
    show_banner()
    print(f"    Dashboard aberto em http://localhost:{port}")
    print("    Clique em 'Iniciar Bot' no dashboard para começar.\n")

    # Keep main thread alive while dashboard is running
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        show_goodbye()
