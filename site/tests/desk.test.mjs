import test from 'node:test';
import assert from 'node:assert/strict';
import { validateTournament, competitionState, reviseTournament, decodeBackup, encodeBackup } from '../assets/js/engine.mjs';
import { planFormats, resultsText, boardModel } from '../assets/js/desk.mjs';

const mixer = (n = 8, rounds = 6) => validateTournament({ id: 'mix', name: 'Mixer', date: '2026-10-06', venue: '', mode: 'singles', courts: 2, target: 11, scheduled: true, withdrawn: [], scores: {}, teams: Array.from({ length: n }, (_, i) => ({ id: `t${i + 1}`, players: [`P${i + 1}`] })), competition: { type: 'rotating_partners', rounds } });
const scoreRounds = (t, rounds) => { for (const r of rounds) for (const m of competitionState(t).matches.filter(m => m.socialRound === r)) t = reviseTournament(t, { type: 'score', id: m.id, score: [11, 7] }).tournament; return t; };
const shape = (t, upTo) => JSON.stringify(competitionState(t).matches.filter(m => m.socialRound <= upTo).map(m => [m.id, m.a, m.b, m.score]));

test('late arrival joins at a later round and never disturbs scored rounds', () => {
  const t = scoreRounds(mixer(), [1, 2]);
  const joined = reviseTournament(t, { type: 'join', team: { id: 'late', players: ['Late'] }, from: 4 });
  assert.equal(joined.cleared.length, 0);
  assert.equal(shape(joined.tournament, 3), shape(t, 3));
  const rounds = new Set(competitionState(joined.tournament).matches.filter(m => [...m.a, ...m.b].includes('late')).map(m => m.socialRound));
  assert.deepEqual([...rounds].sort(), [4, 5, 6]);
  assert.throws(() => reviseTournament(t, { type: 'join', team: { id: 'l2', players: ['L2'] }, from: 2 }), /already have scores/);
  assert.deepEqual(decodeBackup(encodeBackup(joined.tournament)), joined.tournament);
});

test('leaving early removes a person from later rounds only, and four must remain', () => {
  const t = scoreRounds(mixer(), [1]);
  const left = reviseTournament(t, { type: 'leave', id: 't1', after: 2 }).tournament;
  const rounds = new Set(competitionState(left).matches.filter(m => [...m.a, ...m.b].includes('t1')).map(m => m.socialRound));
  assert(![...rounds].some(r => r > 2));
  assert.equal(shape(left, 1), shape(t, 1));
  let small = mixer(5);
  small = reviseTournament(small, { type: 'leave', id: 't1', after: 1 }).tournament;
  assert.throws(() => reviseTournament(small, { type: 'leave', id: 't2', after: 1 }), /at least four people/);
});

test('arrival and departure only apply to rotating partners, and are validated', () => {
  const rr = validateTournament({ id: 'rr', name: 'RR', date: '2026-10-06', venue: '', mode: 'singles', courts: 1, target: 11, scheduled: true, withdrawn: [], scores: {}, teams: [1, 2, 3, 4].map(i => ({ id: `t${i}`, players: [`P${i}`] })) });
  assert.throws(() => reviseTournament(rr, { type: 'join', team: { id: 'x', players: ['X'] }, from: 2 }), /rotating-partners/);
  const t = mixer();
  assert.throws(() => validateTournament({ ...t, windows: { nobody: [1, null] } }), /invalid/);
  assert.throws(() => validateTournament({ ...t, windows: { t1: [3, 2] } }), /Last round/);
});

test('time planner suggests the first format that fits and marks the fastest otherwise', () => {
  const fits = planFormats({ entries: 8, courts: 2, minutes: 120, perGame: 15, individuals: false });
  assert.equal(fits.filter(r => r.suggested).length, 1);
  assert(fits.find(r => r.suggested).fits);
  assert.equal(fits.find(r => r.type === 'single_elimination').minutes, 60);
  const tight = planFormats({ entries: 16, courts: 1, minutes: 30, perGame: 15, individuals: false });
  const best = tight.find(r => r.suggested);
  assert(!best.fits);
  assert.equal(best.minutes, Math.min(...tight.map(r => r.minutes)));
  const social = planFormats({ entries: 8, courts: 2, minutes: 90, perGame: 15, individuals: true });
  assert.deepEqual(social.map(r => r.type), ['rotating_partners', 'king_queen']);
  assert.equal(social[0].settings.rounds, 6);
  assert.deepEqual(planFormats({ entries: 3, courts: 1, minutes: 60, perGame: 15, individuals: true }), []);
});

test('results text and the board model describe the same event', () => {
  const t = scoreRounds(mixer(), [1]);
  const state = competitionState(t);
  const text = resultsText(t, state, 'https://example.org/');
  assert(text.startsWith('Mixer · 2026-10-06'));
  assert(text.includes('results so far'));
  assert(text.endsWith('Run your own: https://example.org/'));
  const board = boardModel(state);
  assert.equal(board.now.length, 2);
  assert.equal(board.now[0].socialRound, 2);
  assert(board.next.every(m => m.group === board.next[0].group && m.group > board.now[0].group));
});
