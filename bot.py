import os
import logging
import calendar

from google.cloud.firestore_v1 import FieldFilter
from telegram import Update, ReplyKeyboardRemove
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, filters, MessageHandler

from transaction import Transaction, Firebase

from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


Categories = {
    'vivienda': {'1': 'Dividendo',
                 '2': 'Contribuciones/ gastos poblacion',
                 '3': 'Celular',
                 '4': 'Gas',
                 '5': 'Electricidad',
                 '6': 'Agua',
                 '7': 'Cable - Teléfono - Internet',
                 '8': 'Vestuario',
                 '9': 'Electrodomesticos',
                 '10': 'Mantenimiento y/o Aseo',
                 '11': 'Materiales y/o herramientas',
                 '12': 'Menaje',
                 '13': 'Calefacción',
                 '14': 'Alarma',
                 '15': 'Café',
                 '16': 'Dinero Thiare',
                 '17': 'Dinero Mera',
                 '18': 'Eventos', },
    'alimentación': {'1': 'Supermercado',
                     '2': 'Restaurantes',
                     '3': 'Feria',
                     '4': 'Otras compras menores',
                     '5': 'evey y luna', },
    'transporte': {'1': 'Locomoción Pública',
                   '2': 'Viajes',
                   '3': 'Revisión Técnica/ Mantencion',
                   '4': 'Combustible',
                   '5': 'Estacionamiento',
                   '6': 'Seguro',
                   '7': 'Otros Transporte', },
    'hijo': {
        '1': 'Ropa',
        '2': 'Juguetes',
        '3': 'Otros Hijo',
        '4': 'higiene', },
    'deudas': {
        '1': 'BancoChile',
        '2': 'Crédito automotriz',
        '3': 'CMR',
        '4': 'Cencosud',
        '5': 'lider',
        '6': 'Otros deuda', },
    'salud': {
        '1': 'Gastos Médicos',
        '2': 'Farmacia',
        '3': 'Actividades Deportivas',
        '4': 'Otros salud', },
    'recreacion': {
        '1': 'Cine',
        '2': 'Ocio hogar',
        '3': 'Eventos',
        '4': 'Otros recreación',
    },
    'otros': {

        '1': 'Regalos',
        '2': 'Donaciones',
        '3': 'Compra casa',
        '4': 'Giros',
        '5': 'Prestamo',
        '6': 'Otros Otros', },
    'vacaciones': {
        '1': 'Seguro',
        '2': 'Viaje',
        '3': 'Souvenirs + aeropuerto',
        '4': 'Comida',
        '5': 'Dolares',
        '6': 'Tour', },
    'no categorizable': {
        '1': 'no contable'
    }}

api_key = os.environ["TELEGRAMTOKEN"]
user_id = int(os.environ["USERID"])

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
SUBCATEGORY, CATEGORIZE = range(2)

MONTH = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="comandos: \n/last\n/cancel")


async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if validate_session_user(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(first_non_classified(update.message.chat.id)))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(categories()))

    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")
    return SUBCATEGORY


async def subcategory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text
    if validate_session_user(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(subcategories(response)))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")
    return CATEGORIZE


async def categoryze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if validate_session_user(update):
        response = update.message.text
        category_id, subcategory_id = response.split('.')
        category_keys = list(Categories.keys())
        category = category_keys[int(category_id)-1]
        subcategory_list = list(Categories[category].keys())
        subcategory_key = subcategory_list[int(subcategory_id)-1]
        await update.message.reply_text(
            "Comenzando!"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(update_category(first_non_classified(update.message.chat.id).doc, Categories[category][subcategory_key], update.message.chat.id)))

    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")
    return ConversationHandler.END


async def monthly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if validate_session_user(update):
        await build_summary(context, update.effective_chat.id)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if validate_session_user(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ingresa mes a consultar")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")
    return MONTH


