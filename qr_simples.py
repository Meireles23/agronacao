# qr_simples.py - Gerador de QR Code em Python puro (sem instalar nada)
# Modo de bytes, correção de erros nível M, versões 1 a 10 (até 213 caracteres).
# Uso: qr_svg("http://192.168.1.10:8080/lote/ABC12345") devolve um desenho SVG pronto a mostrar ou imprimir.

# versão: (palavras de dados, palavras de correção por bloco, [(nº de blocos, palavras de dados por bloco), ...], posições de alinhamento)
_VERSOES = {
    1: (16, 10, [(1, 16)], []),
    2: (28, 16, [(1, 28)], [6, 18]),
    3: (44, 26, [(1, 44)], [6, 22]),
    4: (64, 18, [(2, 32)], [6, 26]),
    5: (86, 24, [(2, 43)], [6, 30]),
    6: (108, 16, [(4, 27)], [6, 34]),
    7: (124, 18, [(4, 31)], [6, 22, 38]),
    8: (154, 22, [(2, 38), (2, 39)], [6, 24, 42]),
    9: (182, 22, [(3, 36), (2, 37)], [6, 26, 46]),
    10: (216, 26, [(4, 43), (1, 44)], [6, 28, 50]),
}


def _multiplicar(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _divisor_rs(grau):
    r = [0] * (grau - 1) + [1]
    raiz = 1
    for _ in range(grau):
        for j in range(grau):
            r[j] = _multiplicar(r[j], raiz)
            if j + 1 < grau:
                r[j] ^= r[j + 1]
        raiz = _multiplicar(raiz, 2)
    return r


def _resto_rs(dados, divisor):
    r = [0] * len(divisor)
    for b in dados:
        fator = b ^ r.pop(0)
        r.append(0)
        for i, coef in enumerate(divisor):
            r[i] ^= _multiplicar(coef, fator)
    return r


def _bit(x, i):
    return (x >> i) & 1


def _penalidade(m):
    n = len(m)
    p = 0
    linhas = [list(l) for l in m] + [[m[r][c] for r in range(n)] for c in range(n)]
    for linha in linhas:
        corrida = 1
        for i in range(1, n):
            if linha[i] == linha[i - 1]:
                corrida += 1
                if corrida == 5:
                    p += 3
                elif corrida > 5:
                    p += 1
            else:
                corrida = 1
        padrao = "".join("1" if v else "0" for v in linha)
        for alvo in ("10111010000", "00001011101"):
            i = padrao.find(alvo)
            while i != -1:
                p += 40
                i = padrao.find(alvo, i + 1)
    for r in range(n - 1):
        for c in range(n - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                p += 3
    escuros = sum(1 for l in m for v in l if v)
    total = n * n
    p += 10 * ((abs(escuros * 20 - total * 10) + total - 1) // total - 1)
    return p


def gerar_matriz(texto):
    dados = texto.encode("utf-8")
    versao = None
    for v in sorted(_VERSOES):
        cap_bits = 8 * _VERSOES[v][0]
        if 4 + (8 if v < 10 else 16) + 8 * len(dados) <= cap_bits:
            versao = v
            break
    if versao is None:
        raise ValueError("Texto demasiado longo para este gerador de QR.")
    n_dados, n_ec, blocos_cfg, alinh = _VERSOES[versao]
    n = 17 + 4 * versao

    bits = "0100" + format(len(dados), "08b" if versao < 10 else "016b") + "".join(format(b, "08b") for b in dados)
    bits += "0" * min(4, 8 * n_dados - len(bits))
    bits += "0" * (-len(bits) % 8)
    palavras = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(palavras) < n_dados:
        palavras.append(pad)
        pad ^= 0xEC ^ 0x11

    blocos, pos = [], 0
    for qtd, tam in blocos_cfg:
        for _ in range(qtd):
            blocos.append(palavras[pos:pos + tam])
            pos += tam
    divisor = _divisor_rs(n_ec)
    ecs = [_resto_rs(b, divisor) for b in blocos]
    final = []
    for i in range(max(len(b) for b in blocos)):
        for b in blocos:
            if i < len(b):
                final.append(b[i])
    for i in range(n_ec):
        for e in ecs:
            final.append(e[i])
    fluxo = [(w >> (7 - k)) & 1 for w in final for k in range(8)]

    m = [[0] * n for _ in range(n)]
    fn = [[False] * n for _ in range(n)]

    def definir(x, y, v):
        if 0 <= x < n and 0 <= y < n:
            m[y][x] = 1 if v else 0
            fn[y][x] = True

    for i in range(n):
        definir(6, i, i % 2 == 0)
        definir(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                definir(cx + dx, cy + dy, max(abs(dx), abs(dy)) not in (2, 4))
    ultimo = len(alinh) - 1
    for i, ax in enumerate(alinh):
        for j, ay in enumerate(alinh):
            if (i == 0 and j == 0) or (i == 0 and j == ultimo) or (i == ultimo and j == 0):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    definir(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)

    def formato(mascara):
        dados_f = mascara  # nível M = 00
        r = dados_f
        for _ in range(10):
            r = (r << 1) ^ ((r >> 9) * 0x537)
        bits_f = ((dados_f << 10) | r) ^ 0x5412
        for i in range(6):
            definir(8, i, _bit(bits_f, i))
        definir(8, 7, _bit(bits_f, 6))
        definir(8, 8, _bit(bits_f, 7))
        definir(7, 8, _bit(bits_f, 8))
        for i in range(9, 15):
            definir(14 - i, 8, _bit(bits_f, i))
        for i in range(8):
            definir(n - 1 - i, 8, _bit(bits_f, i))
        for i in range(8, 15):
            definir(8, n - 15 + i, _bit(bits_f, i))
        definir(8, n - 8, True)

    formato(0)
    if versao >= 7:
        r = versao
        for _ in range(12):
            r = (r << 1) ^ ((r >> 11) * 0x1F25)
        bits_v = (versao << 12) | r
        for i in range(18):
            a, b = n - 11 + i % 3, i // 3
            definir(a, b, _bit(bits_v, i))
            definir(b, a, _bit(bits_v, i))

    i = 0
    for direita in range(n - 1, 0, -2):
        if direita == 6:
            direita = 5
        for vert in range(n):
            for j in range(2):
                x = direita - j
                subindo = ((direita + 1) & 2) == 0
                y = n - 1 - vert if subindo else vert
                if not fn[y][x] and i < len(fluxo):
                    m[y][x] = fluxo[i]
                    i += 1

    regras = (
        lambda r, c: (r + c) % 2 == 0, lambda r, c: r % 2 == 0, lambda r, c: c % 3 == 0,
        lambda r, c: (r + c) % 3 == 0, lambda r, c: (r // 2 + c // 3) % 2 == 0,
        lambda r, c: (r * c) % 2 + (r * c) % 3 == 0, lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
        lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
    )
    melhor, melhor_p = None, None
    for k, regra in enumerate(regras):
        for r in range(n):
            for c in range(n):
                if not fn[r][c] and regra(r, c):
                    m[r][c] ^= 1
        formato(k)
        p = _penalidade(m)
        if melhor_p is None or p < melhor_p:
            melhor_p, melhor = p, k
        for r in range(n):
            for c in range(n):
                if not fn[r][c] and regra(r, c):
                    m[r][c] ^= 1
    for r in range(n):
        for c in range(n):
            if not fn[r][c] and regras[melhor](r, c):
                m[r][c] ^= 1
    formato(melhor)
    return m


def qr_svg(texto, modulo=6, margem=4):
    m = gerar_matriz(texto)
    n = len(m)
    lado = n + 2 * margem
    partes = []
    for r in range(n):
        c = 0
        while c < n:
            if m[r][c]:
                inicio = c
                while c < n and m[r][c]:
                    c += 1
                partes.append(f"M{inicio + margem} {r + margem}h{c - inicio}v1h-{c - inicio}z")
            else:
                c += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}" width="{lado * modulo}" height="{lado * modulo}" shape-rendering="crispEdges">'
            f'<rect width="{lado}" height="{lado}" fill="#ffffff"/><path d="{" ".join(partes)}" fill="#000000"/></svg>')