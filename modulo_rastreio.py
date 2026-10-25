# modulo_rastreio.py - Módulo Rastreabilidade (lotes com página pública e QR Code)
# Cada lote guarda uma "fotografia" da origem no momento do registo: rega, humidade, ocorrências de pragas
# e score da exploração. O comprador vê isto ao ler o QR Code. Guarda em dados_rastreio.json.
# Nota: é informação registada pelo produtor e lida pelos sensores. Não é uma certificação oficial.
import datetime
import hashlib
import html
import json
import os
import random

from qr_simples import qr_svg

LETRAS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _numero(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _data(texto):
    try:
        return datetime.date.fromisoformat(str(texto).strip()[:10])
    except ValueError:
        return None


class ModuloRastreio:
    def __init__(self, campo, praga, clima, score, ficheiro=None):
        self.campo, self.praga, self.clima, self.score = campo, praga, clima, score
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_rastreio.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {"config": {"base_url": "http://localhost:8080"}, "lotes": [], "prox": 1}
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass

    def _url(self, codigo):
        return self.d["config"]["base_url"].rstrip("/") + "/lote/" + codigo

    # --- consulta ---
    def dados(self):
        lotes = []
        for lt in self.d["lotes"]:
            f = lt["foto"]
            lotes.append({
                "id": lt["id"], "numero": f["lote"], "codigo": lt["codigo"], "produto": f["produto"], "parcela": f["parcela"],
                "cultura": f["cultura"], "quantidade_kg": f["quantidade_kg"], "data_colheita": f["data_colheita"],
                "estado": lt["estado"], "motivo": lt.get("motivo", ""), "selo": lt["selo"], "url": self._url(lt["codigo"]),
            })
        return {
            "config": self.d["config"],
            "parcelas": [{"id": p["id"], "cultura": p["cultura"]} for p in self.campo.dados()["parcelas"]],
            "lotes": sorted(lotes, key=lambda x: x["id"], reverse=True),
        }

    # --- ações ---
    def configurar(self, base_url):
        url = str(base_url or "").strip().rstrip("/")
        if not (url.startswith("http://") or url.startswith("https://")) or len(url) > 100 or " " in url:
            return {"ok": False, "mensagem": "Indica um endereço válido, por exemplo http://192.168.1.10:8080"}
        self.d["config"]["base_url"] = url
        self._guardar()
        return {"ok": True, "mensagem": "Endereço guardado. Os QR Codes passam a apontar para ele."}

    def registar_lote(self, parcela, produto, quantidade, data_colheita, data_sementeira, notas):
        pid = str(parcela).strip()
        parcelas = {p["id"]: p["cultura"] for p in self.campo.dados()["parcelas"]}
        if pid not in parcelas:
            return {"ok": False, "mensagem": "Escolhe a parcela."}
        qtd = _numero(quantidade)
        if qtd is None or not (0 < qtd <= 1000000000):
            return {"ok": False, "mensagem": "Indica a quantidade colhida em kg."}
        hoje = datetime.date.today()
        colheita = _data(data_colheita) if str(data_colheita or "").strip() else hoje
        if colheita is None or colheita > hoje:
            return {"ok": False, "mensagem": "Data de colheita inválida (AAAA-MM-DD, não pode ser futura)."}
        assumido = not str(data_sementeira or "").strip()
        inicio = colheita - datetime.timedelta(days=90) if assumido else _data(data_sementeira)
        if inicio is None or inicio > colheita:
            return {"ok": False, "mensagem": "Data de sementeira inválida (AAAA-MM-DD, anterior à colheita)."}
        produto = str(produto or "").strip()[:40] or parcelas[pid]

        i0, i1 = inicio.isoformat(), colheita.isoformat()
        rega = len([r for r in self.campo.rega_log() if r["parcela"] == pid and r["acao"] == "ligada" and i0 <= r["quando"][:10] <= i1])
        medias, stress = [], 0
        limiar = self.clima.d["config"]["limiar"]
        for dia, rec in self.clima.d["diario"].get(pid, {}).items():
            if i0 <= dia <= i1 and rec.get("n", 0) > 0 and not rec.get("simulado"):
                m = rec["soma"] / rec["n"]
                medias.append(m)
                stress += 1 if m < limiar else 0
        ocorr = [{"praga": r["praga"], "nivel": r["nivel"], "estado": r["estado"], "data": r["data"][:10]}
                 for r in self.praga.dados()["registos"] if r["parcela"] == pid and i0 <= r["data"][:10] <= i1]
        sc = self.score.calcular()
        cfg = self.score.d["config"]
        numero = f"L{self.d['prox']:04d}"
        foto = {
            "lote": numero, "exploracao": cfg["nome"], "proprietario": cfg["proprietario"], "produto": produto, "parcela": pid,
            "cultura": parcelas[pid], "quantidade_kg": round(qtd, 2), "data_colheita": i1, "inicio": i0, "periodo_assumido": assumido,
            "registado": hoje.isoformat(), "rega_operacoes": rega,
            "humidade": {"dias": len(medias), "media": round(sum(medias) / len(medias), 1) if medias else None, "dias_stress": stress},
            "ocorrencias": ocorr,
            "score": {"valor": sc["score"], "faixa": sc["faixa"], "confianca": sc["confianca"]["nivel"]},
            "demonstracao": not cfg["dados_reais"], "notas": str(notas or "").strip()[:150],
        }
        selo = hashlib.sha256(json.dumps(foto, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16].upper()
        codigo = "".join(random.SystemRandom().choice(LETRAS) for _ in range(8))
        self.d["lotes"].append({"id": self.d["prox"], "codigo": codigo, "estado": "ativo", "motivo": "", "selo": selo, "foto": foto})
        self.d["prox"] += 1
        self._guardar()
        return {"ok": True, "mensagem": f"Lote {numero} registado. Abre a etiqueta para imprimir o QR Code."}

    def retirar(self, id_lote, motivo):
        for lt in self.d["lotes"]:
            if lt["id"] == id_lote and lt["estado"] == "ativo":
                lt["estado"] = "retirado"
                lt["motivo"] = str(motivo or "").strip()[:80]
                self._guardar()
                return {"ok": True, "mensagem": "Lote retirado. Quem ler o QR Code passa a ver o aviso."}
        return {"ok": False, "mensagem": "Lote não encontrado."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações da Rastreabilidade
        try:
            if acao == "config":
                return self.configurar(dados.get("base_url"))
            if acao == "lote":
                return self.registar_lote(dados.get("parcela"), dados.get("produto"), dados.get("quantidade"),
                                          dados.get("data_colheita"), dados.get("data_sementeira"), dados.get("notas"))
            if acao == "retirar":
                return self.retirar(int(dados.get("id")), dados.get("motivo"))
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}

    # --- páginas públicas ---
    def _achar(self, codigo):
        return next((x for x in self.d["lotes"] if x["codigo"] == str(codigo).strip().upper()), None)

    def qr_do_lote(self, codigo):
        lt = self._achar(codigo)
        return qr_svg(self._url(lt["codigo"]), modulo=6) if lt else None

    def pagina_lote(self, codigo):
        lt = self._achar(codigo)
        if not lt:
            return None
        e, f = html.escape, lt["foto"]
        estilo = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;padding:18px;color:#1b2b26;background:#f4f8f6}"
                  "h1{font-size:1.35rem;margin:0 0 2px}.m{color:#5b6f67;font-size:.88rem}.c{background:#fff;border:1px solid #d5e0db;border-radius:12px;padding:14px 16px;margin:12px 0}"
                  ".c h2{font-size:.95rem;margin:0 0 8px;color:#2d6a4f}.l{display:flex;justify-content:space-between;gap:12px;padding:5px 0;border-bottom:1px solid #eef3f0;font-size:.9rem}"
                  ".l:last-child{border-bottom:none}.l span:last-child{text-align:right}.alerta{border:2px solid #b3402f;color:#b3402f;padding:10px;border-radius:10px;font-weight:bold;margin:12px 0}"
                  ".nota{font-size:.78rem;color:#5b6f67;margin-top:16px}")

        def linha(a, b):
            return f"<div class='l'><span>{a}</span><span>{b}</span></div>"

        faixa = ""
        if lt["estado"] == "retirado":
            faixa += f"<div class='alerta'>LOTE RETIRADO. Não consumir nem vender.{(' Motivo: ' + e(lt['motivo'])) if lt['motivo'] else ''}</div>"
        if f["demonstracao"]:
            faixa += "<div class='alerta'>DADOS DE DEMONSTRAÇÃO. Esta página mostra o funcionamento e não descreve uma colheita real.</div>"
        h = f["humidade"]
        humidade = (f"{h['dias']} dia(s) com leituras reais; humidade média {h['media']:g}%; {h['dias_stress']} dia(s) com stress hídrico"
                    if h["dias"] else "Sem leituras reais de sensores neste período")
        ocorr = "".join(linha(e(o["praga"]) + f" ({o['data']})", f"nível {o['nivel']} · " + ("tratada" if o["estado"] != "ativo" else "ativa")) for o in f["ocorrencias"]) \
            or linha("Ocorrências de pragas registadas", "nenhuma")
        sc = f["score"]
        periodo = f"{f['inicio']} a {f['data_colheita']}" + (" (90 dias antes da colheita, por não haver data de sementeira)" if f["periodo_assumido"] else "")
        produtor = linha("Produtor", e(f["proprietario"])) if f["proprietario"] else ""
        qtd_txt = "{:g} kg".format(f["quantidade_kg"])
        notas = f"<div class='c'><h2>Notas do produtor</h2><div class='m'>{e(f['notas'])}</div></div>" if f["notas"] else ""
        return (f"<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Lote {f['lote']}</title><style>{estilo}</style></head><body>"
                f"<h1>{e(f['produto'])} · lote {f['lote']}</h1><div class='m'>Rastreabilidade AgroNação</div>{faixa}"
                f"<div class='c'><h2>Origem</h2>{linha('Exploração', e(f['exploracao']))}{produtor}{linha('Parcela', f['parcela'] + ' · ' + e(f['cultura']))}"
                f"{linha('Data de colheita', f['data_colheita'])}{linha('Quantidade', qtd_txt)}</div>"
                f"<div class='c'><h2>Cultivo ({periodo})</h2>{linha('Operações de rega registadas', str(f['rega_operacoes']))}{linha('Humidade do solo', humidade)}</div>"
                f"<div class='c'><h2>Proteção das plantas</h2>{ocorr}</div>"
                f"<div class='c'><h2>Score AgroNação da exploração</h2>{linha('Score', (str(sc['valor']) + '/100 · faixa ' + sc['faixa']) if sc['valor'] is not None else 'sem dados')}{linha('Confiança dos dados', e(sc['confianca']))}</div>"
                f"{notas}<div class='c'><h2>Verificação</h2>{linha('Selo de integridade', lt['selo'])}{linha('Registado em', f['registado'])}</div>"
                "<p class='nota'>Informação registada pelo produtor e lida por sensores da AgroNação no momento do registo. Não é uma certificação oficial. "
                "O selo deteta alterações ao conteúdo desta página; não prova, por si só, a origem dos dados.</p></body></html>")

    def etiqueta_html(self, codigo):
        lt = self._achar(codigo)
        if not lt:
            return None
        e, f = html.escape, lt["foto"]
        return ("<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><title>Etiqueta " + f["lote"] + "</title><style>"
                "body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;color:#111}.et{width:340px;border:2px solid #111;border-radius:10px;padding:16px;text-align:center}"
                "h1{font-size:1.15rem;margin:0}p{margin:4px 0;font-size:.9rem}.q svg{width:230px;height:230px}.b{margin-top:16px;font-size:.85rem}"
                "@media print{.b{display:none}}</style></head><body><div class='et'>"
                f"<h1>{e(f['produto'])}</h1><p>Lote {f['lote']} · colheita {f['data_colheita']}</p><p>{e(f['exploracao'])}</p>"
                f"<div class='q'>{qr_svg(self._url(lt['codigo']), modulo=6)}</div><p>Lê o QR Code para ver a origem</p><p><small>{e(self._url(lt['codigo']))}</small></p></div>"
                "<p class='b'><button onclick='window.print()'>Imprimir etiqueta</button></p></body></html>")