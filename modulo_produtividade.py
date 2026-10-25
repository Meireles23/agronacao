# modulo_produtividade.py - Previsão de produtividade (estimativa indicativa por parcela)
# Como funciona: rendimento base x fator da água x fator das pragas, com uma margem de incerteza.
# O rendimento base vem das colheitas anteriores registadas na Rastreabilidade; sem colheitas usa um valor de
# referência PROVISÓRIO que deve ser confirmado com um técnico agrário. Guarda em dados_produtividade.json.
import datetime
import json
import os

from modulo_mercado import _norm

# Valores provisórios de demonstração: confirmar com um técnico agrário da zona e ajustar.
CULTURAS_BASE = {
    "Milho": {"ref": 2000, "ciclo": 120},
    "Feijão": {"ref": 800, "ciclo": 90},
    "Mandioca": {"ref": 10000, "ciclo": 300},
}
PENALIDADE_PRAGA = {"alto": 0.15, "medio": 0.08, "baixo": 0.03}
SENSIBILIDADE_AGUA = 0.5  # com todos os dias em stress, o rendimento cai 50%
MARGEM = {"baixa": 0.30, "média": 0.20, "boa": 0.10}


def _numero(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


class ModuloProdutividade:
    def __init__(self, campo, praga, clima, rastreio, mercado, ficheiro=None):
        self.campo, self.praga, self.clima, self.rastreio, self.mercado = campo, praga, clima, rastreio, mercado
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_produtividade.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {"culturas": {k: dict(v) for k, v in CULTURAS_BASE.items()}, "sementeiras": {}}
        # Sementeira de exemplo (editável) para as parcelas que ainda não têm data
        ex = (datetime.date.today() - datetime.timedelta(days=40)).isoformat()
        for p in self.campo.dados()["parcelas"]:
            self.d["sementeiras"].setdefault(p["id"], {"data": ex, "exemplo": True})
        self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass

    # --- cálculo por parcela ---
    def _calibracao(self, cultura):
        areas = {p["id"]: p["area_ha"] for p in self.campo.dados()["parcelas"]}
        valores = []
        for lt in sorted(self.rastreio.d["lotes"], key=lambda x: x["id"]):
            f = lt["foto"]
            if f["cultura"] == cultura and areas.get(f["parcela"]):
                valores.append(f["quantidade_kg"] / areas[f["parcela"]])
        return valores[-3:]

    def _parcela(self, p):
        pid, cultura, area = p["id"], p["cultura"], p["area_ha"]
        cfg = self.d["culturas"].get(cultura)
        sem = self.d["sementeiras"].get(pid)
        saida = {"id": pid, "cultura": cultura, "area_ha": area, "previsao": False, "motivo": "",
                 "sementeira": sem["data"] if sem else "", "sementeira_exemplo": bool(sem and sem.get("exemplo")),
                 "ciclo_dias": cfg["ciclo"] if cfg else None}
        if not cfg or not sem:
            saida["motivo"] = "Indica a data de sementeira e os valores da cultura."
            return saida
        hoje = datetime.date.today()
        inicio = datetime.date.fromisoformat(sem["data"])
        dias = (hoje - inicio).days
        saida["dias"] = dias
        saida["progresso"] = max(0, min(100, round(100 * dias / cfg["ciclo"])))
        saida["colheita_prevista"] = (inicio + datetime.timedelta(days=cfg["ciclo"])).isoformat()

        calib = self._calibracao(cultura)
        if calib:
            base, fonte = sum(calib) / len(calib), f"média das últimas {len(calib)} colheita(s) registadas"
        else:
            base, fonte = cfg["ref"], "valor de referência provisório (confirmar com um técnico agrário)"

        limiar = self.clima.d["config"]["limiar"]
        total = stress = 0
        for dia, rec in self.clima.d["diario"].get(pid, {}).items():
            if sem["data"] <= dia < hoje.isoformat() and rec.get("n", 0) > 0 and not rec.get("simulado"):
                total += 1
                stress += 1 if rec["soma"] / rec["n"] < limiar else 0
        f_agua = 1 - SENSIBILIDADE_AGUA * (stress / total) if total else 1.0
        ativas = [r for r in self.praga.dados()["registos"] if r["parcela"] == pid and r["estado"] == "ativo"]
        f_praga = max(0.5, 1 - sum(PENALIDADE_PRAGA.get(r["nivel"], 0) for r in ativas))
        fator = f_agua * f_praga

        confianca = "boa" if (len(calib) >= 3 and total >= 30) else "média" if (calib or total >= 14) else "baixa"
        kg_ha = base * fator
        margem = MARGEM[confianca]
        kg_total = kg_ha * area
        receita = None
        for produto in self.mercado.dados()["produtos"]["venda"]:
            if _norm(produto) == _norm(cultura):
                ops = self.mercado.melhor(produto, "venda").get("opcoes", [])
                if ops:
                    o = ops[0]
                    receita = {"preco": o["liquido"], "fonte": o["fonte"], "exemplo": o["exemplo"],
                               "min": round(kg_total * (1 - margem) * o["liquido"]), "max": round(kg_total * (1 + margem) * o["liquido"])}
                break
        saida.update({
            "previsao": True, "base_kg_ha": round(base), "base_fonte": fonte, "n_calibracao": len(calib),
            "dias_dados": total, "dias_stress": stress,
            "fatores": [
                {"nome": f"Água: {stress} de {total} dia(s) com stress" if total else "Água: ainda sem dias de leitura real", "efeito": round((f_agua - 1) * 100)},
                {"nome": f"Pragas ativas: {len(ativas)}", "efeito": round((f_praga - 1) * 100)},
            ],
            "pct_condicoes": round(fator * 100), "kg_ha": round(kg_ha), "kg_total": round(kg_total),
            "kg_min": round(kg_total * (1 - margem)), "kg_max": round(kg_total * (1 + margem)),
            "margem": round(margem * 100), "confianca": confianca, "receita": receita,
            "ciclo_concluido": dias >= cfg["ciclo"],
        })
        return saida

    def dados(self):
        parcelas = [self._parcela(p) for p in self.campo.dados()["parcelas"]]
        com = [p for p in parcelas if p["previsao"]]
        return {
            "parcelas": parcelas, "culturas": self.d["culturas"],
            "total_min": sum(p["kg_min"] for p in com), "total_max": sum(p["kg_max"] for p in com),
            "total_estimado": sum(p["kg_total"] for p in com),
        }

    # --- ações ---
    def definir_sementeira(self, parcela, data):
        pid = str(parcela).strip()
        if pid not in [p["id"] for p in self.campo.dados()["parcelas"]]:
            return {"ok": False, "mensagem": "Parcela não encontrada."}
        try:
            dia = datetime.date.fromisoformat(str(data).strip()[:10])
        except ValueError:
            return {"ok": False, "mensagem": "Data inválida (AAAA-MM-DD)."}
        hoje = datetime.date.today()
        if dia > hoje or (hoje - dia).days > 730:
            return {"ok": False, "mensagem": "A data de sementeira tem de ser passada (até 2 anos)."}
        self.d["sementeiras"][pid] = {"data": dia.isoformat(), "exemplo": False}
        self._guardar()
        return {"ok": True, "mensagem": f"Sementeira da parcela {pid} guardada."}

    def definir_cultura(self, cultura, ref, ciclo):
        r, c = _numero(ref), _numero(ciclo)
        if cultura not in self.d["culturas"] or r is None or c is None or not (50 <= r <= 100000) or not (30 <= c <= 730):
            return {"ok": False, "mensagem": "Valores inválidos: referência entre 50 e 100000 kg/ha e ciclo entre 30 e 730 dias."}
        self.d["culturas"][cultura] = {"ref": r, "ciclo": int(c)}
        self._guardar()
        return {"ok": True, "mensagem": f"Valores de {cultura} guardados."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações da Produtividade
        if acao == "sementeira":
            return self.definir_sementeira(dados.get("parcela"), dados.get("data"))
        if acao == "cultura":
            return self.definir_cultura(dados.get("cultura"), dados.get("ref"), dados.get("ciclo"))
        return {"ok": False, "mensagem": "Pedido inválido."}