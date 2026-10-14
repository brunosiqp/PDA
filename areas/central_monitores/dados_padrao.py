"""Clientes da Central de Monitores como vinham no HTML até a 3.2.7.2 (padrão quando não existe o
central_monitores.json, que é o que a aba Editar grava, 3.2.8.0). Gerado dos antigos CLIENT_META e clients do
telas/central_monitores.py; os logos "__LOGO_MONITOR_<NOME>__" e "__LOGO__" são trocados pela imagem ao montar a página."""
import json

CLIENTES_PADRAO = json.loads(r'''[
 {
  "name": "Saas",
  "sub": "",
  "color": "linear-gradient(135deg, oklch(0.7 0.13 205), oklch(0.83 0.19 120))",
  "initials": "IV",
  "logo": "__LOGO__",
  "logoBg": "",
  "links": [
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://saas.example.app/NFePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe 2",
    "type": "NFe",
    "url": "https://saas2.example.app/NFePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFCe",
    "type": "NFCe",
    "url": "https://saas.example.app/NFCePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://saas.example.app/CTePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "CTe 2",
    "type": "CTe",
    "url": "https://saas.example.app/CTe2PackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "MDFe",
    "type": "MDFe",
    "url": "https://saas.example.app/MDFePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://saas.example.app/NFSePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSe Soft",
    "type": "NFSe Soft",
    "url": "https://saas.example.app/soft/NFSePackMonitor/Sessao.aspx/Entrar",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs 2",
    "type": "PowerDocs",
    "url": "https://saas.example.app/powerdocs2/#/home",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://hom.example.app/nfepackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "NFCe",
    "type": "NFCe",
    "url": "https://hom.example.app/nfcepackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://hom.example.app/ctepackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "MDFe",
    "type": "MDFe",
    "url": "https://hom.example.app/mdfepackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://hom.example.app/nfsepackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "NFSeR",
    "type": "NFSeR",
    "url": "https://hom.example.app/nfserpackmonitor",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://hom.example.app/powerdocs",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "RabbitMQ Saas",
    "type": "RabbitMQ",
    "url": "http://srv809.example.net:15672/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "FTP Saas",
    "type": "FTP",
    "url": "http://ftp.example.net/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "Graylog Saas",
    "type": "Graylog",
    "url": "http://srv738.example.net:9000/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ Saas",
    "type": "RabbitMQ",
    "url": "http://srv221.example.net:15672/",
    "env": "HML",
    "grupo": ""
   }
  ],
  "servidores": [
   {
    "grupo": "Servidores",
    "env": "PRD",
    "itens": [
     "srv576",
     "srv647",
     "srv720",
     "srv809"
    ]
   }
  ],
  "aplicacoes": [
   {
    "host": "192.0.2.164",
    "env": "PRD",
    "produtos": [
     "CTePack",
     "CTePackClienteM",
     "CTePackHML",
     "EmailPack",
     "MDFePack",
     "NFCePack",
     "NFePack",
     "NFePackRT",
     "NFePackWebScraping",
     "NFSePack",
     "NFSeRPack",
     "PowerDocs",
     "Publicador"
    ]
   },
   {
    "host": "192.0.2.229",
    "env": "PRD",
    "produtos": [
     "CTePack",
     "EmailPack",
     "NFCePack",
     "NFePack",
     "NFSePack",
     "NFSeRPack",
     "PowerDocs",
     "PowerDocs2",
     "Publicador"
    ]
   },
   {
    "host": "192.0.2.46",
    "env": "PRD",
    "produtos": [
     "CTePack",
     "EmailPack",
     "NFCePack",
     "NFePack",
     "NFSeRPack",
     "PowerDocs2",
     "Publicador"
    ]
   },
   {
    "host": "192.0.2.228",
    "env": "PRD",
    "produtos": [
     "MDFePack",
     "NFSePackSoft"
    ]
   },
   {
    "host": "192.0.2.206",
    "env": "PRD",
    "produtos": [
     "NFSePackSoft"
    ]
   },
   {
    "host": "192.0.2.186",
    "env": "PRD",
    "produtos": [
     "EmailPack",
     "NFePack"
    ]
   }
  ]
 },
 {
  "name": "ClienteH",
  "sub": "",
  "color": "#E4007C",
  "initials": "RI",
  "logo": "__LOGO_MONITOR_CLIENTE_H__",
  "logoBg": "",
  "links": [
   {
    "label": "NFCe",
    "type": "NFCe",
    "url": "http://cliente_h.example.app/NFCePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "Publicador eDocs",
    "type": "Publicador",
    "url": "http://srv213.example.net/publicadormonitor/#/reintegrar",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_h.example.app/powerdocs/#/login",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "Redis",
    "type": "Outros",
    "url": "https://cliente_h.example.app/nfcepackmonitor/DocumentoIntegrarRedis.aspx",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ ClienteH",
    "type": "RabbitMQ",
    "url": "http://srv235.example.net:15672",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteJ",
  "sub": "",
  "color": "#004E9F",
  "initials": "CA",
  "logo": "__LOGO_MONITOR_CLIENTE_J__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_j.example.app/CTePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://cliente_j.example.app/NFePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe CDs",
    "type": "NFe",
    "url": "http://192.0.2.181/NFePACKMonitorCDs/Login.aspx?ReturnUrl=%2fNFePACKMonitorCDs%2f",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFCe",
    "type": "NFCe",
    "url": "http://192.0.2.232/NFCePackMonitor/Login.aspx?ReturnUrl=%2fNFCePackMonitor%2f",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe Balcão",
    "type": "NFe",
    "url": "http://192.0.2.181/nfepackmonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "Publicador eDocs",
    "type": "Publicador",
    "url": "http://192.0.2.206/publicadoredocsmonitor/#/documento",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_j.example.app/powerdocs/#/login",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ ClienteJ",
    "type": "RabbitMQ",
    "url": "http://192.0.2.49:15672/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [
   {
    "grupo": "Máquinas NFCe",
    "env": "PRD",
    "itens": [
     "192.0.2.232",
     "192.0.2.245",
     "192.0.2.109",
     "192.0.2.223",
     "192.0.2.247"
    ]
   },
   {
    "grupo": "Máquinas NFe CDs",
    "env": "PRD",
    "itens": [
     "192.0.2.181",
     "192.0.2.75",
     "192.0.2.174:8032",
     "192.0.2.73:8032"
    ]
   },
   {
    "grupo": "Máquinas NFe Balcão",
    "env": "PRD",
    "itens": [
     "192.0.2.181",
     "192.0.2.75",
     "192.0.2.73:8031",
     "192.0.2.174:8031"
    ]
   },
   {
    "grupo": "Máquinas Publicador, REINF e Custódia",
    "env": "PRD",
    "itens": [
     "192.0.2.206",
     "192.0.2.85"
    ]
   },
   {
    "grupo": "Máquinas Homologação",
    "env": "HML",
    "itens": [
     "192.0.2.73",
     "192.0.2.94"
    ]
   },
   {
    "grupo": "Máquinas Infra Empresa",
    "env": "PRD",
    "itens": [
     "svca4edocs10710",
     "svca4edocs10711",
     "svca4lnx10720"
    ]
   }
  ],
  "aplicacoes": []
 },
 {
  "name": "ClienteK",
  "sub": "",
  "color": "#C8102E",
  "initials": "LA",
  "logo": "__LOGO_MONITOR_CLIENTE_L__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_k.example.app/CTePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://cliente_k.example.app/NFePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://cliente_k.example.app/NFSePackMonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe Legado",
    "type": "NFe",
    "url": "https://historicocliente_k.example.app/nfepackmonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSeR",
    "type": "NFSeR",
    "url": "https://cliente_k.example.app/nfserpackmonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ ClienteK",
    "type": "RabbitMQ",
    "url": "http://srv044.example.net:15672/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteM",
  "sub": "",
  "color": "#D40511",
  "initials": "ClienteM",
  "logo": "__LOGO_MONITOR_CLIENTE_M__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_m.example.app/CTePackMonitor/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteA",
  "sub": "",
  "color": "#0B0B0B",
  "initials": "SH",
  "logo": "__LOGO_MONITOR_CLIENTE_A__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_a.example.app/CTePackMonitor/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteE",
  "sub": "",
  "color": "#003DA5",
  "initials": "NI",
  "logo": "__LOGO_MONITOR_CLIENTE_E__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_e.example.app/CTePackMonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "MDFe",
    "type": "MDFe",
    "url": "https://cliente_e.example.app/MDFePackMonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFCe",
    "type": "NFCe",
    "url": "https://cliente_e.example.app/NFCePackMonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://cliente_e.example.app/NFePackMonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_e.example.app/powerdocs/#/login?returnUrl=%2Femissao%2Fnfe",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteN",
  "sub": "",
  "color": "#E4002B",
  "initials": "IG",
  "logo": "__LOGO_MONITOR_CLIENTE_N__",
  "logoBg": "",
  "links": [
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_n.example.app/ctepackmonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://cliente_n.example.app/nfepackmonitor/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://cliente_n.example.app/nfsepackmonitor/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteB",
  "sub": "",
  "color": "#0072B8",
  "initials": "SP",
  "logo": "__LOGO_MONITOR_CLIENTE_B__",
  "logoBg": "",
  "links": [
   {
    "label": "NFe",
    "type": "NFe",
    "url": "https://cliente_b.example.app/nfepackmonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "CTe",
    "type": "CTe",
    "url": "https://cliente_b.example.app/ctepackmonitor/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteI",
  "sub": "",
  "color": "#5B3FD6",
  "initials": "MY",
  "logo": "__LOGO_MONITOR_CLIENTE_I__",
  "logoBg": "",
  "links": [
   {
    "label": "ClienteI Enterprise",
    "type": "ClienteI",
    "url": "https://cliente_ah.cliente_i.app/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "ClienteI Standard",
    "type": "ClienteI",
    "url": "http://prd.cliente_i.app/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "ClienteI ClienteAE",
    "type": "ClienteI",
    "url": "https://cliente_ae.cliente_i.app/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "ClienteI Demo",
    "type": "ClienteI",
    "url": "https://demo.cliente_i.com.br/",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "RabbitMQ ClienteI",
    "type": "RabbitMQ",
    "url": "http://192.0.2.89:15672/",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [
   {
    "grupo": "Servidores",
    "env": "PRD",
    "itens": [
     "srv218",
     "srv207",
     "srv139",
     "srv519"
    ]
   }
  ],
  "aplicacoes": [
   {
    "host": "srv218",
    "env": "PRD",
    "produtos": [
     "MDFePack",
     "BatimentoWebApp",
     "NFCePack",
     "NFSePack"
    ]
   },
   {
    "host": "srv207",
    "env": "PRD",
    "produtos": [
     "CTePack",
     "EmailPack",
     "MDFePack",
     "NFePack"
    ]
   },
   {
    "host": "srv099",
    "env": "PRD",
    "produtos": [
     "EmailPack",
     "NFCePack",
     "NFePack",
     "NFSePack"
    ]
   },
   {
    "host": "srv218",
    "env": "PRD",
    "produtos": [
     "NFePack_CLIENTE_AE",
     "NFSePack_CLIENTE_AE"
    ]
   }
  ]
 },
 {
  "name": "ClienteG",
  "sub": "",
  "color": "#660099",
  "initials": "VI",
  "logo": "__LOGO_MONITOR_CLIENTE_G__",
  "logoBg": "#ffffff",
  "links": [
   {
    "label": "Graylog",
    "type": "Graylog",
    "url": "http://srv916.example.net:9000/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "Graylog OLD",
    "type": "Graylog",
    "url": "http://srv581.example.net:9000/",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ PRD",
    "type": "RabbitMQ",
    "url": "http://srv893.example.net:15672/#/queues",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "RabbitMQ HML",
    "type": "RabbitMQ",
    "url": "http://srv175.example.net:15672/#/",
    "env": "HML",
    "grupo": ""
   },
   {
    "label": "Kubernetes",
    "type": "Kubernetes",
    "url": "https://192.0.2.24/#/login",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_g.example.app/powerdocs#/emissao/nfcom",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_g_hom.example.app/cliente_gpowerdocsclient/#/login",
    "env": "HML",
    "grupo": ""
   }
  ],
  "servidores": [
   {
    "grupo": "Jumper",
    "env": "PRD",
    "itens": [
     "srv901.example.net"
    ]
   },
   {
    "grupo": "JMeter",
    "env": "PRD",
    "itens": [
     "srv001.example.net"
    ]
   },
   {
    "grupo": "NFCe",
    "env": "PRD",
    "itens": [
     "srv130.example.net"
    ]
   },
   {
    "grupo": "NFCe",
    "env": "HML",
    "itens": [
     "srv709.example.net"
    ]
   },
   {
    "grupo": "Linux",
    "env": "PRD",
    "itens": [
     "srv066.example.net"
    ]
   },
   {
    "grupo": "Linux",
    "env": "HML",
    "itens": [
     "srv702.example.net"
    ]
   }
  ],
  "aplicacoes": []
 },
 {
  "name": "ClienteO",
  "sub": "",
  "color": "#212E3E",
  "initials": "ED",
  "logo": "__LOGO_MONITOR_CLIENTE_O__",
  "logoBg": "#212E3E",
  "links": [
   {
    "label": "PowerDocs",
    "type": "PowerDocs",
    "url": "https://cliente_o.example.app/powerdocs/#/recuperarconta",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteD",
  "sub": "",
  "color": "#1E2A5A",
  "initials": "AC",
  "logo": "__LOGO_MONITOR_CLIENTE_D__",
  "logoBg": "",
  "links": [
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://cliente_d.example.app/nfsepackmonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSeR",
    "type": "NFSeR",
    "url": "https://cliente_d.example.app/nfserpackmonitor",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 },
 {
  "name": "ClienteP",
  "sub": "",
  "color": "#1F2A3C",
  "initials": "AT",
  "logo": "__LOGO_MONITOR_CLIENTE_P__",
  "logoBg": "#ffffff",
  "links": [
   {
    "label": "NFSe",
    "type": "NFSe",
    "url": "https://cliente_p.example.app/NFSePackMonitor",
    "env": "PRD",
    "grupo": ""
   },
   {
    "label": "NFSeR",
    "type": "NFSeR",
    "url": "https://cliente_p.example.app/nfserpackmonitor",
    "env": "PRD",
    "grupo": ""
   }
  ],
  "servidores": [],
  "aplicacoes": []
 }
]''')
