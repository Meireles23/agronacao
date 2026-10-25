# modulo_score.py - Score AgroNação (indicador explicável para acesso a financiamento)
# O score é calculado com os dados que o produtor regista e com as leituras dos sensores.
# Só é partilhado com autorização: cada partilha tem destinatário, validade e pode ser revogada.
# Guarda a configuração, o histórico e as partilhas em dados_score.json (na mesma pasta).
# Nota: é um indicador da AgroNação. Não é uma avaliação de crédito nem substitui a análise de um banco.
import datetime
import hashlib
import html
import json
import os
import random
import string

PESOS = {"financas": 30, "gestao": 25, "agua": 25, "consistencia": 20}

SUGESTOES = {
    "financas": "Regista todas as receitas e custos do mês para o retorno refletir a realidade.",
    "gestao": "Conclui as tarefas da escala, trata as pragas registadas e repõe os stocks abaixo do mínimo.",
    "agua": "Mantém a humidade das parcelas na faixa ideal e deixa o servidor ligado para guardar as leituras de todos os dias.",
    "consistencia": "Usa a plataforma todos os dias: leituras, presenças e registos nos últimos 30 dias.",
}


def _limitar(x, a=0.0, b=100.0):
    return max(a, min(b, x))


def _faixa(score):
    if score is None:
        return "-"
    return "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"


