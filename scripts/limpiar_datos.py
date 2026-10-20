#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpiar_datos.py

Extrae información estructurada de anuncios de motos en texto crudo
usando expresiones regulares y guarda el resultado en motos_limpias.csv.

Lee el texto crudo desde el archivo 'datos_crudos.txt'.
"""

import re
import csv
import sys

# ---------------------------------------------------------------------------
# LISTAS AUXILIARES
# ---------------------------------------------------------------------------
# Municipios / provincias conocidas de Cuba (amplía según necesites)
MUNICIPIOS_CONOCIDOS = [
    "Centro Habana", "La Habana", "Artemisa", "Habana Vieja", "Vedado",
    "Marianao", "Playa", "Diez de Octubre", "Cerro", "Boyeros", "Arroyo Naranjo",
    "San Miguel del Padrón", "Regla", "Guanabacoa", "Cotorro", "Lisa",
    "Plaza de la Revolución", "Este", "Holguín", "Santiago de Cuba",
    "Camagüey", "Santa Clara", "Matanzas", "Pinar del Río", "Cienfuegos",
    "Bayamo", "Las Tunas", "Ciego de Ávila", "Sancti Spíritus", "Guantánamo",
]

# Marcas conocidas de motos (amplía según necesites)
MARCAS_CONOCIDAS = [
    "Treck", "Topmaq", "Yamaki", "Motorstreck", "Jin", "Krathos", "Kratos",
    "Yamaha", "Honda", "Suzuki", "Kawasaki", "Shikra", "AVA", "MT",
]

# Ruta del archivo de entrada
ARCHIVO_ENTRADA = "datos_crudos.txt"


# ---------------------------------------------------------------------------
# LECTURA DEL ARCHIVO
# ---------------------------------------------------------------------------

def leer_texto_crudo(ruta=ARCHIVO_ENTRADA):
    """
    Lee el archivo de texto crudo con open() y read().
    Devuelve el contenido como string. Si el archivo no existe,
    muestra un mensaje y termina el programa.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo '{ruta}'.")
        print("Asegúrate de que esté en el mismo directorio que este script.")
        sys.exit(1)
    except OSError as e:
        print(f"ERROR al leer '{ruta}': {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# FUNCIONES DE EXTRACCIÓN
# ---------------------------------------------------------------------------

def dividir_anuncios(texto):
    """
    Divide el texto crudo en anuncios individuales.
    Consideramos que cada anuncio termina con la línea de WhatsApp.
    """
    # Patrón: cualquier bloque que termine en "WhatsApp: <número>"
    # re.DOTALL permite que '.' incluya saltos de línea
    patron = re.compile(
        r"(.*?WhatsApp:\s*\d+)",
        re.DOTALL | re.IGNORECASE
    )
    bloques = patron.findall(texto)
    return [b.strip() for b in bloques if b.strip()]


def extraer_contacto(bloque):
    """
    Extrae el número de WhatsApp.
    Patrón: 'WhatsApp:' seguido de dígitos (con posibles espacios).
    """
    m = re.search(r"WhatsApp\s*:\s*([\d\s]+)", bloque, re.IGNORECASE)
    if m:
        # Quitamos espacios internos del número
        return re.sub(r"\s+", "", m.group(1).strip())
    return ""


def extraer_precio(bloque):
    """
    Extrae el precio. Busca la primera aparición de un número seguido de
    'usd', 'cup' o '$'. Devuelve el valor numérico con su moneda.
    """
    m = re.search(r"(\d[\d\.,]*)\s*(USD|CUP|\$)", bloque, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2).upper() if m.group(2) != '$' else '$'}"
    # Fallback: línea "Precio: ..."
    m = re.search(r"Precio\s*:\s*([^\n]+)", bloque, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def extraer_anio(bloque):
    """
    Busca un año de 4 dígitos (rango razonable 1990-2099).
    """
    m = re.search(r"\b(19\d{2}|20\d{2})\b", bloque)
    if m:
        return m.group(1)
    return ""


def extraer_cilindraje_potencia(bloque):
    """
    Extrae cilindraje (cc) o potencia (Wats/W).
    Prioriza 'cc'; si no, busca 'Wats' o 'W'.
    Devuelve el primer valor encontrado con su unidad.
    """
    # Cilindraje: número seguido de cc (con o sin espacio)
    m = re.search(r"(\d{2,4})\s*cc\b", bloque, re.IGNORECASE)
    if m:
        return f"{m.group(1)} cc"
    # Potencia en Wats
    m = re.search(r"(\d{2,5})\s*(Wats|W)\b", bloque, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return ""


def extraer_marca(bloque):
    """
    Busca alguna marca conocida dentro del texto (case-insensitive).
    Devuelve la marca con formato capitalizado.
    """
    for marca in MARCAS_CONOCIDAS:
        # \b para límites de palabra y evitar falsos positivos
        if re.search(rf"\b{re.escape(marca)}\b", bloque, re.IGNORECASE):
            return marca
    return ""


def extraer_tipo_motor(bloque):
    """
    Determina si la moto es de Combustión o Eléctrica según palabras clave.
    """
    texto = bloque.lower()
    if any(p in texto for p in ["eléctrica", "electrica", "eléctrico", "electrico"]):
        return "Eléctrica"
    if any(p in texto for p in ["combustión", "combustion", "gasolina", "cc"]):
        return "Combustión"
    return ""


def extraer_estado(bloque):
    """
    Determina si es Nueva o Usada.
    '0km', '0 km', 'nueva' -> Nueva
    'usada', 'usado', 'km recorridos' -> Usada
    """
    texto = bloque.lower()
    if re.search(r"\b(0\s*km|0km|nueva|nuevo)\b", texto):
        return "Nueva"
    if re.search(r"\b(usada|usado|segunda mano)\b", texto):
        return "Usada"
    return ""


def extraer_papeles(bloque):
    """
    Determina si tiene papeles en regla.
    Busca: 'papeles en regla', 'factura', 'legal', 'mipime', 'garantía'...
    Devuelve 'Sí' o 'No'.
    """
    texto = bloque.lower()
    patrones = [
        r"papeles en regla", r"factura", r"legal", r"mipime",
        r"documentaci[oó]n", r"t[ií]tulo",
    ]
    for p in patrones:
        if re.search(p, texto):
            return "Sí"
    return "No"


def extraer_ubicacion(bloque):
    """
    Extrae la ubicación. La ubicación suele estar en la línea inmediatamente
    anterior a la de WhatsApp, o al inicio si no hay otra.

    Devuelve (direccion, ciudad, municipio).
    """
    lineas = [l.strip() for l in bloque.splitlines() if l.strip()]
    if not lineas:
        return "", "", ""

    # Buscamos la línea con WhatsApp y tomamos la anterior
    idx_ws = None
    for i, l in enumerate(lineas):
        if re.search(r"WhatsApp\s*:", l, re.IGNORECASE):
            idx_ws = i
            break

    linea_ubic = ""
    if idx_ws is not None and idx_ws > 0:
        linea_ubic = lineas[idx_ws - 1]
    elif lineas:
        linea_ubic = lineas[0]

    # Intentamos separar "Municipio, Provincia"
    ciudad, municipio = "", ""
    partes = [p.strip() for p in linea_ubic.split(",") if p.strip()]
    if len(partes) >= 2:
        # Convención: "Municipio, Provincia"
        municipio = partes[0]
        ciudad = partes[1]
    elif len(partes) == 1:
        # Un solo valor: intentamos adivinar si es municipio o ciudad
        for m in MUNICIPIOS_CONOCIDOS:
            if m.lower() in partes[0].lower():
                municipio = m
                break

    # Dirección / zona: buscamos palabras clave en todo el bloque
    direccion = ""
    patron_dir = re.compile(
        r"\b(Calle|Avenida|Ave\.?|Reparto|Barrio|Zona|Consejo Popular|Carretera)\b[^\n,\.]*",
        re.IGNORECASE,
    )
    m = patron_dir.search(bloque)
    if m:
        direccion = m.group(0).strip()

    return direccion, ciudad, municipio


def extraer_fecha(bloque):
    """
    Busca patrones de fecha: dd/mm/aaaa, dd-mm-aaaa, aaaa-mm-dd,
    o nombres de mes.
    """
    patrones = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        r"\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|"
        r"agosto|septiembre|octubre|noviembre|diciembre)\s+(de\s+)?\d{2,4}\b",
    ]
    for p in patrones:
        m = re.search(p, bloque, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""


# ---------------------------------------------------------------------------
# PROCESAMIENTO PRINCIPAL
# ---------------------------------------------------------------------------

def procesar_anuncio(bloque):
    """
    Procesa un solo anuncio y devuelve un dict con todas las columnas.
    """
    direccion, ciudad, municipio = extraer_ubicacion(bloque)
    return {
        "Direccion/Zona": direccion,
        "Ciudad": ciudad,
        "Municipio": municipio,
        "Marca": extraer_marca(bloque),
        "Cilindraje/Potencia": extraer_cilindraje_potencia(bloque),
        "Tipo Motor": extraer_tipo_motor(bloque),
        "Estado": extraer_estado(bloque),
        "Papeles": extraer_papeles(bloque),
        "Precio": extraer_precio(bloque),
        "Año/Modelo": extraer_anio(bloque),
        "Fecha Anuncio": extraer_fecha(bloque),
        "Contacto": extraer_contacto(bloque),
    }


def main():
    # Leemos el texto crudo del archivo externo
    texto_crudo = leer_texto_crudo()

    anuncios = dividir_anuncios(texto_crudo)
    print(f"Anuncios detectados: {len(anuncios)}\n")

    columnas = [
        "Direccion/Zona", "Ciudad", "Municipio", "Marca",
        "Cilindraje/Potencia", "Tipo Motor", "Estado", "Papeles",
        "Precio", "Año/Modelo", "Fecha Anuncio", "Contacto",
    ]

    filas = [procesar_anuncio(a) for a in anuncios]

    with open("motos_limpias.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)

    # Mostrar resumen por consola
    for i, fila in enumerate(filas, 1):
        print(f"--- Anuncio {i} ---")
        for k, v in fila.items():
            print(f"  {k}: {v}")
        print()

    print("Archivo 'motos_limpias.csv' generado correctamente.")


if __name__ == "__main__":
    main()
