import { MAX_FILE_BYTES, validateTournament, makeSchedule, isWalkover, teamName, standings, validateScore, encodeBackup, decodeBackup, parseRoster } from './engine.mjs';
import { createStore, ConflictError } from './storage.mjs';

const $ = selector => document.querySelector(selector);
const escape = value => String(value).replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[char]);
// randomUUID needs a secure context; getRandomValues does not (e.g. a copy served over plain http).
const uuid = () => crypto.randomUUID?.() ?? [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2, '0')).join('');
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month:'long', day:'numeric', year:'numeric' });
const button = (label, action, classes = 'secondary', attrs = '') => `<button class="button ${classes}" data-action="${action}" ${attrs}>${label}</button>`;
const unit = () => tournament?.mode === 'singles' ? 'players' : 'teams';
const scope = location.pathname.replace(/index\.html$/, '').replace(/\/$/, '') || '/';
const key = `open-pickleball-browser:v1:${scope}`;
// Access to localStorage itself can throw under browser privacy policies.
const storage = { getItem: name => window.localStorage.getItem(name), setItem: (name,value) => window.localStorage.setItem(name,value) };
// A page opened from a file has no usable browser locks. The read/compare/write is still one
// synchronous step with stale-tab detection; only truly simultaneous tabs are uncoordinated.
const locks = location.protocol === 'file:' ? { request: (_name, run) => Promise.resolve().then(run) } : navigator.locks;
const store = createStore(storage, locks, key);
let tournament = null, view = 'home', unsaved = false, corrupt = false, stale = false, formDirty = false;
let pendingScore = null, pendingImport = null, askResolve = null, working = false, problemText = '';

try { tournament = store.read(); } catch (error) { corrupt = Boolean(store.raw()); problemText = corrupt ? 'The saved tournament could not be opened. Download the original data below before replacing it, or open a good saved copy.' : 'This browser is blocking automatic saving. You can work here and use Download a copy to keep your tournament.'; }

function announce(message) { $('#announcement').textContent = message; }
function showProblem(message) {
  problemText = message;
  const node = $('#problem');
  node.hidden = !message;
  node.innerHTML = message ? `<p>${escape(message)}</p>${stale ? `<div class="button-row">${button('Load saved version','reload','small secondary')}${tournament ? button('Back up this tab first','backup','small secondary') : ''}</div>` : ''}` : '';
}
function errorAt(form, error) {
  const target = form.querySelector('.form-error');
  if (target) { target.textContent = error.message; target.focus(); }
  else showProblem(error.message);
}
function status() {
  $('#utility').hidden = !tournament;
  $('#save-status').dataset.state = stale ? 'stale' : unsaved ? 'unsaved' : 'saved';
  $('#save-status').textContent = stale ? 'Another tab has newer changes' : unsaved ? 'Not saved — download a copy' : 'Saved in this browser on this device';
  showProblem(problemText);
}
async function commit(next) {
  next = validateTournament(next);
  if (stale) throw new ConflictError('Load the saved version before making changes. You can back up this tab first.');
  try {
    await store.save(next);
    unsaved = false; corrupt = false; problemText = '';
  } catch (error) {
    if (error instanceof ConflictError) {
      stale = true; status(); showProblem(error.message); throw error;
    }
    unsaved = true;
    problemText = 'Your latest changes are only in this open tab. Automatic saving is unavailable or storage is full. Use Download a copy before closing.';
  }
  tournament = next;
  formDirty = false;
  status();
}
async function change(edit) { const next = structuredClone(tournament); edit(next); await commit(next); }
function options(values, selected) { return values.map(([value,label]) => `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`).join(''); }
function heading(kicker, title, subtitle = '', actions = '') {
  return `<div class="page-heading"><div><p class="eyebrow">${kicker}</p><h1 tabindex="-1" id="view-title">${escape(title)}</h1>${subtitle ? `<p class="muted">${subtitle}</p>` : ''}</div>${actions ? `<div class="button-row">${actions}</div>` : ''}</div>`;
}
let lastScoreTriggerId = null;

