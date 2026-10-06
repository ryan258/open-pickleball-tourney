// Pure browser-edition rules. No Django imports, network, clock, or storage.
import { formatType, playoffFormat, normalizeCompetition, buildCompetition, sideSignature, present } from './competition.mjs';
export { FORMAT_OPTIONS, formatType, socialFormat, playoffFormat, formatLabel, sideName, formatStandings, formatSummary, poolsFor } from './competition.mjs';
export const FORMAT = 'open-pickleball-browser';
export const VERSION = 1;
export const MAX_TEAMS = 16;
export const MAX_FILE_BYTES = 100_000;

function fail(message) { throw new Error(message); }
function record(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function integer(value, low, high, label) {
  if (!Number.isInteger(value) || value < low || value > high) fail(`${label} must be a whole number from ${low} to ${high}.`);
  return value;
}
function text(value, max, label, empty = false) {
  if (typeof value !== 'string' || value.length > max || (!empty && !value.trim()) || /[\u0000-\u001f\u007f]/u.test(value)) fail(`${label} needs ${empty ? 'at most ' : '1–'}${max} ordinary characters.`);
  return value.trim();
}
function id(value) {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9_-]{1,64}$/.test(value)) fail('This tournament has an invalid record ID.');
  return value;
}
export function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === value && value >= '2000-01-01' && value <= '2100-12-31';
}
export function teamName(team) { return team.players.join(' & '); }

export function makeSchedule(teams, courts) {
  integer(courts, 1, 8, 'Courts');
  if (!Array.isArray(teams) || teams.length < 2 || teams.length > MAX_TEAMS) fail('Add 2–16 players or teams before making the schedule.');
  const ring = teams.map(team => team.id);
  if (ring.length % 2) ring.push(null);
  const queue = [];
  for (let round = 1; round < ring.length; round += 1) {
    for (let i = 0; i < ring.length / 2; i += 1) {
      const a = ring[i], b = ring[ring.length - 1 - i];
      if (a !== null && b !== null) queue.push({ a: round % 2 ? a : b, b: round % 2 ? b : a, round });
    }
    ring.splice(1, 0, ring.pop());
  }
  const matches = [];
  let remaining = queue;
  let group = 0;
  while (remaining.length > 0) {
    group += 1;
    const active = new Set();
    const nextRemaining = [];
    let court = 0;
    for (const match of remaining) {
      if (court < courts && !active.has(match.a) && !active.has(match.b)) {
        court += 1;
        active.add(match.a);
        active.add(match.b);
        matches.push({ id: `m${matches.length + 1}`, a: match.a, b: match.b, round: match.round, group, court });
      } else {
        nextRemaining.push(match);
      }
    }
    remaining = nextRemaining;
  }
  return matches;
}

export function validateScore(a, b, target) {
  if (![11, 15, 21].includes(target)) fail('Choose a game to 11, 15, or 21.');
  integer(a, 0, 999, 'First score');
  integer(b, 0, 999, 'Second score');
  const high = Math.max(a, b), low = Math.min(a, b);
  if (high < target || high - low < 2) fail(`Play to ${target}, win by 2. These scores do not finish the game yet.`);
  if (high > target && high - low !== 2) fail('After the target, the game ends as soon as a team leads by 2. Check these scores.');
  return [a, b];
}

