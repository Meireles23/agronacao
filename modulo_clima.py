# modulo_clima.py - Módulo ClimaSeguro (seguro paramétrico piloto)
# Lógica: se a humidade média diária do solo ficar abaixo de um limiar durante N dias seguidos,
# o seguro "ativa" sozinho e regista o pagamento. Não precisa de peritagem.
# Guarda as leituras diárias e os eventos em dados_clima.json (na mesma pasta).
# Nota: é um PILOTO. Preços de prémio e pagamentos reais exigem uma seguradora autorizada.
import datetime
import json
import os
import random
import time

CONFIG_BASE = {"limiar": 50.0, "dias": 5, "pct1": 30.0, "pct2": 60.0, "valor_ha": 300000}


def _hoje():
    return datetime.date.today()


def _numero(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


class ModuloClima:
    def __init__(self, campo, ficheiro=None):
        self.campo = campo
        self.avisar = None  # função (nivel, texto) ligada pelo servidor à Central da Agro
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_clima.json")
        self._ultimo_guardar = 0.0
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {"config": dict(CONFIG_BASE), "diario": {}, "episodios": {}, "eventos": [], "prox": 1}
            self._guardar(True)

    def _guardar(self, forcar=False):
        if not forcar and time.time() - self._ultimo_guardar < 60:
            return
        self._ultimo_guardar = time.time()
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass

    # --- leituras diárias ---
    @staticmethod
    def _media(rec):
        return rec["soma"] / rec["n"] if rec and rec.get("n") else None

    def atualizar(self):
        hoje = _hoje().isoformat()
        for p in self.campo.dados()["parcelas"]:
            dias = self.d["diario"].setdefault(p["id"], {})
            rec = dias.setdefault(hoje, {"soma": 0.0, "n": 0, "min": 100.0, "simulado": False})
            rec["soma"] += p["humidade"]
            rec["n"] += 1
            rec["min"] = min(rec["min"], p["humidade"])
            for velho in sorted(dias)[:-60]:
                del dias[velho]
        self._avaliar_todas()
        self._guardar()

    def _secos_consecutivos(self, pid):
        # Conta os dias completos (até ontem) com humidade média abaixo do limiar. Um dia sem leitura interrompe a contagem.
        limiar = self.d["config"]["limiar"]
        dia = _hoje() - datetime.timedelta(days=1)
        contagem, simulado = 0, False
        while contagem < 60:
            rec = self.d["diario"].get(pid, {}).get(dia.isoformat())
            m = self._media(rec)
            if m is None or m >= limiar:
                break
            contagem += 1
            simulado = simulado or bool(rec.get("simulado"))
            dia -= datetime.timedelta(days=1)
        return contagem, simulado

    def _avaliar_todas(self):
        for p in self.campo.dados()["parcelas"]:
            self._avaliar(p)

    def _avaliar(self, p):
        cfg, pid = self.d["config"], p["id"]
        cont, simulado = self._secos_consecutivos(pid)
        ep = self.d["episodios"].get(pid, 0)
        if cont == 0:
            self.d["episodios"][pid] = 0
            return
        segurado = p["area_ha"] * cfg["valor_ha"]
        novos = []
        if cont >= cfg["dias"] and ep < 1:
            novos.append((1, segurado * cfg["pct1"] / 100))
            ep = 1
        if cont >= 2 * cfg["dias"] and ep < 2:
            novos.append((2, segurado * max(0.0, cfg["pct2"] - cfg["pct1"]) / 100))
            ep = 2
        for nivel, pagamento in novos:
            dias_ev = cfg["dias"] if nivel == 1 else min(cont, 2 * cfg["dias"])
            self.d["eventos"].append({
                "id": self.d["prox"], "data": _hoje().isoformat(), "parcela": pid, "cultura": p["cultura"],
                "nivel": nivel, "dias": dias_ev, "pagamento": round(pagamento), "simulado": simulado,
            })
            self.d["prox"] += 1
            if self.avisar:
                kz = f"{round(pagamento):,}".replace(",", ".")
                self.avisar("alta" if nivel == 2 else "media",
                            f"Seguro ativado (nível {nivel}) na parcela {pid} ({p['cultura']}): {dias_ev} dias seguidos com humidade abaixo de {cfg['limiar']:g}%. "
                            f"Pagamento registado: {kz} Kz" + (" (simulação)." if simulado else "."))
            self._guardar(True)
        self.d["episodios"][pid] = ep

    # --- consulta ---
    def _estado(self, pid, cont):
        ep = self.d["episodios"].get(pid, 0)
        if ep == 2:
            return "ativada2"
        if ep == 1:
            return "ativada1"
        return "alerta" if cont > 0 else "coberta"

    def dados(self):
        self.atualizar()
        cfg = self.d["config"]
        parcelas = []
        for p in self.campo.dados()["parcelas"]:
            pid = p["id"]
            cont, _ = self._secos_consecutivos(pid)
            # índice de stress: % dos últimos 10 dias completos com humidade média abaixo do limiar
            amostra = []
            dia = _hoje() - datetime.timedelta(days=1)
            for _ in range(10):
                m = self._media(self.d["diario"].get(pid, {}).get(dia.isoformat()))
                if m is not None:
                    amostra.append(m < cfg["limiar"])
                dia -= datetime.timedelta(days=1)
            segurado = p["area_ha"] * cfg["valor_ha"]
            pagos = sum(e["pagamento"] for e in self.d["eventos"] if e["parcela"] == pid)
            parcelas.append({
                "id": pid, "cultura": p["cultura"], "area_ha": p["area_ha"], "humidade": p["humidade"],
                "secos": cont, "estado": self._estado(pid, cont),
                "indice": round(100 * sum(amostra) / len(amostra)) if amostra else None, "dias_com_dados": len(amostra),
                "segurado": round(segurado), "pagamento_nivel1": round(segurado * cfg["pct1"] / 100),
                "pagamento_nivel2": round(segurado * max(0.0, cfg["pct2"] - cfg["pct1"]) / 100), "pago": pagos,
            })
        eventos = sorted(self.d["eventos"], key=lambda e: e["id"], reverse=True)[:15]
        return {
            "config": cfg, "parcelas": parcelas, "eventos": eventos,
            "total_segurado": sum(p["segurado"] for p in parcelas),
            "total_pago": sum(e["pagamento"] for e in self.d["eventos"]),
        }

    def alertas(self):
        # Usado pela Central da Agro
        saida = []
        cfg = self.d["config"]
        for p in self.campo.dados()["parcelas"]:
            cont, _ = self._secos_consecutivos(p["id"])
            if cont == 0:
                continue
            ep = self.d["episodios"].get(p["id"], 0)
            if ep:
                saida.append({"nivel": "alta", "modulo": "ClimaSeguro",
                              "texto": f"Seguro ativado na parcela {p['id']} ({p['cultura']}): {cont} dias seguidos abaixo de {cfg['limiar']:g}%."})
            else:
                saida.append({"nivel": "media", "modulo": "ClimaSeguro",
                              "texto": f"Parcela {p['id']} com {cont} dia(s) seguidos abaixo de {cfg['limiar']:g}% de humidade (o seguro ativa aos {cfg['dias']})."})
        return saida

    # --- ações ---
    def configurar(self, limiar, dias, pct1, pct2, valor_ha):
        l, d, a, b, v = _numero(limiar), _numero(dias), _numero(pct1), _numero(pct2), _numero(valor_ha)
        if None in (l, d, a, b, v) or not (10 <= l <= 80) or not (2 <= d <= 30) or not (0 < a <= b <= 100) or not (0 <= v <= 100000000):
            return {"ok": False, "mensagem": "Valores inválidos. Limiar 10-80%, 2 a 30 dias, % do nível 1 menor ou igual à do nível 2, valor por hectare válido."}
        self.d["config"] = {"limiar": l, "dias": int(d), "pct1": a, "pct2": b, "valor_ha": v}
        self._guardar(True)
        return {"ok": True, "mensagem": "Condições da apólice piloto atualizadas."}

    def simular_seca(self, parcela, dias):
        pid = str(parcela).strip()
        n = _numero(dias)
        ids = [p["id"] for p in self.campo.dados()["parcelas"]]
        if pid not in ids or n is None or not (1 <= n <= 30):
            return {"ok": False, "mensagem": "Escolhe uma parcela e entre 1 e 30 dias."}
        cfg = self.d["config"]
        self.d["eventos"] = [e for e in self.d["eventos"] if not (e["simulado"] and e["parcela"] == pid)]
        self.d["episodios"][pid] = 0
        registos = self.d["diario"].setdefault(pid, {})
        for i in range(1, int(n) + 1):
            chave = (_hoje() - datetime.timedelta(days=i)).isoformat()
            if chave in registos and not registos[chave].get("simulado") and registos[chave]["n"] > 0:
                continue  # nunca apaga leituras reais
            m = round(max(10.0, cfg["limiar"] - random.uniform(4, 12)), 1)
            registos[chave] = {"soma": m, "n": 1, "min": m, "simulado": True}
        self._avaliar_todas()
        self._guardar(True)
        return {"ok": True, "mensagem": f"Seca simulada na parcela {pid}: {int(n)} dia(s) abaixo do limiar (dados de demonstração)."}

    def remover_simulacao(self):
        for pid in list(self.d["diario"]):
            self.d["diario"][pid] = {k: v for k, v in self.d["diario"][pid].items() if not v.get("simulado")}
        self.d["eventos"] = [e for e in self.d["eventos"] if not e["simulado"]]
        self.d["episodios"] = {}
        self._avaliar_todas()
        self._guardar(True)
        return {"ok": True, "mensagem": "Simulações removidas."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações do ClimaSeguro
        if acao == "config":
            return self.configurar(dados.get("limiar"), dados.get("dias"), dados.get("pct1"), dados.get("pct2"), dados.get("valor_ha"))
        if acao == "simular":
            return self.simular_seca(dados.get("parcela"), dados.get("dias"))
        if acao == "remover_simulacao":
            return self.remover_simulacao()
        return {"ok": False, "mensagem": "Pedido inválido."}