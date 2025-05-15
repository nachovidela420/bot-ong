import os, json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
import gspread

# Estados de la conversación
MENU, PRODUCTO, CANTIDAD_V, PRECIO, NOMBRE, EDAD, DNI, CANTIDAD_P, TIPO_GASTO, MONTO_GASTO, DETALLE_GASTO = range(11)

# Configuración de acceso a Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
if os.getenv("GOOGLE_CREDS_JSON"):
    creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)

client = gspread.authorize(creds)
sheet_ventas = client.open("RegistroBot").worksheet("Ventas")
sheet_pacientes = client.open("RegistroBot").worksheet("Pacientes")
sheet_gastos = client.open("RegistroBot").worksheet("Gastos")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Registrar venta", "Registrar paciente", "Registrar gasto"], ["Ver resumen"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("¡Hola! ¿Qué te gustaría hacer?", reply_markup=markup)
    return MENU

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()

    if "venta" in text:
        await update.message.reply_text("¿Qué producto se vendió?")
        return PRODUCTO
    elif "paciente" in text:
        await update.message.reply_text("Nombre del paciente:")
        return NOMBRE
    elif "gasto" in text:
        reply_keyboard = [["Insumos club", "Insumos obra", "Insumos personal"]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Seleccioná el tipo de gasto:", reply_markup=markup)
        return TIPO_GASTO
    elif "resumen" in text:
        return await resumen(update, context)
    else:
        await update.message.reply_text("Opción no válida. Elegí una opción del menú.")
        return MENU

# Venta
async def producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["producto"] = update.message.text
    await update.message.reply_text("¿Cantidad vendida?")
    return CANTIDAD_V

async def cantidad_v(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cantidad"] = update.message.text
    await update.message.reply_text("¿Precio unitario?")
    return PRECIO

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["precio"] = update.message.text
    producto = context.user_data["producto"]
    cantidad = context.user_data["cantidad"]
    precio = context.user_data["precio"]
    total = float(cantidad) * float(precio)
    sheet_ventas.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), producto, cantidad, precio, total])
    await update.message.reply_text("✅ Venta registrada correctamente.")
    return ConversationHandler.END

# Paciente
async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("Edad:")
    return EDAD

async def edad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edad"] = update.message.text
    await update.message.reply_text("DNI:")
    return DNI

async def dni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dni"] = update.message.text
    await update.message.reply_text("Cantidad de sesiones:")
    return CANTIDAD_P

async def cantidad_p(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cantidad_p"] = update.message.text
    sheet_pacientes.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        context.user_data["nombre"],
        context.user_data["edad"],
        context.user_data["dni"],
        context.user_data["cantidad_p"]
    ])
    await update.message.reply_text("✅ Paciente registrado correctamente.")
    return ConversationHandler.END

# Gasto
async def tipo_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tipo_gasto"] = update.message.text
    await update.message.reply_text("Monto del gasto:")
    return MONTO_GASTO

async def monto_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["monto_gasto"] = update.message.text
    await update.message.reply_text("Descripción breve del gasto:")
    return DETALLE_GASTO

async def detalle_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detalle"] = update.message.text
    sheet_gastos.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        context.user_data["tipo_gasto"],
        context.user_data["monto_gasto"],
        context.user_data["detalle"]
    ])
    await update.message.reply_text("✅ Gasto registrado correctamente.")
    return ConversationHandler.END

# Resumen
async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ventas = sheet_ventas.get_all_values()[1:]
    pacientes = sheet_pacientes.get_all_values()[1:]
    gastos = sheet_gastos.get_all_values()[1:]

    total_ventas = sum(float(v[4]) for v in ventas if v[4])
    total_pacientes = len(pacientes)
    total_gastos = sum(float(g[2]) for g in gastos if g[2])

    resumen_text = (
        f"📊 *Resumen general:*\n"
        f"- Ventas totales: ${total_ventas:.2f}\n"
        f"- Pacientes registrados: {total_pacientes}\n"
        f"- Gastos totales: ${total_gastos:.2f}"
    )
    await update.message.reply_text(resumen_text, parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

async def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN") or "TOKEN_NO_DEFINIDO"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, producto)],
            CANTIDAD_V: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_v)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
            EDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edad)],
            DNI: [MessageHandler(filters.TEXT & ~filters.COMMAND, dni)],
            CANTIDAD_P: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_p)],
            TIPO_GASTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_gasto)],
            MONTO_GASTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_gasto)],
            DETALLE_GASTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, detalle_gasto)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("resumen", resumen))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