export function validateTournament(input) {
  if (!record(input)) fail('The tournament is missing.');
  const tournament = {
    id: id(input.id), name: text(input.name, 100, 'Tournament name'),
    date: input.date, venue: text(input.venue, 100, 'Location', true),
    mode: input.mode, courts: integer(input.courts, 1, 8, 'Courts'),
    target: input.target, teams: [], scheduled: input.scheduled, withdrawn: [], scores: {},
  };
  if (!validDate(input.date)) fail('Choose a valid date between 2000 and 2100.');
  if (!['singles', 'doubles'].includes(input.mode)) fail('Choose singles or doubles.');
  if (![11, 15, 21].includes(input.target)) fail('Choose a game to 11, 15, or 21.');
  if (typeof input.scheduled !== 'boolean') fail('The schedule status is invalid.');
  if (!Array.isArray(input.teams) || input.teams.length > MAX_TEAMS) fail('A tournament can have at most 16 players or teams.');
  const ids = new Set(), people = new Set();
  tournament.teams = input.teams.map(team => {
    if (!record(team) || !Array.isArray(team.players) || team.players.length !== (input.mode === 'singles' ? 1 : 2)) fail('Each team must have the right number of players.');
    const key = id(team.id);
    if (ids.has(key)) fail('Two teams have the same ID.');
    ids.add(key);
    const players = team.players.map(player => {
      const name = text(player, 60, 'Player name');
      const normalized = name.normalize('NFKC').toLocaleLowerCase('en-US').replace(/\s+/g, ' ');
      if (people.has(normalized)) fail(`${name} is already on the roster. Add an initial to distinguish people with the same name.`);
      people.add(normalized);
      return name;
    });
    return { id: key, players };
  });
  const withdrawn = input.withdrawn ?? [];
  if (!Array.isArray(withdrawn) || new Set(withdrawn).size !== withdrawn.length || withdrawn.some(key => !ids.has(key)) || (withdrawn.length && !input.scheduled)) fail('The withdrawn entries are invalid.');
  tournament.withdrawn = [...withdrawn];
  if (input.competition !== undefined) tournament.competition = normalizeCompetition(input.competition, tournament);
  const extended = formatType(tournament) !== 'round_robin';
  if (extended) {
    if (!record(input.scoreSides ?? {}) || !record(input.advancement ?? {})) fail('The saved pairings or playoff selection are invalid.');
    tournament.scoreSides = {};
    tournament.advancement = {};
    const qualifyingWithdrawn = input.qualifyingWithdrawn ?? [];
    if (!Array.isArray(qualifyingWithdrawn) || new Set(qualifyingWithdrawn).size !== qualifyingWithdrawn.length || qualifyingWithdrawn.some(key => !ids.has(key))) fail('The qualification withdrawal record is invalid.');
    tournament.qualifyingWithdrawn = [...qualifyingWithdrawn];
    for (const [key, value] of Object.entries(input.scoreSides ?? {})) {
      if (!/^(?:e-|all-|pool-|mix|kq)/.test(key) || typeof value !== 'string' || value.length > 600) fail('A saved pairing is invalid.');
      tournament.scoreSides[key] = value;
    }
    for (const [key, order] of Object.entries(input.advancement ?? {})) {
      if (!['all', 'pool-1', 'pool-2', 'pool-3', 'pool-4'].includes(key) || !Array.isArray(order) || order.length > MAX_TEAMS || order.some(key => !ids.has(key))) fail('The playoff order is invalid.');
      tournament.advancement[key] = [...order];
    }
    if (!playoffFormat(tournament) && Object.keys(tournament.advancement).length) fail('This format does not have a pool qualification step.');
    if (!tournament.scheduled && Object.keys(tournament.advancement).length) fail('Playoff selection needs a completed preliminary stage.');
    if (!Object.keys(tournament.advancement).length && tournament.qualifyingWithdrawn.length) fail('Qualification withdrawals need a confirmed playoff order.');
  }
  if (input.windows !== undefined) {
    if (formatType(tournament) !== 'rotating_partners' || !record(input.windows)) fail('Arrival and departure rounds apply only to rotating partners.');
    const rounds = tournament.competition.rounds, windows = {};
    for (const [person, w] of Object.entries(input.windows)) {
      if (!ids.has(person) || !Array.isArray(w) || w.length !== 2) fail('A saved arrival or departure is invalid.');
      const from = integer(w[0], 1, rounds, 'First round');
      windows[person] = [from, w[1] === null ? null : integer(w[1], from, rounds, 'Last round')];
    }
    if (Object.keys(windows).length) {
      tournament.windows = windows;
      for (let round = 1; tournament.scheduled && round <= rounds; round++) {
        if (tournament.teams.filter(team => present(tournament, team.id, round)).length < 4) fail(`Rotating partners needs at least four people in round ${round}.`);
      }
    }
  }
  if (!record(input.scores)) fail('The scores are invalid.');
  if (Object.keys(input.scores).length > 256) fail('There are too many scores in this record.');
  for (const [key, score] of Object.entries(input.scores)) {
    if (!/^[a-zA-Z0-9_-]{1,64}$/.test(key) || ['__proto__', 'constructor', 'prototype'].includes(key) || !Array.isArray(score) || score.length !== 2) fail('A score does not belong to this schedule.');
    tournament.scores[key] = validateScore(score[0], score[1], tournament.target);
  }
  const state = competitionState(tournament);
  if (state.invalidScores.length) fail('A saved score has unresolved or different opponents. Restore a copy with the original pairings.');
  if (!state.advancementValid) fail('The playoff order must include every eligible entry once, in standings order. Only tied entries may swap.');
  if (extended && Object.keys(tournament.scoreSides).some(key => !Object.hasOwn(tournament.scores, key))) fail('A saved pairing has no score.');
  return tournament;
}

