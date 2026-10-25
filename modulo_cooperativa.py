# modulo_cooperativa.py - Cooperativa / várias explorações (painel agregado)
# Cada produtor mantém os seus dados no seu computador. Para entrar no painel de uma cooperativa, gera um
# "pacote" com o que decide partilhar (e para quem, e até quando). A cooperativa importa o pacote e o painel soma tudo.
# O pacote NÃO inclui custos, receitas, funcionários, preços nem stocks.
# Guarda os pacotes importados em dados_cooperativa.json (na mesma pasta).
import datetime
import hashlib
import json
import os
import random

from modulo_mercado import _norm, PROVINCIAS
from modulo_produtividade import CULTURAS_BASE

MAX_MEMBROS = 200


def _texto(v, n):
    return str(v if v is not None else "").strip()[:n]


def _selo(pacote):
    base = {k: v for k, v in pacote.items() if k != "selo"}
    return hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16].upper()


class ModuloCooperativa:
    def __init__(self, campo, produtividade, agro, score, mercado, ficheiro=None):
        self.campo, self.produtividade, self.agro, self.score, self.mercado = campo, produtividade, agro, score, mercado
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_cooperativa.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {"config": {"nome": "Cooperativa (piloto)"}, "membros": [], "prox": 1}
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass

    # --- pacote desta exploração ---
    def _pacote_local(self, destinatario="", dias=30):
        hoje = datetime.date.today()
        parcelas = self.campo.dados()["parcelas"]
        previsoes = self.produtividade.dados()["parcelas"]
        culturas = {}
        for p in previsoes:
            c = culturas.setdefault(p["cultura"], {"cultura": p["cultura"], "area_ha": 0.0, "kg_min": 0, "kg_max": 0, "kg_estimado": 0, "confianca": "baixa"})
            c["area_ha"] = round(c["area_ha"] + p["area_ha"], 2)
            if p["previsao"]:
                c["kg_min"] += p["kg_min"]
                c["kg_max"] += p["kg_max"]
                c["kg_estimado"] += p["kg_total"]
                c["confianca"] = p["confianca"]
        al = self.agro.dados()["alertas"]
        sc = self.score.calcular()
        cfg = self.score.d["config"]
        pacote = {
            "versao": 1, "exploracao": cfg["nome"], "produtor": cfg["proprietario"],
            "provincia": self.mercado.d["config"]["provincia"], "gerado": hoje.isoformat(),
            "valido_ate": (hoje + datetime.timedelta(days=dias)).isoformat(), "destinatario": destinatario,
            "area_ha": round(sum(p["area_ha"] for p in parcelas), 2), "culturas": list(culturas.values()),
            "alertas": {"alta": len([a for a in al if a["nivel"] == "alta"]), "media": len([a for a in al if a["nivel"] == "media"])},
            "score": {"valor": sc["score"], "faixa": sc["faixa"], "confianca": sc["confianca"]["nivel"]},
            "demonstracao": not cfg["dados_reais"],
        }
        pacote["selo"] = _selo(pacote)
        return pacote

    def exportar(self, destinatario, dias):
        destinatario = _texto(destinatario, 60)
        try:
            n = int(float(str(dias).replace(",", ".")))
        except ValueError:
            n = 0
        if not destinatario or not (1 <= n <= 365):
            return {"ok": False, "mensagem": "Indica a cooperativa destinatária e uma validade entre 1 e 365 dias."}
        return {"ok": True, "texto": json.dumps(self._pacote_local(destinatario, n), ensure_ascii=False, indent=1)}

    # --- importação com verificação ---
    def _validar(self, texto):
        try:
            o = json.loads(texto)
        except (TypeError, ValueError):
            return None, "O texto não é um pacote válido da AgroNação."
        try:
            if o.get("versao") != 1 or not isinstance(o.get("culturas"), list) or len(o["culturas"]) > 20:
                return None, "Pacote com formato desconhecido."
            if str(o.get("selo", "")) != _selo(o):
                return None, "O selo não confere: o ficheiro foi alterado depois de gerado. Pacote recusado."
            datetime.date.fromisoformat(o["gerado"])
            valido = datetime.date.fromisoformat(o["valido_ate"])
            p = {
                "versao": 1, "exploracao": _texto(o["exploracao"], 60), "produtor": _texto(o.get("produtor"), 60),
                "provincia": _texto(o["provincia"], 30), "gerado": o["gerado"], "valido_ate": valido.isoformat(),
                "destinatario": _texto(o.get("destinatario"), 60), "area_ha": round(float(o["area_ha"]), 2),
                "culturas": [{"cultura": _texto(c["cultura"], 30), "area_ha": round(float(c["area_ha"]), 2), "kg_min": int(c["kg_min"]),
                              "kg_max": int(c["kg_max"]), "kg_estimado": int(c["kg_estimado"]), "confianca": _texto(c["confianca"], 10)} for c in o["culturas"]],
                "alertas": {"alta": int(o["alertas"]["alta"]), "media": int(o["alertas"]["media"])},
                "score": {"valor": None if o["score"]["valor"] is None else int(o["score"]["valor"]), "faixa": _texto(o["score"]["faixa"], 2),
                          "confianca": _texto(o["score"]["confianca"], 10)},
                "demonstracao": bool(o["demonstracao"]), "selo": o["selo"],
            }
        except (KeyError, TypeError, ValueError, AttributeError):
            return None, "Pacote incompleto ou com valores inválidos."
        if not p["exploracao"]:
            return None, "Pacote sem nome de exploração."
        if valido < datetime.date.today():
            return None, "A autorização deste pacote já expirou. Pede um pacote novo ao produtor."
        return p, ""

    def importar(self, texto):
        p, erro = self._validar(texto)
        if not p:
            return {"ok": False, "mensagem": erro}
        chave = (p["exploracao"], p["provincia"], p["produtor"])
        for m in self.d["membros"]:
            q = m["pacote"]
            if m["origem"] == "importado" and (q["exploracao"], q["provincia"], q["produtor"]) == chave:
                if p["gerado"] < q["gerado"]:
                    return {"ok": False, "mensagem": "Já existe um pacote mais recente desta exploração."}
                m["pacote"] = p
                self._guardar()
                return {"ok": True, "mensagem": f"Pacote de {p['exploracao']} atualizado."}
        if len(self.d["membros"]) >= MAX_MEMBROS:
            return {"ok": False, "mensagem": "Limite de membros atingido."}
        self.d["membros"].append({"id": self.d["prox"], "origem": "importado", "pacote": p})
        self.d["prox"] += 1
        self._guardar()
        return {"ok": True, "mensagem": f"{p['exploracao']} adicionada à cooperativa."}

    def gerar_demo(self):
        self.d["membros"] = [m for m in self.d["membros"] if m["origem"] != "demonstracao"]
        hoje = datetime.date.today()
        nomes = [("Huambo", "Milho"), ("Bié", "Feijão"), ("Malanje", "Mandioca"), ("Benguela", "Milho"), ("Uíge", "Mandioca"), ("Huíla", "Feijão")]
        for i, (prov, cultura) in enumerate(nomes, 1):
            area = round(random.uniform(2, 20), 1)
            kg = round(area * CULTURAS_BASE[cultura]["ref"] * random.uniform(0.55, 1.0))
            conf = random.choice(["baixa", "média"])
            marg = 0.3 if conf == "baixa" else 0.2
            pacote = {
                "versao": 1, "exploracao": f"Exploração demo {i}", "produtor": "", "provincia": prov, "gerado": hoje.isoformat(),
                "valido_ate": (hoje + datetime.timedelta(days=30)).isoformat(), "destinatario": self.d["config"]["nome"], "area_ha": area,
                "culturas": [{"cultura": cultura, "area_ha": area, "kg_min": round(kg * (1 - marg)), "kg_max": round(kg * (1 + marg)), "kg_estimado": kg, "confianca": conf}],
                "alertas": {"alta": random.choice([0, 0, 1]), "media": random.randint(0, 3)},
                "score": {"valor": random.randint(42, 86), "faixa": "-", "confianca": conf}, "demonstracao": True,
            }
            v = pacote["score"]["valor"]
            pacote["score"]["faixa"] = "A" if v >= 80 else "B" if v >= 65 else "C" if v >= 50 else "D"
            pacote["selo"] = _selo(pacote)
            self.d["membros"].append({"id": self.d["prox"], "origem": "demonstracao", "pacote": pacote})
            self.d["prox"] += 1
        self._guardar()
        return {"ok": True, "mensagem": "6 explorações de demonstração criadas (dados inventados, só para mostrar o painel)."}

    def remover(self, id_membro):
        antes = len(self.d["membros"])
        self.d["membros"] = [m for m in self.d["membros"] if m["id"] != id_membro]
        if len(self.d["membros"]) < antes:
            self._guardar()
            return {"ok": True, "mensagem": "Membro removido do painel."}
        return {"ok": False, "mensagem": "Membro não encontrado."}

    def remover_demo(self):
        self.d["membros"] = [m for m in self.d["membros"] if m["origem"] != "demonstracao"]
        self._guardar()
        return {"ok": True, "mensagem": "Demonstração removida."}

    def configurar(self, nome):
        nome = _texto(nome, 60)
        if not nome:
            return {"ok": False, "mensagem": "Indica o nome da cooperativa."}
        self.d["config"]["nome"] = nome
        self._guardar()
        return {"ok": True, "mensagem": "Nome guardado."}

    # --- painel ---
    def dados(self):
        hoje = datetime.date.today().isoformat()
        membros = [{"id": "local", "origem": "ao vivo", "pacote": self._pacote_local(self.d["config"]["nome"], 30)}] + self.d["membros"]
        lista, agr = [], {"culturas": {}, "provincias": {}}
        scores, area, alta, media, ativos = [], 0.0, 0, 0, 0
        for m in membros:
            p = m["pacote"]
            expirado = p["valido_ate"] < hoje
            kg_est = sum(c["kg_estimado"] for c in p["culturas"])
            lista.append({
                "id": m["id"], "origem": m["origem"], "exploracao": p["exploracao"], "produtor": p["produtor"], "provincia": p["provincia"],
                "area_ha": p["area_ha"], "culturas": ", ".join(c["cultura"] for c in p["culturas"]), "kg_estimado": kg_est,
                "kg_min": sum(c["kg_min"] for c in p["culturas"]), "kg_max": sum(c["kg_max"] for c in p["culturas"]),
                "score": p["score"]["valor"], "faixa": p["score"]["faixa"], "alertas_alta": p["alertas"]["alta"], "alertas_media": p["alertas"]["media"],
                "gerado": p["gerado"], "valido_ate": p["valido_ate"], "expirado": expirado, "demonstracao": p["demonstracao"], "selo": p["selo"],
            })
            if expirado:
                continue
            ativos += 1
            area += p["area_ha"]
            alta += p["alertas"]["alta"]
            media += p["alertas"]["media"]
            if p["score"]["valor"] is not None:
                scores.append(p["score"]["valor"])
            for c in p["culturas"]:
                a = agr["culturas"].setdefault(c["cultura"], {"cultura": c["cultura"], "area_ha": 0.0, "kg_min": 0, "kg_max": 0, "kg_estimado": 0})
                a["area_ha"] = round(a["area_ha"] + c["area_ha"], 2)
                for k in ("kg_min", "kg_max", "kg_estimado"):
                    a[k] += c[k]
            agr["provincias"][p["provincia"]] = agr["provincias"].get(p["provincia"], 0) + kg_est
        venda = []
        for c in agr["culturas"].values():
            item = dict(c, mercado=None)
            for produto in self.mercado.dados()["produtos"]["venda"]:
                if _norm(produto) == _norm(c["cultura"]):
                    ops = self.mercado.melhor(produto, "venda").get("opcoes", [])
                    if ops:
                        o = ops[0]
                        item["mercado"] = {"nome": o["nome"], "provincia": o["provincia"], "liquido": o["liquido"], "fonte": o["fonte"], "exemplo": o["exemplo"],
                                           "receita_min": round(c["kg_min"] * o["liquido"]), "receita_max": round(c["kg_max"] * o["liquido"])}
                    break
            venda.append(item)
        return {
            "config": self.d["config"], "membros": lista,
            "kpis": {"membros_ativos": ativos, "area_ha": round(area, 1), "alertas_alta": alta, "alertas_media": media,
                     "score_medio": round(sum(scores) / len(scores)) if scores else None,
                     "inclui_demo": any(x["demonstracao"] and not x["expirado"] for x in lista)},
            "culturas": sorted(venda, key=lambda x: -x["kg_estimado"]),
            "provincias": sorted(({"provincia": k, "kg": v} for k, v in agr["provincias"].items()), key=lambda x: -x["kg"]),
        }

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações da Cooperativa
        try:
            if acao == "importar":
                return self.importar(dados.get("texto"))
            if acao == "demo":
                return self.gerar_demo()
            if acao == "remover_demo":
                return self.remover_demo()
            if acao == "remover":
                return self.remover(int(dados.get("id")))
            if acao == "config":
                return self.configurar(dados.get("nome"))
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}