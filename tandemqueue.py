"""Simulador de duas filas em tandem usando eventos discretos."""

import heapq
from collections import deque
from enum import IntEnum

SEED_INICIAL_PADRAO = 22132110088
A = 1664525
C = 1013904223
M = 4294967296.0
LIMITE_ALEATORIOS = 100000


class GeradorAleatorio:
    def __init__(self, seed_inicial: int = SEED_INICIAL_PADRAO):
        self.seed = seed_inicial
        self.numeros_usados = 0

    def uniform(self, a: float, b: float) -> float:
        self.seed = (A * self.seed + C) % M
        self.numeros_usados += 1
        return a + (b - a) * (self.seed / M)

    def limite_atingido(self) -> bool:
        return self.numeros_usados >= LIMITE_ALEATORIOS


class TipoEvento(IntEnum):
    SAIDA = 0
    PASSAGEM = 1
    CHEGADA = 2


class Event:
    __slots__ = ("tempo", "tipo", "id_cliente", "fila_id")

    def __init__(self, tempo: float, tipo: TipoEvento,
                 id_cliente: int, fila_id: int):
        self.tempo = tempo
        self.tipo = tipo
        self.id_cliente = id_cliente
        self.fila_id = fila_id

    def chave_ordenacao(self):
        return self.tempo, self.tipo, self.id_cliente

    def __repr__(self):
        return (f"Event(t={self.tempo:.4f}, tipo={self.tipo.name}, "
                f"cliente={self.id_cliente}, fila={self.fila_id})")


class Fila:
    def __init__(self, servidores: int, capacidade: int,
                 min_servico: float, max_servico: float,
                 gerador: GeradorAleatorio, nome: str = "Fila"):
        self.servidores = servidores
        self.capacidade = capacidade
        self.min_servico = min_servico
        self.max_servico = max_servico
        self.gerador = gerador
        self.nome = nome
        self.clientes = 0
        self.em_atendimento = 0
        self.c_perdidos = 0
        self.c_atendidos = 0
        self._espera_ids = deque()
        self.tempo_por_estado = {}
        self.ultimo_tempo_evento = 0.0
        self.iniciou_atendimento_imediato = False

    def gerar_tempo_servico(self) -> float:
        return self.gerador.uniform(self.min_servico, self.max_servico)

    def status(self) -> int:
        return self.clientes

    def capacity(self) -> int:
        return self.capacidade

    def loss(self) -> int:
        return self.c_perdidos

    def servidores_livres(self) -> int:
        return self.servidores - self.em_atendimento

    def cheia(self) -> bool:
        return self.capacidade != 0 and self.clientes >= self.capacidade

    def _acumula_tempo(self, tempo_atual: float):
        intervalo = tempo_atual - self.ultimo_tempo_evento
        if intervalo > 0:
            self.tempo_por_estado[self.clientes] = (
                self.tempo_por_estado.get(self.clientes, 0.0) + intervalo
            )
        self.ultimo_tempo_evento = tempo_atual

    def tentar_entrar(self, tempo_atual: float, id_cliente: int) -> bool:
        self._acumula_tempo(tempo_atual)
        if self.cheia():
            self.c_perdidos += 1
            self.iniciou_atendimento_imediato = False
            return False

        self.clientes += 1
        self.iniciou_atendimento_imediato = self.servidores_livres() > 0
        if self.iniciou_atendimento_imediato:
            self.em_atendimento += 1
        else:
            self._espera_ids.append(id_cliente)
        return True

    def iniciar_atendimento_se_possivel(self):
        if not self._espera_ids or self.servidores_livres() <= 0:
            return None
        self.em_atendimento += 1
        return self._espera_ids.popleft()

    def concluir_atendimento(self, tempo_atual: float):
        self._acumula_tempo(tempo_atual)
        self.em_atendimento -= 1
        self.clientes -= 1
        self.c_atendidos += 1

    def finalizar_estatisticas(self, tempo_final: float):
        self._acumula_tempo(tempo_final)

    def probabilidades_estado(self, tempo_total: float) -> dict:
        if tempo_total <= 0:
            return {}
        return {
            estado: tempo / tempo_total
            for estado, tempo in sorted(self.tempo_por_estado.items())
        }