async def month_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    month = int(update.message.text)
    if validate_session_user(update):
        await build_summary(context, update.effective_chat.id, month)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    await update.message.reply_text(
        "Ups comienza denuevo", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def send_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id == user_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(categories()))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No te conozco")


def first_non_classified(user_id):
    tr = transactions(user_id)
    response = tr.order_by("timestamp").where(filter=FieldFilter("category", "==", None)).limit_to_last(1).get()
    if len(response) > 0:
        response = response[0]
        tr_dict = {'doc': response.id}
        tr_dict.update(response.to_dict())
        return Transaction.from_dict(tr_dict)
    return "No hay más transacciones sin clasificación"


def update_category(key, category, user_id):
    tr = transactions(user_id)
    t = tr.document(key)
    t.set({"category": category}, merge=True)
    return 'categorizado'
    # tr_dict = t.get().to_dict()
    # tr_dict['doc'] = key
    # t = Transaction.from_dict(tr_dict)
    # tr = tr.where(filter=FieldFilter("category", "==", None)). \
    #     where(filter=FieldFilter("activity", "==", t.activity)). \
    #     where(filter=FieldFilter("description", "==", t.description))
    # tr_collection = tr.get()
    # for transaction in tr_collection:
    #     transaction.reference.set({"category": category}, merge=True)
    # return f"{len(tr_collection)} movimientos categorizados!"


def subcategories(number):
    category = list(Categories.keys())[int(number)-1]
    cat = ""
    for key in Categories[category]:
        cat += f"{number}.{key}) {Categories[category][key]}\n"
    return cat


def categories():
    cat = ""
    for i, c in enumerate(list(Categories.keys())):
        cat += f"{str(i+1)}) {c}\n"
    return cat


def validate_session_user(update):
    return update.message.chat.id == user_id


def subcategory_summary(subcategory, month, user_id):
    start_date = datetime.today().replace(day=1).replace(month=month)
    end_month = calendar.monthrange(start_date.year, month)[1]
    end_date = start_date.replace(day=end_month)

    tr = transactions(user_id)
    tr = tr.where(filter=FieldFilter("category", "==", subcategory)). \
        where(filter=FieldFilter("timestamp", ">=", start_date)). \
        where(filter=FieldFilter("timestamp", "<=", end_date)). \
        where(filter=FieldFilter("type", "==", 'debito'))
    tr_collection = tr.get()
    total = 0
    for transaction in tr_collection:
        total += int(transaction.to_dict()['amount'])
    return total


def transactions(user_id):
    db = firestore.client()
    return db.collection('users').document(str(user_id)).collection("transactions")


def summary(user_id):
    output = ""
    for k in Categories:
        amount = 0
        for subk in Categories[k]:
            amount += subcategory_summary(Categories[k][subk], None, user_id)
        output += "{}:{}\n".format(k, amount)
    return output


async def build_summary(context, chat_id, month=datetime.today().month):
    for k in Categories:
        output = k + ":\n"
        for subk in Categories[k]:
            output += Categories[k][subk] + ": $" + str(subcategory_summary(Categories[k][subk], month, chat_id)) + "\n"

        await context.bot.send_message(chat_id=chat_id, text=output)


if __name__ == '__main__':
    Firebase()
    application = ApplicationBuilder().token(api_key).build()

    last_command_handler = ConversationHandler(
        entry_points=[CommandHandler("last", last)],
        states={
            SUBCATEGORY: [MessageHandler(filters.Regex(r"[0-9]+$"), subcategory_command)],
            CATEGORIZE: [MessageHandler(filters.Regex(r"[0-9]+$"), categoryze_command)],

        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    summary_handler = ConversationHandler(
        entry_points=[CommandHandler("summary", summary_command)],
        states={
            MONTH: [MessageHandler(filters.Regex(r"[0-9]+$"), month_summary)],

        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(last_command_handler)
    application.add_handler(summary_handler)
    application.add_handler(CommandHandler("monthly_summary", monthly_summary))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
