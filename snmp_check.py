#!/usr/bin/python3

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
#   
#                           Qualquer duvida consulte o tutorial.txt
# 
#''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''' 

import sys
import asyncio
import csv
from pysnmp.hlapi.v3arch.asyncio import *

printer_ips = []  # Cria uma lista vazia
for i in range(1, 26):
    ip = f"172.16.5.{i}"
    printer_ips.append(ip)
    
community_string = 'public'

oids = {
    'Printer Model': '1.3.6.1.2.1.1.1.0',
    'Total Page Count': '1.3.6.1.2.1.43.10.2.1.4.1.1',
    'Device Status': '1.3.6.1.2.1.25.3.2.1.5.1',
}

def load_sector_mapping(csv_filepath):
    """
    Loads IP to Sector mapping from a CSV file.
    Assumes the CSV has 'IP' and 'Sector' columns.
    """
    sector_map = {}
    try:
        with open(csv_filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ip = row.get('IP')
                sector = row.get('Sector')
                if ip and sector:
                    sector_map[ip.strip()] = sector.strip()
                else:
                    print(f"Warning: Skipping row due to missing 'IP' or 'Sector' field: {row}")
    except FileNotFoundError:
        print(f"Error: Sector mapping file '{csv_filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading sector mapping CSV: {e}")
        sys.exit(1)
    return sector_map

async def get_snmp_value(snmpEngine, printer_ip, community_string, oid):
    """
    Helper function to fetch a single SNMP OID value from a printer.
    """
    transport_target = await UdpTransportTarget.create((printer_ip, 161))

    errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
        snmpEngine,
        CommunityData(community_string, mpModel=0),
        transport_target,
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    if errorIndication:
        return None, f"Error: {errorIndication}"
    elif errorStatus:
        if str(errorStatus).startswith('noSuch'):
            return None, f"Error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1] or '?'}"
        else:
            return None, f"Error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1] or '?'}"
    else:
        if varBinds:
            return str(varBinds[0][1]), None
        else:
            return None, "Error: No data returned for OID."

async def get_printer_info(snmpEngine, printer_ip, community_string, oids, sector_map):
    """
    Fetches various SNMP details for a given printer, including a robust serial number check,
    and adds the sector information.
    """
    printer_data = {'IP Address': printer_ip}

    printer_data['Sector'] = sector_map.get(printer_ip, 'N/A - Sector nao encontrado')

    for name, oid in oids.items():
        value, error_msg = await get_snmp_value(snmpEngine, printer_ip, community_string, oid)
        if error_msg:
            printer_data[name] = error_msg
        else:
            printer_data[name] = value

    serial_oids_to_try = [
        '1.3.6.1.2.1.43.5.1.1.17.1',  # Standard MIB serial number OID
        '1.3.6.1.4.1.367.3.2.1.2.1.4.0'  # Ricoh specific serial number OID
    ]

    serial_number_found = False
    final_serial_error = "Error: Serial Number OID not found on this device."

    for serial_oid in serial_oids_to_try:
        value, error_msg = await get_snmp_value(snmpEngine, printer_ip, community_string, serial_oid)

        if value is not None:
            printer_data['Serial Number'] = value
            serial_number_found = True
            break
        elif error_msg and "noSuch" in error_msg:
            final_serial_error = error_msg
            continue
        else:
            printer_data['Serial Number'] = error_msg
            serial_number_found = True
            break

    if not serial_number_found:
        printer_data['Serial Number'] = final_serial_error

    return printer_ip, printer_data

async def main():
    """
    Main function to orchestrate fetching printer information and saving it to a CSV file.
    """
    snmpEngine = SnmpEngine()
    output_filename = 'printers_info.csv'
    sector_mapping_file = 'ip_sector.csv' 

    ip_to_sector_map = load_sector_mapping(sector_mapping_file)

    filtered_printer_ips = [ip for ip in printer_ips if ip in ip_to_sector_map]
    if len(filtered_printer_ips) < len(printer_ips):
        print("Warning: Some printer IPs from the original list were not found in the sector mapping file and will be excluded or marked as 'N/A'.")

    tasks = [get_printer_info(snmpEngine, ip, community_string, oids, ip_to_sector_map) for ip in printer_ips] 

    print(f"Carregando... (Salvando resultados em {output_filename})")
    results = await asyncio.gather(*tasks)

    csv_header = ['IP Address', 'Sector'] + list(oids.keys()) + ['Serial Number']

    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)

            csv_writer.writerow(csv_header)

            for printer_ip, printer_data in results:
                row_data = [printer_data.get(header, 'N/A') for header in csv_header]
                csv_writer.writerow(row_data)
        print(f"Informacoes salvas em: {output_filename}")
    except IOError as e:
        print(f"Error: Could not write to file {output_filename}. {e}")
    finally:
        snmpEngine._close()

if __name__ == "__main__":
    asyncio.run(main())
