# Monitor de Impressoras SNMP - Full Stack

Sistema completo de monitoramento de impressoras via SNMP com backend FastAPI e frontend HTML/JavaScript.

## 🚀 Características

### Backend (FastAPI)
- **API REST** com endpoints para consulta de impressoras
- **Consultas SNMP assíncronas** para melhor performance
- **Cache de mapeamento de setores**
- **CORS habilitado** para facilitar desenvolvimento
- **Documentação automática** (Swagger UI)

### Frontend (HTML/CSS/JavaScript)
- **Interface moderna e responsiva**
- **Atualização em tempo real** dos dados
- **Filtros por setor** e busca textual
- **Dashboard com estatísticas** (online/offline)
- **Cards informativos** para cada impressora
- **Design gradient** com visual profissional

## 📋 Pré-requisitos

```bash
Python 3.8+
pip (gerenciador de pacotes Python)
```

## 🔧 Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

Ou instalar manualmente:

```bash
pip install fastapi uvicorn pysnmp pysnmp-hlapi python-multipart
```

### 2. Configurar arquivo de mapeamento IP-Setor

Certifique-se de ter o arquivo `ip_sector.csv` no diretório raiz com o seguinte formato:

```csv
IP,Sector
172.16.5.1,TI
172.16.5.2,Administrativo
172.16.5.3,Financeiro
...
```

## 🎯 Como Usar

### Iniciar o servidor

```bash
python backend.py
```

Ou usando uvicorn diretamente:

```bash
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

### Acessar a aplicação

1. **Interface Web**: http://localhost:8000
2. **Documentação da API**: http://localhost:8000/docs
3. **API alternativa**: http://localhost:8000/redoc

## 📡 Endpoints da API

### GET /api/printers
Retorna informações de todas as impressoras.

**Resposta:**
```json
[
  {
    "ip_address": "172.16.5.1",
    "sector": "TI",
    "status": "online",
    "printer_model": "HP LaserJet Pro M404dn",
    "serial_number": "ABC123456",
    "total_page_count": "15432",
    "device_status": "3"
  }
]
```

### GET /api/printer/{ip}
Retorna informações de uma impressora específica.

**Exemplo:**
```
GET /api/printer/172.16.5.1
```

### GET /api/sectors
Lista todos os setores disponíveis.

**Resposta:**
```json
["Administrativo", "Financeiro", "TI", "RH"]
```

### GET /api/printers/sector/{sector}
Retorna impressoras de um setor específico.

**Exemplo:**
```
GET /api/printers/sector/TI
```

## 🎨 Funcionalidades do Frontend

### Dashboard Principal
- **Estatísticas em tempo real**: Total, Online, Offline
- **Cards de impressoras**: Com status visual por cor
- **Informações detalhadas**: IP, Setor, Modelo, Serial, Páginas

### Filtros e Busca
- **Filtro por setor**: Dropdown com todos os setores
- **Busca textual**: Por IP, modelo, serial ou setor
- **Atualização manual**: Botão para forçar refresh

### Status das Impressoras
- 🟢 **Online**: Impressora respondendo ao SNMP
- 🔴 **Offline**: Sem resposta ou erro de conexão
- 🟡 **Checking**: Verificando status

## ⚙️ Configuração Avançada

### Alterar IPs das impressoras

No arquivo `backend.py`, modifique a lista:

```python
printer_ips = [f"172.16.5.{i}" for i in range(1, 26)]
```

### Alterar community string SNMP

```python
community_string = 'public'  # Altere para sua community
```

### Adicionar novos OIDs

```python
oids = {
    'Printer Model': '1.3.6.1.2.1.1.1.0',
    'Total Page Count': '1.3.6.1.2.1.43.10.2.1.4.1.1',
    'Device Status': '1.3.6.1.2.1.25.3.2.1.5.1',
    'Novo Campo': 'SEU.OID.AQUI',
}
```

### Alterar porta do servidor

```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Altere a porta aqui
```

## 🐛 Troubleshooting

### Erro: "Arquivo ip_sector.csv não encontrado"
- Verifique se o arquivo está no diretório raiz do projeto
- Confirme que o nome está correto (case-sensitive)

### Impressoras não respondem
- Verifique conectividade de rede
- Confirme que SNMP está habilitado nas impressoras
- Teste a community string (padrão: 'public')
- Verifique firewall/regras de rede

### Timeout nas consultas
- Aumente o timeout no código (padrão: 2 segundos)
- Verifique latência da rede
- Reduza número de impressoras consultadas simultaneamente

### CORS errors no frontend
- Middleware CORS já está configurado
- Verifique se está acessando pela mesma origem

## 📦 Estrutura do Projeto

```
.
├── backend.py              # Servidor FastAPI
├── static/
│   └── index.html         # Frontend HTML/CSS/JS
├── ip_sector.csv          # Mapeamento IP-Setor
├── requirements.txt       # Dependências Python
└── README.md             # Esta documentação
```

## 🔒 Segurança

⚠️ **Importante para produção:**

1. **Não use 'public' como community string**
2. **Configure HTTPS** (use certificados SSL/TLS)
3. **Implemente autenticação** na API
4. **Restrinja CORS** para domínios específicos
5. **Use SNMPv3** com criptografia quando possível
6. **Valide e sanitize inputs** do usuário

## 📝 Melhorias Futuras

- [ ] Autenticação de usuários
- [ ] Histórico de status das impressoras
- [ ] Alertas por email/SMS
- [ ] Gráficos de consumo de páginas
- [ ] Exportação de relatórios em PDF/Excel
- [ ] Suporte a múltiplas redes/subnets
- [ ] Agendamento de verificações
- [ ] Dashboard administrativo

## 👨‍💻 Autor

Sistema desenvolvido para monitoramento de impressoras corporativas via SNMP.

## 📄 Licença

Este projeto é de código aberto para uso educacional e corporativo.
