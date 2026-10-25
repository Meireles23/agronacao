# servidor_web.py - AgroNação OS (interface fina, tecnológica, verde escuro e cinza suave)
# Não precisa de instalar nada: só Python. Guarde o ficheiro com codificação UTF-8.
# Cada habilidade vive no seu ficheiro: AgroSinal -> modulo_campo.py | PragaAlerta -> modulo_praga.py | AgroGestão -> modulo_gestao.py | FazendaDirecta -> modulo_mercado.py | Central da Agro -> modulo_agro.py | ClimaSeguro -> modulo_clima.py | Score -> modulo_score.py | Rastreabilidade -> modulo_rastreio.py (+ qr_simples.py) | Produtividade -> modulo_produtividade.py | Cooperativa -> modulo_cooperativa.py
import http.server
import socketserver
import webbrowser
import os
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

from modulo_campo import ModuloCampo
from modulo_praga import ModuloPraga
from modulo_gestao import ModuloGestao
from modulo_mercado import ModuloMercado
from modulo_agro import ModuloAgro
from modulo_clima import ModuloClima
from modulo_score import ModuloScore
from modulo_rastreio import ModuloRastreio
from modulo_produtividade import ModuloProdutividade
from modulo_cooperativa import ModuloCooperativa

PORTA = int(os.environ.get("PORT", 8080))
DIRETORIO = os.path.dirname(os.path.abspath(__file__))

CAMPO = ModuloCampo()
PRAGA = ModuloPraga({p["id"]: p["cultura"] for p in CAMPO.dados()["parcelas"]})
GESTAO = ModuloGestao([p["id"] for p in CAMPO.dados()["parcelas"]])
MERCADO = ModuloMercado()
CLIMA = ModuloClima(CAMPO)
SCORE = ModuloScore(CAMPO, PRAGA, GESTAO, CLIMA)
RASTREIO = ModuloRastreio(CAMPO, PRAGA, CLIMA, SCORE)
PRODUTIV = ModuloProdutividade(CAMPO, PRAGA, CLIMA, RASTREIO, MERCADO)
AGRO = ModuloAgro(CAMPO, PRAGA, GESTAO, MERCADO)
AGRO.clima = CLIMA
AGRO.produtividade = PRODUTIV
COOP = ModuloCooperativa(CAMPO, PRODUTIV, AGRO, SCORE, MERCADO)
CLIMA.avisar = lambda nivel, texto: AGRO.notificar_externo(nivel, texto, "ClimaSeguro")
TRAVA = threading.Lock()

HTML_CONTEUDO = r"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgroNação</title>
<style>
:root{
  --bg:#0a1110; --bg2:#0e1816;
  --pn:rgba(22,38,34,.55); --pn2:rgba(30,50,45,.38);
  --bd:rgba(150,200,180,.13); --bd2:rgba(150,200,180,.26);
  --tx:#dbe7e2; --mu:#86a095; --ac:#4fb08a; --ac2:#3d8f9a;
}
*{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif;font-weight:400}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--tx)}
body::before{content:"";position:fixed;inset:0;z-index:0;
  background:radial-gradient(60% 50% at 18% 12%,rgba(79,176,138,.16),transparent 70%),
             radial-gradient(50% 45% at 88% 85%,rgba(61,143,154,.13),transparent 70%),
             radial-gradient(40% 40% at 60% 40%,rgba(120,150,140,.06),transparent 70%)}
.app{position:relative;z-index:1;display:flex;height:100vh}

/* Menu lateral */
.side{width:244px;flex:none;display:flex;flex-direction:column;padding:18px 14px;
  background:var(--pn);backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);border-right:1px solid var(--bd)}
.brand{display:flex;align-items:center;gap:11px;padding:4px 8px 18px;font-size:1.02rem;letter-spacing:.2px}
.orb{width:26px;height:26px;border-radius:50%;flex:none;
  background:radial-gradient(circle at 32% 28%,#c9f5e1,var(--ac) 45%,#1d5a4a 100%);
  box-shadow:0 0 16px rgba(79,176,138,.55)}
.orb.sm{width:22px;height:22px;box-shadow:0 0 10px rgba(79,176,138,.45)}
.nav{display:flex;flex-direction:column;gap:2px}
.nav button,.conv button,.foot button{display:flex;align-items:center;gap:11px;width:100%;text-align:left;
  background:none;border:1px solid transparent;color:var(--tx);padding:9px 10px;border-radius:10px;
  font-size:.88rem;cursor:pointer;transition:background .2s,border-color .2s}
.nav button:hover,.conv button:hover,.foot button:hover{background:var(--pn2)}
.nav button.on{background:rgba(79,176,138,.13);border-color:var(--bd2)}
.nav svg{width:17px;height:17px;flex:none;stroke:var(--ac);fill:none;stroke-width:1.3;stroke-linecap:round;stroke-linejoin:round}
.sep{height:1px;background:var(--bd);margin:14px 6px}
.conv{flex:1;overflow:auto;display:flex;flex-direction:column;gap:2px}
.conv button{color:var(--mu);font-size:.84rem}
.conv button.on{background:var(--pn2);color:var(--tx);border-color:var(--bd)}
.conv .new{color:var(--tx)}
.foot{border-top:1px solid var(--bd);padding-top:10px;margin-top:10px}
.foot button{color:var(--mu)}

/* Zona principal */
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.tip{padding:13px 26px;font-size:.84rem;color:var(--mu);border-bottom:1px solid var(--bd);
  background:rgba(10,17,16,.35);backdrop-filter:blur(12px)}
.tip b{color:var(--ac);margin-right:8px}
.stage{flex:1;min-height:0;display:flex}

/* Área de trabalho da habilidade */
#work{display:none;flex:1;overflow:auto;padding:28px 32px}
[data-mode=skill] #work{display:block}
.wh{display:flex;align-items:baseline;justify-content:space-between;gap:14px;margin-bottom:22px;
  padding-bottom:14px;border-bottom:1px solid var(--bd)}
.wh h2{font-size:1.3rem;letter-spacing:.2px}
.wh span{font-size:.82rem;color:var(--ac);display:flex;align-items:center;gap:7px}
.wh span::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--ac);box-shadow:0 0 8px var(--ac)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{background:var(--pn);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border:1px solid var(--bd);border-radius:16px;padding:18px 20px}
.card.wide{grid-column:1/-1}
.card h3{font-size:.95rem;margin-bottom:10px}
.card p,.card li{font-size:.86rem;color:var(--mu);line-height:1.6}
.card ul{list-style:none}
.row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:7px 0;
  font-size:.86rem;border-bottom:1px solid var(--bd)}
