# modulo_mercado.py - Módulo FazendaDirecta (preços, compradores e melhor mercado)
# Não precisa de instalar nada. Guarda os dados em dados_mercado.json (na mesma pasta).
# Regra do módulo: todo o preço tem FONTE e DATA. Preços com mais de 30 dias aparecem como desatualizados.
import csv
import datetime
import io
import json
import math
import os
import unicodedata

# Capitais de província (coordenadas aproximadas) - usadas só para estimar distâncias em linha reta
PROVINCIAS = {
    "Bengo": (-8.58, 13.66), "Benguela": (-12.58, 13.41), "Bié": (-12.38, 16.93),
    "Cabinda": (-5.55, 12.20), "Cuando Cubango": (-14.66, 17.69), "Cuanza Norte": (-9.30, 14.91),
    "Cuanza Sul": (-11.20, 13.84), "Cunene": (-17.07, 15.73), "Huambo": (-12.78, 15.74),
    "Huíla": (-14.92, 13.50), "Luanda": (-8.84, 13.23), "Lunda Norte": (-7.37, 20.83),
    "Lunda Sul": (-9.66, 20.39), "Malanje": (-9.54, 16.34), "Moxico": (-11.78, 19.92),
    "Namibe": (-15.20, 12.15), "Uíge": (-7.61, 15.06), "Zaire": (-6.27, 14.24),
}

DIAS_VALIDADE = 30


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto or "").lower().strip())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _numero(valor):
    t = str(valor if valor is not None else "").strip().replace(" ", "")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _distancia_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)))


def _provincia(texto):
    alvo = _norm(texto)
    for nome in PROVINCIAS:
        if _norm(nome) == alvo:
            return nome
    return ""


def _idade(data):
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(str(data)[:10])).days
    except ValueError:
        return 9999