function render(focus = true) {
  const openSummaries = new Set([...document.querySelectorAll('#main details[open] summary')].map(s => s.textContent.trim()));
  const nav = $('#steps');
  nav.hidden = view === 'home' || !tournament;
  nav.innerHTML = ['setup','teams','play','results'].map((step,index) => `<button data-action="navigate" data-view="${step}" ${view === step ? 'aria-current="step"' : ''} ${!tournament && index ? 'disabled' : ''}><span class="step-number">${index+1}</span>${['Set up','Add '+unit(),'Play','Results'][index]}</button>`).join('');
  $('#main').innerHTML = ({ home: homeView, setup: setupView, teams: teamsView, play: playView, results: resultsView })[view]();
  for (const details of document.querySelectorAll('#main details')) {
    const summary = details.querySelector('summary')?.textContent.trim();
    if (summary && openSummaries.has(summary)) details.open = true;
  }
  status();
  document.title = tournament && view !== 'home' ? `${tournament.name} · Open Pickleball Tourney` : 'Open Pickleball Tourney';
  if (focus) {
    $('#view-title')?.focus();
    window.scrollTo({ top:0, behavior:'instant' });
  } else if (lastScoreTriggerId) {
    const trigger = document.querySelector(`[data-action="score"][data-id="${lastScoreTriggerId}"]`);
    if (trigger) trigger.focus();
    lastScoreTriggerId = null;
  }
}
async function navigate(next) {
  if (formDirty && !await ask('Leave these edits?', 'The fields you are editing have not been saved yet. Stay here to finish, or leave these edits behind.', 'Leave edits')) return;
  formDirty = false; view = next; render();
}
function homeView() {
  const saved = tournament ? `<div class="panel tint" style="margin-bottom:2rem"><p class="eyebrow">YOUR TOURNAMENT</p><h2>${escape(tournament.name)}</h2><p>${escape(dateLabel(tournament.date))} · ${tournament.teams.length} ${unit()}${tournament.scheduled ? ` · ${Object.keys(tournament.scores).length} scores saved` : ''}</p>${button('Continue tournament →','continue','')}</div>` : '';
  return `${saved}${corrupt ? `<div class="notice"><p>Your original saved data is still here.</p>${button('Download original data','raw','secondary')}</div>` : ''}<section class="hero"><div><p class="eyebrow">GOOD COMPANY. GREAT GAMES.</p><h1 id="view-title" tabindex="-1">You bring the people.<br><em>We’ll sort the games.</em></h1><p class="lead">A little less paperwork. A lot more play. Run your neighborhood pickleball tournament, one easy step at a time.</p><div class="hero-actions">${button('Start a tournament →','new','')}${button('Try a practice tournament','sample','secondary')}</div><p class="hint">No account needed. Your tournament stays on this device.</p>${button('Open a saved tournament','import','quiet small')}</div><div class="scoreboard" aria-label="An example match card, not a live tournament"><div class="scoreboard-top"><span>THE SATURDAY SOCIAL</span><span>EXAMPLE</span></div><span class="badge">COURT 1</span><h2 style="margin-top:1rem">Good game, everyone.</h2><p class="sample-note">A clear schedule. A simple scorecard.</p><div class="sample-match"><div class="sample-team"><span>Pat &amp; Lee</span><strong>11</strong></div><div class="sample-team"><span>Jo &amp; Sam</span><strong>7</strong></div></div><div class="scoreboard-bottom"><span>Game saved</span><span>Next game, please →</span></div></div></section><section class="workflow" aria-label="Three easy steps"><div class="workflow-item"><span class="step-number">1</span><div><h3>Get everyone together.</h3><p>Name your day, choose your courts, and add your players.</p></div></div><div class="workflow-item"><span class="step-number">2</span><div><h3>Let’s play.</h3><p>Get a round-robin schedule. See who’s up and enter each score.</p></div></div><div class="workflow-item"><span class="step-number">3</span><div><h3>Make it a regular thing.</h3><p>Print the results and use your setup again next time.</p></div></div></section>`;
}
function setupView() {
  const t = tournament || { name:'', date:today(), venue:'', mode:'doubles', courts:2, target:11 };
  const locked = t.scheduled;
  return `${heading('STEP 1 · A PLAN FOR THE DAY', 'Let’s get your game on.', 'A few details, and you’re on your way.')}<div class="workspace"><section class="panel"><form data-form="setup" class="form-grid"><div><label for="event-name">Tournament name</label><input id="event-name" name="name" required maxlength="100" value="${escape(t.name)}" placeholder="Saturday at the park" autocomplete="off"></div><div class="grid-two"><div><label for="event-date">Date</label><input id="event-date" name="date" type="date" required min="2000-01-01" max="2100-12-31" value="${t.date}"></div><div><label for="event-venue">Location <span class="muted">(optional)</span></label><input id="event-venue" name="venue" maxlength="100" value="${escape(t.venue)}" placeholder="Riverside courts"></div></div><div class="grid-two"><div><label for="event-mode">Who’s playing?</label><select id="event-mode" name="mode" ${t.teams?.length ? 'disabled' : ''}>${options([['doubles','Doubles · two players per team'],['singles','Singles · one player per side']],t.mode)}</select>${t.teams?.length ? '<p class="hint">Remove the roster to switch singles or doubles.</p>' : ''}</div><div><label for="event-courts">How many courts?</label><select id="event-courts" name="courts">${options(Array.from({length:8},(_,i)=>[i+1,`${i+1} court${i ? 's' : ''}`]),t.courts)}</select></div></div><details><summary>Game settings</summary><label for="event-target">Play each game to</label><select id="event-target" name="target" ${locked ? 'disabled' : ''}>${options([11,15,21].map(n=>[n,`${n} points · win by 2`]),t.target)}</select><p class="hint">One game per match. Every ${t.mode === 'singles' ? 'player' : 'team'} plays every other ${t.mode === 'singles' ? 'player' : 'team'} once. These are casual community games.</p></details>${locked ? '<p class="hint">Scoring settings are locked to the schedule. You can adjust the court count as needed.</p>' : ''}<p class="form-error" role="alert" tabindex="-1"></p><div class="form-actions"><button class="button" type="submit">Save & continue →</button>${button('Back to home','home','quiet')}</div></form></section><aside class="stack"><div class="panel tint"><p class="eyebrow">KEEP IT FRIENDLY</p><h2>Everybody gets to play.</h2><p>Round robin means everyone meets every other team once. No one is knocked out after their first game.</p><p class="hint">For 2–16 teams or singles players, on up to 8 courts.</p></div><div class="panel"><h2>Your work stays with you.</h2><p>We save after each completed step and confirmed score. Come back in the same browser, on this device.</p><p class="hint">Download a copy to move your tournament to another computer or to keep a spare.</p></div></aside></div>`;
}
function teamsView() {
  const t = tournament;
  const unplayedTeams = new Set();
  if (t.scheduled) {
    const schedule = makeSchedule(t.teams, t.courts);
    for (const m of schedule) {
      if (!t.scores[m.id]) {
        unplayedTeams.add(m.a);
        unplayedTeams.add(m.b);
      }
    }
  }
  const list = t.teams.map((team,index) => `<li class="team-item"><span class="team-label"><small>${t.mode === 'doubles' ? 'TEAM' : 'PLAYER'} ${index+1}</small>${escape(teamName(team))}</span>${!t.scheduled ? button('Remove','remove-team','quiet small',`data-id="${team.id}" aria-label="Remove ${escape(teamName(team))}"`) : (t.withdrawn.includes(team.id) ? `<span class="badge neutral">Withdrawn</span>${button('Add back','reinstate-team','quiet small',`data-id="${team.id}" aria-label="Add back ${escape(teamName(team))}"`)}` : unplayedTeams.has(team.id) ? button('Withdraw','withdraw-team','quiet small',`data-id="${team.id}" aria-label="Withdraw ${escape(teamName(team))}"`) : '')}</li>`).join('');
  const total = t.teams.length * (t.teams.length-1) / 2;
  return `${heading('STEP 2 · THE GOOD COMPANY', `Add your ${unit()}.`, 'Use names people will recognize. No emails or sign-ups needed.')}<div class="workspace"><div class="stack"><section class="panel"><h2>${t.teams.length} ${unit()} on the list</h2>${list ? `<ul class="team-list">${list}</ul>` : `<p class="muted">Your first ${t.mode === 'doubles' ? 'team' : 'player'} goes here. Add at least two to get started.</p>`}${t.scheduled ? `<p class="hint">Your roster is locked to the current schedule. Withdraw an entry if they need to leave early, or start a new schedule to change the roster. Court count can be changed on the setup step.</p>${button('Change roster','reset-schedule','secondary')}` : ''}</section>${!t.scheduled && t.teams.length < 16 ? `<section class="panel"><form data-form="team" class="form-grid"><h2>Add ${t.mode === 'doubles' ? 'a team' : 'a player'}</h2><div class="${t.mode === 'doubles' ? 'grid-two' : ''}"><div><label for="player-one">${t.mode === 'doubles' ? 'First player' : 'Player name'}</label><input id="player-one" name="one" maxlength="60" required autocomplete="off" placeholder="Pat"></div>${t.mode === 'doubles' ? '<div><label for="player-two">Second player</label><input id="player-two" name="two" maxlength="60" required autocomplete="off" placeholder="Lee"></div>' : ''}</div><p class="form-error" role="alert" tabindex="-1"></p><button type="submit" class="button secondary">Add ${t.mode === 'doubles' ? 'team' : 'player'}</button></form><details${t.teams.length ? '' : ' open'}><summary>Have a list? Paste it all at once.</summary><form data-form="bulk" class="form-grid"><div><label for="roster-list">One ${t.mode === 'doubles' ? 'team' : 'player'} per line</label><textarea id="roster-list" name="roster" maxlength="4000" required aria-describedby="roster-help" placeholder="${t.mode === 'doubles' ? 'Pat and Lee&#10;Jo and Sam' : 'Pat&#10;Lee&#10;Jo'}"></textarea><p class="hint" id="roster-help">${t.mode === 'doubles' ? 'Put “and” between partners, like Pat and Lee. “&” or “/” also work.' : 'Enter each player on their own line.'} This adds to the list above.</p></div><p class="form-error" role="alert" tabindex="-1"></p><button type="submit" class="button secondary">Add this list</button></form></details></section>` : ''}</div><aside class="panel tint"><p class="eyebrow">READY WHEN YOU ARE</p><h2>${total ? `${total} games. Plenty of play.` : 'A game for everyone.'}</h2><p>${t.teams.length >= 2 ? `Each ${t.mode === 'doubles' ? 'team' : 'player'} gets ${t.teams.length-1} games. We’ll spread the matches across ${t.courts} court${t.courts===1 ? '' : 's'}.` : 'Add at least two entries. We’ll take care of the matchups.'}</p><p class="hint">With an odd number, someone rests each round. Take breaks between rounds whenever you need them.</p>${button(t.scheduled ? 'Go to the games →' : 'Make the schedule →',t.scheduled ? 'go-play' : 'schedule','',t.teams.length<2 ? 'disabled' : '')}</aside></div>`;
}
function matchCard(match) {
  const a = tournament.teams.find(t=>t.id===match.a), b = tournament.teams.find(t=>t.id===match.b), score = tournament.scores[match.id];
  return `<article class="court-card"><div class="court-head"><span>COURT ${match.court}</span><span>${score ? 'SCORE SAVED' : `GAME ${match.id.slice(1)}`}</span></div><div class="court-body"><div class="match-side"><span>${escape(teamName(a))}</span><b>${score ? score[0] : '—'}</b></div><div class="versus">VERSUS</div><div class="match-side"><span>${escape(teamName(b))}</span><b>${score ? score[1] : '—'}</b></div>${button(score ? 'Correct score' : 'Enter score','score',score ? 'secondary' : '',`data-id="${match.id}" aria-label="${score ? 'Correct' : 'Enter'} score for court ${match.court}, ${escape(teamName(a))} versus ${escape(teamName(b))}"`)}</div></article>`;
}
function playView() {
  const t = tournament;
  if (!t.scheduled) return `${heading('STEP 3 · LET’S PLAY', 'Your courts are nearly ready.')}<div class="panel empty"><h2>First, make your schedule.</h2><p>Add your ${unit()}, then we’ll work out who plays whom.</p>${button('Go to the roster →','go-teams','')}</div>`;
  const matches = makeSchedule(t.teams,t.courts), complete = Object.keys(t.scores).length;
  const playable = matches.filter(m=>!isWalkover(t,m)), walkovers = matches.length - playable.length;
  const group = playable.find(m=>!t.scores[m.id])?.group;
  const current = playable.filter(m=>m.group===group);
  const byId = new Map(t.teams.map(team=>[team.id,teamName(team)]));
  const resting = t.teams.filter(team=>!current.some(m=>m.a===team.id || m.b===team.id));
  const groupIds = [...new Set(matches.map(m=>m.group))];
  const schedule = groupIds.map(n=>`<div class="schedule-group"><h3>Round ${n}${n===group ? ' · playing now' : ''}</h3>${matches.filter(m=>m.group===n).map(m=>`<div class="schedule-row"><small>Court ${m.court}</small><p>${escape(byId.get(m.a))}<br><small>vs.</small> ${escape(byId.get(m.b))}</p>${t.scores[m.id] ? button(`${t.scores[m.id].join(' – ')} · Correct`,'score','small secondary',`data-id="${m.id}" aria-label="Correct game ${m.id.slice(1)} score, ${t.scores[m.id].join(' to ')}"`) : isWalkover(t,m) ? `<span class="badge neutral">No game${t.withdrawn.includes(m.a) && t.withdrawn.includes(m.b) ? '' : ` · ${escape(byId.get(t.withdrawn.includes(m.a) ? m.b : m.a))} gets the win`}</span>` : `<span class="badge neutral">${n===group ? 'Playing now' : 'Waiting'}</span>`}</div>`).join('')}</div>`).join('');
  return `${heading(escape(t.name), group ? 'A good day on the courts.' : 'That’s a wrap. Good games!', `${escape(dateLabel(t.date))}${t.venue ? ` · ${escape(t.venue)}` : ''}`,button('Print schedule','print-schedule','secondary small'))}<div class="stat-strip"><div><strong>${complete} / ${playable.length + complete}</strong><span>games scored${walkovers ? ` · ${walkovers} not played` : ''}</span></div><div><strong>${t.teams.length}</strong><span>${unit()}</span></div><div><strong>${t.target}</strong><span>points · win by 2</span></div></div>${group ? `<div class="section-heading"><h2>On court · round ${group} of ${groupIds.length}</h2><span class="badge">LET’S PLAY</span></div><p class="hint">Start this group together when everyone is ready. Finish every game here before starting the next round.</p><div class="court-grid">${current.map(matchCard).join('')}</div>${resting.length ? `<p class="hint" style="margin-top:1rem">Sitting out this round: ${resting.map(team=>escape(teamName(team))).join('; ')}.</p>` : ''}<p class="hint">${group < groupIds.length ? `Up next: round ${group+1}. Matchups are in the full schedule below.` : 'This is the last round. The results are nearly in.'}</p>` : `<section class="panel tint"><h2>Every game is scored.</h2><p>Take a look at the standings, print the results, and download a copy of the day to keep.</p><div class="button-row">${button('See the results →','go-results','')}${button('Download a copy','backup','secondary')}</div></section>`}<details><summary>Full schedule & score corrections</summary><p class="hint">Correct a saved score here. The standings update automatically.</p>${schedule}</details>`;
}
function resultsTable() {
  return `<div class="table-wrap" role="region" aria-label="Tournament standings" tabindex="0"><table><caption class="sr-only">Standings ranked by wins, then point difference, then points scored</caption><thead><tr><th scope="col">Place</th><th scope="col">${tournament.mode==='singles' ? 'Player' : 'Team'}</th><th scope="col">Played</th><th scope="col">Won</th><th scope="col" class="optional-column">Lost</th><th scope="col"><abbr title="Points scored minus points conceded">Point margin</abbr></th><th scope="col" class="optional-column">Points scored</th></tr></thead><tbody>${standings(tournament).map(row=>`<tr><td><span class="place">${row.rank ?? '—'}</span></td><td class="name">${escape(row.name)}${row.withdrawn ? ' <span class="badge neutral">Withdrawn</span>' : ''}</td><td>${row.played}</td><td>${row.wins}</td><td class="optional-column">${row.losses}</td><td>${row.difference>0?'+':''}${row.difference}</td><td class="optional-column">${row.for}</td></tr>`).join('')}</tbody></table></div>`;
}
function resultsView() {
  if (!tournament.scheduled) return `${heading('STEP 4 · THE RESULTS', 'The best part is still ahead.')}<div class="panel empty"><h2>Let’s get some games going.</h2><p>Your standings appear once the schedule is ready.</p>${button('Go to the roster →','go-teams','')}</div>`;
  const matches = makeSchedule(tournament.teams,tournament.courts), count = Object.keys(tournament.scores).length, walkovers = matches.filter(m=>isWalkover(tournament,m)).length, done = matches.length===count+walkovers;
  return `${heading(done ? 'THE RESULTS ARE IN' : 'STANDINGS · TOURNAMENT IN PROGRESS',tournament.name,`${count} games scored${walkovers ? `, ${walkovers} not played` : ''}. ${done ? 'Every game is complete.' : 'Places can change as more games are played.'}`,button('Print results','print-results','secondary small'))}<section class="panel"><label for="game-progress">${done ? 'All games complete' : 'Tournament progress'}</label><progress id="game-progress" max="${matches.length}" value="${count+walkovers}">${count+walkovers} of ${matches.length}</progress><div style="margin-top:1.5rem">${resultsTable()}</div><p class="hint" style="margin-top:1rem">Ranked by games won, then point margin (points scored minus points conceded), then total points scored. Remaining ties share a place. If an entry withdraws, each game it did not play counts as a win for the other side, with no points recorded. These are casual event standings.</p></section><div class="section-heading"><h2>${done ? 'Keep a little record of a good day.' : 'More games, more good company.'}</h2></div><div class="button-row">${button('Print results','print-results','')}${button('Download a copy','backup','secondary')}${button('Back to the games','go-play','secondary')}${button('Use this setup next time','reuse','secondary')}</div><p class="hint" style="margin-top:1rem">A copy includes the names, settings and scores. Check your Downloads folder, and move the file somewhere you can find it again.</p>`;
}

