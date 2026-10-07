#include "sim.h"
#include <queue>

#define LCG_A 1664525u
#define LCG_C 1013904223u
#define LCG_M 4294967296.0

#define EV_OUT 0
#define EV_PASS 1
#define EV_ARR 2

struct Event {
    double t;
    int type, from, to;
    long seq;
};

static bool later(const Event &a, const Event &b) {
    if (a.t != b.t) return a.t > b.t;
    if (a.type != b.type) return a.type > b.type;
    return a.seq > b.seq;
}

static std::priority_queue<Event, std::vector<Event>, bool (*)(const Event &, const Event &)> agenda(later);
static std::vector<Queue> *qs;
static Rnd *rnd;
static double now;
static long seq;

static double rnd_next() {
    if (rnd->used >= rnd->limit)
        throw NO_RND;

    double v;

    if (rnd->list.empty()) {
        rnd->seed = LCG_A * rnd->seed + LCG_C;
        v = rnd->seed / LCG_M;
    } else {
        v = rnd->list[rnd->used];
    }

    rnd->used++;
    return v;
}

static double rnd_uniform(double a, double b) {
    return a + (b - a) * rnd_next();
}

static void queue_acc(Queue &q, double t) {
    if (t > q.last_t)
        q.time_in[q.n] += t - q.last_t;

    q.last_t = t;
}

static bool queue_enter(Queue &q, double t) {
    queue_acc(q, t);

    if (q.cap >= 0 && q.n >= q.cap) {
        q.lost++;
        return false;
    }

    q.n++;
    return q.n <= q.servers;
}

static bool queue_leave(Queue &q, double t) {
    queue_acc(q, t);
    q.n--;
    return q.n >= q.servers;
}

static void sched(double t, int type, int from, int to) {
    agenda.push({t, type, from, to, seq++});
}

static int pick_dest(Queue &q) {
    if (q.routes.empty())
        return -1;

    if (q.routes.size() == 1 && q.routes[0].second >= 1.0)
        return q.routes[0].first;

    double r = rnd_next();
    double acc = 0;

    for (auto &rt : q.routes) {
        acc += rt.second;

        if (r < acc)
            return rt.first;
    }

    return -1;
}

static void start_service(int i) {
    Queue &q = (*qs)[i];

    double dur = rnd_uniform(q.min_srv, q.max_srv);
    int to = pick_dest(q);

    sched(now + dur,
          to < 0 ? EV_OUT : EV_PASS,
          i,
          to);
}

static void enter(int i) {
    if (queue_enter((*qs)[i], now))
        start_service(i);
}

double simulate(std::vector<Queue> &queues,
                const std::vector<std::pair<int, double>> &first_arr,
                Rnd &r) {
    qs = &queues;
    rnd = &r;

    now = 0;
    seq = 0;

    while (!agenda.empty())
        agenda.pop();

    for (auto &a : first_arr)
        sched(a.second, EV_ARR, a.first, -1);

    try {
        while (!agenda.empty() && r.used < r.limit) {
            Event e = agenda.top();
            agenda.pop();

            now = e.t;

            Queue &q = queues[e.from];

            if (e.type == EV_ARR) {
                enter(e.from);

                sched(now + rnd_uniform(q.min_arr, q.max_arr),
                      EV_ARR,
                      e.from,
                      -1);
            } else {
                if (queue_leave(q, now))
                    start_service(e.from);

                if (e.type == EV_PASS)
                    enter(e.to);
            }
        }
    } catch (int) {
    }

    for (auto &q : queues)
        queue_acc(q, now);

    return now;
}