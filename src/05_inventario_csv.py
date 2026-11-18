"""
05_inventario_csv.py
Inventario de la red desde el Network Controller de Packet Tracer, exportado a CSV.

A diferencia de los scripts 02, 03 y 04 (que solo imprimen en pantalla), este script:
  1. pide el ticket solo (no hay que copiarlo a mano),
  2. consulta /network-device y /host,
  3. valida el codigo de estado de cada respuesta,
  4. guarda todo en un unico CSV con una columna "categoria" (dispositivo / host),
  5. muestra un resumen: cantidad de equipos por estado (Managed / Wrong credential, etc.)
     y de hosts por resultado de ping.

La clave del controlador no esta escrita en el codigo: se pide por teclado
(o se toma de la variable de entorno NC_PASSWORD). Asi no queda en el repositorio.

Uso:
    python src/05_inventario_csv.py
    python src/05_inventario_csv.py --user cisco --salida inventario.csv
    python src/05_inventario_csv.py --sep ","     (si tu Excel usa coma como separador)

El CSV usa ";" como separador por defecto porque Excel en espanol lo espera asi.
"""
import argparse
import csv
import getpass
import os
import sys
from collections import Counter
from datetime import datetime

import requests

COLUMNAS = [
    "categoria", "nombre", "tipo", "ip", "mac",
    "modelo", "serie", "version", "estado", "conectado_a", "interfaz",
]


def pedir_ticket(base_url, usuario, clave):
    """POST /ticket: devuelve el serviceTicket que se usa como X-Auth-Token."""
    resp = requests.post(
        base_url + "/ticket",
        json={"username": usuario, "password": clave},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        sys.exit(f"No se pudo obtener el ticket (HTTP {resp.status_code}): {resp.text}")
    return resp.json()["response"]["serviceTicket"]


def consultar(base_url, ruta, ticket):
    """GET de un recurso; corta con un mensaje claro si la respuesta no es 200."""
    resp = requests.get(base_url + ruta, headers={"X-Auth-Token": ticket}, timeout=15)
    if resp.status_code != 200:
        sys.exit(f"Error al consultar {ruta} (HTTP {resp.status_code}): {resp.text}")
    return resp.json()["response"]


def fila_dispositivo(d):
    return {
        "categoria": "dispositivo",
        "nombre": d.get("hostname", ""),
        "tipo": d.get("type", ""),
        "ip": d.get("managementIpAddress", ""),
        "mac": d.get("macAddress", ""),
        "modelo": d.get("platformId", ""),
        "serie": d.get("serialNumber", ""),
        "version": d.get("softwareVersion", ""),
        "estado": d.get("collectionStatus", ""),
        "conectado_a": " | ".join(d.get("connectedNetworkDeviceName") or []),
        "interfaz": "",
    }


def fila_host(h):
    return {
        "categoria": "host",
        "nombre": h.get("hostName", ""),
        "tipo": h.get("hostType", ""),
        "ip": h.get("hostIp", ""),
        "mac": h.get("hostMac", ""),
        "modelo": "",
        "serie": "",
        "version": "",
        "estado": h.get("pingStatus", ""),
        "conectado_a": h.get("connectedNetworkDeviceName", ""),
        "interfaz": h.get("connectedInterfaceName", ""),
    }


def main():
    ap = argparse.ArgumentParser(description="Inventario del Network Controller a CSV")
    ap.add_argument("--url", default="http://localhost:58000/api/v1",
                    help="URL base de la API (por defecto la de Packet Tracer)")
    ap.add_argument("--user", default="cisco", help="usuario del controlador")
    ap.add_argument("--salida", default=None, help="archivo CSV de salida")
    ap.add_argument("--sep", default=";",
                    help="separador de columnas (';' para Excel en espanol, ',' para otros)")
    args = ap.parse_args()

    clave = os.environ.get("NC_PASSWORD") or getpass.getpass(
        f"Clave del controlador para '{args.user}': ")
    salida = args.salida or f"inventario_{datetime.now():%Y%m%d_%H%M%S}.csv"

    ticket = pedir_ticket(args.url, args.user, clave)
    dispositivos = consultar(args.url, "/network-device", ticket)
    hosts = consultar(args.url, "/host", ticket)

    filas = [fila_dispositivo(d) for d in dispositivos] + [fila_host(h) for h in hosts]
    # utf-8-sig agrega la marca BOM para que Excel respete los acentos
    with open(salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=args.sep)
        w.writeheader()
        w.writerows(filas)

    print(f"Inventario guardado en: {salida}")
    print(f"  Dispositivos: {len(dispositivos)}  |  Hosts: {len(hosts)}")
    print("  Dispositivos por estado:",
          dict(Counter(d.get("collectionStatus", "?") for d in dispositivos)))
    print("  Hosts por ping:",
          dict(Counter(h.get("pingStatus", "?") for h in hosts)))


if __name__ == "__main__":
    main()
