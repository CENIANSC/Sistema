import pandas as pd
import gspread

import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime

from reportlab.lib import colors

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)


# ==================================
# CONEXION
# ==================================

def conectar():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scope
    )

    gc = gspread.authorize(creds)

    spreadsheet = gc.open("Compras_DB")

    return {
        "spreadsheet": spreadsheet,
        "ws_productos": spreadsheet.worksheet("Productos"),
        "ws_historial": spreadsheet.worksheet("Historial_Precios"),
        "ws_ordenes": spreadsheet.worksheet("Ordenes"),
        "ws_recepciones": spreadsheet.worksheet("Recepciones"),
        "ws_config": spreadsheet.worksheet("Configuracion")
    }


# ==================================
# PRODUCTOS
# ==================================

def cargar_productos():

    datos = conectar()

    return pd.DataFrame(
        datos["ws_productos"].get_all_records()
    )


def categorias_con_productos():

    df = cargar_productos()

    resultado = {}

    for categoria in sorted(
        df["Categoría"].unique()
    ):

        resultado[categoria] = (
            df[
                df["Categoría"] == categoria
            ]["Producto"]
            .tolist()
        )

    return resultado


# ==================================
# FOLIOS
# ==================================

def obtener_siguiente_folio():

    datos = conectar()

    ws_config = datos["ws_config"]

    config = pd.DataFrame(
        ws_config.get_all_records()
    )

    ultimo = int(
        config.loc[
            config["Variable"] == "UltimoFolio",
            "Valor"
        ].iloc[0]
    )

    return ultimo, ultimo + 1


# ==================================
# PRECIOS
# ==================================

def obtener_ultimo_precio(producto):

    datos = conectar()

    ws_historial = datos["ws_historial"]

    df_hist = pd.DataFrame(
        ws_historial.get_all_records()
    )

    if len(df_hist) == 0:
        return 0

    filtro = df_hist[
        df_hist["Producto"] == producto
    ]

    if len(filtro) == 0:
        return 0

    return float(
        filtro.iloc[-1]["Precio Unitario"]
    )


# ==================================
# PDF
# ==================================

def generar_pdf_orden(
    df_pedido,
    folio,
    fecha,
    archivo_pdf
):

    doc = SimpleDocTemplate(archivo_pdf)

    elementos = []

    estilos = getSampleStyleSheet()

    elementos.append(
        Paragraph(
            f"ORDEN DE COMPRA {folio}",
            estilos["Title"]
        )
    )

    elementos.append(
        Spacer(1, 12)
    )

    elementos.append(
        Paragraph(
            f"Fecha: {fecha}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Spacer(1, 12)
    )

    datos = [[
        "Proveedor",
        "Producto",
        "Cantidad",
        "Precio",
        "Importe"
    ]]

    for _, row in df_pedido.iterrows():

        datos.append([
            str(row["Proveedor"]),
            str(row["Producto"]),
            str(row["Cantidad"]),
            f"${row['Precio Estimado']:,.2f}",
            f"${row['Importe']:,.2f}"
        ])

    tabla = Table(datos)

    tabla.setStyle(
        TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
            ('GRID',(0,0),(-1,-1),1,colors.black),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
        ])
    )

    elementos.append(tabla)
    total = df_pedido["Importe"].sum()

    elementos.append(
        Spacer(1,20)
    )

    elementos.append(
        Paragraph(
            f"TOTAL ESTIMADO: ${total:,.2f}",
            estilos["Heading2"]
        )
    )

    doc.build(elementos)


# ==================================
# PEDIDOS
# ==================================

def construir_pedido(items):

    df_productos = cargar_productos()

    filas = []

    for item in items:

        producto = item["Producto"]
        cantidad = float(item["Cantidad"])

        datos_producto = df_productos[
            df_productos["Producto"] == producto
        ]

        if len(datos_producto) == 0:
            continue

        proveedor = (
            datos_producto.iloc[0]["Proveedor"]
        )

        unidad = (
            datos_producto.iloc[0]["Unidad"]
        )

        precio = obtener_ultimo_precio(
            producto
        )

        importe = cantidad * precio

        filas.append({
            "Producto": producto,
            "Cantidad": cantidad,
            "Proveedor": proveedor,
            "Unidad": unidad,
            "Precio Estimado": precio,
            "Importe": importe
        })

    return pd.DataFrame(filas)


# ==================================
# ORDENES DE COMPRA
# ==================================

def generar_oc(df_pedido):

    datos = conectar()

    ws_ordenes = datos["ws_ordenes"]
    ws_config = datos["ws_config"]

    ultimo, siguiente = (
        obtener_siguiente_folio()
    )

    folio = f"OC-{ultimo:04d}"

    fecha = datetime.now().strftime(
        "%Y-%m-%d"
    )

    for _, row in df_pedido.iterrows():

        ws_ordenes.append_row([
            folio,
            fecha,
            row["Proveedor"],
            row["Producto"],
            row["Cantidad"],
            row["Precio Estimado"],
            row["Importe"]
        ])

    archivo_pdf = f"{folio}.pdf"

    generar_pdf_orden(
        df_pedido,
        folio,
        fecha,
        archivo_pdf
    )

    celda = ws_config.find(
        "UltimoFolio"
    )

    ws_config.update(
        values=[[siguiente]],
        range_name=f"B{celda.row}"
    )

    return folio, archivo_pdf


def generar_oc_desde_items(items):

    df_pedido = construir_pedido(
        items
    )

    if len(df_pedido) == 0:
        return None

    folio, pdf = generar_oc(
        df_pedido
    )

    return {
        "folio": folio,
        "pdf": pdf,
        "pedido": df_pedido
    }