class ModuloScore:
    def __init__(self, campo, praga, gestao, clima, ficheiro=None):
        self.campo, self.praga, self.gestao, self.clima = campo, praga, gestao, clima
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_score.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {
                "config": {"nome": "Exploração AgroNação (demonstração)", "proprietario": "", "dados_reais": False},
                "historico": [], "partilhas": [], "prox": 1,
            }
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass

    # --- cálculo ---
    def _dias_reais(self):
        # Dias completos dos últimos 30 com leituras reais (as simulações não contam)
        hoje = datetime.date.today()
        limite = (hoje - datetime.timedelta(days=30)).isoformat()
        dias = set()
        for registos in self.clima.d["diario"].values():
            for dia, rec in registos.items():
                if limite <= dia < hoje.isoformat() and rec.get("n", 0) > 0 and not rec.get("simulado"):
                    dias.add(dia)
        return dias

    def calcular(self):
        campo, praga, g = self.campo.dados(), self.praga.dados(), self.gestao.dados()
        comps = []

        roi = g["financas"]["roi"]
        comps.append({"id": "financas", "nome": "Resultados financeiros", "peso": PESOS["financas"],
                      "pontos": None if roi is None else round(_limitar(50 + roi * 2.5)),
                      "detalhe": "Sem custos registados neste mês." if roi is None else f"Retorno do mês: {roi:+d}%."})

        subs, notas = [], []
        tarefas = self.gestao.d.get("tarefas", [])
        if tarefas:
            feitas = len([t for t in tarefas if t["estado"] == "concluida"])
            subs.append(100 * feitas / len(tarefas))
            notas.append(f"tarefas da Agro concluídas: {feitas} de {len(tarefas)}")
        regs = praga["registos"]
        if regs:
            tratados = len([r for r in regs if r["estado"] != "ativo"])
            subs.append(100 * tratados / len(regs))
            notas.append(f"pragas tratadas: {tratados} de {len(regs)}")
        stocks = g["stocks"]
        if stocks:
            ok = len([s for s in stocks if s["estado"] == "ok"])
            subs.append(100 * ok / len(stocks))
            notas.append(f"stocks acima do mínimo: {ok} de {len(stocks)}")
        comps.append({"id": "gestao", "nome": "Gestão da exploração", "peso": PESOS["gestao"],
                      "pontos": round(sum(subs) / len(subs)) if subs else None,
                      "detalhe": ("; ".join(notas) + ".").capitalize() if notas else "Sem dados de gestão."})

        subs, notas = [], []
        parcelas = campo["parcelas"]
        ideais = len([p for p in parcelas if p["estado"] == "ideal"])
        subs.append(100 * ideais / len(parcelas))
        notas.append(f"parcelas na humidade ideal agora: {ideais} de {len(parcelas)}")
        limiar = self.clima.d["config"]["limiar"]
        dias = self._dias_reais()
        total = bons = 0
        for registos in self.clima.d["diario"].values():
            for dia, rec in registos.items():
                if dia in dias and rec.get("n", 0) > 0 and not rec.get("simulado"):
                    total += 1
                    bons += 1 if rec["soma"] / rec["n"] >= limiar else 0
        if total:
            subs.append(100 * bons / total)
            notas.append(f"dias sem stress hídrico: {bons} de {total} (parcela-dia)")
        comps.append({"id": "agua", "nome": "Água e sensores", "peso": PESOS["agua"],
                      "pontos": round(sum(subs) / len(subs)), "detalhe": ("; ".join(notas) + ".").capitalize()})

        lim = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        atividade = len([m for m in self.gestao.d["movimentos"] if m["data"] >= lim])
        atividade += sum(1 for f in self.gestao.d["funcionarios"] for d in f["presencas"] if d >= lim)
        atividade += len([r for r in regs if r["data"][:10] >= lim])
        pts = (_limitar(100 * len(dias) / 30) + _limitar(100 * atividade / 10)) / 2
        comps.append({"id": "consistencia", "nome": "Consistência de uso", "peso": PESOS["consistencia"], "pontos": round(pts),
                      "detalhe": f"{len(dias)} dia(s) com leituras reais nos últimos 30; {atividade} registo(s) no mesmo período."})

        com_dados = [c for c in comps if c["pontos"] is not None]
        score = round(sum(c["peso"] * c["pontos"] for c in com_dados) / sum(c["peso"] for c in com_dados)) if com_dados else None
        n = len(dias)
        confianca = {"nivel": "baixa" if n < 7 else "média" if n < 30 else "boa", "dias": n}
        return {
            "score": score, "faixa": _faixa(score), "componentes": comps, "confianca": confianca,
            "demonstracao": not self.d["config"]["dados_reais"],
            "sugestoes": [SUGESTOES[c["id"]] for c in comps if c["pontos"] is None or c["pontos"] < 70],
        }

    def _historico(self, score):
        if score is None:
            return
        hoje = datetime.date.today().isoformat()
        h = self.d["historico"]
        if h and h[-1]["data"] == hoje:
            h[-1]["score"] = score
        else:
            h.append({"data": hoje, "score": score})
            del h[:-90]
        self._guardar()

    def dados(self):
        r = self.calcular()
        self._historico(r["score"])
        agora = datetime.date.today().isoformat()
        partilhas = []
        for p in self.d["partilhas"]:
            partilhas.append({k: p[k] for k in ("id", "codigo", "destinatario", "finalidade", "criada", "valida_ate", "selo")} |
                             {"estado": "revogada" if not p["ativa"] else "expirada" if p["valida_ate"] < agora else "ativa"})
        r.update({
            "config": self.d["config"], "historico": [h["score"] for h in self.d["historico"]],
            "partilhas": sorted(partilhas, key=lambda x: x["id"], reverse=True),
        })
        return r

    # --- ações ---
    def configurar(self, nome, proprietario, dados_reais):
        nome = str(nome or "").strip()[:60]
        if not nome:
            return {"ok": False, "mensagem": "Indica o nome da exploração."}
        self.d["config"] = {"nome": nome, "proprietario": str(proprietario or "").strip()[:60], "dados_reais": str(dados_reais) in ("1", "true", "True")}
        self._guardar()
        return {"ok": True, "mensagem": "Configuração guardada."}

    def partilhar(self, destinatario, finalidade, validade_dias):
        destinatario = str(destinatario or "").strip()[:60]
        finalidade = str(finalidade or "").strip()[:80]
        try:
            dias = int(float(str(validade_dias).replace(",", ".")))
        except ValueError:
            dias = 0
        if not destinatario or not finalidade or not (1 <= dias <= 365):
            return {"ok": False, "mensagem": "Indica o destinatário, a finalidade e uma validade entre 1 e 365 dias."}
        r = self.calcular()
        if r["score"] is None:
            return {"ok": False, "mensagem": "Ainda não há dados suficientes para calcular o score."}
        cfg = self.d["config"]
        hoje = datetime.date.today()
        foto = {
            "exploracao": cfg["nome"], "proprietario": cfg["proprietario"], "data": hoje.isoformat(),
            "score": r["score"], "faixa": r["faixa"], "confianca": r["confianca"], "demonstracao": r["demonstracao"],
            "componentes": [{"nome": c["nome"], "peso": c["peso"], "pontos": c["pontos"], "detalhe": c["detalhe"]} for c in r["componentes"]],
        }
        selo = hashlib.sha256(json.dumps(foto, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16].upper()
        codigo = "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        self.d["partilhas"].append({
            "id": self.d["prox"], "codigo": codigo, "destinatario": destinatario, "finalidade": finalidade,
            "criada": hoje.isoformat(), "valida_ate": (hoje + datetime.timedelta(days=dias)).isoformat(),
            "ativa": True, "selo": selo, "foto": foto,
        })
        self.d["prox"] += 1
        self._guardar()
        return {"ok": True, "mensagem": f"Partilha autorizada para {destinatario} até {(hoje + datetime.timedelta(days=dias)).isoformat()}. Código: {codigo}."}

    def revogar(self, id_partilha):
        for p in self.d["partilhas"]:
            if p["id"] == id_partilha and p["ativa"]:
                p["ativa"] = False
                self._guardar()
                return {"ok": True, "mensagem": "Autorização revogada. O relatório deixou de estar disponível."}
        return {"ok": False, "mensagem": "Partilha não encontrada."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações do Score
        try:
            if acao == "config":
                return self.configurar(dados.get("nome"), dados.get("proprietario"), dados.get("dados_reais"))
            if acao == "partilhar":
                return self.partilhar(dados.get("destinatario"), dados.get("finalidade"), dados.get("validade"))
            if acao == "revogar":
                return self.revogar(int(dados.get("id")))
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}

    # --- relatório para o destinatário autorizado ---
    def relatorio_html(self, codigo):
        e = html.escape
        p = next((x for x in self.d["partilhas"] if x["codigo"] == str(codigo).strip().upper()), None)
        estilo = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:760px;margin:30px auto;padding:0 20px;color:#1b2b26}"
                  "h1{font-size:1.5rem;margin-bottom:4px}.m{color:#5b6f67;font-size:.9rem}table{width:100%;border-collapse:collapse;margin:16px 0}"
                  "td,th{border-bottom:1px solid #d5e0db;padding:8px;text-align:left;font-size:.92rem}.s{font-size:3rem;margin:8px 0}"
                  ".mark{border:2px solid #b3402f;color:#b3402f;padding:10px;margin:14px 0;font-weight:bold}.nota{font-size:.8rem;color:#5b6f67;margin-top:24px}")
        if not p:
            return None
        hoje = datetime.date.today().isoformat()
        if not p["ativa"] or p["valida_ate"] < hoje:
            motivo = "A autorização foi revogada pelo produtor." if not p["ativa"] else "A validade desta autorização terminou."
            return f"<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><title>Relatório indisponível</title><style>{estilo}</style></head><body><h1>Relatório indisponível</h1><p>{motivo}</p></body></html>"
        f = p["foto"]
        linhas = "".join(
            f"<tr><td>{e(c['nome'])}</td><td>{c['peso']}%</td><td>{'sem dados' if c['pontos'] is None else str(c['pontos']) + '/100'}</td><td>{e(c['detalhe'])}</td></tr>"
            for c in f["componentes"])
        aviso = ("<div class='mark'>DADOS DE DEMONSTRAÇÃO OU SIMULADOS. Este relatório não é válido para decisões de crédito.</div>"
                 if f["demonstracao"] else "")
        dono = f"<p class='m'>Produtor: {e(f['proprietario'])}</p>" if f["proprietario"] else ""
        return (f"<!DOCTYPE html><html lang='pt'><head><meta charset='utf-8'><title>Score AgroNação</title><style>{estilo}</style></head><body>"
                f"<h1>Score AgroNação</h1><p class='m'>{e(f['exploracao'])} · calculado em {f['data']}</p>{dono}{aviso}"
                f"<div class='s'>{f['score']}/100 <small>faixa {f['faixa']}</small></div>"
                f"<p class='m'>Confiança dos dados: {f['confianca']['nivel']} ({f['confianca']['dias']} dia(s) de leituras reais nos últimos 30).</p>"
                f"<table><tr><th>Componente</th><th>Peso</th><th>Pontos</th><th>Detalhe</th></tr>{linhas}</table>"
                f"<p class='m'>Partilhado com: {e(p['destinatario'])} · finalidade: {e(p['finalidade'])} · válido até {p['valida_ate']}</p>"
                f"<p class='m'>Selo de integridade: <b>{p['selo']}</b> · código {p['codigo']}</p>"
                "<p class='nota'>Indicador calculado pela AgroNação a partir de dados registados pelo produtor e de leituras de sensores. "
                "Não é uma avaliação de crédito e não substitui a análise da instituição financeira. "
                "O selo permite detetar alterações ao conteúdo deste relatório; não prova, por si só, a origem dos dados.</p></body></html>")