export function encodeBackup(tournament) {
  const checked = validateTournament(tournament);
  return JSON.stringify({ format: FORMAT, version: formatType(checked) === 'round_robin' ? VERSION : 2, tournament: checked }, null, 2);
}
export function decodeBackup(source) {
  if (typeof source !== 'string' || new TextEncoder().encode(source).length > MAX_FILE_BYTES) fail('Choose a tournament backup smaller than 100 KB.');
  let data;
  try { data = JSON.parse(source); } catch { fail('This file is not a readable tournament backup.'); }
  if (!record(data) || data.format !== FORMAT || ![VERSION, 2].includes(data.version)) fail('Choose a version 1 or 2 backup from this browser edition. Django archives and other files cannot be opened here.');
  if ((data.version === 1 && formatType(data.tournament ?? {}) !== 'round_robin') || (data.version === 2 && formatType(data.tournament ?? {}) === 'round_robin')) fail('The backup version does not match its tournament format.');
  return validateTournament(data.tournament);
}

export function competitionState(tournament) { return buildCompetition(tournament, makeSchedule); }

// Prepare a reviewable edit without mutating the current event. Dependent scores
// are removed only from this proposal; the UI confirms the effect before saving.
export function reviseTournament(tournament, edit) {
  const next = structuredClone(tournament), before = competitionState(tournament);
  const extended = formatType(next) !== 'round_robin';
  const remove = key => { delete next.scores[key]; if (next.scoreSides) delete next.scoreSides[key]; };
  let prelimChanged = false;
  if (edit.type === 'score') {
    const match = before.matches.find(m => m.id === edit.id);
    if (!match || !['ready', 'scored'].includes(match.status)) fail('That game is not ready for a score.');
    if (edit.score) {
      next.scores[edit.id] = validateScore(...edit.score, next.target);
      if (extended) { next.scoreSides ??= {}; next.scoreSides[edit.id] = sideSignature(match); }
    } else remove(edit.id);
    const changed = JSON.stringify(match.score) !== JSON.stringify(edit.score);
    prelimChanged = changed && match.preliminary;
    if (formatType(next) === 'king_queen' && changed && (!edit.score || !match.score || (edit.score[0] > edit.score[1]) !== (match.score[0] > match.score[1]))) {
      before.matches.filter(m => m.socialRound > match.socialRound).forEach(m => remove(m.id));
    }
  } else if (edit.type === 'withdrawal') {
    if (!next.scheduled || !next.teams.some(team => team.id === edit.id)) fail('Choose a scheduled roster entry.');
    next.withdrawn = next.withdrawn.filter(id => id !== edit.id);
    if (edit.withdrawn) next.withdrawn.push(edit.id);
    prelimChanged = !Object.keys(next.advancement ?? {}).length;
  } else if (edit.type === 'join' || edit.type === 'leave') {
    // Rounds with scores are frozen; the change applies only to rounds nobody has scored.
    if (formatType(next) !== 'rotating_partners' || !next.scheduled) fail('Late arrivals and early departures are for a started rotating-partners event.');
    const played = Math.max(0, ...before.matches.filter(m => m.score).map(m => m.socialRound));
    next.windows ??= {};
    if (edit.type === 'join') {
      if (next.teams.length >= MAX_TEAMS) fail('The event is full: 16 people is the limit.');
      if (!Number.isInteger(edit.from) || edit.from <= played) fail(`Rounds up to ${played} already have scores. Choose a later round.`);
      next.teams.push(edit.team);
      next.windows[edit.team.id] = [edit.from, null];
    } else {
      if (!next.teams.some(team => team.id === edit.id)) fail('Choose a person on the roster.');
      if (!Number.isInteger(edit.after) || edit.after < played) fail(`Rounds up to ${played} already have scores. Choose a later round.`);
      next.windows[edit.id] = [next.windows[edit.id]?.[0] ?? 1, edit.after];
    }
  } else fail('Unknown tournament change.');
  if (playoffFormat(next) && prelimChanged) {
    next.advancement = {};
    next.qualifyingWithdrawn = [];
    Object.keys(next.scores).filter(key => key.startsWith('e-')).forEach(remove);
  }
  if (extended) {
    // Removing an unreachable score can make another later score unreachable.
    for (let i = 0; i <= 256; i++) {
      const state = competitionState(next);
      if (!state.invalidScores.length) break;
      state.invalidScores.forEach(remove);
    }
  }
  const cleared = Object.keys(tournament.scores).filter(id => id !== edit.id && !Object.hasOwn(next.scores, id));
  return { tournament: validateTournament(next), cleared, advancementReset: Boolean(Object.keys(tournament.advancement ?? {}).length && !Object.keys(next.advancement ?? {}).length) };
}

