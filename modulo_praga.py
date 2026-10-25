# modulo_praga.py - Módulo PragaAlerta (registo de pragas e diagnóstico guiado)
# Não precisa de instalar nada. Guarda as ocorrências em dados_pragas.json (na mesma pasta).
# Nota: o diagnóstico é indicativo. Antes de aplicar qualquer produto, confirmar com um técnico agrário.
import datetime
import json
import os

SINTOMAS = {
    "furos_folhas": "Folhas com furos ou partes roídas",
    "cartucho_serradura": "Resíduo tipo serradura no cartucho (centro da planta)",
    "colmo_furos": "Orifícios no caule com serradura",
    "pontas_mortas": "Folha central seca (coração morto)",
    "ferrugem": "Pústulas castanho-avermelhadas nas folhas",
    "manchas_angulares": "Manchas castanhas de forma angular nas folhas",
    "mosca_branca": "Insetos brancos pequenos debaixo das folhas",
    "caule_base": "Plântulas murchas com a base do caule escura ou inchada",
    "mosaico": "Folhas deformadas com mosaico amarelo e verde",
    "cochonilha": "Rebentos atrofiados com cobertura branca farinhenta",
    "acaro": "Folhas com pontos amarelos e rebentos atrofiados",
}

CULTURA_SINTOMAS = {
    "Milho": ["furos_folhas", "cartucho_serradura", "colmo_furos", "pontas_mortas"],
    "Feijão": ["furos_folhas", "ferrugem", "manchas_angulares", "mosca_branca", "caule_base"],
    "Mandioca": ["mosaico", "cochonilha", "acaro", "mosca_branca"],
}

TECNICO = "Confirmar com um técnico agrário antes de aplicar qualquer produto."

PRAGAS = [
    {
        "nome": "Lagarta-do-cartucho", "culturas": ["Milho", "Feijão"],
        "pesos": {"furos_folhas": 2, "cartucho_serradura": 3, "pontas_mortas": 1},
        "descricao": "Larva que se alimenta das folhas e do cartucho do milho; também pode atacar outras culturas.",
        "acoes": ["Inspecionar o cartucho de várias plantas da parcela, de manhã cedo",
                  "Retirar à mão as lagartas visíveis e as folhas muito afetadas",
                  "Em ataque leve, dar preferência a produtos biológicos e a inimigos naturais", TECNICO],
    },
    {
        "nome": "Broca-do-colmo", "culturas": ["Milho"],
        "pesos": {"colmo_furos": 3, "pontas_mortas": 2},
        "descricao": "Larva que perfura o caule e enfraquece a planta.",
        "acoes": ["Retirar e destruir as plantas com o caule furado",
                  "Eliminar os restos da cultura depois da colheita", "Rodar a cultura na próxima campanha", TECNICO],
    },
    {
        "nome": "Ferrugem do feijoeiro", "culturas": ["Feijão"],
        "pesos": {"ferrugem": 4},
        "descricao": "Doença de fungos com pústulas castanho-avermelhadas nas folhas, favorecida pela humidade.",
        "acoes": ["Retirar as folhas muito atacadas", "Evitar molhar a folhagem, sobretudo ao fim da tarde",
                  "Na próxima sementeira, usar variedades tolerantes e espaçamento adequado", TECNICO],
    },
    {
        "nome": "Mancha angular do feijoeiro", "culturas": ["Feijão"],
        "pesos": {"manchas_angulares": 4},
        "descricao": "Doença de fungos com manchas castanhas limitadas pelas nervuras, que ficam angulares.",
        "acoes": ["Não trabalhar na parcela com a folhagem molhada", "Rodar com cereais na próxima campanha",
                  "Usar sementes sãs", TECNICO],
    },
    {
        "nome": "Mosca-do-caule do feijoeiro", "culturas": ["Feijão"],
        "pesos": {"caule_base": 4},
        "descricao": "Larva que escava a base do caule das plantas jovens.",
        "acoes": ["Amontoar terra à volta da base das plantas para estimular novas raízes",
                  "Retirar as plantas muito afetadas", "Semear a tempo e manter as plantas vigorosas", TECNICO],
    },
    {
        "nome": "Mosca-branca", "culturas": ["Feijão", "Mandioca"],
        "pesos": {"mosca_branca": 3, "mosaico": 2},
        "descricao": "Inseto sugador que enfraquece a planta e transmite vírus, como o do mosaico da mandioca.",
        "acoes": ["Inspecionar a parte de baixo das folhas", "Eliminar ervas daninhas à volta da parcela",
                  "Usar armadilhas amarelas com cola para acompanhar a população", TECNICO],
    },
    {
        "nome": "Mosaico da mandioca", "culturas": ["Mandioca"],
        "pesos": {"mosaico": 4, "mosca_branca": 2},
        "descricao": "Doença de vírus transmitida pela mosca-branca e por estacas infetadas. A planta doente não se cura.",
        "acoes": ["Arrancar e destruir as plantas doentes", "Plantar apenas estacas de plantas sãs",
                  "Na próxima campanha, procurar variedades resistentes", TECNICO],
    },
    {
        "nome": "Cochonilha-farinhenta da mandioca", "culturas": ["Mandioca"],
        "pesos": {"cochonilha": 4},
        "descricao": "Inseto sugador que deforma os rebentos e atrofia a planta.",
        "acoes": ["Cortar e destruir os rebentos infestados", "Não levar estacas de zonas afetadas para outras parcelas",
                  "Avisar os serviços agrários: existe controlo biológico para esta praga", TECNICO],
    },
    {
        "nome": "Ácaro-verde da mandioca", "culturas": ["Mandioca"],
        "pesos": {"acaro": 4},
        "descricao": "Ácaros minúsculos que provocam pontos amarelos e rebentos atrofiados, sobretudo na época seca.",
        "acoes": ["Inspecionar os rebentos jovens, de preferência com uma lupa",
                  "Não mover material infestado para outras parcelas",
                  "Na próxima campanha, preferir variedades tolerantes", TECNICO],
    },
]

