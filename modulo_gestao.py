# modulo_gestao.py - Módulo AgroGestão (equipa, escala, stocks e finanças)
# Não precisa de instalar nada. Guarda os dados em dados_gestao.json (na mesma pasta).
import datetime
import json
import os

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

TAREFAS = {
    "A": ["Manutenção e irrigação", "Inspeção dos sensores", "Limpeza e capinação", "Manutenção e irrigação"],
    "B": ["Controlo de pragas e adubação", "Capinação e adubação", "Inspeção fitossanitária", "Controlo de pragas e adubação"],
}


def _numero(valor):
    try:
        return float(str(valor).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


class ModuloGestao:
    def __init__(self, parcelas=("1", "2", "3"), ficheiro=None):
        self.parcelas = list(parcelas)
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_gestao.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            hoje = datetime.date.today().isoformat()
            self.d = {
                "funcionarios": [
                    {"id": 1, "nome": "António M.", "funcao": "Operador de irrigação", "equipa": "A", "diaria": 5000, "presencas": []},
                    {"id": 2, "nome": "Maria S.", "funcao": "Manutenção", "equipa": "A", "diaria": 5000, "presencas": []},
                    {"id": 3, "nome": "João P.", "funcao": "Técnico fitossanitário", "equipa": "B", "diaria": 6000, "presencas": []},
                    {"id": 4, "nome": "Luísa C.", "funcao": "Adubação", "equipa": "B", "diaria": 5500, "presencas": []},
                ],
                "stocks": [
                    {"id": 1, "nome": "Sementes de milho", "qtd": 120, "unidade": "kg", "minimo": 40, "passo": 10},
                    {"id": 2, "nome": "Sementes de feijão", "qtd": 35, "unidade": "kg", "minimo": 20, "passo": 5},
                    {"id": 3, "nome": "Fertilizante NPK", "qtd": 450, "unidade": "kg", "minimo": 200, "passo": 25},
                    {"id": 4, "nome": "Bio-pesticidas", "qtd": 6, "unidade": "L", "minimo": 20, "passo": 5},
                ],
                "movimentos": [
                    {"id": 1, "tipo": "custo", "descricao": "Fertilizante NPK", "valor": 450000, "data": hoje},
                    {"id": 2, "tipo": "receita", "descricao": "Venda de feijão (Rede Kifica)", "valor": 576000, "data": hoje},
                ],
                "prox": {"f": 5, "m": 3},
            }
            self._guardar()

        self.d.setdefault("tarefas", [])
        self.d.setdefault("previstos", [])
        self.d["prox"].setdefault("t", 1)
        self.d["prox"].setdefault("v", 1)

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    # --- consulta ---
    def _escala(self):
        hoje = datetime.date.today()
        saida = []
        for i in range(15):
            dia = hoje + datetime.timedelta(days=i)
            item = {"data": dia.strftime("%d/%m"), "dia": DIAS[dia.weekday()]}
            if dia.weekday() == 6:
                item["descanso"] = True
            else:
                item["A"] = f"{TAREFAS['A'][i % 4]} · Parcela {self.parcelas[i % len(self.parcelas)]}"
                item["B"] = f"{TAREFAS['B'][i % 4]} · Parcela {self.parcelas[(i + 1) % len(self.parcelas)]}"
            saida.append(item)
        return saida

    def dados(self):
        hoje = datetime.date.today()
        mes = hoje.strftime("%Y-%m")
        equipa = []
        mao_obra = 0
        for f in self.d["funcionarios"]:
            dias = len([p for p in f["presencas"] if p.startswith(mes)])
            a_pagar = dias * f["diaria"]
            mao_obra += a_pagar
            equipa.append({
                "id": f["id"], "nome": f["nome"], "funcao": f["funcao"], "equipa": f["equipa"],
                "diaria": f["diaria"], "dias_mes": dias, "a_pagar": a_pagar,
                "presente_hoje": hoje.isoformat() in f["presencas"],
            })
        stocks = []
        for s in self.d["stocks"]:
            stocks.append({
                "id": s["id"], "nome": s["nome"], "qtd": s["qtd"], "unidade": s["unidade"],
                "minimo": s["minimo"], "passo": s["passo"],
                "estado": "repor" if s["qtd"] <= s["minimo"] else "ok",
                "nivel": min(100, round(100 * s["qtd"] / (s["minimo"] * 4))) if s["minimo"] else 100,
            })
        do_mes = [m for m in self.d["movimentos"] if m["data"].startswith(mes)]
        custos = sum(m["valor"] for m in do_mes if m["tipo"] == "custo")
        receitas = sum(m["valor"] for m in do_mes if m["tipo"] == "receita")
        resultado = receitas - custos - mao_obra
        base = custos + mao_obra
        return {
            "funcionarios": equipa,
            "stocks": stocks,
            "escala": self._escala(),
            "tarefas": sorted([t for t in self.d["tarefas"] if t["estado"] == "pendente"], key=lambda t: t["id"], reverse=True),
            "previstos": sorted([v for v in self.d["previstos"] if v["estado"] == "pendente"], key=lambda v: v["id"], reverse=True),
            "financas": {
                "custos": custos, "receitas": receitas, "mao_obra": mao_obra, "resultado": resultado,
                "roi": round(100 * resultado / base) if base > 0 else None,
                "movimentos": sorted(do_mes, key=lambda m: m["id"], reverse=True)[:6],
            },
        }

    # --- ações ---
    def presenca(self, id_func):
        hoje = datetime.date.today().isoformat()
        for f in self.d["funcionarios"]:
            if f["id"] == id_func:
                if hoje in f["presencas"]:
                    f["presencas"].remove(hoje)
                    msg = f"Presença de hoje retirada: {f['nome']}"
                else:
                    f["presencas"].append(hoje)
                    msg = f"Presença de hoje registada: {f['nome']}"
                self._guardar()
                return {"ok": True, "mensagem": msg}
        return {"ok": False, "mensagem": "Funcionário não encontrado."}

    def adicionar_funcionario(self, nome, funcao, equipa, diaria):
        nome = str(nome or "").strip()[:40]
        funcao = str(funcao or "").strip()[:40]
        valor = _numero(diaria)
        if not nome or not funcao or equipa not in ("A", "B") or valor is None or not (0 < valor <= 1000000):
            return {"ok": False, "mensagem": "Preenche o nome, a função, a equipa e uma diária válida."}
        self.d["funcionarios"].append({
            "id": self.d["prox"]["f"], "nome": nome, "funcao": funcao, "equipa": equipa,
            "diaria": round(valor), "presencas": [],
        })
        self.d["prox"]["f"] += 1
        self._guardar()
        return {"ok": True, "mensagem": f"{nome} adicionado à equipa {equipa}."}

    def remover_funcionario(self, id_func):
        antes = len(self.d["funcionarios"])
        self.d["funcionarios"] = [f for f in self.d["funcionarios"] if f["id"] != id_func]
        if len(self.d["funcionarios"]) < antes:
            self._guardar()
            return {"ok": True, "mensagem": "Funcionário removido."}
        return {"ok": False, "mensagem": "Funcionário não encontrado."}

    def mover_stock(self, id_stock, delta):
        valor = _numero(delta)
        if valor is None:
            return {"ok": False, "mensagem": "Quantidade inválida."}
        for s in self.d["stocks"]:
            if s["id"] == id_stock:
                if s["qtd"] + valor < 0:
                    return {"ok": False, "mensagem": f"Não há {s['nome']} suficiente em stock."}
                s["qtd"] = round(s["qtd"] + valor, 2)
                self._guardar()
                aviso = " Abaixo do mínimo: repor." if s["qtd"] <= s["minimo"] else ""
                return {"ok": True, "mensagem": f"{s['nome']}: {s['qtd']:g} {s['unidade']}.{aviso}"}
        return {"ok": False, "mensagem": "Produto não encontrado."}

    def registar_movimento(self, tipo, descricao, valor):
        descricao = str(descricao or "").strip()[:60]
        v = _numero(valor)
        if tipo not in ("custo", "receita") or not descricao or v is None or not (0 < v <= 1000000000):
            return {"ok": False, "mensagem": "Preenche o tipo, a descrição e um valor válido."}
        self.d["movimentos"].append({
            "id": self.d["prox"]["m"], "tipo": tipo, "descricao": descricao, "valor": round(v),
            "data": datetime.date.today().isoformat(),
        })
        self.d["prox"]["m"] += 1
        self._guardar()
        return {"ok": True, "mensagem": "Custo registado." if tipo == "custo" else "Receita registada."}

    # --- tarefas e custos previstos (criados sobretudo pela Agro) ---
    def adicionar_tarefa(self, texto, equipa="A", origem="Agro"):
        texto = str(texto or "").strip()[:120]
        if not texto or equipa not in ("A", "B"):
            return {"ok": False, "mensagem": "Tarefa inválida."}
        for t in self.d["tarefas"]:
            if t["estado"] == "pendente" and t["texto"] == texto:
                return {"ok": True, "mensagem": "Esta tarefa já está na lista.", "duplicada": True}
        self.d["tarefas"].append({
            "id": self.d["prox"]["t"], "texto": texto, "equipa": equipa, "origem": str(origem)[:30],
            "data": datetime.date.today().isoformat(), "estado": "pendente",
        })
        self.d["prox"]["t"] += 1
        del self.d["tarefas"][:-200]
        self._guardar()
        return {"ok": True, "mensagem": "Tarefa adicionada à escala."}

    def concluir_tarefa(self, id_tarefa):
        for t in self.d["tarefas"]:
            if t["id"] == id_tarefa and t["estado"] == "pendente":
                t["estado"] = "concluida"
                self._guardar()
                return {"ok": True, "mensagem": "Tarefa concluída."}
        return {"ok": False, "mensagem": "Tarefa não encontrada."}

    def adicionar_previsto(self, descricao, valor, origem="Agro"):
        descricao = str(descricao or "").strip()[:80]
        v = _numero(valor)
        if not descricao or v is None or not (0 < v <= 1000000000):
            return {"ok": False, "mensagem": "Custo previsto inválido."}
        for p in self.d["previstos"]:
            if p["estado"] == "pendente" and p["descricao"] == descricao:
                return {"ok": True, "mensagem": "Este custo previsto já está registado.", "duplicado": True}
        self.d["previstos"].append({
            "id": self.d["prox"]["v"], "descricao": descricao, "valor": round(v), "origem": str(origem)[:30],
            "data": datetime.date.today().isoformat(), "estado": "pendente",
        })
        self.d["prox"]["v"] += 1
        del self.d["previstos"][:-200]
        self._guardar()
        return {"ok": True, "mensagem": "Custo previsto registado."}

    def confirmar_previsto(self, id_previsto):
        for p in self.d["previstos"]:
            if p["id"] == id_previsto and p["estado"] == "pendente":
                p["estado"] = "confirmado"
                self.registar_movimento("custo", p["descricao"], p["valor"])
                return {"ok": True, "mensagem": "Custo confirmado e lançado nas finanças."}
        return {"ok": False, "mensagem": "Custo previsto não encontrado."}

    def cancelar_previsto(self, id_previsto):
        for p in self.d["previstos"]:
            if p["id"] == id_previsto and p["estado"] == "pendente":
                p["estado"] = "cancelado"
                self._guardar()
                return {"ok": True, "mensagem": "Custo previsto cancelado."}
        return {"ok": False, "mensagem": "Custo previsto não encontrado."}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações do AgroGestão
        try:
            if acao == "presenca":
                return self.presenca(int(dados.get("id")))
            if acao == "funcionario":
                return self.adicionar_funcionario(dados.get("nome"), dados.get("funcao"), dados.get("equipa"), dados.get("diaria"))
            if acao == "remover":
                return self.remover_funcionario(int(dados.get("id")))
            if acao == "stock":
                return self.mover_stock(int(dados.get("id")), dados.get("delta"))
            if acao == "movimento":
                return self.registar_movimento(dados.get("tipo"), dados.get("descricao"), dados.get("valor"))
            if acao == "tarefa_concluir":
                return self.concluir_tarefa(int(dados.get("id")))
            if acao == "previsto_confirmar":
                return self.confirmar_previsto(int(dados.get("id")))
            if acao == "previsto_cancelar":
                return self.cancelar_previsto(int(dados.get("id")))
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}