# modulo_campo.py - Módulo de AgroSinal e PragaAlerta
# Os métodos ler_sensores() e verificar_pragas() ficam como estavam.
# Acrescentado: dados em direto das parcelas, rega e registo (usados pela interface web).
import datetime
import json
import os
import random
import time


class ModuloCampo:
    def __init__(self):
        self.sensores_ativos = 12
        # Estado em direto das parcelas (valores simulados até haver sensores reais)
        self._parcelas = {
            "1": {"cultura": "Milho", "area_ha": 4.2, "humidade": 72.0, "temperatura": 26.0, "irrigando": False, "sensores": 4},
            "2": {"cultura": "Feijão", "area_ha": 2.8, "humidade": 58.0, "temperatura": 28.0, "irrigando": False, "sensores": 4},
            "3": {"cultura": "Mandioca", "area_ha": 3.5, "humidade": 65.0, "temperatura": 25.0, "irrigando": False, "sensores": 4},
        }
        self._historico = {k: [p["humidade"]] for k, p in self._parcelas.items()}
        self._eventos = []
        self._ultimo = time.time()
        # Registo permanente das operações de rega (usado pela rastreabilidade)
        self._ficheiro_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados_campo.json")
        self._rega_log = []
        try:
            with open(self._ficheiro_log, "r", encoding="utf-8") as f:
                self._rega_log = json.load(f).get("rega_log", [])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Métodos originais (sem alterações)
    # ------------------------------------------------------------------
    def ler_sensores(self, parcela):
        parcela_num = parcela.strip()
        # Simulação de leitura de dados reais do campo
        dados = {
            "1": {"cultura": "Milho", "humidade": "72%", "temperatura": "26°C", "status_irrigacao": "Ideal"},
            "2": {"cultura": "Feijão", "humidade": "58%", "temperatura": "28°C", "status_irrigacao": "Atenção: Necessária irrigação"},
            "3": {"cultura": "Mandioca", "humidade": "65%", "temperatura": "25°C", "status_irrigacao": "Ideal"}
        }

        if parcela_num in dados:
            d = dados[parcela_num]
            return (
                f"📡 [AgroSinal - Parcela {parcela_num}]\n"
                f"- Cultura: {d['cultura']}\n"
                f"- Humidade do Solo: {d['humidade']}\n"
                f"- Temperatura: {d['temperatura']}\n"
                f"- Estado da Irrigação: {d['status_irrigacao']}"
            )
        else:
            return "⚠️ Parcela não encontrada. Por favor, especifique uma parcela válida (ex: 1, 2 ou 3)."

    def verificar_pragas(self):
        return (
            "🔬 [PragaAlerta - Diagnóstico por Imagem]\n"
            "- Análise de imagem recente da Parcela 2 concluída.\n"
            "- Diagnóstico: Indícios leves de Lagarta-do-cartucho detetados nas folhas inferiores.\n"
            "- Recomendação de Tratamento: Aplicação localizada de bio-inseticida recomendado nas próximas 48 horas. "
            "Risco de propagação: Baixo."
        )

    # ------------------------------------------------------------------
    # Novo: AgroSinal em direto
    # ------------------------------------------------------------------
    def _log_rega(self, parcela, acao):
        self._rega_log.append({"quando": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "parcela": str(parcela), "acao": acao})
        del self._rega_log[:-500]
        try:
            with open(self._ficheiro_log, "w", encoding="utf-8") as f:
                json.dump({"rega_log": self._rega_log}, f, ensure_ascii=False)
        except OSError:
            pass

    def rega_log(self):
        return list(self._rega_log)

    def _log(self, texto):
        hora = datetime.datetime.now().strftime("%H:%M:%S")
        self._eventos.insert(0, {"hora": hora, "texto": texto})
        del self._eventos[8:]

    @staticmethod
    def _estado(humidade):
        if humidade < 60:
            return "regar"
        if humidade > 80:
            return "excesso"
        return "ideal"

    def _tick(self):
        for k, p in self._parcelas.items():
            if p["irrigando"]:
                p["humidade"] = min(95.0, p["humidade"] + random.uniform(1.0, 2.0))
                if p["humidade"] >= 78:
                    p["irrigando"] = False
                    self._log(f"A Agro parou a rega da parcela {k} (humidade {p['humidade']:.0f}%)")
                    self._log_rega(k, "parada automática")
            else:
                p["humidade"] = max(20.0, p["humidade"] - random.uniform(0.05, 0.3))
            p["temperatura"] = min(34.0, max(22.0, p["temperatura"] + random.uniform(-0.3, 0.3)))
            hist = self._historico[k]
            hist.append(round(p["humidade"], 1))
            del hist[:-24]

    def _atualizar(self):
        # Um passo de simulação a cada 4 segundos
        passos = int((time.time() - self._ultimo) // 4)
        if passos <= 0:
            return
        self._ultimo += passos * 4
        for _ in range(min(passos, 30)):
            self._tick()

    def irrigar(self, parcela, ligar):
        self._atualizar()
        k = str(parcela).strip()
        if k not in self._parcelas:
            return {"ok": False, "mensagem": "Parcela não encontrada."}
        p = self._parcelas[k]
        if ligar:
            if p["humidade"] >= 80:
                return {"ok": False, "mensagem": f"Parcela {k} já tem humidade alta ({p['humidade']:.0f}%)."}
            p["irrigando"] = True
            self._log(f"Rega ligada na parcela {k}")
            self._log_rega(k, "ligada")
            return {"ok": True, "mensagem": f"Rega ligada na parcela {k}. A Agro para sozinha aos 78%."}
        p["irrigando"] = False
        self._log(f"Rega parada na parcela {k}")
        self._log_rega(k, "parada")
        return {"ok": True, "mensagem": f"Rega parada na parcela {k}."}

    def dados(self):
        self._atualizar()
        parcelas = []
        alertas = []
        for k, p in self._parcelas.items():
            estado = self._estado(p["humidade"])
            parcelas.append({
                "id": k,
                "cultura": p["cultura"],
                "area_ha": p["area_ha"],
                "humidade": round(p["humidade"], 1),
                "temperatura": round(p["temperatura"], 1),
                "estado": estado,
                "irrigando": p["irrigando"],
                "sensores": p["sensores"],
                "historico": list(self._historico[k]),
            })
            if estado == "regar":
                alertas.append({"nivel": "aviso", "texto": f"Parcela {k} ({p['cultura']}) com {p['humidade']:.0f}% de humidade: recomendada rega."})
            elif estado == "excesso":
                alertas.append({"nivel": "aviso", "texto": f"Parcela {k} ({p['cultura']}) com excesso de humidade ({p['humidade']:.0f}%)."})
            if p["temperatura"] > 32:
                alertas.append({"nivel": "aviso", "texto": f"Parcela {k} com temperatura alta ({p['temperatura']:.0f} °C)."})
            if p["irrigando"]:
                alertas.append({"nivel": "info", "texto": f"Rega em curso na parcela {k}."})
        n = len(parcelas)
        return {
            "hora": datetime.datetime.now().strftime("%H:%M:%S"),
            "sensores_ativos": self.sensores_ativos,
            "humidade_media": round(sum(x["humidade"] for x in parcelas) / n, 1),
            "temperatura_media": round(sum(x["temperatura"] for x in parcelas) / n, 1),
            "previsao": "Sem chuvas fortes nas próximas 48 h",
            "parcelas": parcelas,
            "alertas": alertas,
            "eventos": list(self._eventos),
        }