// A walkover is derived, never stored: an unplayed game involving a withdrawn
// entry. The opponent gets the win; no points are invented for either side.
export function isWalkover(tournament, match) {
  const out = tournament.withdrawn ?? [];
  return !tournament.scores[match.id] && (out.includes(match.a) || out.includes(match.b));
}

export function standings(tournament) {
  const rows = tournament.teams.map(team => ({ id: team.id, name: teamName(team), played: 0, wins: 0, losses: 0, for: 0, against: 0, difference: 0, rank: 0, walkovers: 0, withdrawn: (tournament.withdrawn ?? []).includes(team.id) }));
  const byId = new Map(rows.map(row => [row.id, row]));
  if (tournament.scheduled) for (const match of makeSchedule(tournament.teams, tournament.courts)) {
    const score = tournament.scores[match.id];
    const a = byId.get(match.a), b = byId.get(match.b);
    if (isWalkover(tournament, match)) {
      const [winner, loser] = a.withdrawn ? [b, a] : [a, b];
      if (!winner.withdrawn) { winner.played += 1; loser.played += 1; winner.wins += 1; loser.losses += 1; winner.walkovers += 1; loser.walkovers += 1; }
      continue;
    }
    if (!score) continue;
    a.played += 1; b.played += 1;
    a.for += score[0]; a.against += score[1]; b.for += score[1]; b.against += score[0];
    (score[0] > score[1] ? a : b).wins += 1;
    (score[0] > score[1] ? b : a).losses += 1;
  }
  rows.forEach(row => { row.difference = row.for - row.against; });
  const compare = (a, b) => b.wins - a.wins || b.difference - a.difference || b.for - a.for;
  // Withdrawn entries keep their real results but sit below everyone, unranked.
  rows.sort((a, b) => a.withdrawn - b.withdrawn || compare(a, b));
  rows.forEach((row, index) => { row.rank = row.withdrawn ? null : index && compare(row, rows[index - 1]) === 0 ? rows[index - 1].rank : index + 1; });
  return rows;
}

export function parseRoster(source, mode, makeId) {
  if (typeof source !== 'string' || source.length > 4000) fail('Paste a list of at most 16 entries.');
  const lines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  if (!lines.length || lines.length > MAX_TEAMS) fail('Paste 1–16 lines, one player or team per line.');
  return lines.map((line, index) => {
    const players = mode === 'doubles' ? line.split(/\s*(?:\/|&|\+|\band\b)\s*/i) : [line];
    if (players.length !== (mode === 'doubles' ? 2 : 1) || players.some(name => !name.trim())) fail(`Line ${index + 1}: ${mode === 'doubles' ? 'put “and”, “&” or “/” between the two players, like Pat and Lee.' : 'enter one player name.'}`);
    return { id: makeId(), players };
  });
}
