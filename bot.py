from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import nest_asyncio
import asyncio

# Estados
MENU, PRODUCTO, CANTIDAD_V, PRECIO, NOMBRE, EDAD, DNI, CANTIDAD_P, TIPO_GASTO, MONTO_GASTO, DETALLE_GASTO = range(11)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)
sheet_ventas = client.open("RegistroBot").worksheet("Ventas")
sheet_pacientes = client.open("RegistroBot").worksheet("Pacientes")
sheet_gastos = client.open("RegistroBot").worksheet("Gastos")

# Comienzo
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Registrar una venta", "Registrar un paciente"], ["Registrar gasto"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("¡Hola! ¿Qué acción querés realizar?", reply_markup=reply_markup)
    return MENU

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    if "venta" in text:
        await update.message.reply_text("🛒 ¿Qué producto se vendió?")
        return PRODUCTO
    elif "paciente" in text:
        await update.message.reply_text("🩺 ¿Nombre del paciente?")
        return NOMBRE
    elif "gasto" in text:
        keyboard = [["Insumos club", "Insumos obra", "Insumos personal"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("🧾 ¿Qué tipo de gasto querés registrar?", reply_markup=reply_markup)
        return TIPO_GASTO
    else:
        await update.message.reply_text("Por favor, elegí una opción válida.")
        return MENU

# Flujo de ventas
async def producto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["producto"] = update.message.text
    await update.message.reply_text("¿Cuántas unidades se vendieron?")
    return CANTIDAD_V

async def cantidad_v(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["cantidad"] = int(update.message.text)
    await update.message.reply_text("¿Cuál fue el precio unitario?")
    return PRECIO

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    precio = float(update.message.text)
    producto = context.user_data["producto"]
    cantidad = context.user_data["cantidad"]
    total = precio * cantidad
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = update.message.from_user.username or update.message.from_user.first_name
    sheet_ventas.append_row([producto, cantidad, precio, total, fecha, usuario])
    await update.message.reply_text(
        f"✅ Venta registrada:\nProducto: {producto}\nCantidad: {cantidad}\nPrecio: ${precio}\n"
        f"Total: ${total}\nFecha: {fecha}\nUsuario: {usuario}"
    )
    return ConversationHandler.END

# Flujo de pacientes
async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("¿Edad del paciente?")
    return EDAD

async def edad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edad"] = int(update.message.text)
    await update.message.reply_text("¿DNI del paciente?")
    return DNI

async def dni(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["dni"] = update.message.text
    await update.message.reply_text("¿Cantidad a registrar? (ej: sesiones, medicamentos, etc.)")
    return CANTIDAD_P

async def cantidad_p(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cantidad = int(update.message.text)
    nombre = context.user_data["nombre"]
    edad = context.user_data["edad"]
    dni = context.user_data["dni"]
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = update.message.from_user.username or update.message.from_user.first_name
    sheet_pacientes.append_row([nombre, edad, dni, cantidad, fecha, usuario])
    await update.message.reply_text(
        f"✅ Paciente registrado:\nNombre: {nombre}\nEdad: {edad}\nDNI: {dni}\n"
        f"Cantidad: {cantidad}\nFecha: {fecha}\nUsuario: {usuario}"
    )
    return ConversationHandler.END

# Flujo de gastos
async def tipo_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tipo_gasto"] = update.message.text
    await update.message.reply_text("¿Cuál es el monto del gasto?")
    return MONTO_GASTO

async def monto_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["monto_gasto"] = float(update.message.text)
    await update.message.reply_text("Ingresá una breve descripción del gasto:")
    return DETALLE_GASTO

async def detalle_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tipo = context.user_data["tipo_gasto"]
    monto = context.user_data["monto_gasto"]
    detalle = update.message.text
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = update.message.from_user.username or update.message.from_user.first_name
    sheet_gastos.append_row([tipo, monto, detalle, fecha, usuario])
    await update.message.reply_text(
        f"✅ Gasto registrado:\nTipo: {tipo}\nMonto: ${monto}\nDetalle: {detalle}\n"
        f"Fecha: {fecha}\nUsuario: {usuario}"
    )
    return ConversationHandler.END

# Comando resumen
async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_ventas = len(sheet_ventas.get_all_values()) - 1
    total_pacientes = len(sheet_pacientes.get_all_values()) - 1
    total_gastos = len(sheet_gastos.get_all_values()) - 1
    await update.message.reply_text(
        f"📊 Resumen general:\n\n"
        f"- Ventas registradas: {total_ventas}\n"
        f"- Pacientes registrados: {total_pacientes}\n"
        f"- Gastos registrados: {total_gastos}"
    )

# Cancelar
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# Main
nest_asyncio.apply()
async def main():
    app = ApplicationBuilder().token("7950410156:AAG2vO_4fQUeyyoILbpVRiBrVqrAstIiKYs").build()

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

asyncio.run(main())

