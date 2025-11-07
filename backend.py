#!/usr/bin/python3

"""
Backend FastAPI para monitoramento de impressoras via SNMP
Expõe endpoints REST para consultar informações das impressoras
"""

import asyncio
import csv
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pysnmp.hlapi.v3arch.asyncio import *
import uvicorn

# Configurações globais
printer_ips = [f"172.16.5.{i}" for i in range(1, 26)]
community_string = 'public'

oids = {
    'Printer Model': '1.3.6.1.2.1.1.1.0',
    'Total Page Count': '1.3.6.1.2.1.43.10.2.1.4.1.1',
    'Device Status': '1.3.6.1.2.1.25.3.2.1.5.1',
}

sector_map_cache: Dict[str, str] = {}


def load_sector_mapping(csv_filepath: str = 'ip_sector.csv') -> Dict[str, str]:
    """
    Carrega o mapeamento de IP para Setor a partir de um arquivo CSV.
    Assume que o CSV tem as colunas 'IP' e 'Sector'.
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
    except FileNotFoundError:
        print(f"Aviso: Arquivo de mapeamento '{csv_filepath}' não encontrado.")
    except Exception as e:
        print(f"Erro ao ler CSV de mapeamento: {e}")
    return sector_map


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (startup e shutdown)"""
    # Startup: Carrega o mapeamento de setores
    global sector_map_cache
    sector_map_cache = load_sector_mapping('ip_sector.csv')
    print(f"Mapeamento de setores carregado: {len(sector_map_cache)} entradas")
    yield
    # Shutdown: Cleanup se necessário
    print("Encerrando aplicação...")


app = FastAPI(
    title="Printer Monitoring API", 
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_snmp_value(snmpEngine, printer_ip: str, community_string: str, oid: str) -> tuple[Optional[str], Optional[str]]:
    """
    Função auxiliar para buscar um único valor SNMP OID de uma impressora.
    """
    try:
        transport_target = await UdpTransportTarget.create((printer_ip, 161), timeout=2, retries=1)

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
            return None, f"Error: {errorStatus.prettyPrint()}"
        else:
            if varBinds:
                return str(varBinds[0][1]), None
            else:
                return None, "Error: No data returned for OID."
    except Exception as e:
        return None, f"Exception: {str(e)}"


async def get_printer_info(snmpEngine, printer_ip: str, community_string: str, oids: Dict[str, str], sector_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Busca várias informações SNMP para uma impressora específica,
    incluindo verificação robusta de número de série e informações de setor.
    """
    printer_data = {
        'ip_address': printer_ip,
        'sector': sector_map.get(printer_ip, 'N/A'),
        'status': 'checking'
    }

    # Buscar informações básicas
    for name, oid in oids.items():
        value, error_msg = await get_snmp_value(snmpEngine, printer_ip, community_string, oid)
        field_name = name.lower().replace(' ', '_')
        if error_msg:
            printer_data[field_name] = error_msg
            if 'timeout' in error_msg.lower() or 'unreachable' in error_msg.lower():
                printer_data['status'] = 'offline'
        else:
            printer_data[field_name] = value
            if printer_data.get('status') != 'offline':
                printer_data['status'] = 'online'

    # Tentar buscar número de série com múltiplos OIDs
    serial_oids_to_try = [
        '1.3.6.1.2.1.43.5.1.1.17.1',  # Standard MIB serial number OID
        '1.3.6.1.4.1.367.3.2.1.2.1.4.0'  # Ricoh specific serial number OID
    ]

    serial_number_found = False
    for serial_oid in serial_oids_to_try:
        value, error_msg = await get_snmp_value(snmpEngine, printer_ip, community_string, serial_oid)
        if value is not None:
            printer_data['serial_number'] = value
            serial_number_found = True
            break

    if not serial_number_found:
        printer_data['serial_number'] = "N/A"

    return printer_data


@app.get("/")
async def read_root():
    """Serve o arquivo HTML principal"""
    return FileResponse('static/index.html')


@app.get("/api/printers")
async def get_all_printers() -> List[Dict[str, Any]]:
    """
    Endpoint para buscar informações de todas as impressoras.
    Retorna uma lista de objetos JSON com dados de cada impressora.
    """
    snmpEngine = SnmpEngine()
    
    try:
        tasks = [
            get_printer_info(snmpEngine, ip, community_string, oids, sector_map_cache) 
            for ip in printer_ips
        ]
        
        results = await asyncio.gather(*tasks)
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar informações: {str(e)}")
    
    finally:
        snmpEngine._close()


@app.get("/api/printer/{ip}")
async def get_printer_by_ip(ip: str) -> Dict[str, Any]:
    """
    Endpoint para buscar informações de uma impressora específica por IP.
    """
    if ip not in printer_ips:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")
    
    snmpEngine = SnmpEngine()
    
    try:
        printer_data = await get_printer_info(snmpEngine, ip, community_string, oids, sector_map_cache)
        return printer_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar informações: {str(e)}")
    
    finally:
        snmpEngine._close()


@app.get("/api/sectors")
async def get_sectors() -> List[str]:
    """
    Endpoint para listar todos os setores disponíveis.
    """
    sectors = list(set(sector_map_cache.values()))
    return sorted(sectors)


@app.get("/api/printers/sector/{sector}")
async def get_printers_by_sector(sector: str) -> List[Dict[str, Any]]:
    """
    Endpoint para buscar impressoras de um setor específico.
    """
    # Filtrar IPs do setor solicitado
    sector_ips = [ip for ip, s in sector_map_cache.items() if s == sector]
    
    if not sector_ips:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    
    snmpEngine = SnmpEngine()
    
    try:
        tasks = [
            get_printer_info(snmpEngine, ip, community_string, oids, sector_map_cache) 
            for ip in sector_ips
        ]
        
        results = await asyncio.gather(*tasks)
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar informações: {str(e)}")
    
    finally:
        snmpEngine._close()


# Montar diretório de arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    print("Iniciando servidor FastAPI...")
    print("Acesse: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)