class SimuladorTandem:
    def __init__(self, fila1: Fila, fila2: Fila, gerador: GeradorAleatorio,
                 min_chegada: float = 3.0, max_chegada: float = 5.0,
                 primeira_chegada: float = 3.0):
        self.fila1 = fila1
        self.fila2 = fila2
        self.gerador = gerador
        self.min_chegada = min_chegada
        self.max_chegada = max_chegada
        self.primeira_chegada = primeira_chegada
        self.eventos = []
        self.tempo_atual = 0.0
        self.proximo_id_cliente = 0
        self.total_chegaram = 0
        self.total_encaminhados_fila2 = 0
        self.total_concluidos_fila2 = 0
        self.log = []
        self._log_ativo = False

    def _agendar(self, evento: Event):
        heapq.heappush(self.eventos, (evento.chave_ordenacao(), evento))

    def _registrar(self, mensagem: str):
        if self._log_ativo:
            self.log.append(mensagem)

    def simular(self, log_ativo: bool = False):
        self._log_ativo = log_ativo
        self._agendar(Event(self.primeira_chegada, TipoEvento.CHEGADA,
                            self.proximo_id_cliente, fila_id=1))
        self.proximo_id_cliente += 1

        while self.eventos:
            if self.gerador.limite_atingido():
                self._registrar(
                    f"[FIM] Limite de {LIMITE_ALEATORIOS} numeros aleatorios atingido."
                )
                break

            _, evento = heapq.heappop(self.eventos)
            self.tempo_atual = evento.tempo
            if evento.tipo == TipoEvento.CHEGADA:
                self._trata_chegada(evento)
            elif evento.tipo == TipoEvento.SAIDA:
                self._trata_saida(evento)
            else:
                self._trata_passagem(evento)

        self.fila1.finalizar_estatisticas(self.tempo_atual)
        self.fila2.finalizar_estatisticas(self.tempo_atual)

    def _agendar_servico(self, fila: Fila, id_cliente: int, fila_id: int):
        tempo = self.tempo_atual + fila.gerar_tempo_servico()
        self._agendar(Event(tempo, TipoEvento.SAIDA, id_cliente, fila_id))

    def _trata_chegada(self, evento: Event):
        self.total_chegaram += 1
        entrou = self.fila1.tentar_entrar(self.tempo_atual, evento.id_cliente)
        if entrou:
            self._registrar(
                f"[{self.tempo_atual:.4f}] CHEGADA cliente {evento.id_cliente} "
                f"-> Fila1 (n={self.fila1.status()}, "
                f"atend={self.fila1.em_atendimento})"
            )
            if self.fila1.iniciou_atendimento_imediato:
                self._agendar_servico(self.fila1, evento.id_cliente, 1)
        else:
            self._registrar(
                f"[{self.tempo_atual:.4f}] CHEGADA cliente {evento.id_cliente} "
                f"-> Fila1 CHEIA, cliente perdido "
                f"(perdidos={self.fila1.c_perdidos})"
            )

        if not self.gerador.limite_atingido():
            intervalo = self.gerador.uniform(self.min_chegada, self.max_chegada)
            self._agendar(Event(self.tempo_atual + intervalo,
                                TipoEvento.CHEGADA,
                                self.proximo_id_cliente, fila_id=1))
            self.proximo_id_cliente += 1

    def _trata_saida(self, evento: Event):
        fila = self.fila1 if evento.fila_id == 1 else self.fila2
        fila.concluir_atendimento(self.tempo_atual)
        self._registrar(
            f"[{self.tempo_atual:.4f}] SAIDA cliente {evento.id_cliente} "
            f"<- Fila{evento.fila_id} (n={fila.status()}, "
            f"atend={fila.em_atendimento})"
        )
        id_proximo = fila.iniciar_atendimento_se_possivel()
        if id_proximo is not None:
            self._agendar_servico(fila, id_proximo, evento.fila_id)

        if evento.fila_id == 1:
            self._agendar(Event(self.tempo_atual, TipoEvento.PASSAGEM,
                                evento.id_cliente, fila_id=1))
        else:
            self.total_concluidos_fila2 += 1

    def _trata_passagem(self, evento: Event):
        self.total_encaminhados_fila2 += 1
        entrou = self.fila2.tentar_entrar(self.tempo_atual, evento.id_cliente)
        if entrou:
            self._registrar(
                f"[{self.tempo_atual:.4f}] PASSAGEM cliente {evento.id_cliente} "
                f"Fila1 -> Fila2 (n={self.fila2.status()}, "
                f"atend={self.fila2.em_atendimento})"
            )
            if self.fila2.iniciou_atendimento_imediato:
                self._agendar_servico(self.fila2, evento.id_cliente, 2)
        else:
            self._registrar(
                f"[{self.tempo_atual:.4f}] PASSAGEM cliente {evento.id_cliente} "
                f"Fila1 -> Fila2 CHEIA, cliente perdido na Fila2 "
                f"(perdidos={self.fila2.c_perdidos})"
            )

    def relatorio(self) -> str:
        linhas = [
            "=" * 60,
            "RELATORIO FINAL DA SIMULACAO",
            "=" * 60,
            f"Tempo final de simulacao: {self.tempo_atual:.4f}",
            f"Numeros aleatorios consumidos: {self.gerador.numeros_usados}",
            "",
            f"Clientes que chegaram ao sistema: {self.total_chegaram}",
            f"Clientes perdidos na Fila 1: {self.fila1.loss()}",
            f"Clientes encaminhados a Fila 2: {self.total_encaminhados_fila2}",
            f"Clientes perdidos na Fila 2: {self.fila2.loss()}",
            f"Clientes concluidos na Fila 2: {self.total_concluidos_fila2}",
            f"Clientes na Fila 1 ao fim: {self.fila1.status()}",
            f"Clientes na Fila 2 ao fim: {self.fila2.status()}",
            "",
        ]

        for nome, fila in (("Fila 1", self.fila1), ("Fila 2", self.fila2)):
            linhas.extend([
                f"--- {nome} ---",
                f"  Servidores: {fila.servidores} | Capacidade: {fila.capacidade}",
                f"  Clientes atendidos: {fila.c_atendidos}",
                f"  Clientes perdidos: {fila.loss()}",
                "  Tempo acumulado por estado:",
            ])
            linhas.extend(
                f"    n={estado}: {tempo:.4f}"
                for estado, tempo in sorted(fila.tempo_por_estado.items())
            )
            linhas.extend([
                "  Probabilidade de cada estado (n_clientes: P):",
            ])
            linhas.extend(
                f"    n={estado}: {probabilidade:.4f}"
                for estado, probabilidade in
                fila.probabilidades_estado(self.tempo_atual).items()
            )
            linhas.append("")
        return "\n".join(linhas)


if __name__ == "__main__":
    gerador = GeradorAleatorio()
    fila1 = Fila(2, 3, 4.0, 5.0, gerador, "Fila1")
    fila2 = Fila(1, 5, 1.0, 3.0, gerador, "Fila2")
    simulador = SimuladorTandem(fila1, fila2, gerador,
                                min_chegada=1.0, max_chegada=5.0, primeira_chegada=2.5)
    simulador.simular()
    print(simulador.relatorio())
