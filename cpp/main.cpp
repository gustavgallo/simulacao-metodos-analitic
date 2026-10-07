#include <stdio.h>
#include <stdlib.h>
#include <fstream>
#include <sstream>
#include "sim.h"

#define EQ "========================================================="
#define STAR "*********************************************************"

struct Model {
    std::vector<Queue> queues;
    std::vector<std::pair<int, double>> first_arr;
    std::vector<double> rnd_list;
    std::vector<uint32_t> seeds;
    long per_seed = 100000;
};

static void die(const std::string &msg) {
    fprintf(stderr, "error: %s\n", msg.c_str());
    exit(1);
}

static std::string trim(const std::string &s) {
    size_t a = s.find_first_not_of(" \t\r\n");

    if (a == std::string::npos)
        return "";

    return s.substr(a, s.find_last_not_of(" \t\r\n") - a + 1);
}

static int find_queue(const Model &m, const std::string &name) {
    for (size_t i = 0; i < m.queues.size(); i++) {
        if (m.queues[i].name == name)
            return (int)i;
    }

    die("unknown queue " + name);
    return -1;
}

static Model read_model(const char *path) {
    std::ifstream f(path);

    if (!f)
        die("cannot open " + std::string(path));

    Model m;
    std::string line;
    std::string sec;
    int current_queue = -1;

    std::vector<std::pair<std::string, double>> arrivals;

    while (getline(f, line)) {
        line = trim(line);

        if (line.empty() || line[0] == '#')
            continue;

        if (line[0] == '[' && line.back() == ']') {
            sec = line.substr(1, line.size() - 2);
            current_queue = -1;
            continue;
        }

        std::stringstream ss(line);

        if (sec == "ARRIVALS") {
            std::string name;
            double time;

            ss >> name >> time;
            arrivals.push_back({name, time});
        }

        else if (sec == "QUEUES") {
            std::string key;
            ss >> key;

            if (key == "servers" ||
                key == "capacity" ||
                key == "minService" ||
                key == "maxService" ||
                key == "minArrival" ||
                key == "maxArrival") {

                if (current_queue < 0)
                    die("queue property without queue");

                Queue &q = m.queues[current_queue];

                if (key == "capacity") {
                    std::string value;
                    ss >> value;

                    if (value == "inf" || value == "infinite")
                        q.cap = -1;
                    else
                        q.cap = std::stoi(value);
                }

                else {
                    double value;
                    ss >> value;

                    if (key == "servers")
                        q.servers = (int)value;
                    else if (key == "minService")
                        q.min_srv = value;
                    else if (key == "maxService")
                        q.max_srv = value;
                    else if (key == "minArrival")
                        q.min_arr = value;
                    else if (key == "maxArrival")
                        q.max_arr = value;
                }
            }

            else {
                m.queues.push_back(Queue());
                m.queues.back().name = key;
                current_queue = (int)m.queues.size() - 1;
            }
        }

        else if (sec == "NETWORK") {
            std::string src;
            std::string dst;
            double p;

            ss >> src >> dst >> p;

            int src_id = find_queue(m, src);
            int dst_id = find_queue(m, dst);

            m.queues[src_id].routes.push_back({dst_id, p});
        }

        else if (sec == "RNDNUMBERS") {
            double value;
            ss >> value;
            m.rnd_list.push_back(value);
        }

        else if (sec == "RNDNUMBERSPERSEED") {
            ss >> m.per_seed;
        }

        else if (sec == "SEEDS") {
            uint32_t seed;
            ss >> seed;
            m.seeds.push_back(seed);
        }
    }

    for (auto &a : arrivals) {
        int id = find_queue(m, a.first);
        m.first_arr.push_back({id, a.second});
    }

    return m;
}

static void run(const Model &m,
                Rnd &r,
                std::vector<Queue> &acc,
                double &sum_t) {

    std::vector<Queue> qs = m.queues;

    sum_t += simulate(qs, m.first_arr, r);

    for (size_t i = 0; i < qs.size(); i++) {
        for (auto &s : qs[i].time_in)
            acc[i].time_in[s.first] += s.second;

        acc[i].lost += qs[i].lost;
    }
}

static void print_report(const std::vector<Queue> &qs,
                         double avg_t) {

    printf(EQ "\n======================    REPORT   ======================\n" EQ "\n");

    for (const Queue &q : qs) {
        printf(STAR "\nQueue:   %s (G/G/%d",
               q.name.c_str(),
               q.servers);

        if (q.cap >= 0)
            printf("/%d", q.cap);

        printf(")\n");

        if (q.max_arr > 0)
            printf("Arrival: %.1f ... %.1f\n",
                   q.min_arr,
                   q.max_arr);

        printf("Service: %.1f ... %.1f\n"
               STAR "\n",
               q.min_srv,
               q.max_srv);

        printf("   State               Time               Probability\n");

        double total = 0;

        for (auto &s : q.time_in)
            total += s.second;

        for (auto &s : q.time_in) {
            double probability = total > 0
                ? 100.0 * s.second / total
                : 0.0;

            printf("%7d%21.4f%21.2f%%\n",
                   s.first,
                   s.second,
                   probability);
        }

        printf("\nNumber of losses: %ld\n\n", q.lost);
    }

    printf(EQ "\nSimulation average time: %.4f\n" EQ "\n",
           avg_t);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("usage: %s model.txt\n", argv[0]);
        return 1;
    }

    Model m = read_model(argv[1]);

    std::vector<Queue> acc = m.queues;
    double sum_t = 0;

    int runs = m.seeds.empty()
        ? 1
        : (int)m.seeds.size();

    for (int i = 0; i < runs; i++) {
        Rnd r;

        if (m.seeds.empty()) {
            r.list = m.rnd_list;
            r.limit = (long)r.list.size();
        }

        else {
            r.seed = m.seeds[i];
            r.limit = m.per_seed;
        }

        run(m, r, acc, sum_t);
    }

    print_report(acc, sum_t / runs);

    return 0;
}