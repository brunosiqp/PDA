"""Tela Dashboards Clientes.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_DASHBOARDS_CLIENTES_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Dashboards por Cliente</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
__NAVBAR_CSS__
  .cabecalho-dc { max-width: var(--largura-pagina); margin: 0 auto 24px auto; }
  .cabecalho-dc h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-dc .sub { color: var(--fg-dim); font-size: 12.5px; }
  .aviso-beta-dc { max-width: var(--largura-pagina); margin: 0 auto 24px auto; background: rgba(255,143,163,.08);
                   border: 1px solid rgba(255,143,163,.3); border-radius: 10px; padding: 12px 16px;
                   font-size: 12.5px; color: var(--fg); line-height: 1.6; }
  .aviso-beta-dc b { color: #f5a3d0; }

  .painel-dc { max-width: var(--largura-pagina); margin: 0 auto 20px auto; background: var(--bg-panel);
               backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 24px 26px; }
  .painel-dc h3 { margin: 0 0 16px 0; font-size: 13px; color: var(--teal); text-transform: uppercase; letter-spacing: .04em; }

  .grade-selecao-dc { display: flex; gap: 12px; flex-wrap: wrap; }
  .pill-dc { padding: 12px 22px; border-radius: 10px; border: 1px solid var(--border); background: rgba(var(--tinta),.03);
             cursor: pointer; font-size: 13px; font-weight: 600; color: var(--fg-dim); transition: all .15s; }
  .pill-dc:hover { border-color: var(--border-forte); color: var(--fg); }
  .pill-dc.ativa { border-color: var(--teal); background: rgba(45,184,207,.1); color: var(--teal); }

  .trilha-dc { display: flex; align-items: center; gap: 8px; max-width: var(--largura-pagina); margin: 0 auto 20px auto;
               font-size: 12.5px; color: var(--fg-dim); }
  .trilha-dc .atual { color: var(--teal); font-weight: 700; }

  .placeholder-dc { text-align: center; padding: 50px 20px; color: var(--fg-dim); }
  .placeholder-dc .icone-placeholder-dc { font-size: 40px; margin-bottom: 14px; }
  .placeholder-dc .titulo-placeholder-dc { font-size: 15px; color: var(--fg); font-weight: 700; margin-bottom: 6px; }

  /* Dashboard ClienteB > NFAg - único já implementado de verdade */
  .cabecalho-nfag-dc { display: flex; align-items: center; justify-content: space-between;
      background: #1E2A38; border-radius: 12px; padding: 14px 24px; margin-bottom: 18px; }
  .cabecalho-nfag-dc .logo-nfag-dc { height: 34px; width: auto; }
  .cabecalho-nfag-dc .titulo-nfag-dc { color: #fff; font-size: 15px; font-weight: 700; letter-spacing: .02em; }
  .filtro-data-nfag-dc { display: flex; align-items: flex-end; gap: 14px; flex-wrap: wrap; }
  .filtro-data-nfag-dc div { display: flex; flex-direction: column; gap: 5px; }
  .filtro-data-nfag-dc label { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .04em; }
  .filtro-data-nfag-dc input[type="date"] { padding: 8px 10px; border-radius: 7px; border: 1px solid var(--border);
      background: rgba(var(--poco),.28); color: var(--fg); font-size: 12.5px; font-family: inherit; }
  .grade-kpis-nfag-dc { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0; }
  .kpi-nfag-dc { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px;
      padding: 18px; text-align: center; }
  .kpi-nfag-dc .valor-kpi-nfag-dc { font-size: 26px; font-weight: 800; color: var(--teal); }
  .kpi-nfag-dc .rotulo-kpi-nfag-dc { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; margin-top: 4px; }
  @media (max-width: 700px) { .grade-kpis-nfag-dc { grid-template-columns: repeat(2, 1fr); } }
  .container-grafico-nfag-dc { position: relative; height: 220px; width: 100%; }
  #painel-dashboard-nfag-dc { max-width: var(--largura-pagina); margin: 0 auto; }
  #painel-dashboard-nfag-dc .painel-dc { max-width: none; margin: 0 0 18px 0; }
  .vazio-grafico-nfag-dc { display: flex; align-items: center; justify-content: center; height: 220px;
      color: var(--fg-dim); font-size: 12.5px; text-align: center; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-dc">
      <h1>Dashboards por Cliente</h1>
      <div class="sub">Indicadores específicos de cada cliente, por produto.</div>
    </div>

    <div class="aviso-beta-dc">
      <b>Beta:</b> por enquanto só a navegação entre cliente e produto está pronta - os dashboards de verdade
      (gráficos, indicadores) ainda vão ser construídos. Selecione um cliente e um produto pra ver o estado atual.
    </div>

    <div class="trilha-dc" id="trilha-dc">
      <span>Selecione um cliente</span>
    </div>

    <div class="painel-dc" id="painel-clientes-dc">
      <h3>Cliente</h3>
      <div class="grade-selecao-dc" id="grade-clientes-dc">
        <div class="vazio-mu">Carregando...</div>
      </div>
    </div>

    <div class="painel-dc" id="painel-produtos-dc" style="display:none">
      <h3>Produto</h3>
      <div class="grade-selecao-dc" id="grade-produtos-dc"></div>
    </div>

    <!-- Dashboard ClienteB > NFAg - transcrito do Power BI (08/09/2026),
         único já implementado de verdade por enquanto -->
    <div id="painel-dashboard-nfag-dc" style="display:none">
      <div class="cabecalho-nfag-dc">
        <img class="logo-nfag-dc" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPCFET0NUWVBFIHN2ZyBQVUJMSUMgIi0vL1czQy8vRFREIFNWRyAxLjEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkIj4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZlcnNpb249IjEuMSIgd2lkdGg9IjE4NjlweCIgaGVpZ2h0PSI0NTBweCIgc3R5bGU9InNoYXBlLXJlbmRlcmluZzpnZW9tZXRyaWNQcmVjaXNpb247IHRleHQtcmVuZGVyaW5nOmdlb21ldHJpY1ByZWNpc2lvbjsgaW1hZ2UtcmVuZGVyaW5nOm9wdGltaXplUXVhbGl0eTsgZmlsbC1ydWxlOmV2ZW5vZGQ7IGNsaXAtcnVsZTpldmVub2RkIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayI+CjxnPjxwYXRoIHN0eWxlPSJvcGFjaXR5OjAuOTUxIiBmaWxsPSIjMDE1NjlhIiBkPSJNIDgwLjUsMTYxLjUgQyA4MC40MzQ2LDE2MS45MzggODAuNjAxMiwxNjIuMjcyIDgxLDE2Mi41QyA4My44NDkxLDE2MS42MjIgODYuMzQ5MSwxNjAuMjg5IDg4LjUsMTU4LjVDIDEyMy4xMTcsMTQ4LjU2NCAxNTguNDUxLDE0My4wNjQgMTk0LjUsMTQyQyAxOTYuNSwxNDEgMTk4LjUsMTQwIDIwMC41LDEzOUMgMjQxLjgzMywxMDQgMjgzLjE2Nyw2OSAzMjQuNSwzNEMgMzUwLjE2NywzMy4zMzMzIDM3NS44MzMsMzMuMzMzMyA0MDEuNSwzNEMgNDA2LjQwNCwzNS4xNTYyIDQwNi43MzgsMzcuMTU2MiA0MDIuNSw0MEMgMzQyLjE2Nyw5Mi4zMzMzIDI4MS44MzMsMTQ0LjY2NyAyMjEuNSwxOTdDIDE4Ny4zMjQsMTk3LjQ4OSAxNTMuMzI0LDIwMC4xNTUgMTE5LjUsMjA1QyA5OS40NjMzLDIwOC4xMjMgNzkuOTYzMywyMTMuMjkgNjEsMjIwLjVDIDU5LjUsMjIwLjMzMyA1OC42NjY3LDIxOS41IDU4LjUsMjE4QyA2Mi40NTMxLDIwMC42ODcgNjYuOTUzMSwxODMuNTIxIDcyLDE2Ni41QyA3My43MzQxLDE2My4wNzggNzYuNTY3NCwxNjEuNDExIDgwLjUsMTYxLjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC45NTEiIGZpbGw9IiMwMDU1OWEiIGQ9Ik0gMzU1LjUsMTIyLjUgQyAzNTUuNDM1LDEyMi45MzggMzU1LjYwMSwxMjMuMjcyIDM1NiwxMjMuNUMgMzU3LjAzOSwxMjIuNzU2IDM1Ny41MzksMTIxLjc1NiAzNTcuNSwxMjAuNUMgMzkxLjI5NCw5MS44NzY2IDQyNC45NjEsNjMuMDQzMyA0NTguNSwzNEMgNDg3Ljg5NSwzMy4wMjQzIDUxNy4yMjgsMzMuMzU3NiA1NDYuNSwzNUMgNTQ3LjUsMzcuMDkwNyA1NDYuODMzLDM4Ljc1NzQgNTQ0LjUsNDBDIDQ5Ni44NzQsNzkuMjkwNCA0NDkuNTQxLDExOC45NTcgNDAyLjUsMTU5QyA0NTYuNTMxLDE2NS4xOTUgNTEwLjUzMSwxNjQuODYxIDU2NC41LDE1OEMgNTc3LjIwNiwxNTYuMDU5IDU4OS43MDYsMTUzLjIyNSA2MDIsMTQ5LjVDIDYwMy43MzIsMTQ5LjczNCA2MDQuNTY2LDE1MC43MzQgNjA0LjUsMTUyLjVDIDYwMC40NjksMTcwLjI5IDU5NS45NjksMTg3Ljk1NiA1OTEsMjA1LjVDIDU3Ny45OTgsMjEwLjc2OSA1NjQuNDk4LDIxNC4yNjkgNTUwLjUsMjE2QyA0OTUuODcxLDIyMi44MzcgNDQxLjIwNCwyMjMuMTcgMzg2LjUsMjE3QyAzNDcuNTEzLDIxMS41NzMgMzA4LjUxMywyMDYuMjQgMjY5LjUsMjAxQyAyNjguMjUzLDE5OS41MDYgMjY4LjI1MywxOTguMDA2IDI2OS41LDE5Ni41QyAyOTcuODkxLDE3MS40MzcgMzI2LjU1OCwxNDYuNzcgMzU1LjUsMTIyLjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC4wMzgiIGZpbGw9IiMwMDAwZmYiIGQ9Ik0gMzU3LjUsMTIwLjUgQyAzNTcuNTM5LDEyMS43NTYgMzU3LjAzOSwxMjIuNzU2IDM1NiwxMjMuNUMgMzU1LjYwMSwxMjMuMjcyIDM1NS40MzUsMTIyLjkzOCAzNTUuNSwxMjIuNUMgMzU1LjgzMywxMjEuNSAzNTYuNSwxMjAuODMzIDM1Ny41LDEyMC41IFoiLz48L2c+CjxnPjxwYXRoIHN0eWxlPSJvcGFjaXR5OjAuOTM2IiBmaWxsPSIjMDE1NDk5IiBkPSJNIDc1My41LDI1MS41IEMgNzUyLjYxOCwyNDkuNjE2IDc1MS4xMTgsMjQ4LjI4MyA3NDksMjQ3LjVDIDc0OC42MDEsMjQ3LjcyOCA3NDguNDM1LDI0OC4wNjIgNzQ4LjUsMjQ4LjVDIDcyOC41ODcsMjQ0LjM2NiA3MDkuOTIxLDIzNy4xOTkgNjkyLjUsMjI3QyA2NzkuMjEsMjE0LjI1OCA2NzUuNzEsMTk5LjA5MSA2ODIsMTgxLjVDIDY4Ny4zODYsMTY4Ljc4MSA2OTYuMjE5LDE1OS4yODEgNzA4LjUsMTUzQyA3MTcuNTkzLDE0OS41MjUgNzI2LjkyNywxNDYuODU4IDczNi41LDE0NUMgNzYwLjUyOSwxNDIuOTIxIDc4NC4xOTYsMTQ0LjkyMSA4MDcuNSwxNTFDIDgxMC41ODMsMTUyLjEzOSA4MTMuNTgzLDE1My40NzIgODE2LjUsMTU1QyA4MTcuNTc2LDE1Ni43MjYgODE3Ljc0MywxNTguNTU5IDgxNywxNjAuNUMgODE0LjU1LDE3MS44MDEgODExLjcxNywxODIuOTY4IDgwOC41LDE5NEMgODA1LjgzMywxOTQuNjY3IDgwMy4xNjcsMTk0LjY2NyA4MDAuNSwxOTRDIDc3OC4wMzYsMTc4LjU4OSA3NTQuMDM2LDE3NS41ODkgNzI4LjUsMTg1QyA3MjMuNTM1LDE4OS41MjggNzIzLjUzNSwxOTQuMTk0IDcyOC41LDE5OUMgNzQ0Ljk1NCwyMDUuMjYzIDc2MS42MjEsMjEwLjkyOSA3NzguNSwyMTZDIDgwMS4xNDgsMjI1LjEyNyA4MDkuNjQ4LDI0MS42MjcgODA0LDI2NS41QyA3OTguNDE0LDI4Mi43NTMgNzg3LjA4LDI5NC40MiA3NzAsMzAwLjVDIDczOC4zNDEsMzEwLjYzMiA3MDYuNTA4LDMxMS4xMzIgNjc0LjUsMzAyQyA2NjkuNjY5LDMwMC4zOSA2NjUuMDAzLDI5OC4zOSA2NjAuNSwyOTZDIDY1OS45NzgsMjk1LjQzOSA2NTkuNjQ1LDI5NC43NzIgNjU5LjUsMjk0QyA2NjIuNzE2LDI4MS41ODYgNjY1LjU0OSwyNjkuMDg2IDY2OCwyNTYuNUMgNjcxLjA3MywyNTUuMzgzIDY3NC4yNCwyNTUuMjE2IDY3Ny41LDI1NkMgNzAwLjY4NCwyNzIuNTY5IDcyNi4wMTcsMjc2LjkwMiA3NTMuNSwyNjlDIDc1OS45NTcsMjY1LjEwOCA3NjEuMTI0LDI1OS45NDIgNzU3LDI1My41QyA3NTUuODg3LDI1Mi42OTUgNzU0LjcyMSwyNTIuMDI4IDc1My41LDI1MS41IFoiLz48L2c+CjxnPjxwYXRoIHN0eWxlPSJvcGFjaXR5OjAuOTQiIGZpbGw9IiMwMTU0OWEiIGQ9Ik0gOTExLjUsMTQ0LjUgQyA5MjUuODM3LDE0NC4zMzMgOTQwLjE3MSwxNDQuNSA5NTQuNSwxNDVDIDk1OC43NTMsMTQ1LjIgOTYyLjkyLDE0NS43IDk2NywxNDYuNUMgOTc2Ljk3MSwxOTguOTkzIDk4NS42MzgsMjUxLjY2IDk5MywzMDQuNUMgOTc1LjU3NCwzMDUuNjU4IDk1OC4wNzQsMzA1LjgyNSA5NDAuNSwzMDVDIDkzOC4zODYsMjk0LjkzMSA5MzYuNzIsMjg0Ljc2NSA5MzUuNSwyNzQuNUMgOTEwLjE2NywyNzMuMTY3IDg4NC44MzMsMjczLjE2NyA4NTkuNSwyNzQuNUMgODUyLjUxLDI4NS4wMDcgODQ1LjE3NywyOTUuMTc0IDgzNy41LDMwNUMgODIxLjgyMiwzMDUuNjUzIDgwNi4xNTUsMzA1LjQ4NiA3OTAuNSwzMDQuNUMgNzkwLjM0LDMwMi44MDEgNzkwLjUwNiwzMDEuMTM0IDc5MSwyOTkuNUMgODMxLjM4MiwyNDcuOTU4IDg3MS41NDgsMTk2LjI5MSA5MTEuNSwxNDQuNSBaIE0gOTIyLjUsMTk5LjUgQyA5MjYuMDgxLDIxNC44NzQgOTI4Ljc0OCwyMzAuNTQxIDkzMC41LDI0Ni41QyA5MTQuODMsMjQ2LjY2NyA4OTkuMTYzLDI0Ni41IDg4My41LDI0NkMgODk3LjA4NywyMzAuOTIgOTEwLjA4NywyMTUuNDIgOTIyLjUsMTk5LjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC45NCIgZmlsbD0iIzAwNTU5YiIgZD0iTSAxMzc3LjUsMTQ0LjUgQyAxNDAxLjE3LDE0NC4zMzMgMTQyNC44NCwxNDQuNSAxNDQ4LjUsMTQ1QyAxNDY0LjYzLDE0NC43ODIgMTQ3OS42MywxNDguNzgyIDE0OTMuNSwxNTdDIDE1MDYuMzEsMTY4Ljc1MiAxNTExLjE0LDE4My4yNTIgMTUwOCwyMDAuNUMgMTUwMy40LDIyNC43NyAxNDg5LjI0LDI0MC42MDQgMTQ2NS41LDI0OEMgMTQ2MC45MiwyNDkuNjQ0IDE0NTYuMjYsMjUwLjk3OCAxNDUxLjUsMjUyQyAxNDM1LjI1LDI1NC4yODYgMTQxOC45MiwyNTUuNjIgMTQwMi41LDI1NkMgMTM5OC45NiwyNzIuNzAzIDEzOTUuMjksMjg5LjM2OSAxMzkxLjUsMzA2QyAxMzc2LjE3LDMwNi42NjcgMTM2MC44MywzMDYuNjY3IDEzNDUuNSwzMDZDIDEzNTUuMDUsMjUyLjA4MSAxMzY1LjcyLDE5OC4yNDggMTM3Ny41LDE0NC41IFogTSAxNDUyLjUsMTgyLjUgQyAxNDUyLjgzLDE4My41IDE0NTMuNSwxODQuMTY3IDE0NTQuNSwxODQuNUMgMTQ1OS4wNywxOTAuMzU2IDE0NTkuNzMsMTk2LjY4OSAxNDU2LjUsMjAzLjVDIDE0NTUuNTEsMjA0Ljc5NSAxNDU0LjUxLDIwNi4xMjggMTQ1My41LDIwNy41QyAxNDQ4LjQxLDIxMS4zOCAxNDQyLjc0LDIxNC4yMTMgMTQzNi41LDIxNkMgMTQyNy44OCwyMTcuMjUyIDE0MTkuMjEsMjE3Ljc1MiAxNDEwLjUsMjE3LjVDIDE0MTIuNTksMjA0LjUyNiAxNDE1LjI2LDE5MS42OTMgMTQxOC41LDE3OUMgMTQzMC4xNywxNzcuNTQyIDE0NDEuNSwxNzguNzA5IDE0NTIuNSwxODIuNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjk0IiBmaWxsPSIjMDE1NDlhIiBkPSJNIDE1NzMuNSwxNDQuNSBDIDE1ODcuODQsMTQ0LjMzMyAxNjAyLjE3LDE0NC41IDE2MTYuNSwxNDVDIDE2MjAuNzUsMTQ1LjIgMTYyNC45MiwxNDUuNyAxNjI5LDE0Ni41QyAxNjM4Ljk3LDE5OC45OTMgMTY0Ny42NCwyNTEuNjYgMTY1NSwzMDQuNUMgMTYzNy41NywzMDUuNjU4IDE2MjAuMDcsMzA1LjgyNSAxNjAyLjUsMzA1QyAxNjAwLjM5LDI5NC45MzEgMTU5OC43MiwyODQuNzY1IDE1OTcuNSwyNzQuNUMgMTU3Mi4xNywyNzMuMTY3IDE1NDYuODMsMjczLjE2NyAxNTIxLjUsMjc0LjVDIDE1MTQuNTEsMjg1LjAwNyAxNTA3LjE4LDI5NS4xNzQgMTQ5OS41LDMwNUMgMTQ4My44MiwzMDUuNjUzIDE0NjguMTYsMzA1LjQ4NiAxNDUyLjUsMzA0LjVDIDE0NTIuMzQsMzAyLjgwMSAxNDUyLjUxLDMwMS4xMzQgMTQ1MywyOTkuNUMgMTQ5My4zOCwyNDcuOTU4IDE1MzMuNTUsMTk2LjI5MSAxNTczLjUsMTQ0LjUgWiBNIDE1ODQuNSwxOTkuNSBDIDE1ODguMDgsMjE0Ljg3NCAxNTkwLjc1LDIzMC41NDEgMTU5Mi41LDI0Ni41QyAxNTc2LjgzLDI0Ni42NjcgMTU2MS4xNiwyNDYuNSAxNTQ1LjUsMjQ2QyAxNTU5LjA5LDIzMC45MiAxNTcyLjA5LDIxNS40MiAxNTg0LjUsMTk5LjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC45NDEiIGZpbGw9IiMwMTU0OWEiIGQ9Ik0gMTY5OS41LDE0NC41IEMgMTczMS4xOSwxNDQuMTI1IDE3NjIuODUsMTQ0LjYyNSAxNzk0LjUsMTQ2QyAxODEwLjQ3LDE0Ny41NjkgMTgyMy45NywxNTQuMDY5IDE4MzUsMTY1LjVDIDE4NDYuOTUsMTg3LjY2IDE4NDMuNzgsMjA3LjQ5MyAxODI1LjUsMjI1QyAxODE3LjUyLDIzMC44MjIgMTgwOC44NiwyMzUuMzIyIDE3OTkuNSwyMzguNUMgMTc5OS4zNSwyMzkuNTUyIDE3OTkuNTIsMjQwLjU1MiAxODAwLDI0MS41QyAxODEzLjMzLDI2MS41IDE4MjYuNjcsMjgxLjUgMTg0MCwzMDEuNUMgMTg0MC42OCwzMDIuNzg0IDE4NDAuNTIsMzAzLjk1MSAxODM5LjUsMzA1QyAxODE3LjgzLDMwNi45ODQgMTc5Ni4xNywzMDYuOTg0IDE3NzQuNSwzMDVDIDE3NjEuMTIsMjg1LjA4IDE3NDcuNjIsMjY1LjI0NyAxNzM0LDI0NS41QyAxNzMzLjUxLDI0My44NjYgMTczMy4zNCwyNDIuMTk5IDE3MzMuNSwyNDAuNUMgMTc1MC41NiwyMzkuODgzIDE3NjUuMzksMjMzLjg4MyAxNzc4LDIyMi41QyAxNzg5LjUyLDE5Ny4yMjMgMTc4MS4zNSwxODUuMjIzIDE3NTMuNSwxODYuNUMgMTc0OC44MSwxODYuNjg2IDE3NDQuMTUsMTg3LjAxOSAxNzM5LjUsMTg3LjVDIDE3MjkuOTksMjI2LjU0OCAxNzIxLjgyLDI2NS44ODEgMTcxNSwzMDUuNUMgMTcwOC41OCwzMDYuMTU3IDE3MDIuMDgsMzA2LjQ5MSAxNjk1LjUsMzA2LjVDIDE2ODUuMjIsMzA2LjYzMSAxNjc1LjA2LDMwNS45NjQgMTY2NSwzMDQuNUMgMTY3NS44NiwyNTEuMDY0IDE2ODcuMzYsMTk3LjczIDE2OTkuNSwxNDQuNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjk1IiBmaWxsPSIjMDE1NDliIiBkPSJNIDEwMzUuNSwxNDYuNSBDIDEwNTUuNTIsMTQ2LjE4NSAxMDc1LjUyLDE0Ni42ODUgMTA5NS41LDE0OEMgMTExMi43OSwxNzUuNDE2IDExMjkuOTYsMjAyLjkxNiAxMTQ3LDIzMC41QyAxMTUzLjY2LDIwMy4xODMgMTE2MC4zMywxNzUuODQ5IDExNjcsMTQ4LjVDIDExODQsMTQ1Ljg1NSAxMjAxLDE0NS44NTUgMTIxOCwxNDguNUMgMTIwNi41NSwyMDEuMTQ3IDExOTQuMzgsMjUzLjY0NyAxMTgxLjUsMzA2QyAxMTY1LjgxLDMwNi44MTkgMTE1MC4xNCwzMDYuNDg2IDExMzQuNSwzMDVDIDExMTQuNDYsMjcxLjc1IDEwOTQuMjksMjM4LjU4MyAxMDc0LDIwNS41QyAxMDY1LjIyLDIzOC4zMDYgMTA1Ny4yMiwyNzEuMzA2IDEwNTAsMzA0LjVDIDEwMzkuNzgsMzA1Ljk3IDEwMjkuNDQsMzA2LjYzNiAxMDE5LDMwNi41QyAxMDEyLjI2LDMwNi40OTEgMTAwNS41OSwzMDYuMTU4IDk5OSwzMDUuNUMgMTAxMC4wNSwyNTIuMjgxIDEwMjIuMjIsMTk5LjI4MSAxMDM1LjUsMTQ2LjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC45MjEiIGZpbGw9IiMwMDU1OWIiIGQ9Ik0gMTIzOS41LDE0Ni41IEMgMTI3OC43NCwxNDYuMTcgMTMxNy45MSwxNDYuNTAzIDEzNTcsMTQ3LjVDIDEzNTUuODYsMTU4LjUyIDEzNTMuNywxNjkuMzUzIDEzNTAuNSwxODBDIDEzMjYuMTcsMTgwLjMzMyAxMzAxLjgzLDE4MC42NjcgMTI3Ny41LDE4MUMgMTI3NS4xMywxODcuOTg5IDEyNzMuNDYsMTk1LjE1NSAxMjcyLjUsMjAyLjVDIDEyOTQuNTIsMjAyLjE5NiAxMzE2LjUyLDIwMi42OTYgMTMzOC41LDIwNEMgMTMzOS4wNiwyMDQuNzI1IDEzMzkuMzksMjA1LjU1OCAxMzM5LjUsMjA2LjVDIDEzMzcuMzksMjE2LjA5MSAxMzM1LjA2LDIyNS41OTEgMTMzMi41LDIzNUMgMTMwOS41MiwyMzYuMTMyIDEyODYuNTIsMjM2Ljc5OCAxMjYzLjUsMjM3QyAxMjYwLjk0LDI0Ny43NjIgMTI1OC42LDI1OC41OTUgMTI1Ni41LDI2OS41QyAxMjgwLjUyLDI2OS4xOTEgMTMwNC41MiwyNjkuNjkxIDEzMjguNSwyNzFDIDEzMjkuMDYsMjcxLjcyNSAxMzI5LjM5LDI3Mi41NTggMTMyOS41LDI3My41QyAxMzI3LjM3LDI4My4xOTUgMTMyNC43LDI5Mi42OTUgMTMyMS41LDMwMkMgMTI4My4xOCwzMDMuNSAxMjQ0Ljg1LDMwMy44MzMgMTIwNi41LDMwM0MgMTIwNS4yMywzMDIuNjkxIDEyMDQuMDcsMzAyLjE5MSAxMjAzLDMwMS41QyAxMjE0LjQ2LDI0OS43MjEgMTIyNi42MiwxOTguMDU0IDEyMzkuNSwxNDYuNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjA1OSIgZmlsbD0iIzBkMzVkMiIgZD0iTSA4OC41LDE1OC41IEMgODYuMzQ5MSwxNjAuMjg5IDgzLjg0OTEsMTYxLjYyMiA4MSwxNjIuNUMgODAuNjAxMiwxNjIuMjcyIDgwLjQzNDYsMTYxLjkzOCA4MC41LDE2MS41QyA4Mi45MzYsMTYwLjEyOSA4NS42MDI3LDE1OS4xMjkgODguNSwxNTguNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjA1NSIgZmlsbD0iIzA0MWNlZSIgZD0iTSAxNDU0LjUsMTg0LjUgQyAxNDUzLjUsMTg0LjE2NyAxNDUyLjgzLDE4My41IDE0NTIuNSwxODIuNUMgMTQ1Mi40MywxODIuMDYyIDE0NTIuNiwxODEuNzI4IDE0NTMsMTgxLjVDIDE0NTQuMDQsMTgyLjI0NCAxNDU0LjU0LDE4My4yNDQgMTQ1NC41LDE4NC41IFoiLz48L2c+CjxnPjxwYXRoIHN0eWxlPSJvcGFjaXR5OjAuMDQ4IiBmaWxsPSIjMDUxNmY1IiBkPSJNIDE0NTYuNSwyMDMuNSBDIDE0NTYuNzIsMjA1LjY4MSAxNDU1Ljg4LDIwNy4zNDcgMTQ1NCwyMDguNUMgMTQ1My42LDIwOC4yNzIgMTQ1My40MywyMDcuOTM4IDE0NTMuNSwyMDcuNUMgMTQ1NC41MSwyMDYuMTI4IDE0NTUuNTEsMjA0Ljc5NSAxNDU2LjUsMjAzLjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC45NTIiIGZpbGw9IiMwMDU1OWEiIGQ9Ik0gNTguNSwyNTcuNSBDIDU4LjQzNDYsMjU3LjkzOCA1OC42MDEyLDI1OC4yNzIgNTksMjU4LjVDIDYwLjU3LDI1Ny42NDIgNjIuMjM2NywyNTYuOTc1IDY0LDI1Ni41QyA2NS4wMjk5LDI1Ni4xNjQgNjUuNTI5OSwyNTUuNDk3IDY1LjUsMjU0LjVDIDEwNy45MDcsMjQzLjMwMyAxNTEuMDc0LDIzNy42MzYgMTk1LDIzNy41QyAyMTcuMTg5LDIzNy43MjYgMjM5LjM1NiwyMzguNTU5IDI2MS41LDI0MEMgMzAyLjI3NSwyNDQuNTE0IDM0Mi45NDIsMjQ5Ljg0NyAzODMuNSwyNTZDIDM4NC44NzYsMjU4LjU0IDM4NC4yMSwyNjAuNTQgMzgxLjUsMjYyQyAzMTUuNSwzMTYuNjY3IDI0OS41LDM3MS4zMzMgMTgzLjUsNDI2QyAxNjguODk4LDQyNy4xNDIgMTU0LjIzMiw0MjcuNjQyIDEzOS41LDQyNy41QyAxMjQuODAzLDQyNy40NzUgMTEwLjEzNiw0MjcuMTQyIDk1LjUsNDI2LjVDIDk1LjIzOCw0MjUuMDIyIDk1LjU3MTMsNDIzLjY4OSA5Ni41LDQyMi41QyAxNDguNTMxLDM4MS44MTQgMjAwLjE5OCwzNDAuNjQ4IDI1MS41LDI5OUMgMTk2LjYzMiwyOTMuMjA5IDE0MS45NjUsMjk0Ljg3NiA4Ny41LDMwNEMgNzEuNDUwNywzMDcuMzUgNTUuNjE3NCwzMTEuNTE2IDQwLDMxNi41QyAzOC41LDMxNi4zMzMgMzcuNjY2NywzMTUuNSAzNy41LDMxNEMgNDAuOTYyNCwyOTcuNjUgNDUuMTI5LDI4MS40ODQgNTAsMjY1LjVDIDUwLjc2NzEsMjYwLjU2NSA1My42MDA0LDI1Ny44OTggNTguNSwyNTcuNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjk1MiIgZmlsbD0iIzAxNTU5YSIgZD0iTSA1NzYuNSwyNDUuNSBDIDU4MC4wOTksMjQ0LjkzOCA1ODIuMDk5LDI0Ni40MzggNTgyLjUsMjUwQyA1NzguNDEyLDI2Ni44NTIgNTc0LjI0NSwyODMuNjg1IDU3MCwzMDAuNUMgNTY5LjE2NywzMDEuMzMzIDU2OC4zMzMsMzAyLjE2NyA1NjcuNSwzMDNDIDU1Mi41MTUsMzA3Ljg2NCA1MzcuMTgyLDMxMS4xOTcgNTIxLjUsMzEzQyA0OTYuODkxLDMxNS40ODcgNDcyLjIyNSwzMTcuMTUzIDQ0Ny41LDMxOEMgNDA0LjY4NSwzNTQuMjM4IDM2MS42ODUsMzkwLjIzOCAzMTguNSw0MjZDIDMwNC4zOTksNDI3LjE0MSAyOTAuMjMyLDQyNy42NDEgMjc2LDQyNy41QyAyNjIuNDU3LDQyNy40OTEgMjQ4Ljk1Nyw0MjcuMTU4IDIzNS41LDQyNi41QyAyMzQuMTY3LDQyNS4xNjcgMjM0LjE2Nyw0MjMuODMzIDIzNS41LDQyMi41QyAyOTkuMzU0LDM2OC44MTIgMzYzLjM1NCwzMTUuMzEyIDQyNy41LDI2MkMgNDYxLjQ4NiwyNjAuMTYgNDk1LjQ4NiwyNTguMTYgNTI5LjUsMjU2QyA1NDUuNjczLDI1NC4yMDIgNTYxLjM0LDI1MC43MDIgNTc2LjUsMjQ1LjUgWiIvPjwvZz4KPGc+PHBhdGggc3R5bGU9Im9wYWNpdHk6MC4wNjMiIGZpbGw9IiMwMTEyZjUiIGQ9Ik0gNzUzLjUsMjUxLjUgQyA3NTEuNjMyLDI1MC43MzcgNzQ5Ljk2NSwyNDkuNzM3IDc0OC41LDI0OC41QyA3NDguNDM1LDI0OC4wNjIgNzQ4LjYwMSwyNDcuNzI4IDc0OSwyNDcuNUMgNzUxLjExOCwyNDguMjgzIDc1Mi42MTgsMjQ5LjYxNiA3NTMuNSwyNTEuNSBaIi8+PC9nPgo8Zz48cGF0aCBzdHlsZT0ib3BhY2l0eTowLjA1OSIgZmlsbD0iIzBkMzVkMyIgZD0iTSA2NS41LDI1NC41IEMgNjUuNTI5OSwyNTUuNDk3IDY1LjAyOTksMjU2LjE2NCA2NCwyNTYuNUMgNjIuMjM2NywyNTYuOTc1IDYwLjU3LDI1Ny42NDIgNTksMjU4LjVDIDU4LjYwMTIsMjU4LjI3MiA1OC40MzQ2LDI1Ny45MzggNTguNSwyNTcuNUMgNjAuNjc5NCwyNTYuMzIzIDYzLjAxMjgsMjU1LjMyMyA2NS41LDI1NC41IFoiLz48L2c+Cjwvc3ZnPgo=" alt="ClienteB">
        <div class="titulo-nfag-dc">Visualização por NFAg</div>
        <img class="logo-nfag-dc" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAgElEQVR4nNXOQREAIAzAsFI/+McFlhCxB9coyNrnUiZxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEufvwNQDbrgCNC99lLIAAAAASUVORK5CYII=" alt="Empresa">
      </div>

      <div class="painel-dc filtro-data-nfag-dc">
        <div>
          <label>De</label>
          <input type="date" id="nfag-data-inicio">
        </div>
        <div>
          <label>Até</label>
          <input type="date" id="nfag-data-fim">
        </div>
        <button class="btn-accent" onclick="carregarDashboardNfag()">Aplicar</button>
      </div>

      <div class="grade-kpis-nfag-dc">
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-integradas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Integradas</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-ultima-hora">-</div><div class="rotulo-kpi-nfag-dc">Qtd Última Hora</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-autorizadas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Autorizadas</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-rejeitadas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Rejeitadas</div></div>
      </div>

      <div class="erro-mu" id="nfag-erro-dc"></div>

      <div class="painel-dc">
        <h3>Notas por Status</h3>
        <div class="container-grafico-nfag-dc" id="container-grafico-status-dc">
          <canvas id="grafico-status-nfag-dc"></canvas>
        </div>
      </div>

      <div class="painel-dc">
        <h3>Integrada x Autorizada por Hora</h3>
        <div class="container-grafico-nfag-dc" id="container-grafico-hora-dc">
          <canvas id="grafico-hora-nfag-dc"></canvas>
        </div>
      </div>
    </div>

    <!-- Painel genérico pra relatórios Power BI que já existem prontos e só
         precisam ser incorporados (iframe) - o navegador cuida da
         autenticação com a conta Microsoft/Power BI de quem estiver
         logado, igual abrir o link direto. -->
    <div class="painel-dc" id="painel-iframe-dc" style="display:none; max-width:var(--largura-pagina); margin:0 auto 20px auto">
      <div class="aviso-beta-dc" style="margin-bottom:16px">
        Relatório do Power BI incorporado direto - <b>precisa estar logado com uma conta Microsoft que tenha
        acesso a esse relatório</b> (mesma conta usada no navegador pra abrir o Power BI normalmente).
      </div>
      <iframe id="iframe-powerbi-dc" width="100%" height="620" frameborder="0" allowfullscreen="true"
              style="border-radius: 10px; background: #0b0f14;"></iframe>
    </div>

    <div class="painel-dc" id="painel-placeholder-dc" style="display:none">
      <div class="placeholder-dc">
        <div class="icone-placeholder-dc">🚧</div>
        <div class="titulo-placeholder-dc" id="placeholder-titulo-dc"></div>
        <div>Esse dashboard ainda está em construção - em breve vamos trabalhar nisso.</div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
let clientesDC = {};
let clienteSelecionadoDC = null;

async function carregarClientesDC() {
  try {
    const resp = await fetch('/api/dashboards-clientes');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">' + (dados.erro || 'Erro ao carregar.') + '</div>';
      return;
    }
    clientesDC = dados.clientes;
    const nomes = Object.keys(clientesDC).sort();
    if (nomes.length === 0) {
      document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">Nenhum cliente cadastrado ainda.</div>';
      return;
    }
    document.getElementById('grade-clientes-dc').innerHTML = nomes.map(nome => `
      <div class="pill-dc" data-cliente="${nome}" onclick="selecionarClienteDC('${nome}')">${nome}</div>
    `).join('');
  } catch (e) {
    document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">Erro ao carregar: ' + e + '</div>';
  }
}

function selecionarClienteDC(nome) {
  clienteSelecionadoDC = nome;
  document.querySelectorAll('#grade-clientes-dc .pill-dc').forEach(p => p.classList.toggle('ativa', p.dataset.cliente === nome));

  document.getElementById('trilha-dc').innerHTML = `<span class="atual">${nome}</span><span>·</span><span>Selecione um produto</span>`;
  document.getElementById('painel-placeholder-dc').style.display = 'none';

  const produtos = clientesDC[nome] || [];
  document.getElementById('painel-produtos-dc').style.display = 'block';
  document.getElementById('grade-produtos-dc').innerHTML = produtos.map(produto => `
    <div class="pill-dc" data-produto="${produto}" onclick="selecionarProdutoDC('${produto}')">${produto}</div>
  `).join('');
}

// Relatórios Power BI já prontos, só incorporados via iframe - "Cliente|Produto" -> URL de embed
const IFRAMES_DASHBOARDS_DC = {
  'ClienteH|Mapa Instabilidade': 'https://app.powerbi.com/reportEmbed?reportId=00000000-0000-4000-8000-842524532847&autoAuth=true&ctid=00000000-0000-4000-8000-038484718165',
};

function selecionarProdutoDC(produto) {
  document.querySelectorAll('#grade-produtos-dc .pill-dc').forEach(p => p.classList.toggle('ativa', p.dataset.produto === produto));
  document.getElementById('trilha-dc').innerHTML = `<span class="atual">${clienteSelecionadoDC}</span><span>·</span><span class="atual">${produto}</span>`;

  // ClienteB > NFAg já tem dashboard de verdade (transcrito do Power BI) -
  // qualquer outra combinação cliente/produto ainda cai no placeholder.
  if (clienteSelecionadoDC === 'ClienteB' && produto === 'NFAg') {
    document.getElementById('painel-iframe-dc').style.display = 'none';
    document.getElementById('painel-placeholder-dc').style.display = 'none';
    document.getElementById('painel-dashboard-nfag-dc').style.display = 'block';
    document.getElementById('painel-dashboard-nfag-dc').scrollIntoView({ behavior: 'smooth', block: 'start' });
    carregarDashboardNfag();
    return;
  }

  // Relatório Power BI já pronto, incorporado direto via iframe
  const chaveIframe = clienteSelecionadoDC + '|' + produto;
  if (IFRAMES_DASHBOARDS_DC[chaveIframe]) {
    document.getElementById('painel-dashboard-nfag-dc').style.display = 'none';
    document.getElementById('painel-placeholder-dc').style.display = 'none';
    document.getElementById('iframe-powerbi-dc').src = IFRAMES_DASHBOARDS_DC[chaveIframe];
    document.getElementById('painel-iframe-dc').style.display = 'block';
    document.getElementById('painel-iframe-dc').scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  document.getElementById('painel-dashboard-nfag-dc').style.display = 'none';
  document.getElementById('painel-iframe-dc').style.display = 'none';
  document.getElementById('painel-placeholder-dc').style.display = 'block';
  document.getElementById('placeholder-titulo-dc').innerText = `${clienteSelecionadoDC} · ${produto}`;
  document.getElementById('painel-placeholder-dc').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// -- Dashboard ClienteB > NFAg - transcrito do Power BI (Indicadores_NFAg
// _ClienteB.pbix) em 08/09/2026: mesma query nativa, mesmas medidas DAX
// (Status Descricao, Qtd Integradas/Última Hora/Autorizadas/Rejeitadas),
// calculadas em Python no backend (ver _consultar_dashboard_cliente_b_nfag).
let graficoStatusNfagDC = null;
let graficoHoraNfagDC = null;

async function carregarDashboardNfag() {
  const dataInicio = document.getElementById('nfag-data-inicio').value;
  const dataFim = document.getElementById('nfag-data-fim').value;
  const erroEl = document.getElementById('nfag-erro-dc');
  erroEl.innerText = '';

  let url = '/api/dashboards-clientes/cliente_b/nfag';
  const parametros = [];
  if (dataInicio) parametros.push('data_inicio=' + encodeURIComponent(dataInicio));
  if (dataFim) parametros.push('data_fim=' + encodeURIComponent(dataFim));
  if (parametros.length) url += '?' + parametros.join('&');

  try {
    const resp = await fetch(url);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar o dashboard.';
      mostrarErroNosGraficosNfagDC(dados.erro || 'Não foi possível carregar.');
      return;
    }
    renderizarDashboardNfagDC(dados);
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
    mostrarErroNosGraficosNfagDC('Erro ao carregar.');
  }
}

function mostrarErroNosGraficosNfagDC(mensagem) {
  // Em vez de deixar os dois gráficos como caixas grandes vazias quando
  // não tem dado nenhum (ex.: banco fora do ar), mostra um aviso
  // compacto no lugar - mesma altura do container (220px), só que com
  // uma mensagem centralizada em vez de nada.
  const html = `<div class="vazio-grafico-nfag-dc">⚠️ ${mensagem}</div>`;
  document.getElementById('container-grafico-status-dc').innerHTML = html;
  document.getElementById('container-grafico-hora-dc').innerHTML = html;
}

function restaurarCanvasGraficosNfagDC() {
  document.getElementById('container-grafico-status-dc').innerHTML = '<canvas id="grafico-status-nfag-dc"></canvas>';
  document.getElementById('container-grafico-hora-dc').innerHTML = '<canvas id="grafico-hora-nfag-dc"></canvas>';
}

function renderizarDashboardNfagDC(dados) {
  if (graficoStatusNfagDC) { graficoStatusNfagDC.destroy(); graficoStatusNfagDC = null; }
  if (graficoHoraNfagDC) { graficoHoraNfagDC.destroy(); graficoHoraNfagDC = null; }
  restaurarCanvasGraficosNfagDC();
  document.getElementById('kpi-nfag-integradas').innerText = dados.kpis.qtd_integradas;
  document.getElementById('kpi-nfag-ultima-hora').innerText = dados.kpis.qtd_ultima_hora;
  document.getElementById('kpi-nfag-autorizadas').innerText = dados.kpis.qtd_autorizadas;
  document.getElementById('kpi-nfag-rejeitadas').innerText = dados.kpis.qtd_rejeitadas;

  // canvas não entende variável CSS: lê as cores do tema na hora de desenhar
  const estiloRaiz = getComputedStyle(document.documentElement);
  const temaClaro = document.documentElement.getAttribute('data-tema') === 'claro';
  const corTexto = estiloRaiz.getPropertyValue('--fg-dim').trim() || '#8b98a5';
  const corTextoForte = estiloRaiz.getPropertyValue('--fg').trim() || '#e6edf3';
  const corGrade = temaClaro ? 'rgba(16,32,48,.10)' : 'rgba(255,255,255,.08)';

  // "Notas por Status" - barras horizontais, ordenado decrescente (igual
  // ao Formatar visual > Eixo Y > Ordenar por valor do PBIX original)
  const ctxStatus = document.getElementById('grafico-status-nfag-dc').getContext('2d');
  graficoStatusNfagDC = new Chart(ctxStatus, {
    type: 'bar',
    data: {
      labels: dados.por_status.map(s => s.status),
      datasets: [{ label: 'Qtd Integradas', data: dados.por_status.map(s => s.qtd), backgroundColor: '#2db8cf' }],
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: corTexto }, grid: { color: corGrade }, beginAtZero: true },
        y: { ticks: { color: corTextoForte }, grid: { display: false } },
      },
    },
  });

  // "Integrada x Autorizada por Hora" - colunas agrupadas, escala
  // logarítmica no eixo Y (igual ao original)
  const ctxHora = document.getElementById('grafico-hora-nfag-dc').getContext('2d');
  graficoHoraNfagDC = new Chart(ctxHora, {
    type: 'bar',
    data: {
      labels: dados.por_hora.map(h => h.hora),
      datasets: [
        { label: 'Integradas', data: dados.por_hora.map(h => h.integradas), backgroundColor: '#2db8cf' },
        { label: 'Autorizadas', data: dados.por_hora.map(h => h.autorizadas), backgroundColor: '#b0cb1c' },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#e6edf3' } } },
      scales: {
        x: { ticks: { color: corTexto }, grid: { display: false } },
        y: { type: 'logarithmic', ticks: { color: corTexto }, grid: { color: corGrade } },
      },
    },
  });
}

carregarClientesDC();
</script>
</body>
</html>
"""
