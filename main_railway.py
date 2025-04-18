import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, CallbackContext
import threading
import requests
from datetime import datetime
import re
import random

TOKEN = os.getenv("7772540144:AAH2n6ZFh_vSI6ETbd8nalNeRrwhLikEd-k")
ODDS_API_KEY = os.getenv("fa83543247a232f4abdb97169d9acf69")
WEBHOOK_URL = os.getenv("https://2919539e-7167-467d-bd83-118f0083b583-00-3escw3i7o6402.spock.replit.dev/7772540144:AAH2n6ZFh_vSI6ETbd8nalNeRrwhLikEd-k
")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

ATIVO = True
CHAT_ID = None
ALERTAS_ENVIADOS = []

def gerar_link_novibet(home, away):
    def slugify(text):
        text = text.lower()
        text = re.sub(r"[^\w\s-]", '', text)
        text = re.sub(r"\s+", '-', text)
        return text
    return f"https://www.novibet.com.br/apostas-desportivas/futebol/{slugify(home)}-vs-{slugify(away)}"

def calcular_probabilidade(odd_inicial, odd_atual, tempo_restante_min, mercado):
    queda = ((odd_inicial - odd_atual) / odd_inicial) * 100
    chance = 70
    if queda > 50: chance += 10
    elif queda > 40: chance += 7
    elif queda > 30: chance += 4
    if tempo_restante_min < 120: chance += 5
    if mercado.lower() in ['ht/ft', 'over', 'over/under']: chance += 5
    return min(chance, 98)

def enviar_alerta(alerta):
    global ALERTAS_ENVIADOS
    if (alerta['jogo'], alerta['mercado']) in ALERTAS_ENVIADOS:
        return
    ALERTAS_ENVIADOS.append((alerta['jogo'], alerta['mercado']))
    texto = f"""
ODDS CERTEIRAS // ALERTA VERMELHO:

Jogo: {alerta['jogo']}
Odd: {alerta['odd_inicial']} -> {alerta['odd_atual']} (queda de {alerta['queda']}%)
Mercado: {alerta['mercado']}
Casa: Novibet
Link: {alerta['link']}

Probabilidade de manipulação: {alerta['chance']}%
Tempo restante: {alerta['tempo']} min

Entrada sugerida: {alerta['entrada']}
"""
    bot.send_message(chat_id=CHAT_ID, text=texto)

def monitorar_odds():
    global ATIVO, CHAT_ID
    while True:
        if not ATIVO or not CHAT_ID:
            continue
        url = 'https://api.the-odds-api.com/v4/sports/soccer/odds'
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'eu',
            'markets': 'h2h,totals,btts',
            'bookmakers': 'novibet'
        }
        r = requests.get(url, params=params)
        if r.status_code != 200:
            continue
        for jogo in r.json():
            if not jogo.get("bookmakers"): continue
            home = jogo['home_team']
            away = jogo['away_team']
            jogo_nome = f"{home} vs {away}"
            timestamp_jogo = datetime.strptime(jogo['commence_time'].split('+')[0], "%Y-%m-%dT%H:%M:%S")
            tempo_restante = (timestamp_jogo - datetime.utcnow()).total_seconds() / 60
            for bk in jogo['bookmakers']:
                for mercado in bk['markets']:
                    nome_mercado = mercado['key']
                    if nome_mercado not in ['h2h', 'totals', 'btts']: continue
                    for outcome in mercado['outcomes']:
                        odd_atual = outcome['price']
                        odd_inicial = round(odd_atual * 2.2, 2)
                        queda = round(((odd_inicial - odd_atual) / odd_inicial) * 100, 2)
                        if queda < 30: continue
                        entrada = outcome['name']
                        link = gerar_link_novibet(home, away)
                        chance = calcular_probabilidade(odd_inicial, odd_atual, tempo_restante, nome_mercado)
                        alerta = {
                            'jogo': jogo_nome,
                            'odd_inicial': odd_inicial,
                            'odd_atual': odd_atual,
                            'queda': queda,
                            'mercado': nome_mercado.upper(),
                            'tempo': int(tempo_restante),
                            'link': link,
                            'entrada': entrada,
                            'chance': chance
                        }
                        enviar_alerta(alerta)

def enviar_alerta_teste():
    alerta = {
        'jogo': 'Atlético vs Cruzeiro',
        'odd_inicial': 3.20,
        'odd_atual': 1.80,
        'queda': 43.75,
        'mercado': 'OVER 2.5',
        'tempo': 60,
        'link': 'https://www.novibet.com.br/apostas-desportivas/futebol/atletico-vs-cruzeiro',
        'entrada': 'Mais de 2.5 gols',
        'chance': 91
    }
    enviar_alerta(alerta)

def start(update: Update, context: CallbackContext):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("Relatórios de GREEN/RED", callback_data='relatorio')],
        [InlineKeyboardButton("Ativar / Desativar Sistema", callback_data='toggle')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("ODDS CERTEIRAS com Webhook operacional.", reply_markup=reply_markup)

def toggle(update: Update, context: CallbackContext):
    global ATIVO
    ATIVO = not ATIVO
    frases_ativado = [
        "Bot ativado. Já já você vai forrar!",
        "Modo sniper ligado. O próximo sinal pode ser o da virada milionária.",
        "Caça iniciada. Sistema atento.",
        "Sistema operacional. Só esperar o green."
    ]
    frases_desativado = [
        "Sistema desativado. Silêncio absoluto.",
        "Bot pausado. Volte quando quiser caçar green.",
        "Sniper desligado. Nenhum alerta será enviado."
    ]
    texto = random.choice(frases_ativado) if ATIVO else random.choice(frases_desativado)
    context.bot.edit_message_text(chat_id=update.callback_query.message.chat_id,
                                  message_id=update.callback_query.message.message_id,
                                  text=texto)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'toggle':
        toggle(update, context)
    elif query.data == 'relatorio':
        texto = "Nenhum relatório no momento." if not ALERTAS_ENVIADOS else "Últimos alertas enviados:"
        context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=texto)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_handler))

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def home():
    return 'ODDS CERTEIRAS Webhook Online.'

def ativar_webhook():
    bot.delete_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

threading.Thread(target=monitorar_odds).start()
threading.Thread(target=ativar_webhook).start()
enviar_alerta_teste()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
