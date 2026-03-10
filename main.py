from playwright.sync_api import sync_playwright
from time import sleep
import time
import pandas as pd
from dotenv import load_dotenv
import os
import datetime
from message_sender import MessageSender
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

start_time = time.time()

login_user = os.getenv("LOGIN_USER")
login_password = os.getenv("LOGIN_PASSWORD")
evolution_api_key = os.getenv("EVOLUTION_API_KEY")
evolution_base_url = os.getenv("EVOLUTION_BASE_URL")
instance_name = os.getenv("INSTANCE_NAME")
current_date = datetime.datetime.now().strftime("%d/%m/%Y")

# ─── Banner ───────────────────────────────────────────────────────────
show_banner()

if not login_user or not login_password:
    step_error("Variáveis LOGIN_USER e LOGIN_PASSWORD não configuradas no .env")
    raise ValueError("LOGIN_USER and LOGIN_PASSWORD environment variables must be set")

if not evolution_api_key or not evolution_base_url or not instance_name:
    step_error("Variáveis da Evolution API não configuradas no .env")
    raise ValueError("Evolution API environment variables must be set")

show_config_summary(
    user=login_user,
    date_range=current_date,
    instance=instance_name,
)

# ─── Etapa 1: Autenticação ────────────────────────────────────────────
step_header(1, "Autenticação no SISREG", "Conectando ao sistema de regulação...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    with spinner("Acessando portal SISREG..."):
        page.goto("https://sisregiii.saude.gov.br/cgi-bin/index#")
        page.wait_for_load_state("networkidle")
    step_done("Portal carregado")

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
    step_done(f"Login efetuado como [bold cyan]{login_user}[/]")

    # ─── Etapa 2: Extração de Dados ──────────────────────────────────────
    step_header(2, "Extração de Dados", "Consultando fila de espera no SISREG...")

    with spinner("Navegando para fila de espera..."):
        page.goto("https://sisregiii.saude.gov.br/cgi-bin/cons_fila_espera")
        page.wait_for_load_state("networkidle", timeout=10000)
    step_done("Página da fila de espera carregada")

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
    step_done("Filtros aplicados — buscando resultados...")
    input("Pressione Enter para iniciar a extração dos dados...")

    not_notified = []
    page_count = 0

    while True:
        sleep(5)
        page_count += 1
        step_info(f"Processando página {page_count}...")

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
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    browser.close()

    if len(not_notified) == 0:
        show_no_records()
        show_goodbye()
        exit(0)

    step_done(f"Extração concluída — [bold cyan]{len(not_notified)}[/] agendamento(s) encontrado(s)")

    # ─── Etapa 3: Processamento ──────────────────────────────────────────
    step_header(3, "Processamento de Dados", "Organizando registros extraídos...")

    with spinner("Salvando dados em not_notified.csv..."):
        df = pd.DataFrame(not_notified)
        df.to_csv("not_notified.csv", index=False)
        sleep(0.5)
    step_done("Dados salvos em [bold cyan]not_notified.csv[/]")

    show_data_table(not_notified)

    # ─── Etapa 4: Envio de Mensagens ─────────────────────────────────────
    step_header(4, "Envio de Notificações via WhatsApp", "Enviando mensagens aos pacientes...")

    solicitation = pd.read_csv("not_notified.csv")
    message_sender = MessageSender(
        base_url=evolution_base_url,
        instance=instance_name,
        api_key=evolution_api_key,
    )

    total = len(solicitation)
    sent = 0
    failed = 0

    progress = create_send_progress(total)
    with progress:
        task = progress.add_task("    Enviando notificações", total=total)

        for _, row in solicitation.iterrows():
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
            success = message_sender.send_message(
                remote_jid=phone,
                message=message,
                name=row["nome"],
            )

            if success:
                sent += 1
            else:
                failed += 1

            progress.update(task, advance=1)
            sleep(1)

    # ─── Relatório Final ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    show_summary(total=total, sent=sent, failed=failed, elapsed=elapsed)
    show_goodbye()