function modal(markup) {
  $('#modal-content').innerHTML = markup;
  if (!$('#modal').open) $('#modal').showModal();
  ($('#modal').querySelector('[autofocus]') || $('#modal-title'))?.focus();
}
function ask(title, message, confirmLabel, dangerous = false) {
  return new Promise(resolve => {
    askResolve = resolve;
    modal(`<h2 id="modal-title" tabindex="-1">${escape(title)}</h2><p>${escape(message)}</p><div class="button-row">${button(confirmLabel,'accept',dangerous ? 'danger' : '')}${button('Go back','cancel','secondary','autofocus')}</div>`);
  });
}
$('#modal').addEventListener('close', () => {
  pendingScore = null;
  if (askResolve) { const resolve = askResolve; askResolve = null; resolve(false); }
});
function scoreDialog(matchId, draft = null) {
  lastScoreTriggerId = matchId;
  const match = makeSchedule(tournament.teams,tournament.courts).find(m=>m.id===matchId);
  if (!match) throw new Error('That game is not on this schedule.');
  const byId = new Map(tournament.teams.map(team=>[team.id,teamName(team)]));
  const saved = tournament.scores[match.id];
  const scores = draft || saved || ['', ''];
  pendingScore = { match, a:byId.get(match.a), b:byId.get(match.b), scores:null };
  modal(`<h2 id="modal-title" tabindex="-1">${saved ? 'Correct the score' : 'How did the game go?'}</h2><p class="hint">Court ${match.court} · game ${match.id.slice(1)} · to ${tournament.target}, win by 2</p><form data-form="score"><div class="score-inputs"><div><label for="score-a">${escape(pendingScore.a)}</label><input id="score-a" name="a" type="number" inputmode="numeric" min="0" max="999" step="1" required value="${scores[0]}" autofocus></div><div><label for="score-b">${escape(pendingScore.b)}</label><input id="score-b" name="b" type="number" inputmode="numeric" min="0" max="999" step="1" required value="${scores[1]}"></div></div><p class="form-error" role="alert" tabindex="-1"></p><div class="form-actions"><button class="button" type="submit">Review score →</button>${button('Cancel','cancel','secondary')}${saved ? button('Clear this score','clear-score','quiet small') : ''}</div></form>`);
}
function download(source, filename) {
  const url = URL.createObjectURL(new Blob([source],{type:'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = filename;
  document.body.append(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
}
function backup() {
  if (!tournament) return;
  const slug = tournament.name.normalize('NFKD').replace(/[^a-zA-Z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,50) || 'tournament';
  download(encodeBackup(tournament),`${slug}-${tournament.date}.json`);
  announce('Copy downloaded. Look in your Downloads folder, and keep it somewhere safe such as a USB stick.');
}
function print(kind) {
  if (!tournament?.scheduled) return;
  const t = tournament, matches = makeSchedule(t.teams,t.courts), count = Object.keys(t.scores).length + makeSchedule(t.teams,t.courts).filter(m=>isWalkover(t,m)).length;
  const names = new Map(t.teams.map(team=>[team.id,teamName(team)]));
  const groups = [...new Set(matches.map(m=>m.group))];
  const schedule = groups.map(group=>`<div class="print-group"><h2>Round ${group}</h2><table><thead><tr><th style="width:12%">Court</th><th>Side 1</th><th>Side 2</th><th style="width:18%">Score</th></tr></thead><tbody>${matches.filter(m=>m.group===group).map(m=>`<tr><td>${m.court}</td><td>${escape(names.get(m.a))}</td><td>${escape(names.get(m.b))}</td><td class="score-blank">${t.scores[m.id] ? t.scores[m.id].join(' – ') : '____ : ____'}</td></tr>`).join('')}</tbody></table></div>`).join('');
  $('#print-area').innerHTML = `<h1>${escape(t.name)}</h1><p>${escape(dateLabel(t.date))}${t.venue ? ` · ${escape(t.venue)}` : ''}</p><p>${kind==='schedule' ? `Round-robin schedule · to ${t.target}, win by 2. Start each round together after the previous round finishes. Take breaks as needed.` : `${count===matches.length ? 'Final' : 'In-progress'} standings · ${count} of ${matches.length} games scored. Ranked by wins, then point difference, then points scored; remaining ties share a place.`}</p>${kind==='schedule' ? schedule : resultsTable()}<p class="print-note">Printed ${escape(new Date().toLocaleString())} · Open Pickleball Tourney · A snapshot; later changes are not on this printout.</p>`;
  window.print();
}
async function replaceAllowed(label) {
  if (formDirty && !await ask('Leave these edits?', 'The fields you are editing have not been saved. Leave them behind?', 'Leave edits')) return false;
  if (!tournament && !corrupt) return true;
  return ask(`${label}?`, 'This replaces the tournament saved in this browser. Go back and download a copy first if you want to keep it.', label, true);
}
async function handleAction(action, node) {
  if (action==='accept') { const resolve = askResolve; askResolve=null; $('#modal').close(); resolve?.(true); return; }
  if (action==='cancel') { $('#modal').close(); return; }
  if (action==='home') return navigate('home');
  if (action==='navigate') return navigate(node.dataset.view);
  if (action.startsWith('go-')) return navigate(action.slice(3));
  if (action==='continue') return navigate(tournament.scheduled ? 'play' : tournament.teams.length ? 'teams' : 'setup');
  if (action==='backup') return backup();
  if (action==='raw') { download(store.raw(),'unreadable-tournament-original.json'); return; }
  if (action==='import') { $('#backup-file').value=''; $('#backup-file').click(); return; }
  if (action==='reload') {
    if ((unsaved || formDirty) && !await ask('Load the saved version?', 'Your unsaved edits in this tab will be replaced. Back them up first if you need them.', 'Load saved version',true)) return;
    try { tournament = store.read(); stale=false; unsaved=false; corrupt=false; formDirty=false; problemText=''; view='home'; render(); }
    catch (error) { showProblem(`The saved version could not be opened. ${error.message}`); }
    return;
  }
  if (action==='new') {
    if (!await replaceAllowed('Start a new tournament')) return;
    // Replacement was explicitly reviewed above; the new draft saves now.
    const next = { id:uuid(),name:'My pickleball tournament',date:today(),venue:'',mode:'doubles',courts:2,target:11,teams:[],scheduled:false,withdrawn:[],scores:{} };
    await commit(next); view='setup'; render(); $('#event-name').select(); return;
  }
  if (action==='sample') {
    if (!await replaceAllowed('Start a practice tournament')) return;
    await commit({ id:uuid(),name:'The Saturday Social · practice',date:today(),venue:'Neighborhood courts',mode:'doubles',courts:2,target:11,scheduled:true,withdrawn:[],scores:{},teams:[['Pat','Lee'],['Jo','Sam'],['Alex','Morgan'],['Robin','Casey']].map(players=>({id:uuid(),players})) });
    view='play'; render(); announce('Practice tournament ready. All names are examples.'); return;
  }
  if (action==='reuse') {
    if (!await replaceAllowed('Use this setup for a new day')) return;
    await change(t=>{t.id=uuid();t.date=today();t.name=`${t.name.replace(/ · next time$/,'').slice(0,85)} · next time`;t.scheduled=false;t.scores={};t.withdrawn=[];});
    view='setup'; render(); return;
  }
  if (action==='remove-team') {
    if (tournament.scheduled) throw new Error('Reset the schedule before changing the roster.');
    const team = tournament.teams.find(t=>t.id===node.dataset.id);
    if (!team || !await ask('Remove this entry?', `${teamName(team)} will be removed from the roster.`, 'Remove entry',true)) return;
    await change(t=>{t.teams=t.teams.filter(team=>team.id!==node.dataset.id);}); render(false); return;
  }
  if (action==='withdraw-team') {
    const team = tournament.teams.find(t=>t.id===node.dataset.id);
    if (!team) return;
    if (!await ask(`Withdraw ${teamName(team)}?`, 'Games already played stay on record. Each game still to play is cancelled: the other side gets the win, and no points are recorded. You can add them back later.', 'Withdraw entry', true)) return;
    await change(t=>{ if (!t.withdrawn.includes(team.id)) t.withdrawn.push(team.id); });
    render(false); announce(`${teamName(team)} withdrawn. Their remaining games are cancelled.`); return;
  }
  if (action==='reinstate-team') {
    const team = tournament.teams.find(t=>t.id===node.dataset.id);
    if (!team) return;
    await change(t=>{ t.withdrawn = t.withdrawn.filter(id=>id!==team.id); });
    render(false); announce(`${teamName(team)} added back. Their cancelled games can be played again.`); return;
  }
  if (action==='reset-schedule') {
    if (!await ask('Change the roster?', 'This clears the schedule, every saved score and any withdrawals. The player list and event details stay. Download a copy first to keep today’s results.', 'Clear schedule & scores',true)) return;
    await change(t=>{t.scheduled=false;t.scores={};t.withdrawn=[];}); render(); return;
  }
  if (action==='schedule') {
    if (formDirty && !await ask('Make the schedule without these names?', 'The names still in the entry fields have not been added. Go back to add them, or make the schedule using only the roster above.', 'Use the current roster')) return;
    await change(t=>{t.scheduled=true;}); view='play'; render(); announce('Your schedule is ready.'); return;
  }
  if (action==='score') { lastScoreTriggerId=node.dataset.id; scoreDialog(node.dataset.id); return; }
  if (action==='edit-score') { scoreDialog(pendingScore.match.id,pendingScore.scores); return; }
  if (action==='confirm-score') {
    if (!pendingScore?.scores) return;
    const {match,scores} = pendingScore;
    await change(t=>{t.scores[match.id]=scores;});
    pendingScore=null; $('#modal').close(); render(false); announce(unsaved ? 'Score is in this tab. Download a copy to keep it.' : 'Score saved. Standings updated.'); return;
  }
  if (action==='clear-score') {
    const matchId = pendingScore.match.id;
    if (!await ask('Clear this score?', 'This game will need a score again. If it is in an earlier group, that group becomes current again.', 'Clear score',true)) return;
    await change(t=>{delete t.scores[matchId];}); pendingScore=null; $('#modal').close(); render(false); return;
  }
  if (action==='confirm-import') {
    if (!pendingImport) return;
    await commit(pendingImport); pendingImport=null; $('#modal').close(); view=tournament.scheduled ? 'play' : 'teams'; render(); announce('Saved copy opened.'); return;
  }
  if (action==='print-schedule') return print('schedule');
  if (action==='print-results') return print('results');
  if (action==='help') {
    modal(`<h2 id="modal-title" tabindex="-1">A little help for a good day.</h2><ol><li><strong>Set up:</strong> name the event and choose your courts.</li><li><strong>Add teams:</strong> type names or paste a list. Partners stay together.</li><li><strong>Play:</strong> start one round at a time, then enter and review the scores.</li><li><strong>Results:</strong> see the standings and print them for everyone.</li></ol><p><strong>Where is my tournament?</strong> In this browser, on this device. Use the same website address to come back. Private browsing or clearing browser data can remove it.</p><p><strong>Keep a spare:</strong> “Download a copy” saves a file to your computer. “Open a saved copy” brings it back. Only one tournament is saved here at a time. Save your current one before starting another.</p><p><strong>At the courts:</strong> wait for the footer to say “Ready to reopen offline” before relying on offline use. Print a schedule with blank score spaces as a paper fallback.</p><p><strong>Made for community games:</strong> fixed singles or doubles entries, one round robin, up to 16 entries. Give people breaks as needed. No accounts or shared live editing.</p>${button('Got it','cancel','','autofocus')}`); return;
  }
}

document.addEventListener('click', async event => {
  const node = event.target.closest('[data-action]');
  if (!node || node.disabled) return;
  event.preventDefault();
  // Dialog answers must remain usable while the initiating action awaits them.
  const answer = ['accept','cancel'].includes(node.dataset.action);
  if (working && !answer) return;
  if (!answer) working=true;
  try { await handleAction(node.dataset.action,node); }
  catch (error) {
    showProblem(error.message);
    if ($('#modal').open) {
      let message = $('#modal .modal-error');
      if (!message) {
        message = document.createElement('p');
        message.className = 'form-error modal-error';
        message.setAttribute('role','alert');
        message.tabIndex = -1;
        $('#modal-title').after(message);
      }
      message.textContent = error.message;
      message.focus();
    }
    announce(error.message);
  }
  finally { if (!answer) working=false; }
});

document.addEventListener('submit', async event => {
  const form = event.target;
  if (!form.dataset.form) return;
  event.preventDefault();
  if (working) return;
  working=true;
  const data = new FormData(form);
  try {
    if (form.dataset.form==='setup') {
      const base = tournament || {id:uuid(),teams:[],scheduled:false,withdrawn:[],scores:{}};
      await commit({...base,name:data.get('name'),date:data.get('date'),venue:data.get('venue'),mode:data.get('mode')||base.mode,courts:data.has('courts')?Number(data.get('courts')):base.courts,target:data.has('target')?Number(data.get('target')):base.target});
      view = tournament?.scheduled ? 'play' : 'teams'; render(); announce(unsaved ? 'Details kept in this tab. Download a copy.' : 'Tournament details saved.');
    }
    if (form.dataset.form==='team' || form.dataset.form==='bulk') {
      if (tournament.scheduled) throw new Error('Reset the schedule before changing the roster.');
      const teams = form.dataset.form==='bulk' ? parseRoster(data.get('roster'),tournament.mode,uuid) : [{id:uuid(),players:tournament.mode==='doubles'?[data.get('one'),data.get('two')]:[data.get('one')]}];
      await change(t=>{t.teams.push(...teams);}); render(false); $('#player-one')?.focus(); announce(`${teams.length} ${teams.length===1?'entry':'entries'} added.`);
    }
    if (form.dataset.form==='score') {
      const a = Number(data.get('a')), b = Number(data.get('b'));
      pendingScore.scores = validateScore(a,b,tournament.target);
      const winner = a>b ? pendingScore.a : pendingScore.b;
      modal(`<h2 id="modal-title" tabindex="-1">Does this look right?</h2><div class="score-review"><p>${escape(pendingScore.a)} <strong>${a}</strong></p><p>${escape(pendingScore.b)} <strong>${b}</strong></p><strong>${escape(winner)} wins.</strong></div><p>Confirm to update the standings.</p><div class="button-row">${button('Confirm score','confirm-score','','autofocus')}${button('Change the numbers','edit-score','secondary')}${button('Cancel','cancel','quiet')}</div>`);
    }
  } catch (error) { errorAt(form,error); }
  finally { working=false; }
});

$('#main').addEventListener('input', event => { if (event.target.closest('form')) formDirty=true; });
$('#main').addEventListener('change', event => { if (event.target.closest('form')) formDirty=true; });
$('#backup-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    if (file.size>MAX_FILE_BYTES) throw new Error('Choose a tournament backup smaller than 100 KB.');
    pendingImport=decodeBackup(await file.text());
    const t = pendingImport;
    modal(`<h2 id="modal-title" tabindex="-1">Open this tournament?</h2><div class="score-review"><strong>${escape(t.name)}</strong><p>${escape(dateLabel(t.date))}<br>${t.teams.length} ${t.mode==='singles'?'players':'teams'} · ${Object.keys(t.scores).length} scores</p></div><p>${tournament||corrupt ? 'This replaces the tournament saved in this browser. Go back and download a copy first if you want to keep it.' : 'This saves the tournament in this browser, on this device.'}${formDirty?' Your unsubmitted form edits will also be replaced.':''}</p><div class="button-row">${button('Open this tournament','confirm-import','')}${button('Go back','cancel','secondary','autofocus')}</div>`);
  } catch (error) { pendingImport=null; showProblem(`${error.message} Your current tournament has not been replaced.`); }
});
window.addEventListener('beforeunload', event => {
  if (unsaved || formDirty || pendingScore && $('#modal').open) { event.preventDefault(); event.returnValue=''; }
});
function checkOtherTab() {
  if (store.changed()) { stale=true; showProblem('Another tab changed the saved tournament. Load its version before making more changes, or back up this tab first.'); status(); }
}
window.addEventListener('storage', event => { if (event.key===key || event.key===null) checkOtherTab(); });
window.addEventListener('focus',checkOtherTab);

async function offlineSetup() {
  if (document.body.dataset.portable !== undefined) { $('#offline-status').textContent='Offline copy: works without internet. Keep this folder where it is.'; return; }
  if (!document.body.dataset.worker || !('serviceWorker' in navigator)) return;
  try {
    const registration = await navigator.serviceWorker.register(document.body.dataset.worker);
    // install caches the complete shell before the worker can become active.
    await navigator.serviceWorker.ready;
    $('#offline-status').textContent='Ready to reopen offline in this browser.';
    registration.addEventListener('updatefound',()=>{
      const worker=registration.installing;
      worker?.addEventListener('statechange',()=>{
        if (worker.state==='installed' && navigator.serviceWorker.controller) $('#offline-status').textContent='An update is ready. Close all tournament tabs, then reopen.';
      });
    });
  } catch { $('#offline-status').textContent='Offline reopening unavailable. Keep this tab open or print your schedule.'; }
}
render(false);
offlineSetup();