.row:last-child{border-bottom:none}
.row em{font-style:normal;color:var(--mu)}
.bar{height:3px;border-radius:3px;background:rgba(150,200,180,.15);margin-top:6px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:3px;background:linear-gradient(90deg,var(--ac2),var(--ac));transition:width .6s}
.bar i.warn{background:linear-gradient(90deg,#b8893a,#e0b25a)}
.bar i.azul{background:linear-gradient(90deg,#3d6f9a,#5aa0d8)}
.tag{font-size:.75rem;padding:2px 10px;border-radius:20px;border:1px solid var(--bd2);color:var(--ac);white-space:nowrap}
.tag.warn{color:#e0b25a;border-color:rgba(224,178,90,.4)}
.tag.azul{color:#5aa0d8;border-color:rgba(90,160,216,.4)}
.btn{background:rgba(79,176,138,.15);border:1px solid var(--bd2);color:var(--tx);padding:7px 14px;
  border-radius:20px;font-size:.82rem;cursor:pointer;margin:10px 8px 0 0;transition:background .2s}
.btn:hover{background:rgba(79,176,138,.3)}
.btn.stop{background:rgba(90,160,216,.15);border-color:rgba(90,160,216,.4)}
svg.map{width:100%;height:auto;display:block;border-radius:12px;background:rgba(8,16,14,.5);border:1px solid var(--bd)}
@keyframes pulso{0%{r:3;opacity:.9}100%{r:11;opacity:0}}
.pulso{animation:pulso 2.4s ease-out infinite;fill:none;stroke:var(--ac);stroke-width:1}
.ph{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
.ph h3{margin:0}
.num{font-size:1.7rem;letter-spacing:.3px;margin:4px 0 2px}
.num small{font-size:.82rem;color:var(--mu);margin-left:8px}
.spark{color:var(--ac);margin-top:10px;display:block}
.log li{display:flex;gap:12px;padding:4px 0}
.log li b{color:var(--ac);font-weight:400;flex:none}
.hora{font-size:.78rem;color:var(--mu);margin-top:12px}

.sel{background:rgba(14,26,23,.7);border:1px solid var(--bd2);color:var(--tx);border-radius:10px;padding:7px 12px;font-size:.85rem;outline:none;cursor:pointer}
.sel option{background:#0e1816;color:#dbe7e2}
.chk{display:flex;gap:10px;align-items:flex-start;padding:6px 0;font-size:.86rem;cursor:pointer}
.chk input{accent-color:var(--ac);margin-top:3px}
.res{border:1px solid var(--bd);border-radius:12px;padding:14px 16px;margin-top:12px;background:rgba(10,20,17,.35)}
.res ul{margin:8px 0 0 18px}
.res .ph{margin-bottom:4px}
.aviso{font-size:.84rem;color:var(--ac);margin:8px 0}
.reg{padding:10px 0;border-bottom:1px solid var(--bd)}
.reg:last-child{border-bottom:none}
.reg .ph{margin-bottom:2px}
.reg small{color:var(--mu);font-size:.78rem}

.esc{display:grid;grid-template-columns:110px 1fr 1fr;gap:12px;padding:8px 0;border-bottom:1px solid var(--bd);font-size:.84rem}
.esc.h{color:var(--mu);font-size:.78rem}
.esc.d span:first-child{color:var(--mu)}
.esc .desc{grid-column:2/4;color:var(--mu)}
.form{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.form .sel{width:140px}
.btn.sm{padding:4px 12px;font-size:.78rem;margin:8px 6px 0 0}

textarea.sel{width:100%;min-height:74px;resize:vertical;font-family:inherit;cursor:text}
.nota{font-size:.78rem;color:var(--mu);line-height:1.5;margin-top:10px}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--pn);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid var(--bd);border-radius:14px;padding:14px 16px}
.kpi small{display:block;color:var(--mu);font-size:.76rem;margin-bottom:4px}
.kpi b{font-size:1.45rem;font-weight:400;letter-spacing:.2px}
.kpi span{display:block;font-size:.74rem;color:var(--mu);margin-top:4px}
.cnt{margin-left:auto;background:#e0b25a;color:#241a05;font-size:.7rem;border-radius:20px;padding:1px 8px}
.cnt:empty{display:none}
.tag.alta{color:#e07a6a;border-color:rgba(224,122,106,.45)}
a.btn{text-decoration:none;display:inline-block}

/* Chat (centro no modo conversa, painel à direita no modo habilidade) */
#chat{flex:1;min-width:0;display:flex;flex-direction:column}
.chead{display:none;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--bd);font-size:.9rem}
.chead div{display:flex;align-items:center;gap:10px}
.mini{background:var(--pn2);border:1px solid var(--bd2);color:var(--ac);width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:.9rem}
.mini:hover{background:rgba(79,176,138,.25)}
[data-mode=skill] #chat{flex:none;width:350px;border-left:1px solid var(--bd);background:rgba(12,22,20,.45);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px)}
[data-mode=skill] .chead{display:flex}
#chat.min{display:none}
#msgs{flex:1;overflow:auto;padding:28px 20px 10px}
.col{width:100%;max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:22px}
[data-mode=skill] .col{max-width:none;gap:16px}
#msgs::-webkit-scrollbar,#work::-webkit-scrollbar,.conv::-webkit-scrollbar{width:4px}
#msgs::-webkit-scrollbar-thumb,#work::-webkit-scrollbar-thumb,.conv::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:4px}
.m{display:flex;gap:14px;font-size:.95rem;line-height:1.6}
.m.agro .t{flex:1}
.m.user{justify-content:flex-end}
.m.user .t{background:var(--pn2);border:1px solid var(--bd);padding:9px 18px;border-radius:20px;max-width:78%}
[data-mode=skill] .m{font-size:.86rem}
.chips{display:flex;flex-wrap:wrap;gap:7px;padding:6px 20px}
.chips .in{width:100%;max-width:760px;margin:0 auto;display:flex;flex-wrap:wrap;gap:7px}
[data-mode=skill] .chips .in{max-width:none}
.chip{background:var(--pn2);border:1px solid var(--bd);color:var(--mu);padding:5px 13px;border-radius:20px;
  font-size:.78rem;cursor:pointer;transition:all .2s}
.chip:hover{color:var(--tx);border-color:var(--bd2);background:rgba(79,176,138,.15)}
.bar-in{padding:8px 20px 22px}
.pill{width:100%;max-width:760px;margin:0 auto;display:flex;align-items:center;gap:8px;
  background:rgba(14,26,23,.7);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border:1px solid var(--bd2);border-radius:999px;padding:7px 8px 7px 20px}
[data-mode=skill] .pill{max-width:none}
.pill input{flex:1;background:none;border:none;outline:none;color:var(--tx);font-size:.92rem;padding:7px 0}
.pill input::placeholder{color:#5f7a6f}
.send{width:36px;height:36px;border-radius:50%;border:none;cursor:pointer;flex:none;
  background:linear-gradient(135deg,var(--ac),var(--ac2));display:flex;align-items:center;justify-content:center}
.send svg{width:16px;height:16px;fill:#06130f}
#fab{display:none;position:fixed;right:24px;bottom:24px;z-index:20;width:50px;height:50px;border-radius:50%;
  cursor:pointer;border:1px solid var(--bd2);background:var(--pn);backdrop-filter:blur(14px);
  align-items:center;justify-content:center}
[data-mode=skill] #fab.show{display:flex}
@media(max-width:900px){.side{width:64px}.side .lb,.brand .lb{display:none}[data-mode=skill] #chat{width:300px}}
</style>
</head>
<body>
<div class="app" id="app" data-mode="chat">

  <aside class="side">
    <div class="brand"><div class="orb"></div><span class="lb">AgroNação</span></div>
    <nav class="nav" id="nav">
      <button data-v="chat" class="on"><svg viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z"/></svg><span class="lb">Conversar com a Agro</span></button>
      <button data-v="agro"><svg viewBox="0 0 24 24"><path d="M3 13h4l2-6 4 12 2-6h6"/></svg><span class="lb">Central da Agro</span><span class="cnt" id="cnt"></span></button>
      <button data-v="campo"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/></svg><span class="lb">AgroSinal · Campo</span></button>
      <button data-v="praga"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg><span class="lb">PragaAlerta</span></button>
      <button data-v="gestao"><svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/></svg><span class="lb">AgroGestão</span></button>
      <button data-v="mercado"><svg viewBox="0 0 24 24"><path d="M4 18l5-6 4 3 7-9"/><path d="M15 6h5v5"/></svg><span class="lb">FazendaDirecta</span></button>
      <button data-v="clima"><svg viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/></svg><span class="lb">ClimaSeguro</span></button>
      <button data-v="score"><svg viewBox="0 0 24 24"><path d="M4 16a8 8 0 0 1 16 0"/><path d="M12 16l4-5"/></svg><span class="lb">Score AgroNação</span></button>
      <button data-v="rastreio"><svg viewBox="0 0 24 24"><rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><path d="M14 14h3v3h-3zM19 17v3h-3"/></svg><span class="lb">Rastreabilidade</span></button>
      <button data-v="produtiv"><svg viewBox="0 0 24 24"><path d="M4 18l5-5 4 3 7-9"/><path d="M4 20h16"/></svg><span class="lb">Previsão de colheita</span></button>
      <button data-v="coop"><svg viewBox="0 0 24 24"><circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M2 20c0-3.5 2.7-6 6-6s6 2.5 6 6M12 20c0-3 1.8-5 4-5s6 2 6 5"/></svg><span class="lb">Cooperativa</span></button>
    </nav>
    <div class="sep"></div>
    <div class="conv" id="conv">
      <button class="new" id="novaConv"><span>+</span><span class="lb">Nova conversa</span></button>
    </div>
    <div class="foot"><button id="pers"><span>◐</span><span class="lb">Personalizar</span></button></div>
  </aside>

  <section class="main">
    <div class="tip"><b>Dica</b>Peça à Agro: “resumo da exploração”, “ver sensor parcela 2”, “liga a rega da parcela 2” ou “melhor comprador”.</div>
    <div class="stage">
      <div id="work"></div>

      <div id="chat">
        <div class="chead"><div><span class="orb sm"></span>Agro</div><button class="mini" id="btnMin" title="Minimizar">–</button></div>
        <div id="msgs"><div class="col" id="col"></div></div>
        <div class="chips"><div class="in">
          <span class="chip" data-q="Estado da exploração">Estado da exploração</span>
          <span class="chip" data-q="Verificar pragas">Pragas</span>
          <span class="chip" data-q="Custos de fertilizantes">Custos</span>
          <span class="chip" data-q="Melhor comprador">Mercado</span>
          <span class="chip" data-q="Criar escala de trabalho">Escala</span>
        </div></div>
        <div class="bar-in"><div class="pill">
          <input id="inp" type="text" placeholder="Escreva para a Agro..." autocomplete="off">
          <button class="send" id="enviar" title="Enviar"><svg viewBox="0 0 24 24"><path d="M3 11.5L21 3l-6.5 18-3-7.5z"/></svg></button>
        </div></div>
      </div>
    </div>
  </section>
</div>
<button id="fab" title="Abrir a Agro"><span class="orb"></span></button>

<script>
const $ = s => document.querySelector(s);
const app = $('#app'), col = $('#col'), work = $('#work'), chat = $('#chat'), fab = $('#fab');
const ORB = '<span class="orb sm"></span>';
const SAUDACAO = 'Olá! Sou a Agro, a gestora da tua exploração. Posso resumir o estado do campo, avisar de pragas, organizar equipas e stocks e encontrar compradores. Escolhe uma habilidade no menu ou escreve aqui.';
let vista = 'chat', timerCampo = null;

/* ---------- AgroSinal: dados em direto do servidor ---------- */
const ldCampo = () => fetch('/api/campo').then(r => r.json());

function tagEstado(e){
  if(e === 'ideal') return '<span class="tag">Ideal</span>';
  if(e === 'regar') return '<span class="tag warn">Precisa de rega</span>';
  return '<span class="tag azul">Excesso</span>';
}
function corEstado(e){ return e === 'ideal' ? '#4fb08a' : e === 'regar' ? '#e0b25a' : '#5aa0d8'; }
function classeBarra(e){ return e === 'ideal' ? '' : e === 'regar' ? 'warn' : 'azul'; }

function spark(h){
  const w = 150, ht = 30;
  let lo = Math.min(...h), hi = Math.max(...h);
  if(hi - lo < 4){ hi = lo + 4; }
  const pts = h.map((v, i) => {
    const x = h.length > 1 ? i * (w / (h.length - 1)) : w;
    const y = ht - ((v - lo) / (hi - lo)) * (ht - 2) - 1;
    return x.toFixed(1) + ',' + y.toFixed(1);
  }).join(' ');
  return '<svg class="spark" width="' + w + '" height="' + ht + '" viewBox="0 0 ' + w + ' ' + ht + '"><polyline points="' + pts + '" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>';
}

function mapaCampo(d){
  const xs = [30, 215, 400];
  const pos = [[60,105],[140,150]];
  let s = '<svg class="map" viewBox="0 0 600 220">';
  d.parcelas.forEach((p, i) => {
    const x = xs[i], c = corEstado(p.estado);
    s += '<rect x="' + x + '" y="30" width="170" height="160" rx="6" fill="' + c + '" fill-opacity=".10" stroke="' + c + '" stroke-opacity=".55" stroke-width="1"' + (p.irrigando ? ' stroke-dasharray="4 4"' : '') + '/>';
    s += '<text x="' + (x + 12) + '" y="52" fill="#9bb8ac" font-size="12">Parcela ' + p.id + ' · ' + p.cultura + '</text>';
    s += '<text x="' + (x + 12) + '" y="178" fill="' + c + '" font-size="13">' + p.humidade.toFixed(0) + '%' + (p.irrigando ? ' · a regar' : '') + '</text>';
    pos.forEach(q => { s += '<circle cx="' + (x + q[0]) + '" cy="' + q[1] + '" r="3" fill="' + c + '"/>'; });
    s += '<circle class="pulso" cx="' + (x + pos[0][0]) + '" cy="' + pos[0][1] + '" r="3" style="stroke:' + c + '"/>';
  });
  return s + '</svg>';
}

function renderCampo(d){
  const alvo = $('#campoBody'); if(!alvo) return;
  let h = '<div class="grid"><div class="card wide"><h3>Mapa das parcelas</h3>' + mapaCampo(d) + '</div>';
  d.parcelas.forEach(p => {
    h += '<div class="card"><div class="ph"><h3>Parcela ' + p.id + ' · ' + p.cultura + '</h3>' + tagEstado(p.estado) + '</div>' +
         '<div class="num">' + p.humidade.toFixed(0) + '%<small>humidade · ' + p.temperatura.toFixed(0) + ' °C · ' + p.area_ha + ' ha</small></div>' +
         '<div class="bar"><i class="' + classeBarra(p.estado) + '" style="width:' + p.humidade + '%"></i></div>' + spark(p.historico) +
         '<button class="btn ' + (p.irrigando ? 'stop' : '') + '" data-irr="' + p.id + '" data-lig="' + (p.irrigando ? '0' : '1') + '">' + (p.irrigando ? 'Parar rega' : 'Ligar rega') + '</button></div>';
  });
  h += '<div class="card"><h3>Clima</h3>' +
       '<div class="row"><span>Temperatura média</span><em>' + d.temperatura_media.toFixed(1) + ' °C</em></div>' +
       '<div class="row"><span>Humidade média do solo</span><em>' + d.humidade_media.toFixed(0) + '%</em></div>' +
       '<div class="row"><span>Previsão</span><em>' + d.previsao + '</em></div>' +
       '<div class="row"><span>Sensores ligados</span><em>' + d.sensores_ativos + ' de ' + d.sensores_ativos + '</em></div></div>';
  h += '<div class="card"><h3>Alertas</h3><ul>';
  h += d.alertas.length ? d.alertas.map(a => '<li>' + (a.nivel === 'aviso' ? '⚠ ' : '• ') + a.texto + '</li>').join('') : '<li>Sem alertas. Tudo dentro do normal.</li>';
  h += '</ul></div>';
  h += '<div class="card"><h3>Registo da Agro</h3><ul class="log">';
  h += d.eventos.length ? d.eventos.map(e => '<li><b>' + e.hora + '</b><span>' + e.texto + '</span></li>').join('') : '<li>Ainda sem ações registadas.</li>';
  h += '</ul></div></div><div class="hora">Atualizado às ' + d.hora + ' · valores simulados até ligar sensores reais</div>';
  alvo.innerHTML = h;
}

function carregarCampo(){
  ldCampo().then(renderCampo).catch(() => {
    const a = $('#campoBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function irrigar(parcela, ligar){
  return fetch('/api/campo/irrigar', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({parcela: parcela, ligar: ligar})}).then(r => r.json())
    .then(r => { if(vista === 'campo') carregarCampo(); return r; });
}

/* ---------- PragaAlerta: registo e diagnóstico guiado ---------- */
let PR = null, prParcela = '1', prSint = new Set(), prRes = null, prMsg = '';
const ldPraga = () => fetch('/api/praga').then(r => r.json());
const postPraga = (rota, corpo) => fetch('/api/praga/' + rota, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
const NIVEL = {baixo:'Baixo', medio:'Médio', alto:'Alto'};
function tagNivel(n){ return '<span class="tag' + (n === 'baixo' ? '' : ' warn') + '">' + NIVEL[n] + '</span>'; }

function renderPraga(){
  const alvo = $('#pragaBody'); if(!alvo || !PR) return;
  const cult = (PR.parcelas.find(p => p.id === prParcela) || {}).cultura;
  const sint = PR.sintomas[cult] || [];
  const R = PR.resumo;
  let h = '<div class="grid">';
  h += '<div class="card"><h3>Resumo</h3>' +
       '<div class="row"><span>Ocorrências ativas</span><em>' + R.ativos + '</em></div>' +
       '<div class="row"><span>Parcelas afetadas</span><em>' + R.parcelas_afetadas + ' de ' + PR.parcelas.length + '</em></div>' +
       '<div class="row"><span>Já tratadas</span><em>' + R.tratados + '</em></div></div>';
  h += '<div class="card"><h3>Ocorrências registadas</h3>';
  h += PR.registos.length ? PR.registos.map(r =>
    '<div class="reg"><div class="ph"><span>Parcela ' + r.parcela + ' · ' + r.cultura + ' · ' + esc(r.praga) + '</span>' +
    (r.estado === 'ativo' ? tagNivel(r.nivel) : '<span class="tag">Tratada</span>') + '</div>' +
    '<small>' + r.data + (r.notas ? ' · ' + esc(r.notas) : '') + '</small>' +
    (r.estado === 'ativo' ? '<div><button class="btn" data-trat="' + r.id + '">Marcar como tratada</button></div>' : '') + '</div>').join('')
    : '<p>Sem ocorrências. As parcelas estão limpas.</p>';
  h += '</div>';
  h += '<div class="card wide"><h3>Diagnóstico guiado</h3><p>Escolhe a parcela e marca o que estás a ver nas plantas. A Agro indica as pragas ou doenças mais prováveis e o que fazer.</p>';
  h += '<div style="margin:12px 0"><select class="sel" id="prParcela">' +
       PR.parcelas.map(p => '<option value="' + p.id + '"' + (p.id === prParcela ? ' selected' : '') + '>Parcela ' + p.id + ' · ' + p.cultura + '</option>').join('') + '</select></div>';
  h += sint.map(s => '<label class="chk"><input type="checkbox" data-sint="' + s.id + '"' + (prSint.has(s.id) ? ' checked' : '') + '><span>' + s.texto + '</span></label>').join('');
  h += '<button class="btn" data-diag="1">Diagnosticar</button>';
  if(prMsg) h += '<p class="aviso">' + esc(prMsg) + '</p>';
  if(prRes){
    h += prRes.length ? prRes.map((x, i) =>
      '<div class="res"><div class="ph"><h3>' + x.nome + '</h3><span class="tag">' + x.confianca + '% de correspondência</span></div>' +
      '<div class="bar"><i style="width:' + x.confianca + '%"></i></div>' +
      '<p style="margin-top:8px">' + x.descricao + '</p><ul>' + x.acoes.map(a => '<li>' + a + '</li>').join('') + '</ul>' +
      '<div style="margin-top:10px"><select class="sel" id="nv' + i + '"><option value="baixo">Nível baixo</option><option value="medio">Nível médio</option><option value="alto">Nível alto</option></select> ' +
      '<button class="btn" data-reg="' + i + '">Registar ocorrência</button></div></div>').join('')
      : '<p class="aviso">Os sintomas escolhidos não correspondem a nenhuma praga conhecida desta cultura.</p>';
    h += '<p class="hora">Resultado indicativo. Confirma com um técnico agrário antes de aplicar qualquer produto.</p>';
  }
  h += '</div></div>';
  alvo.innerHTML = h;
}
function carregarPraga(){
  ldPraga().then(d => { PR = d; renderPraga(); }).catch(() => {
    const a = $('#pragaBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}

/* ---------- AgroGestão: equipa, escala, stocks e finanças ---------- */
let GE = null, gMsg = '';
const ldGestao = () => fetch('/api/gestao').then(r => r.json());
const postG = (acao, corpo) => fetch('/api/gestao/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
const kz = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' Kz';

function renderGestao(){
  const alvo = $('#gestaoBody'); if(!alvo || !GE) return;
  const F = GE.financas;
  let h = gMsg ? '<p class="aviso">' + esc(gMsg) + '</p>' : '';
  h += '<div class="grid">';
  h += '<div class="card wide"><h3>Escala dos próximos 15 dias</h3><div class="esc h"><span>Dia</span><span>Equipa A</span><span>Equipa B</span></div>' +
       GE.escala.map(e => e.descanso
         ? '<div class="esc d"><span>' + e.dia + ' ' + e.data + '</span><span class="desc">Descanso</span></div>'
         : '<div class="esc d"><span>' + e.dia + ' ' + e.data + '</span><span>' + e.A + '</span><span>' + e.B + '</span></div>').join('') + '</div>';

  h += '<div class="card wide"><h3>Tarefas e custos previstos criados pela Agro</h3>' +
       (GE.tarefas.length ? GE.tarefas.map(t => '<div class="reg"><div class="ph"><span>' + esc(t.texto) + '</span><span class="tag">Equipa ' + t.equipa + '</span></div>' +
         '<small>' + t.data + ' · criada pela ' + esc(t.origem) + '</small><div><button class="btn sm" data-tc="' + t.id + '">Concluir</button></div></div>').join('') : '<p>Sem tarefas pendentes criadas pela Agro.</p>') +
       (GE.previstos.length ? GE.previstos.map(v => '<div class="reg"><div class="ph"><span>' + esc(v.descricao) + '</span><span class="tag warn">' + kz(v.valor) + ' previsto</span></div>' +
         '<small>' + v.data + ' · registado pela ' + esc(v.origem) + '</small><div><button class="btn sm" data-pc="' + v.id + '">Confirmar custo</button><button class="btn sm" data-px="' + v.id + '">Cancelar</button></div></div>').join('') : '') + '</div>';
  h += '<div class="card"><h3>Equipa e presenças</h3>';
  h += GE.funcionarios.length ? GE.funcionarios.map(f =>
    '<div class="reg"><div class="ph"><span>' + esc(f.nome) + ' · ' + esc(f.funcao) + '</span><span class="tag">Equipa ' + f.equipa + '</span></div>' +
    '<small>' + kz(f.diaria) + ' por dia · ' + f.dias_mes + ' dia(s) este mês · a pagar ' + kz(f.a_pagar) + '</small>' +
    '<div><button class="btn sm' + (f.presente_hoje ? ' stop' : '') + '" data-pres="' + f.id + '">' + (f.presente_hoje ? 'Presente hoje ✓' : 'Marcar presença hoje') + '</button>' +
    '<button class="btn sm" data-rem="' + f.id + '">Remover</button></div></div>').join('') : '<p>Ainda sem funcionários.</p>';
  h += '<div class="form"><input class="sel" id="gNome" placeholder="Nome"><input class="sel" id="gFuncao" placeholder="Função">' +
       '<select class="sel" id="gEquipa"><option value="A">Equipa A</option><option value="B">Equipa B</option></select>' +
       '<input class="sel" id="gDiaria" placeholder="Diária (Kz)" inputmode="numeric"><button class="btn" style="margin:0" data-addf="1">Adicionar</button></div></div>';

  h += '<div class="card"><h3>Stocks</h3>' + GE.stocks.map(s =>
    '<div class="row"><span>' + esc(s.nome) + '</span><em>' + s.qtd + ' ' + s.unidade + '</em></div>' +
    '<div class="bar"><i class="' + (s.estado === 'repor' ? 'warn' : '') + '" style="width:' + s.nivel + '%"></i></div>' +
    '<div>' + (s.estado === 'repor' ? '<span class="tag warn">Repor (mínimo ' + s.minimo + ' ' + s.unidade + ')</span> ' : '') +
    '<button class="btn sm" data-stk="' + s.id + '" data-d="-' + s.passo + '">− ' + s.passo + '</button>' +
    '<button class="btn sm" data-stk="' + s.id + '" data-d="' + s.passo + '">+ ' + s.passo + '</button></div>').join('') + '</div>';

  h += '<div class="card wide"><h3>Finanças do mês</h3>' +
       '<div class="row"><span>Receitas</span><em>' + kz(F.receitas) + '</em></div>' +
       '<div class="row"><span>Custos registados</span><em>' + kz(F.custos) + '</em></div>' +
       '<div class="row"><span>Mão-de-obra (presenças)</span><em>' + kz(F.mao_obra) + '</em></div>' +
       '<div class="row"><span>Resultado</span><em>' + kz(F.resultado) + (F.roi === null ? '' : ' · retorno ' + (F.roi >= 0 ? '+' : '') + F.roi + '%') + '</em></div>';
  h += '<div class="form"><select class="sel" id="mTipo"><option value="custo">Custo</option><option value="receita">Receita</option></select>' +
       '<input class="sel" id="mDesc" placeholder="Descrição" style="width:220px"><input class="sel" id="mValor" placeholder="Valor (Kz)" inputmode="numeric">' +
       '<button class="btn" style="margin:0" data-addm="1">Registar</button></div>';
  h += '<div style="margin-top:12px">' + F.movimentos.map(m => '<div class="row"><span>' + (m.tipo === 'receita' ? '+ ' : '− ') + esc(m.descricao) + '</span><em>' + kz(m.valor) + '</em></div>').join('') + '</div></div>';
  h += '</div>';
  alvo.innerHTML = h;
}
function carregarGestao(){
  ldGestao().then(d => { GE = d; renderGestao(); }).catch(() => {
    const a = $('#gestaoBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoG(acao, corpo){
  return postG(acao, corpo).then(r => { gMsg = r.mensagem || ''; return ldGestao(); }).then(d => { GE = d; renderGestao(); });
}

/* ---------- FazendaDirecta: preços, compradores e melhor mercado ---------- */
let ME = null, meProd = '', meTipo = 'venda', meRes = null, meMsg = '';
const ldMercado = () => fetch('/api/mercado').then(r => r.json());
const melhorMercado = (produto, tipo) => fetch('/api/mercado/melhor?produto=' + encodeURIComponent(produto) + '&tipo=' + tipo).then(r => r.json());
const postM = (acao, corpo) => fetch('/api/mercado/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
const norm = t => String(t).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();

function optProv(sel){
  return '<option value="">Sem província</option>' + ME.provincias.map(p => '<option' + (p === sel ? ' selected' : '') + '>' + p + '</option>').join('');
}
function tagsDado(x){
  return (x.exemplo ? '<span class="tag warn">Exemplo</span> ' : '') + (x.desatualizado ? '<span class="tag warn">Desatualizado (' + x.idade_dias + ' dias)</span>' : '');
}
function textoMercado(r){
  if(!r.ok || !r.opcoes || !r.opcoes.length) return '<b>FazendaDirecta</b><br>' + (r.mensagem || 'Sem dados para este produto.');
  const m = r.opcoes[0];
  return '<b>FazendaDirecta · ' + esc(r.produto) + '</b><br>Melhor opção: ' + esc(m.nome) + (m.provincia ? ' (' + m.provincia + ')' : '') + ' a ' + kz(m.preco) + '/' + r.unidade +
    (m.transporte ? '<br>Com o transporte estimado: ' + kz(m.liquido) + '/' + r.unidade : '') +
    '<br>Fonte: ' + esc(m.fonte) + ', ' + m.data + (m.desatualizado ? ' (desatualizado)' : '') + (m.exemplo ? ' (exemplo)' : '') + '.';
}

function renderMercado(){
  const alvo = $('#mercadoBody'); if(!alvo || !ME) return;
  const lista = ME.produtos[meTipo];
  let h = meMsg ? '<p class="aviso">' + esc(meMsg) + '</p>' : '';
  h += '<div class="grid">';

  h += '<div class="card wide"><h3>Como funciona</h3><p>Todos os preços têm fonte e data. Podes registá-los à mão ou importar uma lista. Os que têm mais de ' + ME.validade_dias +
       ' dias aparecem como desatualizados. A pesquisa automática em fontes online é uma fase seguinte, e precisa de ligação à internet e de uma fonte de dados.</p>' +
       '<div class="form"><select class="sel" id="mProv">' + ME.provincias.map(p => '<option' + (p === ME.config.provincia ? ' selected' : '') + '>' + p + '</option>').join('') + '</select>' +
       '<input class="sel" id="mTransp" value="' + ME.config.transp + '" inputmode="numeric" title="Kz por kg por cada 100 km">' +
       '<button class="btn" style="margin:0" data-cfg="1">Guardar localização e transporte</button></div>' +
       '<p class="nota">A província da exploração e o custo de transporte (Kz por kg por 100 km) servem para estimar o valor líquido de cada mercado.</p></div>';

  h += '<div class="card wide"><h3>Melhor mercado</h3><div class="form" style="margin-top:0">' +
       '<select class="sel" id="meTipoSel"><option value="venda"' + (meTipo === 'venda' ? ' selected' : '') + '>Vender um produto</option><option value="insumo"' + (meTipo === 'insumo' ? ' selected' : '') + '>Comprar um insumo</option></select>' +
       '<select class="sel" id="meProdSel"><option value="">Escolhe o produto</option>' + lista.map(x => '<option' + (x === meProd ? ' selected' : '') + '>' + esc(x) + '</option>').join('') + '</select></div>';
  if(meRes){
    if(!meRes.ok || !meRes.opcoes.length){ h += '<p class="aviso">' + esc(meRes.mensagem || 'Sem dados.') + '</p>'; }
    else {
      h += meRes.opcoes.map((o, i) =>
        '<div class="res"><div class="ph"><h3>' + (i === 0 ? 'Melhor opção · ' : '') + esc(o.nome) + '</h3><span class="tag">' + kz(o.liquido) + '/' + meRes.unidade + '</span></div>' +
        '<small>' + kz(o.preco) + '/' + meRes.unidade + (o.provincia ? ' · ' + o.provincia : '') + (o.dist_km !== null ? ' · ~' + o.dist_km + ' km · transporte ' + kz(o.transporte) : '') + '</small><br>' +
        '<small>Fonte: ' + esc(o.fonte) + ' · ' + o.data + '</small> ' + tagsDado(o) + '</div>').join('');
      h += '<p class="nota">Média dos preços registados: ' + kz(meRes.media) + '/' + meRes.unidade + '. ' + esc(meRes.nota) + '</p>';
    }
  }
  h += '</div>';

  h += '<div class="card"><h3>Propostas de compradores</h3>' + (ME.propostas.length ? ME.propostas.map(c =>
       '<div class="reg"><div class="ph"><span>' + esc(c.comprador) + ' · ' + esc(c.produto) + '</span><span class="tag">' + kz(c.preco) + '/kg</span></div>' +
       '<small>' + (c.provincia || 'Sem província') + ' · ' + c.data + '</small> ' + tagsDado(c) +
       '<div><button class="btn sm" data-rmc="' + c.id + '">Remover</button></div></div>').join('') : '<p>Sem propostas registadas.</p>');
  h += '<div class="form"><input class="sel" id="cNome" placeholder="Comprador"><input class="sel" id="cProd" placeholder="Produto"><input class="sel" id="cPreco" placeholder="Kz por kg" inputmode="numeric">' +
       '<select class="sel" id="cProv">' + optProv('') + '</select><button class="btn" style="margin:0" data-addc="1">Registar</button></div></div>';

  h += '<div class="card"><h3>Preços registados</h3>' + (ME.precos.length ? ME.precos.slice(0, 8).map(p =>
       '<div class="reg"><div class="ph"><span>' + esc(p.produto) + ' · ' + (p.tipo === 'venda' ? 'venda' : 'insumo') + '</span><span class="tag">' + kz(p.preco) + '/' + esc(p.unidade) + '</span></div>' +
       '<small>' + esc(p.local || 'Mercado') + (p.provincia ? ' · ' + p.provincia : '') + ' · Fonte: ' + esc(p.fonte) + ' · ' + p.data + '</small> ' + tagsDado(p) +
       '<div><button class="btn sm" data-rmp="' + p.id + '">Remover</button></div></div>').join('') : '<p>Sem preços registados.</p>');
  h += '<div class="form"><select class="sel" id="pTipo"><option value="venda">Preço de venda</option><option value="insumo">Preço de insumo</option></select>' +
       '<input class="sel" id="pProd" placeholder="Produto"><input class="sel" id="pPreco" placeholder="Preço (Kz)" inputmode="numeric"><input class="sel" id="pUni" placeholder="Unidade (kg)">' +
       '<input class="sel" id="pLocal" placeholder="Mercado ou local"><select class="sel" id="pProv">' + optProv('') + '</select>' +
       '<input class="sel" id="pFonte" placeholder="Fonte (obrigatória)"><input class="sel" id="pData" placeholder="AAAA-MM-DD (vazio = hoje)">' +
       '<button class="btn" style="margin:0" data-addp="1">Registar preço</button></div>' +
       '<p class="nota" style="margin-top:14px">Importar uma lista (uma linha por preço, com cabeçalho): produto;preco;unidade;local;provincia;fonte;data;tipo</p>' +
       '<textarea class="sel" id="pImp" placeholder="produto;preco;unidade;local;provincia;fonte;data&#10;Milho;310;kg;Mercado X;Huambo;Cooperativa Y;2026-10-20"></textarea>' +
       '<button class="btn" data-imp="1">Importar</button><button class="btn" data-rmex="1">Remover exemplos</button></div>';
  h += '</div>';
  alvo.innerHTML = h;
}

function analisarMercado(){
  if(!meProd){ meRes = null; renderMercado(); return Promise.resolve(); }
  return melhorMercado(meProd, meTipo).then(r => { meRes = r; renderMercado(); });
}
function carregarMercado(){
  ldMercado().then(d => { ME = d; renderMercado(); return analisarMercado(); }).catch(() => {
    const a = $('#mercadoBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoM(acao, corpo){
  return postM(acao, corpo).then(r => { meMsg = r.mensagem || ''; return ldMercado(); }).then(d => { ME = d; return analisarMercado(); });
}
document.addEventListener('click', e => {
  if(vista !== 'mercado') return;
  const t = x => e.target.closest(x);
  if(t('[data-cfg]')) acaoM('config', {provincia: $('#mProv').value, transp: $('#mTransp').value});
  else if(t('[data-addc]')) acaoM('proposta', {comprador: $('#cNome').value, produto: $('#cProd').value, preco: $('#cPreco').value, provincia: $('#cProv').value});
  else if(t('[data-rmc]')) acaoM('remover_proposta', {id: Number(t('[data-rmc]').dataset.rmc)});
  else if(t('[data-addp]')) acaoM('preco', {tipo: $('#pTipo').value, produto: $('#pProd').value, preco: $('#pPreco').value, unidade: $('#pUni').value,
                                              local: $('#pLocal').value, provincia: $('#pProv').value, fonte: $('#pFonte').value, data: $('#pData').value});
  else if(t('[data-rmp]')) acaoM('remover_preco', {id: Number(t('[data-rmp]').dataset.rmp)});
  else if(t('[data-imp]')) acaoM('importar', {texto: $('#pImp').value});
  else if(t('[data-rmex]')){ if(confirm('Remover todos os dados de exemplo?')) acaoM('remover_exemplos', {}); }
});
document.addEventListener('change', e => {
  if(vista !== 'mercado') return;
  if(e.target.id === 'meTipoSel'){ meTipo = e.target.value; meProd = ''; meRes = null; renderMercado(); }
  else if(e.target.id === 'meProdSel'){ meProd = e.target.value; analisarMercado(); }
});

/* ---------- Central da Agro: alertas, rotinas e integração entre módulos ---------- */
let AG = null, agMsg = '', timerAgro = null;
const ldAgro = () => fetch('/api/agro').then(r => r.json());
const postA = (acao, corpo) => fetch('/api/agro/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
const NIV_AL = {alta:'Alta', media:'Média', info:'Info'};
function tagAlerta(n){ return '<span class="tag' + (n === 'alta' ? ' alta' : n === 'media' ? ' warn' : '') + '">' + NIV_AL[n] + '</span>'; }
function kpi(rotulo, valor, nota){ return '<div class="kpi"><small>' + rotulo + '</small><b>' + valor + '</b>' + (nota ? '<span>' + nota + '</span>' : '') + '</div>'; }

function renderAgro(){
  const alvo = $('#agroBody'); if(!alvo || !AG) return;
  const K = AG.kpis, S = AG.saude;
  let h = agMsg ? '<p class="aviso">' + esc(agMsg) + '</p>' : '';
  h += '<div class="kpis">' +
       kpi('Saúde da exploração', S.valor + '/100', S.faixa) +
       kpi('Humidade média do solo', K.humidade_media.toFixed(0) + '%', K.sensores + ' sensores') +
       kpi('Pragas ativas', K.pragas_ativas, '') +
       kpi('Stocks a repor', K.stocks_repor, '') +
       kpi('Resultado do mês', kz(K.resultado), K.roi === null ? '' : 'retorno ' + (K.roi >= 0 ? '+' : '') + K.roi + '%') +
       kpi('Tarefas da Agro', K.tarefas_agro, 'por concluir') + '</div>';
  h += '<div class="grid">';
  h += '<div class="card wide"><h3>Alertas agora</h3>' + (AG.alertas.length ? AG.alertas.map(a =>
       '<div class="reg"><div class="ph"><span>' + esc(a.texto) + '</span>' + tagAlerta(a.nivel) + '</div><small>' + esc(a.modulo) + '</small></div>').join('') : '<p>Sem alertas. Tudo dentro do normal.</p>');
  h += '<p class="nota">Saúde da exploração: começa em 100 e desconta ' + (S.descontos.length ? S.descontos.map(d => d.pontos + ' por ' + d.motivo).join('; ') : 'nada neste momento') +
       '. É um indicador simples, calculado com os dados que registas.</p></div>';
  h += '<div class="card wide"><h3>Rotinas da Agro</h3><p>A Agro vigia de 10 em 10 segundos e age sozinha quando uma rotina ativa encontra uma situação nova.</p>' +
       AG.regras.map(r => '<div class="reg"><div class="ph"><span>' + esc(r.descricao) + '</span><span class="tag' + (r.ativa ? '' : ' warn') + '">' + (r.ativa ? 'Ativa' : 'Em pausa') + '</span></div>' +
       '<div><button class="btn sm" data-ralt="' + r.id + '">' + (r.ativa ? 'Pausar' : 'Ativar') + '</button><button class="btn sm" data-rrem="' + r.id + '">Remover</button></div></div>').join('');
  h += '<div class="form"><select class="sel" id="rTipo"><option value="humidade_baixa">Humidade baixa</option><option value="stock_baixo">Stock baixo</option>' +
       '<option value="praga_ativa">Praga ativa</option><option value="preco_desatualizado">Preço desatualizado</option><option value="produtividade_baixa">Produtividade baixa (limite em %)</option></select>' +
       '<select class="sel" id="rParcela"><option value="todas">Todas as parcelas</option>' + AG.parcelas.map(p => '<option value="' + p + '">Parcela ' + p + '</option>').join('') + '</select>' +
       '<input class="sel" id="rLimite" placeholder="Limite de humidade (%)" inputmode="numeric">' +
       '<select class="sel" id="rAcao"><option value="avisar">Avisar e criar tarefa</option><option value="ligar_rega">Ligar a rega</option></select>' +
       '<input class="sel" id="rCusto" placeholder="Custo previsto (Kz)" inputmode="numeric">' +
       '<button class="btn" style="margin:0" data-radd="1">Criar rotina</button></div>' +
       '<p class="nota">Parcela, limite e ação só se aplicam à humidade baixa. O custo previsto só se aplica à praga ativa, e é uma estimativa tua.</p></div>';
  h += '<div class="card wide"><h3>O que a Agro fez</h3>' + (AG.notificacoes.length ? AG.notificacoes.slice(0, 12).map(n =>
       '<div class="reg"><div class="ph"><span>' + esc(n.texto) + '</span>' + tagAlerta(n.nivel) + '</div><small>' + n.hora + ' · ' + esc(n.origem) + '</small></div>').join('') +
       '<button class="btn sm" data-alimpar="1">Limpar histórico</button>' : '<p>Ainda sem ações. Regista uma praga ou baixa um stock e vê a Agro reagir.</p>') + '</div>';
  h += '</div>';
  alvo.innerHTML = h;
}
function carregarAgro(){
  ldAgro().then(d => { AG = d; renderAgro(); badgeAgro(d); }).catch(() => {
    const a = $('#agroBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function badgeAgro(d){ const n = d.alertas.filter(a => a.nivel !== 'info').length; $('#cnt').textContent = n ? String(n) : ''; }
function acaoA(acao, corpo){
  return postA(acao, corpo).then(r => { agMsg = r.mensagem || ''; return ldAgro(); }).then(d => { AG = d; renderAgro(); badgeAgro(d); });
}
document.addEventListener('click', e => {
  const t = x => e.target.closest(x);
  if(vista === 'agro'){
    if(t('[data-ralt]')) acaoA('alternar', {id: Number(t('[data-ralt]').dataset.ralt)});
    else if(t('[data-rrem]')){ if(confirm('Remover esta rotina?')) acaoA('remover_regra', {id: Number(t('[data-rrem]').dataset.rrem)}); }
    else if(t('[data-radd]')) acaoA('regra', {tipo: $('#rTipo').value, parcela: $('#rParcela').value, limite: $('#rLimite').value, acao: $('#rAcao').value, custo_previsto: $('#rCusto').value});
    else if(t('[data-alimpar]')) acaoA('limpar', {});
  }
  if(vista === 'gestao'){
    if(t('[data-tc]')) acaoG('tarefa_concluir', {id: Number(t('[data-tc]').dataset.tc)});
    else if(t('[data-pc]')) acaoG('previsto_confirmar', {id: Number(t('[data-pc]').dataset.pc)});
    else if(t('[data-px]')) acaoG('previsto_cancelar', {id: Number(t('[data-px]').dataset.px)});
  }
});
ldAgro().then(badgeAgro).catch(() => {});
setInterval(() => { if(vista !== 'agro') ldAgro().then(badgeAgro).catch(() => {}); }, 15000);

/* ---------- ClimaSeguro: índice de stress hídrico e seguro paramétrico piloto ---------- */
let CL = null, clMsg = '', timerClima = null;
const ldClima = () => fetch('/api/clima').then(r => r.json());
const postC = (acao, corpo) => fetch('/api/clima/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
function tagClima(e){
  if(e === 'ativada2') return '<span class="tag alta">Ativada · nível 2</span>';
  if(e === 'ativada1') return '<span class="tag warn">Ativada · nível 1</span>';
  if(e === 'alerta') return '<span class="tag warn">Em alerta</span>';
  return '<span class="tag">Coberta</span>';
}
function renderClima(){
  const alvo = $('#climaBody'); if(!alvo || !CL) return;
  const C = CL.config;
  let h = clMsg ? '<p class="aviso">' + esc(clMsg) + '</p>' : '';
  h += '<div class="kpis">' + kpi('Valor segurado (piloto)', kz(CL.total_segurado), 'soma das parcelas') + kpi('Pagamentos ativados', kz(CL.total_pago), 'registados pelo piloto') +
       kpi('Limiar de humidade', C.limiar + '%', 'abaixo disto o dia conta como seco') + kpi('Gatilho', C.dias + ' dias seguidos', 'nível 2 aos ' + (2 * C.dias) + ' dias') + '</div>';
  h += '<div class="grid"><div class="card wide"><h3>Como funciona</h3><p>O seguro paramétrico paga por um índice, não por peritagem. Aqui o índice é a humidade média diária do solo medida pelos teus sensores: ' +
       'se ficar abaixo de ' + C.limiar + '% durante ' + C.dias + ' dias seguidos, o nível 1 ativa e regista ' + C.pct1 + '% do valor segurado; aos ' + (2 * C.dias) + ' dias ativa o nível 2, até ' + C.pct2 + '%.</p>' +
       '<p class="nota">Isto é um piloto da lógica, não um contrato de seguro. Os prémios e os pagamentos reais exigem uma seguradora autorizada. Só conta dias completos com leituras (um dia sem leitura interrompe a contagem) e ainda não usa chuva, apenas a humidade do solo.</p></div>';
  h += CL.parcelas.map(p =>
    '<div class="card"><div class="ph"><h3>Parcela ' + p.id + ' · ' + p.cultura + '</h3>' + tagClima(p.estado) + '</div>' +
    '<div class="num">' + (p.indice === null ? 'sem dados' : p.indice + '%') + '<small>índice de stress hídrico</small></div>' +
    '<div class="bar"><i class="' + (p.indice >= 50 ? 'warn' : '') + '" style="width:' + (p.indice || 0) + '%"></i></div>' +
    '<div class="row"><span>Dias secos seguidos</span><em>' + p.secos + ' de ' + C.dias + '</em></div>' +
    '<div class="row"><span>Humidade agora</span><em>' + p.humidade.toFixed(0) + '%</em></div>' +
    '<div class="row"><span>Valor segurado</span><em>' + kz(p.segurado) + '</em></div>' +
    '<div class="row"><span>Pagamento nível 1 / nível 2 adicional</span><em>' + kz(p.pagamento_nivel1) + ' / ' + kz(p.pagamento_nivel2) + '</em></div>' +
    '<small>Índice: percentagem dos últimos 10 dias completos abaixo do limiar (' + p.dias_com_dados + ' dia(s) com dados).</small>' +
    '<div><button class="btn sm" data-csim="' + p.id + '">Simular seca</button></div></div>').join('');
  h += '<div class="card wide"><h3>Condições da apólice piloto</h3><div class="form" style="margin-top:0">' +
       '<input class="sel" id="clLimiar" value="' + C.limiar + '" title="Limiar de humidade (%)"><input class="sel" id="clDias" value="' + C.dias + '" title="Dias seguidos">' +
       '<input class="sel" id="clP1" value="' + C.pct1 + '" title="% nível 1"><input class="sel" id="clP2" value="' + C.pct2 + '" title="% nível 2">' +
       '<input class="sel" id="clVha" value="' + C.valor_ha + '" title="Valor segurado por hectare (Kz)"><button class="btn" style="margin:0" data-ccfg="1">Guardar</button></div>' +
       '<p class="nota">Ordem: limiar de humidade (%), dias seguidos, % do nível 1, % do nível 2, valor segurado por hectare (Kz). O valor por hectare é um exemplo editável.</p>' +
       '<div class="form"><select class="sel" id="clSimDias"><option value="3">3 dias</option><option value="6" selected>6 dias</option><option value="12">12 dias</option></select>' +
       '<span class="nota" style="align-self:center;margin:0">Dias de seca a simular ao carregar em "Simular seca" numa parcela (dados de demonstração).</span>' +
       '<button class="btn" style="margin:0" data-crem="1">Remover simulações</button></div></div>';
  h += '<div class="card wide"><h3>Eventos de ativação</h3>' + (CL.eventos.length ? CL.eventos.map(e =>
       '<div class="reg"><div class="ph"><span>Parcela ' + e.parcela + ' · ' + e.cultura + ' · nível ' + e.nivel + ' · ' + e.dias + ' dias secos</span><span class="tag ' + (e.nivel === 2 ? 'alta' : 'warn') + '">' + kz(e.pagamento) + '</span></div>' +
       '<small>' + e.data + (e.simulado ? ' · simulação' : '') + '</small></div>').join('') : '<p>Sem ativações. Carrega em "Simular seca" numa parcela para ver o seguro ativar.</p>') + '</div></div>';
  alvo.innerHTML = h;
}
function carregarClima(){
  ldClima().then(d => { CL = d; renderClima(); }).catch(() => {
    const a = $('#climaBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoC(acao, corpo){ return postC(acao, corpo).then(r => { clMsg = r.mensagem || ''; return ldClima(); }).then(d => { CL = d; renderClima(); }); }
document.addEventListener('click', e => {
  if(vista !== 'clima') return;
  const t = x => e.target.closest(x);
  if(t('[data-csim]')) acaoC('simular', {parcela: t('[data-csim]').dataset.csim, dias: $('#clSimDias').value});
  else if(t('[data-crem]')) acaoC('remover_simulacao', {});
  else if(t('[data-ccfg]')) acaoC('config', {limiar: $('#clLimiar').value, dias: $('#clDias').value, pct1: $('#clP1').value, pct2: $('#clP2').value, valor_ha: $('#clVha').value});
});

/* ---------- Score AgroNação: indicador explicável, autorização e relatório ---------- */
let SC = null, scMsg = '';
const ldScore = () => fetch('/api/score').then(r => r.json());
const postS = (acao, corpo) => fetch('/api/score/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
function renderScore(){
  const alvo = $('#scoreBody'); if(!alvo || !SC) return;
  const C = SC.config, ativas = SC.partilhas.filter(p => p.estado === 'ativa').length;
  let h = scMsg ? '<p class="aviso">' + esc(scMsg) + '</p>' : '';
  h += '<div class="kpis">' + kpi('Score AgroNação', SC.score === null ? 'sem dados' : SC.score + '/100', 'faixa ' + SC.faixa + ' · ' + (SC.demonstracao ? 'dados de demonstração' : 'dados reais')) +
       kpi('Confiança dos dados', SC.confianca.nivel, SC.confianca.dias + ' dia(s) de leituras reais') + kpi('Partilhas ativas', ativas, 'com autorização') + '</div>';
  if(SC.demonstracao) h += '<p class="aviso">Estás a ver dados de demonstração ou simulados. O score serve para mostrar o método e não é válido para decisões de crédito.</p>';
  h += '<div class="grid"><div class="card wide"><h3>Como o score é calculado</h3>' + SC.componentes.map(c =>
       '<div class="reg"><div class="ph"><span>' + c.nome + ' · peso ' + c.peso + '%</span><span class="tag' + (c.pontos === null ? ' warn' : '') + '">' + (c.pontos === null ? 'sem dados' : c.pontos + '/100') + '</span></div>' +
       '<div class="bar"><i style="width:' + (c.pontos || 0) + '%"></i></div><small>' + esc(c.detalhe) + '</small></div>').join('') +
       '<p class="nota">Componentes sem dados ficam de fora e os pesos dos restantes são redistribuídos. Faixas: A a partir de 80, B de 65, C de 50, D abaixo de 50. As simulações do ClimaSeguro não contam.</p></div>';
  h += '<div class="card"><h3>Como melhorar</h3>' + (SC.sugestoes.length ? '<ul>' + SC.sugestoes.map(x => '<li>• ' + esc(x) + '</li>').join('') + '</ul>' : '<p>Todos os componentes estão acima de 70. Mantém o ritmo.</p>') +
       (SC.historico.length > 1 ? '<p class="nota">Evolução do score</p>' + spark(SC.historico) : '') + '</div>';
  h += '<div class="card"><h3>A exploração</h3><div class="form" style="margin-top:0"><input class="sel" id="scNome" value="' + esc(C.nome) + '" placeholder="Nome da exploração" style="width:100%">' +
       '<input class="sel" id="scDono" value="' + esc(C.proprietario) + '" placeholder="Produtor (opcional)" style="width:100%">' +
       '<select class="sel" id="scReais"><option value="0"' + (C.dados_reais ? '' : ' selected') + '>Dados de demonstração</option><option value="1"' + (C.dados_reais ? ' selected' : '') + '>Confirmo que os dados são reais</option></select>' +
       '<button class="btn" style="margin:0" data-scfg="1">Guardar</button></div></div>';
  h += '<div class="card wide"><h3>Partilhar com autorização</h3><p>O produtor decide quem vê o score, para quê e durante quanto tempo, e pode revogar a qualquer momento. O relatório mostra só o score, as componentes e a confiança dos dados, sem valores em Kz.</p>' +
       '<div class="form"><input class="sel" id="spDest" placeholder="Banco ou instituição"><input class="sel" id="spFim" placeholder="Finalidade (ex.: pedido de crédito de campanha)" style="width:280px">' +
       '<input class="sel" id="spDias" placeholder="Validade (dias)" value="30" inputmode="numeric"><button class="btn" style="margin:0" data-spart="1">Autorizar e gerar relatório</button></div>' +
       (SC.partilhas.length ? SC.partilhas.map(p => '<div class="reg"><div class="ph"><span>' + esc(p.destinatario) + ' · ' + esc(p.finalidade) + '</span><span class="tag' + (p.estado === 'ativa' ? '' : ' warn') + '">' + p.estado + '</span></div>' +
         '<small>Código ' + p.codigo + ' · criada em ' + p.criada + ' · válida até ' + p.valida_ate + ' · selo ' + p.selo + '</small>' +
         '<div>' + (p.estado === 'ativa' ? '<a class="btn sm" href="/relatorio/' + p.codigo + '" target="_blank">Abrir relatório</a><button class="btn sm" data-sprev="' + p.id + '">Revogar</button>' : '') + '</div></div>').join('') : '<p class="nota">Ainda sem partilhas.</p>') +
       '<p class="nota">O relatório abre neste computador, enquanto o servidor estiver a correr. Para um banco o consultar à distância, será preciso publicá-lo num endereço seguro. O selo deteta alterações ao conteúdo, mas não prova a origem dos dados.</p></div></div>';
  alvo.innerHTML = h;
}
function carregarScore(){
  ldScore().then(d => { SC = d; renderScore(); }).catch(() => {
    const a = $('#scoreBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoS(acao, corpo){ return postS(acao, corpo).then(r => { scMsg = r.mensagem || ''; return ldScore(); }).then(d => { SC = d; renderScore(); }); }
document.addEventListener('click', e => {
  if(vista !== 'score') return;
  const t = x => e.target.closest(x);
  if(t('[data-scfg]')) acaoS('config', {nome: $('#scNome').value, proprietario: $('#scDono').value, dados_reais: $('#scReais').value});
  else if(t('[data-spart]')) acaoS('partilhar', {destinatario: $('#spDest').value, finalidade: $('#spFim').value, validade: $('#spDias').value});
  else if(t('[data-sprev]')){ if(confirm('Revogar esta autorização?')) acaoS('revogar', {id: Number(t('[data-sprev]').dataset.sprev)}); }
});

/* ---------- Rastreabilidade: lotes com página pública e QR Code ---------- */
let RA = null, raMsg = '';
const ldRastreio = () => fetch('/api/rastreio').then(r => r.json());
const postR = (acao, corpo) => fetch('/api/rastreio/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
function renderRastreio(){
  const alvo = $('#rastreioBody'); if(!alvo || !RA) return;
  let h = raMsg ? '<p class="aviso">' + esc(raMsg) + '</p>' : '';
  h += '<div class="grid"><div class="card wide"><h3>Como funciona</h3><p>Cada lote colhido ganha uma página pública e um QR Code para a etiqueta. Quem o ler vê a origem, a rega, a humidade, as ocorrências de pragas e o score da exploração, tal como estavam no dia do registo.</p>' +
       '<div class="form"><input class="sel" id="raUrl" value="' + esc(RA.config.base_url) + '" style="width:320px"><button class="btn" style="margin:0" data-racfg="1">Guardar endereço</button></div>' +
       '<p class="nota">O QR Code aponta para este endereço. Num telemóvel só abre se estiver na mesma rede Wi-Fi do computador, usando o IP do computador (por exemplo http://192.168.1.10:8080), ou se a página estiver publicada na internet. Em localhost só abre neste computador.</p></div>';
  h += '<div class="card"><h3>Registar um lote colhido</h3><div class="form" style="margin-top:0">' +
       '<select class="sel" id="raParcela">' + RA.parcelas.map(p => '<option value="' + p.id + '">Parcela ' + p.id + ' · ' + p.cultura + '</option>').join('') + '</select>' +
       '<input class="sel" id="raProd" placeholder="Produto (vazio = cultura)"><input class="sel" id="raQtd" placeholder="Quantidade (kg)" inputmode="numeric">' +
       '<input class="sel" id="raColh" placeholder="Colheita AAAA-MM-DD (vazio = hoje)"><input class="sel" id="raSem" placeholder="Sementeira AAAA-MM-DD (opcional)">' +
       '<input class="sel" id="raNotas" placeholder="Notas (opcional)" style="width:100%"><button class="btn" style="margin:0" data-ralote="1">Registar lote</button></div>' +
       '<p class="nota">Sem data de sementeira, a Agro considera os 90 dias antes da colheita. A rega e as humidades vêm dos registos reais; as simulações do ClimaSeguro não contam.</p></div>';
  h += '<div class="card"><h3>Lotes</h3>' + (RA.lotes.length ? RA.lotes.map(l =>
       '<div class="reg"><div style="display:flex;gap:14px;align-items:center"><img src="/qr/' + l.codigo + '.svg" width="84" height="84" style="border-radius:6px;background:#fff" alt="QR">' +
       '<div style="flex:1"><div class="ph"><span>' + l.numero + ' · ' + esc(l.produto) + ' · ' + l.quantidade_kg + ' kg</span><span class="tag' + (l.estado === 'ativo' ? '' : ' alta') + '">' + (l.estado === 'ativo' ? 'Ativo' : 'Retirado') + '</span></div>' +
       '<small>Parcela ' + l.parcela + ' · colheita ' + l.data_colheita + ' · selo ' + l.selo + '</small>' +
       '<div><a class="btn sm" href="/lote/' + l.codigo + '" target="_blank">Ver página do lote</a><a class="btn sm" href="/etiqueta/' + l.codigo + '" target="_blank">Etiqueta com QR</a>' +
       (l.estado === 'ativo' ? '<button class="btn sm" data-raret="' + l.id + '">Retirar lote</button>' : '') + '</div></div></div></div>').join('') : '<p>Ainda sem lotes.</p>') + '</div></div>';
  alvo.innerHTML = h;
}
function carregarRastreio(){
  ldRastreio().then(d => { RA = d; renderRastreio(); }).catch(() => {
    const a = $('#rastreioBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoR(acao, corpo){ return postR(acao, corpo).then(r => { raMsg = r.mensagem || ''; return ldRastreio(); }).then(d => { RA = d; renderRastreio(); }); }
document.addEventListener('click', e => {
  if(vista !== 'rastreio') return;
  const t = x => e.target.closest(x);
  if(t('[data-racfg]')) acaoR('config', {base_url: $('#raUrl').value});
  else if(t('[data-ralote]')) acaoR('lote', {parcela: $('#raParcela').value, produto: $('#raProd').value, quantidade: $('#raQtd').value, data_colheita: $('#raColh').value, data_sementeira: $('#raSem').value, notas: $('#raNotas').value});
  else if(t('[data-raret]')){ const m = prompt('Motivo da retirada (opcional):'); if(m !== null) acaoR('retirar', {id: Number(t('[data-raret]').dataset.raret), motivo: m}); }
});

/* ---------- Previsão de colheita: estimativa por parcela ---------- */
let PD = null, pdMsg = '';
const ldProdutiv = () => fetch('/api/produtividade').then(r => r.json());
const postP = (acao, corpo) => fetch('/api/produtividade/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
const nm = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
function renderProdutiv(){
  const alvo = $('#produtivBody'); if(!alvo || !PD) return;
  let h = pdMsg ? '<p class="aviso">' + esc(pdMsg) + '</p>' : '';
  h += '<div class="kpis">' + kpi('Colheita total estimada', nm(PD.total_estimado) + ' kg', 'entre ' + nm(PD.total_min) + ' e ' + nm(PD.total_max) + ' kg') + '</div>';
  h += '<div class="grid"><div class="card wide"><h3>Como a Agro estima</h3><p>Rendimento base (kg por hectare) × fator da água × fator das pragas, com uma margem de incerteza. O rendimento base vem das colheitas que registaste na Rastreabilidade; sem colheitas, usa um valor de referência provisório que deves confirmar com um técnico agrário. ' +
       'O fator da água desconta até 50% se todos os dias reais tiverem stress hídrico. Cada praga ativa desconta 3% (nível baixo), 8% (médio) ou 15% (alto). Estes pesos são provisórios e melhoram com as colheitas reais.</p>' +
       '<p class="nota">É uma estimativa indicativa, não uma garantia. Dias simulados do ClimaSeguro não contam. A margem é de 30% com confiança baixa, 20% com média e 10% com boa.</p></div>';
  h += PD.parcelas.map(p => {
    if(!p.previsao) return '<div class="card"><div class="ph"><h3>Parcela ' + p.id + ' · ' + p.cultura + '</h3></div><p>' + esc(p.motivo || 'Sem previsão.') + '</p>' + formSem(p) + '</div>';
    const baixa = p.pct_condicoes < 75;
    return '<div class="card"><div class="ph"><h3>Parcela ' + p.id + ' · ' + p.cultura + '</h3><span class="tag' + (baixa ? ' warn' : '') + '">' + (baixa ? 'Baixa produtividade prevista' : 'Condições boas') + '</span></div>' +
      '<div class="num">' + nm(p.kg_total) + ' kg<small>entre ' + nm(p.kg_min) + ' e ' + nm(p.kg_max) + ' kg · ' + nm(p.kg_ha) + ' kg/ha</small></div>' +
      '<div class="bar"><i class="' + (baixa ? 'warn' : '') + '" style="width:' + Math.min(100, p.pct_condicoes) + '%"></i></div>' +
      '<div class="row"><span>Condições face ao esperado</span><em>' + p.pct_condicoes + '%</em></div>' +
      p.fatores.map(f => '<div class="row"><span>' + esc(f.nome) + '</span><em>' + (f.efeito === 0 ? 'sem efeito' : f.efeito + '%') + '</em></div>').join('') +
      '<div class="row"><span>Ciclo</span><em>' + (p.ciclo_concluido ? 'concluído, regista o lote' : p.progresso + '% · colheita prevista ' + p.colheita_prevista) + '</em></div>' +
      '<div class="row"><span>Confiança</span><em>' + p.confianca + ' (margem ±' + p.margem + '%)</em></div>' +
      (p.receita ? '<div class="row"><span>Receita potencial</span><em>' + kz(p.receita.min) + ' a ' + kz(p.receita.max) + '</em></div><small>Preço líquido do melhor mercado registado: ' + kz(p.receita.preco) + '/kg · fonte ' + esc(p.receita.fonte) + (p.receita.exemplo ? ' (exemplo)' : '') + '</small><br>' : '') +
      '<small>Base: ' + nm(p.base_kg_ha) + ' kg/ha, ' + esc(p.base_fonte) + '.</small>' + formSem(p) + '</div>';
  }).join('');
  h += '<div class="card wide"><h3>Valores por cultura</h3><p class="nota" style="margin-top:0">Valores provisórios de demonstração. Confirma com um técnico agrário da tua zona e ajusta.</p>' +
       Object.keys(PD.culturas).map(c => '<div class="form"><span style="width:90px;align-self:center">' + c + '</span>' +
         '<input class="sel" id="pdRef_' + c + '" value="' + PD.culturas[c].ref + '" title="Rendimento de referência (kg/ha)"><input class="sel" id="pdCic_' + c + '" value="' + PD.culturas[c].ciclo + '" title="Ciclo (dias)">' +
         '<button class="btn sm" style="margin:0" data-pdcul="' + c + '">Guardar</button></div>').join('') +
       '<p class="nota">Ordem: rendimento de referência (kg por hectare) e duração do ciclo (dias, da sementeira à colheita).</p></div></div>';
  alvo.innerHTML = h;
}
function formSem(p){
  return '<div class="form"><input class="sel" id="pdSem_' + p.id + '" value="' + esc(p.sementeira) + '" placeholder="Sementeira AAAA-MM-DD" title="Data de sementeira">' +
         '<button class="btn sm" style="margin:0" data-pdsem="' + p.id + '">Guardar sementeira</button></div>' + (p.sementeira_exemplo ? '<small>Data de exemplo: corrige-a com a sementeira real.</small>' : '');
}
function carregarProdutiv(){
  ldProdutiv().then(d => { PD = d; renderProdutiv(); }).catch(() => {
    const a = $('#produtivBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoP(acao, corpo){ return postP(acao, corpo).then(r => { pdMsg = r.mensagem || ''; return ldProdutiv(); }).then(d => { PD = d; renderProdutiv(); }); }
document.addEventListener('click', e => {
  if(vista !== 'produtiv') return;
  const t = x => e.target.closest(x);
  if(t('[data-pdsem]')){ const id = t('[data-pdsem]').dataset.pdsem; acaoP('sementeira', {parcela: id, data: $('#pdSem_' + id).value}); }
  else if(t('[data-pdcul]')){ const c = t('[data-pdcul]').dataset.pdcul; acaoP('cultura', {cultura: c, ref: $('#pdRef_' + c).value, ciclo: $('#pdCic_' + c).value}); }
});

/* ---------- Cooperativa: painel de várias explorações ---------- */
let CO = null, coMsg = '';
const ldCoop = () => fetch('/api/cooperativa').then(r => r.json());
const postCo = (acao, corpo) => fetch('/api/cooperativa/' + acao, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)}).then(r => r.json());
function renderCoop(){
  const alvo = $('#coopBody'); if(!alvo || !CO) return;
  const K = CO.kpis;
  let h = coMsg ? '<p class="aviso">' + esc(coMsg) + '</p>' : '';
  h += '<div class="kpis">' + kpi('Explorações ativas', K.membros_ativos, 'no painel') + kpi('Área total', K.area_ha + ' ha', '') +
       kpi('Score médio', K.score_medio === null ? 'sem dados' : K.score_medio + '/100', K.inclui_demo ? 'inclui demonstração' : '') +
       kpi('Alertas', K.alertas_alta + ' altos', K.alertas_media + ' médios') + '</div>';
  if(K.inclui_demo) h += '<p class="aviso">O painel inclui explorações de demonstração (dados inventados). Servem só para mostrar o funcionamento.</p>';
  const maxP = Math.max(1, ...CO.provincias.map(p => p.kg));
  h += '<div class="grid"><div class="card wide"><h3>Oferta agregada e venda coletiva</h3>' + (CO.culturas.length ? CO.culturas.map(c =>
       '<div class="reg"><div class="ph"><span>' + esc(c.cultura) + ' · ' + c.area_ha + ' ha</span><span class="tag">' + nm(c.kg_estimado) + ' kg</span></div>' +
       '<small>Entre ' + nm(c.kg_min) + ' e ' + nm(c.kg_max) + ' kg previstos.' + (c.mercado ?
         ' Melhor mercado registado: ' + esc(c.mercado.nome) + (c.mercado.provincia ? ' (' + c.mercado.provincia + ')' : '') + ' a ' + kz(c.mercado.liquido) + '/kg líquidos, receita potencial de ' + kz(c.mercado.receita_min) + ' a ' + kz(c.mercado.receita_max) +
         ' · fonte ' + esc(c.mercado.fonte) + (c.mercado.exemplo ? ' (exemplo)' : '') : ' Sem preço registado para esta cultura.') + '</small></div>').join('') : '<p>Ainda sem previsões.</p>') +
       '<p class="nota">Volume e receita potencial somam as previsões indicativas de cada exploração. Só entram pacotes dentro da validade.</p></div>';
  h += '<div class="card"><h3>Produção prevista por província</h3>' + (CO.provincias.length ? CO.provincias.map(p =>
       '<div class="row"><span>' + esc(p.provincia) + '</span><em>' + nm(p.kg) + ' kg</em></div><div class="bar"><i style="width:' + Math.round(100 * p.kg / maxP) + '%"></i></div>').join('') : '<p>Sem dados.</p>') + '</div>';
  h += '<div class="card"><h3>Partilhar os dados desta exploração</h3><p>Gera um pacote para a cooperativa que escolheres. Inclui o nome, a província, a área, a previsão de colheita, o número de alertas e o score. <b>Não inclui</b> custos, receitas, funcionários, preços nem stocks.</p>' +
       '<div class="form"><input class="sel" id="coDest" placeholder="Nome da cooperativa"><input class="sel" id="coDias" value="30" inputmode="numeric" title="Validade (dias)"><button class="btn" style="margin:0" data-copac="1">Descarregar pacote</button></div>' +
       '<p class="nota">O pacote tem validade e um selo que deteta alterações. Depois de expirar, deixa de entrar nas somas do painel.</p></div>';
  h += '<div class="card wide"><h3>Membros</h3>' + CO.membros.map(m =>
       '<div class="reg"><div class="ph"><span>' + esc(m.exploracao) + (m.produtor ? ' · ' + esc(m.produtor) : '') + ' · ' + esc(m.provincia) + '</span>' +
       '<span class="tag' + (m.expirado ? ' alta' : m.origem === 'ao vivo' ? '' : ' warn') + '">' + (m.expirado ? 'Expirado' : m.origem === 'ao vivo' ? 'Ao vivo (esta exploração)' : m.origem === 'demonstracao' ? 'Demonstração' : 'Importado') + '</span></div>' +
       '<small>' + m.area_ha + ' ha · ' + esc(m.culturas) + ' · ' + nm(m.kg_min) + ' a ' + nm(m.kg_max) + ' kg · score ' + (m.score === null ? 'sem dados' : m.score + ' (' + m.faixa + ')') +
       ' · alertas: ' + m.alertas_alta + ' altos, ' + m.alertas_media + ' médios · pacote de ' + m.gerado + ', válido até ' + m.valido_ate + '</small>' +
       (m.origem === 'ao vivo' ? '' : '<div><button class="btn sm" data-corem="' + m.id + '">Remover</button></div>') + '</div>').join('') + '</div>';
  h += '<div class="card wide"><h3>Adicionar um membro</h3><p>Cola aqui o pacote que o produtor te enviou. A Agro confere o selo e a validade antes de aceitar.</p>' +
       '<textarea class="sel" id="coTexto" placeholder="Cola o conteúdo do ficheiro pacote_agronacao.json"></textarea>' +
       '<button class="btn" data-coimp="1">Importar pacote</button><button class="btn" data-codemo="1">Criar explorações de demonstração</button><button class="btn" data-coremdemo="1">Remover demonstração</button>' +
       '<p class="nota">Esta versão troca pacotes entre computadores, sem precisar de internet estável. Um painel em tempo real, com todos os produtores ligados, exige um servidor central: é a fase seguinte.</p></div></div>';
  alvo.innerHTML = h;
}
function carregarCoop(){
  ldCoop().then(d => { CO = d; renderCoop(); }).catch(() => {
    const a = $('#coopBody');
    if(a) a.innerHTML = '<div class="card"><p>Sem ligação ao servidor. Confirma que o CMD continua com o servidor_web.py a correr.</p></div>';
  });
}
function acaoCo(acao, corpo){ return postCo(acao, corpo).then(r => { coMsg = r.mensagem || ''; return ldCoop(); }).then(d => { CO = d; renderCoop(); }); }
document.addEventListener('click', e => {
  if(vista !== 'coop') return;
  const t = x => e.target.closest(x);
  if(t('[data-copac]')){
    const dest = $('#coDest').value.trim(), dias = Number($('#coDias').value);
    if(!dest || !(dias >= 1 && dias <= 365)){ coMsg = 'Indica a cooperativa destinatária e uma validade entre 1 e 365 dias.'; renderCoop(); return; }
    window.location = '/api/cooperativa/pacote?destinatario=' + encodeURIComponent(dest) + '&dias=' + dias;
  }
  else if(t('[data-coimp]')) acaoCo('importar', {texto: $('#coTexto').value});
  else if(t('[data-codemo]')) acaoCo('demo', {});
  else if(t('[data-coremdemo]')) acaoCo('remover_demo', {});
  else if(t('[data-corem]')){ if(confirm('Remover este membro do painel?')) acaoCo('remover', {id: Number(t('[data-corem]').dataset.corem)}); }
});

/* ---------- Habilidades (cada uma abre a sua página) ---------- */
const SK = {
agro: {t:'Central da Agro', s:'Monitorização contínua', h:'<div id="agroBody"><div class="card"><p>A ligar à Agro...</p></div></div>'},
coop: {t:'Cooperativa', s:'Painel de várias explorações', h:'<div id="coopBody"><div class="card"><p>A carregar o painel...</p></div></div>'},
produtiv: {t:'Previsão de colheita', s:'Estimativa indicativa', h:'<div id="produtivBody"><div class="card"><p>A calcular as previsões...</p></div></div>'},
rastreio: {t:'Rastreabilidade', s:'Lotes com QR Code', h:'<div id="rastreioBody"><div class="card"><p>A carregar os lotes...</p></div></div>'},
score: {t:'Score AgroNação', s:'Indicador explicável', h:'<div id="scoreBody"><div class="card"><p>A calcular o score...</p></div></div>'},
clima: {t:'ClimaSeguro', s:'Seguro paramétrico piloto', h:'<div id="climaBody"><div class="card"><p>A carregar o ClimaSeguro...</p></div></div>'},
campo: {t:'AgroSinal · Campo', s:'Sensores em direto', h:'<div id="campoBody"><div class="card"><p>A ligar aos sensores...</p></div></div>'},
praga: {t:'PragaAlerta', s:'Diagnóstico guiado', h:'<div id="pragaBody"><div class="card"><p>A carregar o registo de pragas...</p></div></div>'},
gestao: {t:'AgroGestão', s:'Gestão operacional', h:'<div id="gestaoBody"><div class="card"><p>A carregar a gestão da exploração...</p></div></div>'},
mercado: {t:'FazendaDirecta', s:'Preços com fonte e data', h:'<div id="mercadoBody"><div class="card"><p>A carregar preços e compradores...</p></div></div>'}
};

/* ---------- Navegação ---------- */
function abrir(v){
  vista = v;
  if(timerCampo){ clearInterval(timerCampo); timerCampo = null; }
  if(timerAgro){ clearInterval(timerAgro); timerAgro = null; }
  if(timerClima){ clearInterval(timerClima); timerClima = null; }
  document.querySelectorAll('#nav button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  if(v === 'chat'){ app.dataset.mode = 'chat'; chat.classList.remove('min'); fab.classList.remove('show'); }
  else{
    const k = SK[v];
    work.innerHTML = '<div class="wh"><h2>'+k.t+'</h2><span>'+k.s+'</span></div>' + k.h;
    app.dataset.mode = 'skill'; work.scrollTop = 0;
    if(v === 'campo'){ carregarCampo(); timerCampo = setInterval(carregarCampo, 4000); }
    if(v === 'praga'){ prRes = null; prMsg = ''; prSint.clear(); carregarPraga(); }
    if(v === 'gestao'){ gMsg = ''; carregarGestao(); }
    if(v === 'mercado'){ meRes = null; meMsg = ''; meProd = ''; carregarMercado(); }
    if(v === 'agro'){ agMsg = ''; carregarAgro(); timerAgro = setInterval(carregarAgro, 5000); }
    if(v === 'clima'){ clMsg = ''; carregarClima(); timerClima = setInterval(carregarClima, 5000); }
    if(v === 'score'){ scMsg = ''; carregarScore(); }
    if(v === 'rastreio'){ raMsg = ''; carregarRastreio(); }
    if(v === 'produtiv'){ pdMsg = ''; carregarProdutiv(); }
    if(v === 'coop'){ coMsg = ''; carregarCoop(); }
  }
  const m = $('#msgs'); m.scrollTop = m.scrollHeight;
}
$('#nav').addEventListener('click', e => { const b = e.target.closest('button'); if(b) abrir(b.dataset.v); });
$('#btnMin').onclick = () => { chat.classList.add('min'); fab.classList.add('show'); };
fab.onclick = () => { chat.classList.remove('min'); fab.classList.remove('show'); };

/* ---------- Chat ---------- */
function msg(autor, html){
  const d = document.createElement('div'); d.className = 'm ' + autor;
  d.innerHTML = autor === 'agro' ? ORB + '<div class="t">' + html + '</div>' : '<div class="t">' + html + '</div>';
  col.appendChild(d); const m = $('#msgs'); m.scrollTop = m.scrollHeight;
}
function esc(t){ return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function responder(p){
  const c = p.toLowerCase();
  // Ação real: ligar ou parar a rega de uma parcela
  if((c.includes('rega') || c.includes('regar') || c.includes('irrig')) && /[123]/.test(c)){
    const n = c.match(/[123]/)[0];
    const ligar = !(c.includes('parar') || c.includes('desliga'));
    return irrigar(n, ligar).then(r => '<b>AgroSinal</b><br>' + r.mensagem).catch(() => 'Sem ligação aos sensores.');
  }
  if(c.includes('cooperativa') || c.includes('membros') || c.includes('oferta'))
    return ldCoop().then(d => '<b>Cooperativa</b><br>' + d.kpis.membros_ativos + ' exploração(ões) ativa(s), ' + d.kpis.area_ha + ' ha.<br>' +
      (d.culturas.length ? d.culturas.map(c => esc(c.cultura) + ': ' + nm(c.kg_min) + ' a ' + nm(c.kg_max) + ' kg').join('<br>') : 'Sem previsões ainda.') +
      (d.kpis.inclui_demo ? '<br>Inclui explorações de demonstração.' : '')).catch(() => 'Sem ligação à cooperativa.');
  if(c.includes('colheita') || c.includes('produtividade') || c.includes('previs') || c.includes('rendimento') || c.includes('agenda'))
    return ldProdutiv().then(d => '<b>Previsão de colheita</b><br>' + d.parcelas.map(p => p.previsao ?
      'Parcela ' + p.id + ' (' + p.cultura + '): ' + nm(p.kg_min) + ' a ' + nm(p.kg_max) + ' kg, colheita prevista ' + p.colheita_prevista + ', condições ' + p.pct_condicoes + '% do esperado, confiança ' + p.confianca :
      'Parcela ' + p.id + ' (' + p.cultura + '): ' + esc(p.motivo)).join('<br>') +
      '<br>É uma estimativa indicativa. Não marco colheitas sozinha: usa o AgroGestão para criar a tarefa.').catch(() => 'Sem ligação à previsão de colheita.');
  if(c.includes('parcela') || c.includes('sensor') || c.includes('humidade')){
    const n = c.includes('2') ? '2' : c.includes('3') ? '3' : '1';
    return ldCampo().then(d => {
      const x = d.parcelas.find(q => q.id === n);
      return '<b>AgroSinal · Parcela ' + n + '</b><br>' + x.cultura + ' · humidade ' + x.humidade.toFixed(0) + '% · ' + x.temperatura.toFixed(0) + ' °C<br>' +
        (x.irrigando ? 'Rega em curso.' : x.estado === 'ideal' ? 'Estado ideal.' : x.estado === 'regar' ? 'Atenção: precisa de rega.' : 'Humidade em excesso.');
    }).catch(() => 'Sem ligação aos sensores.');
  }
  if(c.includes('lote') || c.includes('rastre') || c.includes('qr'))
    return ldRastreio().then(d => d.lotes.length ? '<b>Rastreabilidade</b><br>' + d.lotes.length + ' lote(s) registado(s). Último: ' + d.lotes[0].numero + ' · ' + esc(d.lotes[0].produto) + ' · ' + d.lotes[0].quantidade_kg + ' kg (' + d.lotes[0].estado + ').<br>Abre a Rastreabilidade para ver a etiqueta com QR Code.' : '<b>Rastreabilidade</b><br>Ainda não há lotes. Regista um lote colhido para gerar o QR Code.').catch(() => 'Sem ligação à Rastreabilidade.');
  if(c.includes('score') || c.includes('crédito') || c.includes('credito') || c.includes('financiamento'))
    return ldScore().then(d => '<b>Score AgroNação</b><br>' + (d.score === null ? 'Ainda sem dados suficientes.' : d.score + '/100, faixa ' + d.faixa + '.') +
      '<br>Confiança dos dados: ' + d.confianca.nivel + (d.demonstracao ? '. Estão em uso dados de demonstração, por isso não vale para crédito.' : '.') +
      (d.sugestoes.length ? '<br>Para melhorar: ' + esc(d.sugestoes[0]) : '')).catch(() => 'Sem ligação ao Score.');
  if(c.includes('seguro') || c.includes('seca') || c.includes('apólice') || c.includes('apolice') || c.includes('clima'))
    return ldClima().then(d => '<b>ClimaSeguro</b><br>' + d.parcelas.map(p => 'Parcela ' + p.id + ' (' + p.cultura + '): ' +
      (p.estado === 'coberta' ? 'coberta, sem dias secos' : p.estado === 'alerta' ? 'em alerta, ' + p.secos + ' dia(s) secos seguidos' : 'seguro ativado, ' + p.secos + ' dias secos')).join('<br>') +
      '<br>Pagamentos registados no piloto: ' + kz(d.total_pago) + '.').catch(() => 'Sem ligação ao ClimaSeguro.');
  if(c.includes('alertas') || c.includes('notifica') || c.includes('saúde') || c.includes('saude'))
    return ldAgro().then(d => '<b>Central da Agro</b><br>Saúde da exploração: ' + d.saude.valor + '/100 (' + d.saude.faixa + ').<br>' +
      (d.alertas.length ? d.alertas.slice(0, 5).map(a => NIV_AL[a.nivel] + ': ' + esc(a.texto)).join('<br>') : 'Sem alertas.')).catch(() => 'Sem ligação à Agro.');
  if(c.includes('praga') || c.includes('doença') || c.includes('inseto'))
    return ldPraga().then(d => {
      const a = d.registos.filter(r => r.estado === 'ativo');
      if(!a.length) return '<b>PragaAlerta</b><br>Sem ocorrências ativas nas parcelas.';
      return '<b>PragaAlerta</b><br>' + a.map(r => 'Parcela ' + r.parcela + ' (' + r.cultura + '): ' + esc(r.praga) + ', nível ' + NIVEL[r.nivel].toLowerCase()).join('<br>') +
             '<br>Abre o PragaAlerta para o diagnóstico guiado e o que fazer.';
    }).catch(() => 'Sem ligação ao PragaAlerta.');
  if(c.includes('estado') || c.includes('resumo'))
    return ldCampo().then(d => '<b>Estado da exploração</b><br>' + d.sensores_ativos + ' sensores ativos, humidade média de ' + d.humidade_media.toFixed(0) + '%, clima estável.<br>' +
      (d.alertas.filter(a => a.nivel === 'aviso').length ? d.alertas.filter(a => a.nivel === 'aviso').length + ' aviso(s) no campo. Abre o AgroSinal para ver.' : 'Sem avisos no campo.'))
      .catch(() => 'Sem ligação aos sensores.');
  if(c.includes('comprador') || c.includes('mercado') || c.includes('preço') || c.includes('preco') || c.includes('vender'))
    return ldMercado().then(d => {
      const todos = d.produtos.venda.concat(d.produtos.insumo), n = norm(c);
      let prod = todos.find(x => n.includes(norm(x).split(' ')[0])), tipo = d.produtos.venda.includes(prod) ? 'venda' : 'insumo';
      if(!prod){ prod = d.produtos.venda.find(x => norm(x).includes('feij')) || d.produtos.venda[0]; tipo = 'venda'; }
      if(!prod) return '<b>FazendaDirecta</b><br>Ainda não há preços nem propostas registados.';
      return melhorMercado(prod, tipo).then(textoMercado);
    }).catch(() => 'Sem ligação ao FazendaDirecta.');
  if(c.includes('stock') || c.includes('insumo') || c.includes('semente'))
    return ldGestao().then(d => '<b>AgroGestão · Stocks</b><br>' + d.stocks.map(s => s.nome + ': ' + s.qtd + ' ' + s.unidade + (s.estado === 'repor' ? ' (repor)' : '')).join('<br>'))
      .catch(() => 'Sem ligação ao AgroGestão.');
  if(c.includes('fertilizante') || c.includes('custo') || c.includes('gast'))
    return ldGestao().then(d => { const f = d.financas;
      return '<b>Finanças</b><br>Custos do mês: ' + kz(f.custos + f.mao_obra) + ' · receitas: ' + kz(f.receitas) + '<br>Resultado: ' + kz(f.resultado) +
        (f.roi === null ? '' : ' (retorno ' + (f.roi >= 0 ? '+' : '') + f.roi + '%)'); }).catch(() => 'Sem ligação ao AgroGestão.');
  if(c.includes('escala') || c.includes('trabalho') || c.includes('equipa'))
    return ldGestao().then(d => '<b>AgroGestão</b><br>Escala dos próximos dias de trabalho:<br>' +
      d.escala.filter(e => !e.descanso).slice(0, 3).map(e => e.dia + ' ' + e.data + ': A) ' + e.A + ' · B) ' + e.B).join('<br>') +
      '<br>Abre o AgroGestão para ver os 15 dias.').catch(() => 'Sem ligação ao AgroGestão.');
  return 'Ainda não percebi esse pedido. Experimenta: “estado da exploração”, “ver sensor parcela 2”, “liga a rega da parcela 2”, “verificar pragas”, “melhor comprador” ou “criar escala de trabalho”.';
}

/* ---------- Conversas ---------- */
let conversas = [], atual = null;
function novaConversa(){
  atual = {titulo:'Nova conversa', html:''}; conversas.unshift(atual);
  col.innerHTML = ''; msg('agro', SAUDACAO); listar();
}
function guardar(){ if(atual) atual.html = col.innerHTML; }
function listar(){
  const box = $('#conv');
  box.querySelectorAll('.item').forEach(e => e.remove());
  conversas.forEach(cv => {
    const b = document.createElement('button'); b.className = 'item' + (cv === atual ? ' on' : '');
    b.innerHTML = '<span class="lb">' + esc(cv.titulo) + '</span>';
    b.onclick = () => { guardar(); atual = cv; col.innerHTML = cv.html; listar(); abrir('chat'); };
    box.appendChild(b);
  });
}
$('#novaConv').onclick = () => { guardar(); novaConversa(); abrir('chat'); };

function perguntar(p){
  if(!p) return;
  if(atual.titulo === 'Nova conversa'){ atual.titulo = p.length > 24 ? p.slice(0,24) + '…' : p; listar(); }
  msg('user', esc(p));
  setTimeout(() => {
    Promise.resolve(responder(p)).then(r => { msg('agro', r); guardar(); });
  }, 350);
}
function enviar(){ const i = $('#inp'); const t = i.value.trim(); i.value = ''; perguntar(t); }
$('#enviar').onclick = enviar;
$('#inp').addEventListener('keydown', e => { if(e.key === 'Enter') enviar(); });
document.addEventListener('click', e => {
  const q = e.target.closest('[data-q]');
  if(q){ if(app.dataset.mode === 'skill' && chat.classList.contains('min')){ chat.classList.remove('min'); fab.classList.remove('show'); } perguntar(q.dataset.q); return; }
  const r = e.target.closest('[data-irr]');
  if(r){ irrigar(r.dataset.irr, r.dataset.lig === '1'); return; }
  if(e.target.closest('[data-diag]')){
    if(!prSint.size){ prMsg = 'Escolhe pelo menos um sintoma.'; prRes = null; renderPraga(); return; }
    postPraga('diagnostico', {parcela: prParcela, sintomas: Array.from(prSint)})
      .then(x => { prRes = x.ok ? x.resultados : null; prMsg = x.ok ? '' : x.mensagem; renderPraga(); });
    return;
  }
  const g = e.target.closest('[data-reg]');
  if(g){
    const i = Number(g.dataset.reg), x = prRes[i];
    postPraga('registar', {parcela: prParcela, praga: x.nome, nivel: $('#nv' + i).value, notas: 'Diagnóstico guiado (' + x.confianca + '% de correspondência)'})
      .then(r => { prMsg = r.mensagem; prRes = null; prSint.clear(); return ldPraga(); })
      .then(d => { PR = d; renderPraga(); });
    return;
  }
  const t = e.target.closest('[data-trat]');
  if(t){
    postPraga('tratar', {id: Number(t.dataset.trat)}).then(() => ldPraga()).then(d => { PR = d; prMsg = ''; renderPraga(); });
    return;
  }
  const gp = e.target.closest('[data-pres]');
  if(gp){ acaoG('presenca', {id: Number(gp.dataset.pres)}); return; }
  const gr = e.target.closest('[data-rem]');
  if(gr){ if(confirm('Remover este funcionário?')) acaoG('remover', {id: Number(gr.dataset.rem)}); return; }
  if(e.target.closest('[data-addf]')){
    acaoG('funcionario', {nome: $('#gNome').value, funcao: $('#gFuncao').value, equipa: $('#gEquipa').value, diaria: $('#gDiaria').value}); return;
  }
  const gs = e.target.closest('[data-stk]');
  if(gs){ acaoG('stock', {id: Number(gs.dataset.stk), delta: Number(gs.dataset.d)}); return; }
  if(e.target.closest('[data-addm]')){
    acaoG('movimento', {tipo: $('#mTipo').value, descricao: $('#mDesc').value, valor: $('#mValor').value});
  }
});
document.addEventListener('change', e => {
  if(e.target.id === 'prParcela'){ prParcela = e.target.value; prSint.clear(); prRes = null; prMsg = ''; renderPraga(); }
  else if(e.target.matches('[data-sint]')){ if(e.target.checked) prSint.add(e.target.dataset.sint); else prSint.delete(e.target.dataset.sint); }
});

/* ---------- Personalizar (muda o tom do verde) ---------- */
const TONS = [['#4fb08a','#3d8f9a'],['#5fa8a0','#4a7fa6'],['#7ab07a','#4f9a86']];
let tom = 0;
$('#pers').onclick = () => {
  tom = (tom + 1) % TONS.length;
  document.documentElement.style.setProperty('--ac', TONS[tom][0]);
  document.documentElement.style.setProperty('--ac2', TONS[tom][1]);
};

novaConversa();
</script>
</body>
</html>
"""


def _vigiar():
    # A Agro vigia a exploração de 10 em 10 segundos, mesmo sem o navegador aberto
    while True:
        time.sleep(10)
        try:
            with TRAVA:
                AGRO.avaliar()
                CLIMA.atualizar()
        except Exception:
            pass


class Handler(http.server.SimpleHTTPRequestHandler):
    def _json(self, obj, codigo=200):
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path.startswith(("/lote/", "/etiqueta/", "/qr/")):
            rota, _, resto = self.path.split("?")[0].lstrip("/").partition("/")
            with TRAVA:
                if rota == "qr":
                    qr = RASTREIO.qr_do_lote(resto.replace(".svg", ""))
                    corpo, tipo = (qr or "").encode("utf-8"), "image/svg+xml; charset=utf-8"
                    pagina = qr
                else:
                    pagina = RASTREIO.pagina_lote(resto) if rota == "lote" else RASTREIO.etiqueta_html(resto)
                    corpo = (pagina or "<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><title>Não encontrado</title></head><body><h1>Lote não encontrado</h1></body></html>").encode("utf-8")
                    tipo = "text/html; charset=utf-8"
            self.send_response(200 if pagina else 404)
            self.send_header("Content-type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        if self.path.startswith("/api/cooperativa/pacote"):
            q = parse_qs(urlparse(self.path).query)
            with TRAVA:
                r = COOP.exportar(q.get("destinatario", [""])[0], q.get("dias", ["30"])[0])
            if not r["ok"]:
                self._json(r, 400)
                return
            corpo = r["texto"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="pacote_agronacao.json"')
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        if self.path == "/api/cooperativa":
            with TRAVA:
                self._json(COOP.dados())
            return
        if self.path == "/api/produtividade":
            with TRAVA:
                self._json(PRODUTIV.dados())
            return
        if self.path == "/api/rastreio":
            with TRAVA:
                self._json(RASTREIO.dados())
            return
        if self.path.startswith("/relatorio/"):
            with TRAVA:
                pagina = SCORE.relatorio_html(self.path.split("?")[0].rsplit("/", 1)[1])
            corpo = (pagina or "<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><title>Não encontrado</title></head><body><h1>Relatório não encontrado</h1></body></html>").encode("utf-8")
            self.send_response(200 if pagina else 404)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        if self.path == "/api/score":
            with TRAVA:
                self._json(SCORE.dados())
            return
        if self.path == "/api/clima":
            with TRAVA:
                self._json(CLIMA.dados())
            return
        if self.path == "/api/agro":
            with TRAVA:
                self._json(AGRO.dados())
            return
        if self.path.startswith("/api/mercado"):
            with TRAVA:
                if self.path.startswith("/api/mercado/melhor"):
                    q = parse_qs(urlparse(self.path).query)
                    self._json(MERCADO.melhor(q.get("produto", [""])[0], q.get("tipo", ["venda"])[0]))
                else:
                    self._json(MERCADO.dados())
            return
        if self.path == "/api/gestao":
            with TRAVA:
                self._json(GESTAO.dados())
            return
        if self.path == "/api/praga":
            with TRAVA:
                self._json(PRAGA.dados())
            return
        if self.path.startswith("/api/campo"):
            with TRAVA:
                self._json(CAMPO.dados())
            return
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTEUDO.encode("utf-8"))

    def do_POST(self):
        try:
            tamanho = int(self.headers.get("Content-Length", 0))
            if tamanho > 2000000:
                raise ValueError("pedido demasiado grande")
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8") or "{}")
        except Exception:
            self._json({"ok": False, "mensagem": "Pedido inválido."}, 400)
            return
        if self.path == "/api/campo/irrigar":
            with TRAVA:
                self._json(CAMPO.irrigar(dados.get("parcela"), bool(dados.get("ligar"))))
        elif self.path == "/api/praga/diagnostico":
            with TRAVA:
                self._json(PRAGA.diagnosticar(dados.get("parcela"), dados.get("sintomas")))
        elif self.path == "/api/praga/registar":
            with TRAVA:
                self._json(PRAGA.registar(dados.get("parcela"), dados.get("praga"), dados.get("nivel"), dados.get("notas")))
        elif self.path == "/api/praga/tratar":
            with TRAVA:
                try:
                    self._json(PRAGA.tratar(int(dados.get("id"))))
                except (TypeError, ValueError):
                    self._json({"ok": False, "mensagem": "Pedido inválido."}, 400)
        elif self.path.startswith("/api/cooperativa/"):
            with TRAVA:
                self._json(COOP.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/produtividade/"):
            with TRAVA:
                self._json(PRODUTIV.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/rastreio/"):
            with TRAVA:
                self._json(RASTREIO.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/score/"):
            with TRAVA:
                self._json(SCORE.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/clima/"):
            with TRAVA:
                self._json(CLIMA.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/agro/"):
            with TRAVA:
                self._json(AGRO.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/mercado/"):
            with TRAVA:
                self._json(MERCADO.executar(self.path.rsplit("/", 1)[1], dados))
        elif self.path.startswith("/api/gestao/"):
            with TRAVA:
                self._json(GESTAO.executar(self.path.rsplit("/", 1)[1], dados))
        else:
            self._json({"ok": False, "mensagem": "Rota não encontrada."}, 404)

    def log_message(self, format, *args):
        pass  # mantém o CMD limpo


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    os.chdir(DIRETORIO)
    threading.Thread(target=_vigiar, daemon=True).start()
    with Servidor(("", PORTA), Handler) as httpd:
        url = f"http://localhost:{PORTA}"
        print("======================================================================")
        print("      AGRONAÇÃO OS - Interface iniciada com sucesso")
        print("======================================================================")
        print(f"Servidor a escutar em 0.0.0.0:{PORTA}")
        print(f"Endereço local: {url}")
        print("Pressione Ctrl+C para fechar o servidor.")
        # webbrowser.open(url)  # desactivado na nuvem
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado com segurança.")