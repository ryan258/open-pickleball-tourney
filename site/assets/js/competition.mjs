// Format rules only. No DOM, persistence, random numbers, or external services.
export const FORMAT_OPTIONS = [
  ['round_robin', 'Round robin', 'Everyone plays every other entry once. Standings decide the finish.'],
  ['round_robin_playoff', 'Round robin → playoffs', 'Everyone meets once, then the top 2, 4 or 8 play a knockout bracket.'],
  ['pools', 'Pool play → playoffs', 'Snake-seeded groups play round robins. The top two from each pool qualify.'],
  ['single_elimination', 'Single elimination', 'One loss ends the championship run. High seeds receive any first-round byes.'],
  ['double_elimination', 'Double elimination', 'Two losses eliminate an entry. A reset final gives both finalists the same two-loss rule.'],
  ['rotating_partners', 'Rotating partners', 'Individuals change doubles partners. Court time is balanced and repeat partners are reduced.'],
  ['king_queen', 'King / queen of the court', 'Winners move up, losers move down, and partners split. Court 1 is the highest court.'],
];
export const formatType = t => t.competition?.type ?? 'round_robin';
export const socialFormat = t => ['rotating_partners', 'king_queen'].includes(formatType(t));
export const playoffFormat = t => ['round_robin_playoff', 'pools'].includes(formatType(t));
export const formatLabel = t => FORMAT_OPTIONS.find(([key]) => key === formatType(t))?.[1] ?? 'Unknown format';
const fail = message => { throw new Error(message); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const names = (t, side) => side?.map(id => t.teams.find(team => team.id === id)?.players.join(' & ')).join(' & ') || 'Bye';
export const sideName = (t, m, side) => m[side] === null ? m[`${side}Label`] || 'To be decided' : names(t, m[side]);
export const sideSignature = m => JSON.stringify([m.a, m.b]);
// Rotating partners only: is this person in the given round? windows[id] = [first, last | null].
export const present = (t, id, round) => { const w = t.windows?.[id]; return !w || (round >= w[0] && (w[1] === null || round <= w[1])); };

export function normalizeCompetition(value, t) {
  if (!object(value) || !FORMAT_OPTIONS.some(([key]) => key === value.type)) fail('Choose a supported tournament format.');
  const c = { type: value.type, pools: value.pools ?? 2, advance: value.advance ?? 4, rounds: value.rounds ?? 6, bronze: value.bronze ?? false };
  if (![2, 4].includes(c.pools)) fail('Choose 2 or 4 pools.');
  if (![2, 4, 8].includes(c.advance)) fail('Choose a top 2, 4 or 8 playoff.');
  if (!Number.isInteger(c.rounds) || c.rounds < 1 || c.rounds > 30) fail('Choose 1–30 social rounds.');
  if (typeof c.bronze !== 'boolean') fail('The bronze-game setting is invalid.');
  if (['rotating_partners', 'king_queen'].includes(c.type) && t.mode !== 'singles') fail('Social formats take individual players. Choose individual players before adding the roster.');
  if (t.scheduled) {
    if (t.teams.length < 2) fail('Add at least two entries.');
    if (c.type === 'round_robin_playoff' && t.teams.length < c.advance) fail(`Add at least ${c.advance} entries or choose a smaller playoff.`);
    if (c.type === 'pools' && t.teams.length < c.pools * 2) fail(`Add at least ${c.pools * 2} entries for ${c.pools} pools.`);
    if (c.type === 'rotating_partners' && t.teams.length < 4) fail('Rotating partners needs at least four individuals.');
    if (c.type === 'king_queen' && t.teams.length !== t.courts * 4) fail('King / queen needs exactly four individuals per court (4, 8, 12 or 16 players).');
    if (c.type === 'king_queen' && t.withdrawn.length) fail('The court ladder needs a full roster. Download a copy, then reset the schedule to change the players.');
  }
  return c;
}

export function poolsFor(t) {
  const pools = Array.from({ length: t.competition.pools }, (_, i) => ({ key: `pool-${i + 1}`, name: `Pool ${String.fromCharCode(65 + i)}`, teams: [] }));
  t.teams.forEach((team, i) => {
    const block = Math.floor(i / pools.length), slot = i % pools.length;
    pools[block % 2 ? pools.length - 1 - slot : slot].teams.push(team);
  });
  return pools;
}

export function rankedRows(t, matches, teams = t.teams, averages = false) {
  const rows = teams.map(team => ({ id: team.id, name: team.players.join(' & '), played: 0, wins: 0, losses: 0, for: 0, against: 0, difference: 0, rank: null, walkovers: 0, withdrawn: (t.withdrawn ?? []).includes(team.id) }));
  const byId = new Map(rows.map(row => [row.id, row]));
  for (const m of matches) {
    if (!['scored', 'walkover'].includes(m.status) || !m.winner?.length) continue;
    for (const [index, side] of [m.a, m.b].entries()) for (const id of side) {
      const row = byId.get(id); if (!row) continue;
      row.played += 1;
      if (m.winner.includes(id)) row.wins += 1; else row.losses += 1;
      if (m.score) { row.for += m.score[index]; row.against += m.score[1 - index]; }
      else row.walkovers += 1;
    }
  }
  rows.forEach(row => { row.difference = row.for - row.against; });
  const compare = (a, b) => averages
    ? b.wins / (b.played || 1) - a.wins / (a.played || 1) || b.difference / (b.played || 1) - a.difference / (a.played || 1) || b.for / (b.played || 1) - a.for / (a.played || 1)
    : b.wins - a.wins || b.difference - a.difference || b.for - a.for;
  rows.sort((a, b) => a.withdrawn - b.withdrawn || compare(a, b));
  rows.forEach((row, i) => { row.rank = row.withdrawn ? null : i && compare(row, rows[i - 1]) === 0 ? rows[i - 1].rank : i + 1; });
  return rows;
}

// Standard high-seed byes: 1–8, 4–5, 2–7, 3–6 in an eight-slot bracket.
function seedSlots(seeds) {
  let order = [1, 2];
  while (order.length < seeds.length) { const size = order.length * 2 + 1; order = order.flatMap(seed => [seed, size - seed]); }
  return order.map(seed => seeds[seed - 1] ? [seeds[seed - 1]] : []);
}

export function buildCompetition(t, roundRobin) {
  const type = formatType(t), matches = [], byId = new Map(), places = Object.create(null), groups = [];
  let nextGroup = 1, champion = [], finished = false, needsAdvancement = false, advancementValid = true;
  const out = new Set(t.withdrawn ?? []), extended = type !== 'round_robin';
  const qualified = Object.keys(t.advancement ?? {}).length > 0;
  const preliminaryOut = qualified ? new Set(t.qualifyingWithdrawn ?? []) : out;
  const resolve = ref => Array.isArray(ref) ? ref : ref ? byId.get(ref.from)?.[ref.take] ?? null : null;
  const ref = (m, take = 'winner') => ({ from: m.id, take, label: `${take === 'winner' ? 'Winner' : 'Loser'} of ${m.label}` });
  const add = input => {
    const a = resolve(input.a), b = resolve(input.b);
    const withdrawn = input.preliminary ? preliminaryOut : out;
    const m = { ...input, a, b, aLabel: input.a?.label, bLabel: input.b?.label, winner: null, loser: null, status: 'blocked', score: null };
    const score = t.scores[m.id];
    if (a !== null && b !== null) {
      if (!a.length || !b.length) {
        m.status = 'bye'; m.winner = a.length ? a : b; m.loser = [];
        if (m.winner.some(id => withdrawn.has(id))) m.winner = [];
      } else if (score && (!extended || t.scoreSides?.[m.id] === sideSignature(m))) {
        m.score = score; m.status = 'scored';
        [m.winner, m.loser] = score[0] > score[1] ? [a, b] : [b, a];
      } else if (a.some(id => withdrawn.has(id)) || b.some(id => withdrawn.has(id))) {
        m.status = 'walkover';
        m.winner = a.some(id => withdrawn.has(id)) ? b.some(id => withdrawn.has(id)) ? [] : b : a;
        m.loser = m.winner.length ? m.winner === a ? b : a : [];
      } else m.status = 'ready';
    }
    m.done = ['scored', 'walkover', 'bye'].includes(m.status);
    matches.push(m); byId.set(m.id, m); return m;
  };
  const stage = (label, pairs, prefix, extra = {}) => {
    const start = nextGroup;
    nextGroup += Math.ceil(pairs.length / t.courts);
    return pairs.map(([a, b], i) => add({ id: `${prefix}-${i + 1}`, label: `${label} · game ${i + 1}`, stage: label, group: start + Math.floor(i / t.courts), round: start, court: i % t.courts + 1, a, b, ...extra }));
  };
  const rr = (teams, prefix, pool = '') => {
    const start = nextGroup - 1;
    const schedule = roundRobin(teams, t.courts);
    const result = schedule.map(m => add({ ...m, id: `${prefix}${m.id}`, a: [m.a], b: [m.b], label: `${pool || 'Round robin'} · game ${m.id.slice(1)}`, stage: pool || 'Round robin', group: m.group + start, preliminary: true, pool }));
    nextGroup += Math.max(...schedule.map(m => m.group));
    return result;
  };
  const bracket = (seeds, double = false) => {
    const slots = seedSlots(seeds), depth = Math.log2(slots.length);
    let upper = [], lower = [], upperFinal, semi = [], remaining = seeds.length;
    for (let round = 1; round <= depth; round++) {
      const sources = round === 1 ? slots : upper.map(m => ref(m));
      upper = stage(`${double ? 'Upper' : 'Playoff'} round ${round}`, Array.from({ length: sources.length / 2 }, (_, i) => sources.slice(i * 2, i * 2 + 2)), `e-w${round}`);
      if (upper.length === 2) semi = upper;
      upperFinal = upper[0];
      if (!double) {
        for (const m of upper) if (m.done) for (const id of m.loser || []) places[id] = upper.length + 1;
        continue;
      }
      if (depth === 1) continue;
      if (round === 1) {
        const losers = upper.map(m => ref(m, 'loser'));
        lower = stage('Lower round 1', Array.from({ length: losers.length / 2 }, (_, i) => losers.slice(i * 2, i * 2 + 2)), 'e-l1');
      } else {
        const pairs = lower.map((m, i) => [ref(m), ref(upper[upper.length > 1 ? i ^ 1 : i], 'loser')]);
        lower = stage(`Lower round ${round * 2 - 2}`, pairs, `e-l${round * 2 - 2}`);
      }
      const placeLosers = wave => {
        const losers = wave.filter(m => m.done).flatMap(m => m.loser || []);
        remaining -= losers.length;
        for (const id of losers) places[id] = remaining + 1;
      };
      placeLosers(lower);
      if (round > 1 && round < depth) {
        const winners = lower.map(m => ref(m));
        lower = stage(`Lower round ${round * 2 - 1}`, Array.from({ length: winners.length / 2 }, (_, i) => winners.slice(i * 2, i * 2 + 2)), `e-l${round * 2 - 1}`);
        placeLosers(lower);
      }
    }
    let last = upperFinal;
    if (double) {
      const lowerWinner = depth === 1 ? ref(upperFinal, 'loser') : ref(lower[0]);
      const [grand] = stage('Championship final', [[ref(upperFinal), lowerWinner]], 'e-final');
      last = grand;
      if (grand.status === 'scored' && equal(grand.winner, grand.b)) [last] = stage('Reset final', [[grand.a, grand.b]], 'e-reset');
      // A withdrawal ends participation; it must not produce an endless reset.
    } else if (t.competition?.bronze && semi.length === 2) {
      const [bronze] = stage('Bronze game', [[ref(semi[0], 'loser'), ref(semi[1], 'loser')]], 'e-bronze');
      if (bronze.done) { for (const id of bronze.winner || []) places[id] = 3; for (const id of bronze.loser || []) places[id] = 4; }
    }
    if (last.done) { champion = last.winner; for (const id of last.winner) places[id] = 1; for (const id of last.loser) places[id] = 2; }
    finished = matches.every(m => m.done);
  };

  if (!t.scheduled) return { matches, groups, places, champion, finished, needsAdvancement, advancementValid, invalidScores: Object.keys(t.scores), current: [] };
  if (type === 'round_robin') { rr(t.teams, ''); finished = matches.every(m => m.done); }
  if (['single_elimination', 'double_elimination'].includes(type)) bracket(t.teams.map(team => team.id), type === 'double_elimination');
  if (playoffFormat(t)) {
    const pools = type === 'pools' ? poolsFor(t) : [{ key: 'all', name: 'Round robin', teams: t.teams }];
    for (const pool of pools) {
      const games = rr(pool.teams, `${pool.key}-`, pool.name);
      groups.push({ ...pool, rows: rankedRows({ ...t, withdrawn: [...preliminaryOut] }, games, pool.teams), matches: games });
    }
    const preliminaryDone = matches.every(m => m.done), selection = t.advancement ?? {};
    advancementValid = Object.keys(selection).length === 0 || (preliminaryDone && Object.keys(selection).length === groups.length && groups.every(group => {
      const eligible = group.rows.filter(row => !row.withdrawn), order = selection[group.key];
      if (!Array.isArray(order) || order.length !== eligible.length || new Set(order).size !== order.length || order.some(id => !eligible.some(row => row.id === id))) return false;
      return order.every((id, i) => !i || eligible.find(row => row.id === order[i - 1]).rank <= eligible.find(row => row.id === id).rank);
    }));
    if (preliminaryDone && (!Object.keys(selection).length || !advancementValid)) needsAdvancement = true;
    else if (preliminaryDone) {
      let seeds;
      if (type === 'round_robin_playoff') seeds = selection.all.slice(0, t.competition.advance);
      else {
        // For 2 pools: A1 v B2, B1 v A2. For 4: A1 v B2, C1 v D2,
        // B1 v A2, D1 v C2. Same-pool qualifiers occupy opposite halves.
        const orders = groups.map(group => selection[group.key]);
        const pairs = orders.map((order, i) => [order[0], orders[i ^ 1][1]]);
        const arranged = orders.length === 4 ? [pairs[0], pairs[2], pairs[1], pairs[3]] : pairs;
        // Invert seedSlots so the displayed pair order is preserved, including byes.
        const positions = seedSlots(Array.from({ length: arranged.length * 2 }, (_, i) => String(i + 1))).flat().map(Number);
        seeds = Array(arranged.length * 2).fill(null);
        arranged.flat().forEach((id, i) => { seeds[positions[i] - 1] = id ?? null; });
      }
      bracket(seeds);
    }
  }
  if (type === 'rotating_partners') {
    const appearances = new Map(t.teams.map(team => [team.id, 0])), partners = new Map(), opponents = new Map();
    const pairKey = (a, b) => [a, b].sort().join('|');
    const cost = (map, a, b) => map.get(pairKey(a, b)) || 0;
    const note = (map, a, b) => map.set(pairKey(a, b), cost(map, a, b) + 1);
    // Late arrivals and early leavers: t.windows[id] = [first round, last round | null].
    // A round is built only from the people present in it, so rounds before a
    // change keep their exact pairings and saved scores stay valid.
    const seen = new Set();
    for (let round = 1; round <= t.competition.rounds; round++) {
      const live = t.teams.filter(team => present(t, team.id, round));
      const count = Math.min(t.courts, Math.floor(live.length / 4));
      // A newcomer starts level with the least-played person, not owed every missed game.
      const veterans = live.filter(team => seen.has(team.id)), least = veterans.length ? Math.min(...veterans.map(team => appearances.get(team.id))) : 0;
      for (const team of live) { if (!seen.has(team.id) && round > 1) appearances.set(team.id, least); seen.add(team.id); }
      const candidates = live.map((team, i) => ({ id: team.id, order: (i + live.length - (round - 1) % live.length) % live.length }));
      candidates.sort((a, b) => appearances.get(a.id) - appearances.get(b.id) || a.order - b.order);
      const selected = candidates.slice(0, count * 4).map(row => row.id), pairs = [];
      for (const id of selected) appearances.set(id, appearances.get(id) + 1);
      while (selected.length) {
        const a = selected.shift();
        selected.sort((b, c) => cost(partners, a, b) - cost(partners, a, c));
        const b = selected.shift(); pairs.push([a, b]); note(partners, a, b);
      }
      const games = [];
      while (pairs.length) {
        const a = pairs.shift(), opposition = b => a.reduce((sum, x) => sum + b.reduce((n, y) => n + cost(opponents, x, y), 0), 0);
        pairs.sort((b, c) => opposition(b) - opposition(c));
        const b = pairs.shift(); games.push([a, b]);
        for (const x of a) for (const y of b) note(opponents, x, y);
      }
      stage(`Mixer round ${round}`, games, `mix${round}`, { socialRound: round });
    }
    finished = matches.every(m => m.done);
  }
  if (type === 'king_queen') {
    let courts = Array.from({ length: t.courts }, (_, i) => t.teams.slice(i * 4, i * 4 + 4).map(team => team.id));
    for (let round = 1; round <= t.competition.rounds; round++) {
      const wave = stage(`Ladder round ${round}`, courts.map(ids => [ids.slice(0, 2), ids.slice(2)]), `kq${round}`, { socialRound: round });
      if (!wave.every(m => m.done)) break;
      if (round === t.competition.rounds) {
        finished = true;
        for (const m of wave) { for (const id of m.winner) places[id] = (m.court - 1) * 4 + 1; for (const id of m.loser) places[id] = (m.court - 1) * 4 + 3; }
        champion = wave[0].winner; break;
      }
      const arrivals = Array.from({ length: t.courts }, () => []);
      wave.forEach((m, i) => { arrivals[Math.max(0, i - 1)].push(m.winner); arrivals[Math.min(t.courts - 1, i + 1)].push(m.loser); });
      courts = arrivals.map(([a, b]) => [a[0], b[0], a[1], b[1]]);
    }
  }
  const invalidScores = Object.keys(t.scores).filter(id => byId.get(id)?.status !== 'scored');
  const first = matches.find(m => m.status === 'ready');
  const current = first ? matches.filter(m => m.group === first.group && ['ready', 'scored'].includes(m.status)) : [];
  return { matches, groups, places, champion, finished, needsAdvancement, advancementValid, invalidScores, current };
}

export function formatStandings(t, state) {
  const type = formatType(t), rows = rankedRows(t, state.matches, t.teams, type === 'rotating_partners');
  if (!['round_robin', 'rotating_partners'].includes(type)) {
    rows.forEach(row => { row.rank = row.withdrawn || !state.finished ? null : state.places[row.id] ?? null; });
    rows.sort((a, b) => a.withdrawn - b.withdrawn || (a.rank ?? Infinity) - (b.rank ?? Infinity));
  }
  return rows;
}

export function formatSummary(t) {
  const n = t.teams.length, c = t.competition, type = formatType(t), bronze = c?.bronze && (type === 'single_elimination' ? n > 2 : type === 'pools' || c.advance > 2) ? 1 : 0;
  if (type === 'round_robin') return `${n * (n - 1) / 2} games; ${Math.max(0, n - 1)} per entry.`;
  if (type === 'single_elimination') return `Up to ${Math.max(0, n - 1) + bronze} games, including ${bronze ? 'a bronze game' : 'the final'}.`;
  if (type === 'double_elimination') return `${Math.max(0, 2 * n - 2)}–${Math.max(0, 2 * n - 1)} games, depending on the reset final.`;
  if (type === 'round_robin_playoff') return `${n * (n - 1) / 2} preliminary games, then up to ${c.advance - 1 + bronze} playoff games.`;
  if (type === 'pools') return `${poolsFor(t).reduce((sum, p) => sum + p.teams.length * (p.teams.length - 1) / 2, 0)} pool games, then up to ${c.pools * 2 - 1 + bronze} playoff games. Top two per pool advance.`;
  if (type === 'rotating_partners') return `${c.rounds} rounds; ${c.rounds * Math.min(t.courts, Math.floor(n / 4))} games. Individual standings use win percentage, then average point margin and average points scored.`;
  return `${c.rounds} rounds; ${c.rounds * t.courts} games. Final court and last-round result determine shared places.`;
}
