# modulo_agro.py - Central da Agro (rotinas, alertas e integração entre módulos)
# A Agro vigia o campo, as pragas, os stocks e os preços e age sozinha segundo as rotinas ativas.
# Guarda as rotinas e o histórico em dados_agro.json (na mesma pasta).
import datetime
import json
import os

from modulo_mercado import _norm
from modulo_praga import PRAGAS

TIPOS = ("humidade_baixa", "stock_baixo", "praga_ativa", "preco_desatualizado", "produtividade_baixa")
ORDEM = {"alta": 0, "media": 1, "info": 2}


def _n(x):
    return f"{int(x):,}".replace(",", ".")


def _kz(n):
    return f"{int(round(n)):,}".replace(",", ".") + " Kz"


class ModuloAgro:
    def __init__(self, campo, praga, gestao, mercado, ficheiro=None):
        self.campo, self.praga, self.gestao, self.mercado = campo, praga, gestao, mercado
        self.clima = None  # ligado pelo servidor (ClimaSeguro)
        self.produtividade = None  # ligado pelo servidor (previsão de produtividade)
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_agro.json")
        self.d = {}
        self._estado = {}
        self._carregar()
        # Ao arrancar, o que já existe não gera avisos repetidos
        for r in self.d["regras"]:
            if r["ativa"]:
                self._estado[r["id"]] = set(self._condicoes(r))

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {
                "regras": [
                    {"id": 1, "tipo": "humidade_baixa", "ativa": True, "parcela": "todas", "limite": 60, "acao": "avisar", "custo_previsto": 0},
                    {"id": 2, "tipo": "stock_baixo", "ativa": True, "parcela": "todas", "limite": 0, "acao": "avisar", "custo_previsto": 0},
                    {"id": 3, "tipo": "praga_ativa", "ativa": True, "parcela": "todas", "limite": 0, "acao": "avisar", "custo_previsto": 20000},
                    {"id": 4, "tipo": "preco_desatualizado", "ativa": True, "parcela": "todas", "limite": 0, "acao": "avisar", "custo_previsto": 0},
                ],
                "notificacoes": [],
                "prox": {"r": 5, "n": 1},
            }
            self._guardar()

        if not any(r["tipo"] == "produtividade_baixa" for r in self.d["regras"]):
            self.d["regras"].append({"id": self.d["prox"]["r"], "tipo": "produtividade_baixa", "ativa": True, "parcela": "todas",
                                    "limite": 75, "acao": "avisar", "custo_previsto": 0})
            self.d["prox"]["r"] += 1
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    @staticmethod
    def descricao(r):
        if r["tipo"] == "humidade_baixa":
            onde = "todas as parcelas" if r["parcela"] == "todas" else f"a parcela {r['parcela']}"
            if r["acao"] == "ligar_rega":
                return f"Humidade abaixo de {r['limite']:g}% em {onde}: ligar a rega e criar tarefa de verificação"
            return f"Humidade abaixo de {r['limite']:g}% em {onde}: recomendar rega e criar tarefa na escala"
        if r["tipo"] == "stock_baixo":
            return "Stock abaixo do mínimo: avisar e sugerir onde comprar mais barato"
        if r["tipo"] == "praga_ativa":
            extra = f" e registar custo previsto de {_kz(r['custo_previsto'])}" if r["custo_previsto"] > 0 else ""
            return "Praga ativa (nível médio ou alto): recomendar tratamento, criar tarefa" + extra
        if r["tipo"] == "produtividade_baixa":
            onde = "todas as parcelas" if r["parcela"] == "todas" else f"a parcela {r['parcela']}"
            return f"Produtividade prevista abaixo de {r['limite']:g}% do esperado em {onde}: avisar e sugerir ajustar a venda"
        return "Preço com mais de 30 dias: avisar para atualizar a fonte"

    # --- condições de cada tipo de rotina ---
    def _condicoes(self, r):
        saida = {}
        if r["tipo"] == "humidade_baixa":
            for p in self.campo.dados()["parcelas"]:
                if r["parcela"] in ("todas", p["id"]) and p["humidade"] < r["limite"]:
                    saida[p["id"]] = p
        elif r["tipo"] == "stock_baixo":
            for s in self.gestao.dados()["stocks"]:
                if s["estado"] == "repor":
                    saida[str(s["id"])] = s
        elif r["tipo"] == "praga_ativa":
            for g in self.praga.dados()["registos"]:
                if g["estado"] == "ativo" and g["nivel"] in ("medio", "alto"):
                    saida[str(g["id"])] = g
        elif r["tipo"] == "produtividade_baixa" and self.produtividade:
            for p in self.produtividade.dados()["parcelas"]:
                if p["previsao"] and r["parcela"] in ("todas", p["id"]) and p["pct_condicoes"] < r["limite"]:
                    saida[p["id"]] = p
        elif r["tipo"] == "preco_desatualizado":
            for p in self.mercado.dados()["precos"]:
                if p["desatualizado"] and not p["exemplo"]:
                    saida[str(p["id"])] = p
        return saida

    def _notificar(self, nivel, texto, origem):
        n = self.d["prox"]["n"]
        self.d["prox"]["n"] += 1
        self.d["notificacoes"].append({
            "id": n, "hora": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
            "nivel": nivel, "texto": texto, "origem": origem,
        })
        del self.d["notificacoes"][:-50]

    def notificar_externo(self, nivel, texto, origem):
        # Usado por outros módulos (por exemplo o ClimaSeguro) para avisar através da Agro
        self._notificar(nivel, texto, origem)
        self._guardar()

    # --- ações automáticas quando uma condição aparece ---
    def _agir(self, r, item):
        tipo = r["tipo"]
        if tipo == "humidade_baixa":
            pid, cultura = item["id"], item["cultura"]
            texto = f"Parcela {pid} ({cultura}): humidade {item['humidade']:.0f}% abaixo de {r['limite']:g}%."
            if r["acao"] == "ligar_rega":
                if self.campo.irrigar(pid, True).get("ok"):
                    texto += " A Agro ligou a rega."
                self.gestao.adicionar_tarefa(f"Verificar a rega da parcela {pid} e confirmar a humidade", "A", "Agro")
            else:
                texto += " Rega recomendada."
                self.gestao.adicionar_tarefa(f"Regar a parcela {pid} ({cultura})", "A", "Agro")
            return "media", texto + " Tarefa adicionada à escala."
        if tipo == "stock_baixo":
            texto = f"Stock de {item['nome']} abaixo do mínimo ({item['qtd']:g} {item['unidade']})."
            for produto in self.mercado.dados()["produtos"]["insumo"]:
                if _norm(produto) == _norm(item["nome"]):
                    ops = self.mercado.melhor(produto, "insumo").get("opcoes", [])
                    if ops:
                        o = ops[0]
                        local = o["nome"] + (f" ({o['provincia']})" if o["provincia"] else "")
                        texto += (f" Melhor preço registado: {local} a {_kz(o['preco'])}, fonte {o['fonte']} de {o['data']}"
                                  + (" (exemplo)" if o["exemplo"] else "") + ".")
                    break
            return "media", texto
        if tipo == "praga_ativa":
            conhecida = next((p for p in PRAGAS if p["nome"] == item["praga"]), None)
            acao = conhecida["acoes"][0] if conhecida else "Inspecionar a parcela"
            texto = f"Praga na parcela {item['parcela']}: {item['praga']} (nível {item['nivel']}). Recomendação: {acao.rstrip('.')}."
            self.gestao.adicionar_tarefa(f"Parcela {item['parcela']}: {acao.rstrip('.')}", "B", "Agro")
            texto += " Tarefa adicionada à escala."
            if r["custo_previsto"] > 0:
                self.gestao.adicionar_previsto(f"Tratamento: {item['praga']} (parcela {item['parcela']})", r["custo_previsto"], "Agro")
                texto += f" Custo previsto de {_kz(r['custo_previsto'])} registado no AgroGestão."
            texto += " Se não for controlada, pode afetar a produtividade da parcela. Confirma com um técnico agrário."
            return ("alta" if item["nivel"] == "alto" else "media"), texto
        if tipo == "produtividade_baixa":
            texto = (f"Parcela {item['id']} ({item['cultura']}): produtividade prevista em {item['pct_condicoes']}% do esperado, "
                     f"cerca de {_n(item['kg_min'])} a {_n(item['kg_max'])} kg no total. "
                     f"Evita prometer volumes acima de {_n(item['kg_min'])} kg e revê os compromissos de venda.")
            for produto in self.mercado.dados()["produtos"]["venda"]:
                if _norm(produto) == _norm(item["cultura"]):
                    ops = self.mercado.melhor(produto, "venda").get("opcoes", [])
                    if ops:
                        o = ops[0]
                        local = o["nome"] + (f" ({o['provincia']})" if o["provincia"] else "")
                        texto += (f" Melhor mercado registado para {produto}: {local} a {_kz(o['liquido'])}/kg líquidos, fonte {o['fonte']} de {o['data']}"
                                  + (" (exemplo)" if o["exemplo"] else "") + ".")
                    break
            return "media", texto
        return "info", f"Preço de {item['produto']} ({item['local'] or 'mercado'}) com {item['idade_dias']} dias. Atualizar a fonte: {item['fonte']}."

    def avaliar(self):
        mudou = False
        for r in self.d["regras"]:
            if not r["ativa"]:
                continue
            try:
                atuais = self._condicoes(r)
                antigas = self._estado.get(r["id"], set())
                for chave, item in atuais.items():
                    if chave not in antigas:
                        nivel, texto = self._agir(r, item)
                        self._notificar(nivel, texto, self.descricao(r))
                        mudou = True
                self._estado[r["id"]] = set(atuais)
            except Exception:
                continue
        if mudou:
            self._guardar()

    # --- vista geral ---
    def _alertas(self, campo, praga, gestao, mercado):
        al = []
        for a in campo["alertas"]:
            al.append({"nivel": "media" if a["nivel"] == "aviso" else "info", "texto": a["texto"], "modulo": "AgroSinal"})
        for g in praga["registos"]:
            if g["estado"] == "ativo":
                nv = {"alto": "alta", "medio": "media"}.get(g["nivel"], "info")
                al.append({"nivel": nv, "texto": f"Praga ativa na parcela {g['parcela']}: {g['praga']} (nível {g['nivel']}).", "modulo": "PragaAlerta"})
        for s in gestao["stocks"]:
            if s["estado"] == "repor":
                al.append({"nivel": "media", "texto": f"Stock de {s['nome']} abaixo do mínimo ({s['qtd']:g} {s['unidade']}).", "modulo": "AgroGestão"})
        if gestao["tarefas"]:
            al.append({"nivel": "info", "texto": f"{len(gestao['tarefas'])} tarefa(s) criada(s) pela Agro à espera na escala.", "modulo": "AgroGestão"})
        if gestao["previstos"]:
            total = sum(v["valor"] for v in gestao["previstos"])
            al.append({"nivel": "info", "texto": f"Custos previstos por confirmar: {_kz(total)}.", "modulo": "AgroGestão"})
        velhos = [p for p in mercado["precos"] if p["desatualizado"] and not p["exemplo"]]
        if velhos:
            al.append({"nivel": "info", "texto": f"{len(velhos)} preço(s) com mais de {mercado['validade_dias']} dias.", "modulo": "FazendaDirecta"})
        if self.clima:
            al.extend(self.clima.alertas())
        al.sort(key=lambda a: ORDEM[a["nivel"]])
        return al

    def _saude(self, campo, praga, gestao):
        desc = []
        fora = [p for p in campo["parcelas"] if p["estado"] != "ideal"]
        if fora:
            desc.append({"motivo": f"{len(fora)} parcela(s) fora da humidade ideal", "pontos": 10 * len(fora)})
        for nv, pts in (("alto", 12), ("medio", 8), ("baixo", 4)):
            n = len([g for g in praga["registos"] if g["estado"] == "ativo" and g["nivel"] == nv])
            if n:
                desc.append({"motivo": f"{n} ocorrência(s) de praga de nível {nv}", "pontos": pts * n})
        repor = [s for s in gestao["stocks"] if s["estado"] == "repor"]
        if repor:
            desc.append({"motivo": f"{len(repor)} stock(s) abaixo do mínimo", "pontos": 6 * len(repor)})
        valor = max(0, 100 - sum(x["pontos"] for x in desc))
        return {"valor": valor, "faixa": "boa" if valor >= 80 else "atenção" if valor >= 50 else "crítica", "descontos": desc}

    def dados(self):
        self.avaliar()
        campo, praga, gestao, mercado = self.campo.dados(), self.praga.dados(), self.gestao.dados(), self.mercado.dados()
        fin = gestao["financas"]
        regras = []
        for r in self.d["regras"]:
            x = dict(r)
            x["descricao"] = self.descricao(r)
            regras.append(x)
        return {
            "kpis": {
                "humidade_media": campo["humidade_media"], "sensores": campo["sensores_ativos"],
                "pragas_ativas": praga["resumo"]["ativos"],
                "stocks_repor": len([s for s in gestao["stocks"] if s["estado"] == "repor"]),
                "resultado": fin["resultado"], "roi": fin["roi"], "tarefas_agro": len(gestao["tarefas"]),
            },
            "saude": self._saude(campo, praga, gestao),
            "alertas": self._alertas(campo, praga, gestao, mercado),
            "notificacoes": list(reversed(self.d["notificacoes"])),
            "regras": regras,
            "parcelas": [p["id"] for p in campo["parcelas"]],
        }

    # --- gestão das rotinas ---
    def adicionar_regra(self, tipo, parcela, limite, acao, custo_previsto):
        if tipo not in TIPOS:
            return {"ok": False, "mensagem": "Escolhe o tipo de rotina."}
        regra = {"id": self.d["prox"]["r"], "tipo": tipo, "ativa": True, "parcela": "todas", "limite": 0, "acao": "avisar", "custo_previsto": 0}
        if tipo in ("humidade_baixa", "produtividade_baixa"):
            if tipo == "produtividade_baixa":
                acao = "avisar"
            ids = [p["id"] for p in self.campo.dados()["parcelas"]]
            try:
                lim = float(str(limite).replace(",", "."))
            except ValueError:
                lim = -1
            if (parcela != "todas" and parcela not in ids) or not (10 <= lim <= (90 if tipo == "humidade_baixa" else 100)) or acao not in ("avisar", "ligar_rega"):
                return {"ok": False, "mensagem": "Indica a parcela, um limite entre 10 e 90 e a ação."}
            regra.update({"parcela": parcela, "limite": lim, "acao": acao})
        if tipo == "praga_ativa":
            try:
                custo = float(str(custo_previsto or 0).replace(",", "."))
            except ValueError:
                custo = -1
            if not (0 <= custo <= 100000000):
                return {"ok": False, "mensagem": "Custo previsto inválido."}
            regra["custo_previsto"] = round(custo)
        self.d["prox"]["r"] += 1
        self.d["regras"].append(regra)
        self._guardar()
        return {"ok": True, "mensagem": "Rotina criada. A Agro já está a vigiar."}

    def alternar(self, id_regra):
        for r in self.d["regras"]:
            if r["id"] == id_regra:
                r["ativa"] = not r["ativa"]
                self._estado[r["id"]] = set(self._condicoes(r)) if r["ativa"] else set()
                self._guardar()
                return {"ok": True, "mensagem": "Rotina ativada." if r["ativa"] else "Rotina em pausa."}
        return {"ok": False, "mensagem": "Rotina não encontrada."}

    def remover_regra(self, id_regra):
        antes = len(self.d["regras"])
        self.d["regras"] = [r for r in self.d["regras"] if r["id"] != id_regra]
        self._estado.pop(id_regra, None)
        if len(self.d["regras"]) < antes:
            self._guardar()
            return {"ok": True, "mensagem": "Rotina removida."}
        return {"ok": False, "mensagem": "Rotina não encontrada."}

    def limpar(self):
        self.d["notificacoes"] = []
        self._guardar()
        return {"ok": True, "mensagem": "Histórico limpo."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações da Central da Agro
        try:
            if acao == "regra":
                return self.adicionar_regra(dados.get("tipo"), str(dados.get("parcela") or "todas"), dados.get("limite"),
                                            dados.get("acao"), dados.get("custo_previsto"))
            if acao == "alternar":
                return self.alternar(int(dados.get("id")))
            if acao == "remover_regra":
                return self.remover_regra(int(dados.get("id")))
            if acao == "limpar":
                return self.limpar()
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}