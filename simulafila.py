seed_inicial_padrao = 22132110088
A = 1664525
C = 1013904223
M = 4294967296.0  ## 2^32

LIMITE_ALEATORIOS = 100000


def simular(c_servidores, capacidade, seed_inicial):
    # -------- estado interno da simulacao (isolado por chamada) --------
    seed = seed_inicial
    numeros_usados = 0

    def uniform(a, b):
        nonlocal seed, numeros_usados
        seed = ((A * seed) + C) % M
        numeros_usados += 1 ## aumenta a quantidade de aleatorios gerados
        u = seed / M 
        return a + (b - a) * u ## manda normalizado pq sim

    relogio = 0.0                     # tempo atual da simulacao
    estado = 0                        # numero de clientes
    servidores = [float('inf')] * c_servidores  # tempo de saida de cada servidor (inf = livre)
    t_chegada = 3.0                   # primeiro cliente chega em t=3.0 (fixo, nao consome aleatorio)

    tempo_acumulado_estado = [0.0] * (capacidade + 1)  # tempo acumulado
    perdidos = 0                      # clientes perdidos por falta de capacidade


    while numeros_usados < LIMITE_ALEATORIOS:

        t_saida_min = min(servidores)          # menor tempo de saida
        if t_chegada <= t_saida_min: 
            tipo_evento = 'chegada'
            tempo_evento = t_chegada
        else:
            tipo_evento = 'saida'
            tempo_evento = t_saida_min
            idx_servidor = servidores.index(t_saida_min)

        # acumula o tempo
        tempo_acumulado_estado[estado] += (tempo_evento - relogio)
        relogio = tempo_evento

        if tipo_evento == 'chegada':
            if estado < capacidade:
                estado += 1
                livre = None
                for i in range(c_servidores):
                    if servidores[i] == float('inf'):
                        livre = i
                        break
                if livre is not None:
                    servidores[livre] = relogio + uniform(4, 5)  # agenda saida
            else:
                perdidos += 1  # sistema cheio -> cliente perdido

            # agenda a proxima chegada, mesmo se perder cliente
            if numeros_usados < LIMITE_ALEATORIOS:
                t_chegada = relogio + uniform(3, 5)
            else:
                t_chegada = float('inf')  # cabo

        else:  # tipo_evento == 'saida'
            estado -= 1
            servidores[idx_servidor] = float('inf')  # servidor fica livre

            if estado >= c_servidores:
                if numeros_usados < LIMITE_ALEATORIOS:
                    servidores[idx_servidor] = relogio + uniform(4, 5)

    tempo_total_simulacao = relogio
    return tempo_acumulado_estado, perdidos, tempo_total_simulacao, numeros_usados


def imprimir_resultado(nome_modelo, tempo_acumulado_estado, perdidos, tempo_total, numeros_usados):
    # imprime a distribuicao de probabilidades dos estados, perdas e tempo global
    print(f"\n===== {nome_modelo} =====")
    print(f"aleatorios consumidos : {numeros_usados}")
    print(f"tempo global simulacao: {tempo_total:.4f}")
    print(f"clientes perdidos     : {perdidos}")
    print("\nEstado | Tempo acumulado | Probabilidade")
    for i, tempo_estado in enumerate(tempo_acumulado_estado):
        prob = tempo_estado / tempo_total if tempo_total > 0 else 0.0
        print(f"  {i:2d}   |   {tempo_estado:12.4f}  |   {prob:.6f}")


# --- G/G/1/5: 1 servidor, capacidade 5 (fila + servidor) ---
tempos_1, perdidos_1, tempo_total_1, usados_1 = simular(
    c_servidores=1, capacidade=5, seed_inicial=seed_inicial_padrao
)
imprimir_resultado("G/G/1/5", tempos_1, perdidos_1, tempo_total_1, usados_1)

# --- G/G/2/5: 2 servidores, capacidade 5 (fila + servidores) ---
tempos_2, perdidos_2, tempo_total_2, usados_2 = simular(
    c_servidores=2, capacidade=5, seed_inicial=seed_inicial_padrao
)
imprimir_resultado("G/G/2/5", tempos_2, perdidos_2, tempo_total_2, usados_2)