#pragma once
#include <stdint.h>
#include <map>
#include <string>
#include <vector>

#define NO_RND 1  // lancado quando acabam os numeros aleatorios

struct Queue {
    std::string name;
    int servers = 1, cap = -1;  // cap -1 = infinita
    double min_srv = 0, max_srv = 0;
    double min_arr = 0, max_arr = 0;  // max_arr > 0 => tem chegada externa
    std::vector<std::pair<int, double>> routes;  // (indice destino, probabilidade)

    int n = 0;  // clientes na fila
    long lost = 0;
    double last_t = 0;
    std::map<int, double> time_in;  // estado -> tempo acumulado
};

// Usa lista pronta se list nao estiver vazia, senao gera por LCG a partir de seed
struct Rnd {
    uint32_t seed = 0;
    std::vector<double> list;
    long used = 0, limit = 0;
};

// simula ate acabarem os aleatorios; devolve o tempo global final
double simulate(std::vector<Queue> &queues,
                const std::vector<std::pair<int, double>> &first_arr, Rnd &rnd);
