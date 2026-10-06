// Organizer helpers: pick a format by time, shareable results text, wall-board model.
// Pure functions. No DOM, storage, clock, or network.
import { competitionState, formatLabel, formatStandings } from './engine.mjs';

// Minutes per game including changeover. An organizer-adjustable guess, not a measurement.
export const GAME_MINUTES = { 11: 15, 15: 20, 21: 30 };

const roster = n => Array.from({ length: n }, (_, i) => ({ id: `t${i}`, players: [`P${i}`] }));
const lastGroup = (n, courts, competition) => Math.max(0, ...competitionState({
  teams: roster(n), courts, scheduled: true, withdrawn: [], scores: {}, mode: 'singles', target: 11,
  competition: { pools: 2, advance: 4, rounds: 6, bronze: false, ...competition },
}).matches.filter(m => m.status !== 'bye').map(m => m.group));
const knockout = (entries, courts) => { let groups = 0; for (let k = entries / 2; k >= 1; k /= 2) groups += Math.ceil(k / courts); return groups; };

// Ranked suggestions, best first. `groups` = court groups played one after another.
export function planFormats({ entries, courts, minutes, perGame, individuals }) {
  const rows = [], add = (type, groups, detail, settings = {}) => rows.push({ type, label: formatLabel({ competition: { type } }), groups, minutes: groups * perGame, fits: groups * perGame <= minutes, detail, settings: { type, ...settings } });
  const rounds = Math.min(30, Math.max(1, Math.floor(minutes / perGame)));
  if (individuals) {
    if (entries >= 4) {
      const used = Math.min(courts, Math.floor(entries / 4));
      add('rotating_partners', rounds, `${rounds} rounds · about ${(rounds * used * 4 / entries).toFixed(1)} games each · new partners`, { rounds });
    }
    if (entries >= 4 && entries % 4 === 0 && entries / 4 <= courts) add('king_queen', rounds, `${rounds} rounds on ${entries / 4} courts · winners move up`, { rounds, courts: entries / 4 });
    return finish(rows);
  }
  if (entries >= 2) add('round_robin', lastGroup(entries, courts, { type: 'round_robin' }), `${entries * (entries - 1) / 2} games · everyone plays everyone`);
  if (entries >= 4) {
    const advance = entries >= 12 ? 8 : entries >= 6 ? 4 : 2, pools = entries >= 12 ? 4 : 2;
    add('round_robin_playoff', lastGroup(entries, courts, { type: 'round_robin_playoff', advance }) + knockout(advance, courts), `Everyone plays everyone, then the top ${advance} play off`, { advance });
    add('pools', lastGroup(entries, courts, { type: 'pools', pools }) + knockout(pools * 2, courts), `${pools} pools, then the top two from each play off`, { pools });
  }
  if (entries >= 2) {
    add('single_elimination', lastGroup(entries, courts, { type: 'single_elimination' }), 'One loss and you are out');
    add('double_elimination', lastGroup(entries, courts, { type: 'double_elimination' }), 'Two losses and you are out');
  }
  return finish(rows);
}
function finish(rows) {
  const best = rows.find(row => row.fits) ?? [...rows].sort((a, b) => a.minutes - b.minutes)[0];
  if (best) best.suggested = true;
  return rows;
}

// Plain text for a group chat. Names are included on purpose; the organizer chooses to share.
export function resultsText(t, state, url = '') {
  const lines = [`${t.name} · ${t.date}`, `${formatLabel(t)} · ${state.finished ? 'final results' : 'results so far'}`, ''];
  for (const row of formatStandings(t, state)) {
    const margin = row.difference ? ` (${row.difference > 0 ? '+' : ''}${row.difference})` : '';
    lines.push(`${row.rank ?? '–'}. ${row.name}${row.withdrawn ? ' (withdrawn)' : ''} · ${row.wins}-${row.losses}${margin}`);
  }
  if (url) lines.push('', `Run your own: ${url}`);
  return lines.join('\n');
}

// What a TV or second screen shows: games on court now, then the next group.
export function boardModel(state) {
  const now = state.current, group = now[0]?.group ?? 0;
  const later = state.matches.filter(m => !m.done && m.status !== 'bye' && m.group > group);
  const nextGroup = later.length ? Math.min(...later.map(m => m.group)) : null;
  return { now, next: nextGroup === null ? [] : later.filter(m => m.group === nextGroup), finished: state.finished };
}