class ModuloMercado:
    def __init__(self, ficheiro=None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro = ficheiro or os.path.join(base, "dados_mercado.json")
        self.d = {}
        self._carregar()

    # --- gravação simples em ficheiro ---
    def _carregar(self):
        try:
            with open(self.ficheiro, "r", encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            hoje = datetime.date.today().isoformat()
            ex = "Exemplo (demonstração)"

            def p(i, tipo, produto, preco, prov):
                return {"id": i, "tipo": tipo, "produto": produto, "preco": preco, "unidade": "kg",
                        "local": "Mercado (exemplo)", "provincia": prov, "fonte": ex, "data": hoje, "exemplo": True}

            self.d = {
                "config": {"provincia": "Luanda", "transp": 10},
                "precos": [
                    p(1, "venda", "Milho", 320, "Huambo"), p(2, "venda", "Milho", 380, "Luanda"),
                    p(3, "venda", "Feijão", 800, "Benguela"),
                    p(4, "insumo", "Fertilizante NPK", 1100, "Luanda"), p(5, "insumo", "Fertilizante NPK", 1250, "Huambo"),
                ],
                "propostas": [
                    {"id": 1, "comprador": "Rede Kifica", "produto": "Feijão", "preco": 850, "provincia": "Luanda",
                     "data": hoje, "exemplo": True},
                ],
                "prox": {"p": 6, "c": 2},
            }
            self._guardar()

    def _guardar(self):
        try:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    # --- consulta ---
    def _marcar(self, item):
        r = dict(item)
        r["idade_dias"] = _idade(item["data"])
        r["desatualizado"] = r["idade_dias"] > DIAS_VALIDADE
        r["exemplo"] = bool(item.get("exemplo"))
        return r

    @staticmethod
    def _unicos(nomes):
        vistos = {}
        for n in nomes:
            vistos.setdefault(_norm(n), n)
        return sorted(vistos.values(), key=_norm)

    def dados(self):
        precos = [self._marcar(p) for p in self.d["precos"]]
        propostas = [self._marcar(c) for c in self.d["propostas"]]
        return {
            "config": self.d["config"],
            "provincias": sorted(PROVINCIAS, key=_norm),
            "precos": sorted(precos, key=lambda x: x["id"], reverse=True),
            "propostas": sorted(propostas, key=lambda x: x["id"], reverse=True),
            "produtos": {
                "venda": self._unicos([p["produto"] for p in self.d["precos"] if p["tipo"] == "venda"] +
                                      [c["produto"] for c in self.d["propostas"]]),
                "insumo": self._unicos([p["produto"] for p in self.d["precos"] if p["tipo"] == "insumo"]),
            },
            "validade_dias": DIAS_VALIDADE,
        }

    def melhor(self, produto, tipo):
        tipo = tipo if tipo in ("venda", "insumo") else "venda"
        alvo = _norm(produto)
        if not alvo:
            return {"ok": False, "mensagem": "Escolhe um produto."}
        brutas = []
        for p in self.d["precos"]:
            if p["tipo"] == tipo and _norm(p["produto"]) == alvo:
                brutas.append((p["local"] or "Mercado", p["provincia"], p["preco"], p["unidade"],
                               p["fonte"], p["data"], bool(p.get("exemplo"))))
        if tipo == "venda":
            for c in self.d["propostas"]:
                if _norm(c["produto"]) == alvo:
                    brutas.append((c["comprador"], c["provincia"], c["preco"], "kg",
                                   "Proposta de comprador", c["data"], bool(c.get("exemplo"))))
        if not brutas:
            return {"ok": True, "produto": produto, "tipo": tipo, "opcoes": [],
                    "mensagem": "Ainda não há preços registados para este produto."}
        unidades = [b[3] for b in brutas]
        unidade = max(set(unidades), key=lambda u: (unidades.count(u), u == "kg"))
        cfg = self.d["config"]
        origem = PROVINCIAS.get(cfg["provincia"])
        opcoes = []
        for nome, prov, preco, uni, fonte, data, exemplo in brutas:
            if uni != unidade:
                continue
            dist = _distancia_km(origem, PROVINCIAS[prov]) if origem and prov in PROVINCIAS else None
            transp = round(cfg["transp"] * dist / 100, 1) if dist is not None else 0
            liquido = round(preco - transp if tipo == "venda" else preco + transp, 1)
            idade = _idade(data)
            opcoes.append({
                "nome": nome, "provincia": prov, "preco": preco, "dist_km": dist, "transporte": transp,
                "liquido": liquido, "fonte": fonte, "data": data, "idade_dias": idade,
                "desatualizado": idade > DIAS_VALIDADE, "exemplo": exemplo,
            })
        opcoes.sort(key=lambda o: o["liquido"], reverse=(tipo == "venda"))
        nota = ("Distâncias em linha reta entre capitais de província; o transporte real pode ser diferente. "
                "O custo de transporte por 100 km é uma estimativa tua.")
        if len(opcoes) < len(brutas):
            nota += f" Só são comparados preços em {unidade}."
        return {
            "ok": True, "produto": produto, "tipo": tipo, "unidade": unidade, "opcoes": opcoes[:5],
            "media": round(sum(o["preco"] for o in opcoes) / len(opcoes), 1),
            "origem": cfg["provincia"], "nota": nota,
        }

    # --- registo ---
    def _preco_valido(self, tipo, produto, preco, unidade, local, provincia, fonte, data):
        tipo = _norm(tipo) or "venda"
        produto = str(produto or "").strip()[:40]
        valor = _numero(preco)
        fonte = str(fonte or "").strip()[:60]
        if tipo not in ("venda", "insumo") or not produto or not fonte:
            return None
        if valor is None or not (0 < valor <= 100000000):
            return None
        try:
            dia = datetime.date.fromisoformat(str(data).strip()[:10])
        except ValueError:
            return None
        if dia > datetime.date.today():
            return None
        return {
            "tipo": tipo, "produto": produto, "preco": round(valor, 2),
            "unidade": (str(unidade or "kg").strip()[:10] or "kg"), "local": str(local or "").strip()[:50],
            "provincia": _provincia(provincia), "fonte": fonte, "data": dia.isoformat(),
        }

    def registar_preco(self, tipo, produto, preco, unidade, local, provincia, fonte, data):
        data = str(data or "").strip() or datetime.date.today().isoformat()
        r = self._preco_valido(tipo, produto, preco, unidade, local, provincia, fonte, data)
        if not r:
            return {"ok": False, "mensagem": "Preenche o produto, um preço válido, a fonte e uma data válida (AAAA-MM-DD)."}
        r["id"] = self.d["prox"]["p"]
        self.d["prox"]["p"] += 1
        self.d["precos"].append(r)
        self._guardar()
        return {"ok": True, "mensagem": "Preço registado com a fonte indicada."}

    def remover_preco(self, id_preco):
        antes = len(self.d["precos"])
        self.d["precos"] = [p for p in self.d["precos"] if p["id"] != id_preco]
        if len(self.d["precos"]) < antes:
            self._guardar()
            return {"ok": True, "mensagem": "Preço removido."}
        return {"ok": False, "mensagem": "Preço não encontrado."}

    def registar_proposta(self, comprador, produto, preco, provincia):
        comprador = str(comprador or "").strip()[:50]
        produto = str(produto or "").strip()[:40]
        valor = _numero(preco)
        if not comprador or not produto or valor is None or not (0 < valor <= 100000000):
            return {"ok": False, "mensagem": "Preenche o comprador, o produto e um preço válido."}
        self.d["propostas"].append({
            "id": self.d["prox"]["c"], "comprador": comprador, "produto": produto, "preco": round(valor, 2),
            "provincia": _provincia(provincia), "data": datetime.date.today().isoformat(),
        })
        self.d["prox"]["c"] += 1
        self._guardar()
        return {"ok": True, "mensagem": "Proposta registada."}

    def remover_proposta(self, id_proposta):
        antes = len(self.d["propostas"])
        self.d["propostas"] = [c for c in self.d["propostas"] if c["id"] != id_proposta]
        if len(self.d["propostas"]) < antes:
            self._guardar()
            return {"ok": True, "mensagem": "Proposta removida."}
        return {"ok": False, "mensagem": "Proposta não encontrada."}

    def configurar(self, provincia, transp):
        prov = _provincia(provincia)
        valor = _numero(transp)
        if not prov or valor is None or not (0 <= valor <= 1000):
            return {"ok": False, "mensagem": "Escolhe a província e um custo de transporte válido (0 a 1000)."}
        self.d["config"] = {"provincia": prov, "transp": valor}
        self._guardar()
        return {"ok": True, "mensagem": f"Exploração em {prov}, transporte {valor:g} Kz/kg por 100 km."}

    def remover_exemplos(self):
        self.d["precos"] = [p for p in self.d["precos"] if not p.get("exemplo")]
        self.d["propostas"] = [c for c in self.d["propostas"] if not c.get("exemplo")]
        self._guardar()
        return {"ok": True, "mensagem": "Dados de exemplo removidos."}

    def importar(self, texto):
        # Colunas: produto;preco;unidade;local;provincia;fonte;data;tipo (tipo e unidade são opcionais)
        texto = str(texto or "").strip()
        if not texto:
            return {"ok": False, "mensagem": "Cola primeiro a lista de preços."}
        delim = ";" if ";" in texto.splitlines()[0] else ","
        leitor = csv.DictReader(io.StringIO(texto), delimiter=delim)
        leitor.fieldnames = [_norm(h) for h in (leitor.fieldnames or [])]
        bons = falhas = 0
        for i, linha in enumerate(leitor):
            if i >= 500:
                break
            r = self._preco_valido(linha.get("tipo") or "venda", linha.get("produto"), linha.get("preco"),
                                   linha.get("unidade") or "kg", linha.get("local"), linha.get("provincia"),
                                   linha.get("fonte"), linha.get("data"))
            if r:
                r["id"] = self.d["prox"]["p"]
                self.d["prox"]["p"] += 1
                self.d["precos"].append(r)
                bons += 1
            else:
                falhas += 1
        self._guardar()
        if not bons:
            return {"ok": False, "mensagem": "Nenhuma linha válida. Cada linha precisa de produto, preço, fonte e data (AAAA-MM-DD)."}
        return {"ok": True, "mensagem": f"{bons} preço(s) importado(s)" + (f"; {falhas} linha(s) ignorada(s) por faltar fonte, data ou preço." if falhas else ".")}

    def executar(self, acao, dados):
        # Ponto único usado pelo servidor para as ações do FazendaDirecta
        try:
            if acao == "preco":
                return self.registar_preco(dados.get("tipo"), dados.get("produto"), dados.get("preco"), dados.get("unidade"),
                                           dados.get("local"), dados.get("provincia"), dados.get("fonte"), dados.get("data"))
            if acao == "remover_preco":
                return self.remover_preco(int(dados.get("id")))
            if acao == "proposta":
                return self.registar_proposta(dados.get("comprador"), dados.get("produto"), dados.get("preco"), dados.get("provincia"))
            if acao == "remover_proposta":
                return self.remover_proposta(int(dados.get("id")))
            if acao == "config":
                return self.configurar(dados.get("provincia"), dados.get("transp"))
            if acao == "importar":
                return self.importar(dados.get("texto"))
            if acao == "remover_exemplos":
                return self.remover_exemplos()
        except (TypeError, ValueError):
            pass
        return {"ok": False, "mensagem": "Pedido inválido."}