NIVEIS = ("baixo", "medio", "alto")


class ModuloPraga:
    def __init__(self, culturas=None, ficheiro=None):
        self.culturas = culturas or {"1": "Milho", "2": "Feijão", "3": "Mandioca"}
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_pragas.json")
        self._registos = []
        self._proximo = 1
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self._registos = json.load(f)["registos"]
            self._proximo = max([r["id"] for r in self._registos] + [0]) + 1
        except Exception:
            self._registos = [{
                "id": 1, "parcela": "2", "cultura": self.culturas.get("2", ""),
                "praga": "Lagarta-do-cartucho", "nivel": "baixo",
                "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "notas": "Indícios leves nas folhas inferiores", "estado": "ativo",
            }]
            self._proximo = 2
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump({"registos": self._registos}, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    # --- consulta ---
    def dados(self):
        regs = sorted(self._registos, key=lambda r: r["id"], reverse=True)
        ativos = [r for r in regs if r["estado"] == "ativo"]
        return {
            "parcelas": [{"id": k, "cultura": v} for k, v in self.culturas.items()],
            "sintomas": {c: [{"id": s, "texto": SINTOMAS[s]} for s in ids] for c, ids in CULTURA_SINTOMAS.items()},
            "registos": regs,
            "resumo": {
                "ativos": len(ativos),
                "tratados": len(regs) - len(ativos),
                "parcelas_afetadas": len(set(r["parcela"] for r in ativos)),
            },
        }

    # --- diagnóstico guiado ---
    def diagnosticar(self, parcela, sintomas):
        k = str(parcela).strip()
        if k not in self.culturas:
            return {"ok": False, "mensagem": "Parcela não encontrada."}
        cultura = self.culturas[k]
        validos = set(CULTURA_SINTOMAS.get(cultura, []))
        escolhidos = [s for s in (sintomas or []) if s in validos]
        if not escolhidos:
            return {"ok": False, "mensagem": "Escolhe pelo menos um sintoma desta cultura."}
        resultados = []
        for p in PRAGAS:
            if cultura not in p["culturas"]:
                continue
            total = sum(p["pesos"].values())
            pontos = sum(peso for s, peso in p["pesos"].items() if s in escolhidos)
            if pontos > 0:
                resultados.append({
                    "nome": p["nome"], "confianca": round(100 * pontos / total),
                    "descricao": p["descricao"], "acoes": p["acoes"],
                })
        resultados.sort(key=lambda r: r["confianca"], reverse=True)
        return {"ok": True, "cultura": cultura, "resultados": resultados[:3]}

    # --- registo de ocorrências ---
    def registar(self, parcela, praga, nivel, notas=""):
        k = str(parcela).strip()
        praga = str(praga or "").strip()[:80]
        nivel = nivel if nivel in NIVEIS else "baixo"
        notas = str(notas or "").strip()[:200]
        if k not in self.culturas or not praga:
            return {"ok": False, "mensagem": "Indica a parcela e a praga."}
        for r in self._registos:
            if r["parcela"] == k and r["praga"] == praga and r["estado"] == "ativo":
                r["nivel"] = nivel
                self._guardar()
                return {"ok": True, "mensagem": f"Já havia esta ocorrência na parcela {k}. Nível atualizado para {nivel}."}
        self._registos.append({
            "id": self._proximo, "parcela": k, "cultura": self.culturas[k], "praga": praga, "nivel": nivel,
            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "notas": notas, "estado": "ativo",
        })
        self._proximo += 1
        self._guardar()
        return {"ok": True, "mensagem": f"Ocorrência registada na parcela {k}."}

    def tratar(self, id_registo):
        for r in self._registos:
            if r["id"] == id_registo and r["estado"] == "ativo":
                r["estado"] = "tratado"
                self._guardar()
                return {"ok": True, "mensagem": "Ocorrência marcada como tratada."}
        return {"ok": False, "mensagem": "Ocorrência não encontrada."}