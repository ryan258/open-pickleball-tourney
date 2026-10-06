import { MAX_FILE_BYTES, validateTournament, teamName, validateScore, encodeBackup, decodeBackup, parseRoster, FORMAT_OPTIONS, formatType, socialFormat, formatLabel, sideName, formatStandings, formatSummary, poolsFor, competitionState, reviseTournament } from './engine.mjs';
import { createStore, ConflictError } from './storage.mjs';
import { GAME_MINUTES, planFormats, resultsText, boardModel } from './desk.mjs';

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
let tournament = null, view = location.hash === '#board' ? 'board' : 'home', unsaved = false, corrupt = false, stale = false, formDirty = false;
let pendingScore = null, pendingImport = null, askResolve = null, working = false, problemText = '';
let undo = null, planRows = [], wake = null, boardRaw = null;

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
  document.body.dataset.screen = view;
  const openSummaries = new Set([...document.querySelectorAll('#main details[open] summary')].map(s => s.textContent.trim()));
  const nav = $('#steps');
  nav.hidden = view === 'home' || view === 'board' || !tournament;
  nav.innerHTML = ['setup','teams','play','results'].map((step,index) => `<button data-action="navigate" data-view="${step}" ${view === step ? 'aria-current="step"' : ''} ${!tournament && index ? 'disabled' : ''}><span class="step-number">${index+1}</span>${['Set up','Add '+unit(),'Play','Results'][index]}</button>`).join('');
  $('#main').innerHTML = ({ home: homeView, setup: setupView, teams: teamsView, play: playView, results: resultsView, board: boardView })[view]();
  for (const details of document.querySelectorAll('#main details')) {
    const summary = details.querySelector('summary')?.textContent.trim();
    if (summary && openSummaries.has(summary)) details.open = true;
  }
  status();
  if (view === 'setup') renderPlan();
  keepAwake();
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
  const saved = tournament ? `<section class="saved-tournament" aria-label="Your saved tournament"><div><p class="eyebrow">PICK UP WHERE YOU LEFT OFF</p><h2>${escape(tournament.name)}</h2><p>${escape(dateLabel(tournament.date))} · ${tournament.teams.length} ${unit()}${tournament.scheduled ? ` · ${Object.keys(tournament.scores).length} scores saved` : ''}</p></div>${button('Continue tournament →','continue','')}</section>` : '';
  return `${saved}${corrupt ? `<div class="notice recovery-notice"><p>Your original saved data is still here.</p>${button('Download original data','raw','secondary')}</div>` : ''}
    <section class="hero">
      <div class="hero-copy">
        <h1 id="view-title" tabindex="-1"><span class="headline-line">You bring</span> <span class="headline-line">the people.</span> <span class="headline-line headline-red">We’ll sort</span> <span class="headline-line headline-red">the games.</span></h1>
        <p class="lead">A little less paperwork. A lot more play.<br>Run your neighborhood pickleball tournament, one easy step at a time.</p>
        <div class="hero-actions">${button('Start a tournament →','new','')}${button('Try a practice tournament','sample','secondary')}</div>
        <div class="practice-picker"><label for="practice-format">Practice format</label><select id="practice-format" aria-label="Practice format">${options(FORMAT_OPTIONS.map(([id,label])=>[id,label]),'round_robin')}</select></div>
        <p class="hero-note">No account needed. Your tournament stays on this device.</p>
      </div>
      <div class="hero-artwork" aria-hidden="true"><img src="${escape(document.body.dataset.poster)}" alt="" width="1448" height="1086" fetchpriority="high"></div>
      <div class="scoreboard" aria-label="An example match card, not a live tournament">
        <div class="scoreboard-top"><span>THE SATURDAY SOCIAL</span><span>EXAMPLE</span></div><span class="badge">COURT 1</span>
        <h2>Good game, everyone.</h2><p class="sample-note">A clear schedule. A simple scorecard.</p>
        <div class="sample-match"><div class="sample-team"><span>Pat &amp; Lee</span><strong>11</strong></div><div class="sample-team"><span>Jo &amp; Sam</span><strong>7</strong></div></div>
        <div class="scoreboard-bottom"><span>Game saved</span><span>Next game, please →</span></div>
      </div>
    </section>
    <section class="workflow" aria-label="How it works">
      <div class="workflow-intro"><p class="eyebrow">HOW IT WORKS</p><h2>Less organizing.<br>More pickleball.</h2></div>
      <div class="workflow-item"><span class="step-number">1</span><div><h3>Get everyone<br>together.</h3><p>Name your day, choose your courts, and add your players.</p></div></div>
      <div class="workflow-item"><span class="step-number">2</span><div><h3>Let’s play.</h3><p>Choose your format. See who’s up and enter each score.</p></div></div>
      <div class="workflow-item"><span class="step-number">3</span><div><h3>Make it a<br>regular thing.</h3><p>Print the results and use your setup again next time.</p></div></div>
      <img class="community-art" src="${escape(document.body.dataset.community)}" alt="" width="600" height="300" loading="lazy">
    </section>`;
}
function setupView() {
  const t = tournament, type = formatType(t), c = t.competition || { pools:2, advance:4, rounds:6, bronze:false };
  const disabled = t.scheduled ? 'disabled' : '';
  const planner = t.scheduled ? '' : `<div class="panel" id="planner"><p class="eyebrow">NOT SURE WHAT FITS?</p><h2>Plan by time.</h2><div class="form-grid"><div><label for="plan-who">Who is signing up?</label><select id="plan-who">${options([['fixed','Singles players or fixed teams'],['individuals','Individuals · partners rotate']],socialFormat(t)?'individuals':'fixed')}</select></div><div class="grid-two"><div><label for="plan-people">How many?</label><input id="plan-people" type="number" inputmode="numeric" min="2" max="16" value="${Math.min(16,Math.max(2,t.teams.length||8))}"></div><div><label for="plan-minutes">Minutes you have</label><input id="plan-minutes" type="number" inputmode="numeric" min="15" max="720" step="15" value="120"></div></div><div><label for="plan-game">Minutes per game</label><input id="plan-game" type="number" inputmode="numeric" min="5" max="60" value="${GAME_MINUTES[t.target]}"></div></div><div id="plan-results" aria-live="polite"></div><p class="hint">Rough estimates using your court count. Games run back to back; this tool does not time games.</p></div>`;
  return `${heading('STEP 1 · A PLAN FOR THE DAY', 'Let’s get your game on.', 'Choose a format, then add the people.')}<div class="workspace"><section class="panel"><form data-form="setup" class="form-grid">
    <div><label for="event-name">Tournament name</label><input id="event-name" name="name" required maxlength="100" value="${escape(t.name)}" autocomplete="off"></div>
    <div class="grid-two"><div><label for="event-date">Date</label><input id="event-date" name="date" type="date" required min="2000-01-01" max="2100-12-31" value="${t.date}"></div><div><label for="event-venue">Location (optional)</label><input id="event-venue" name="venue" maxlength="100" value="${escape(t.venue)}"></div></div>
    <div><label for="event-format">Tournament format</label><select id="event-format" name="format" ${disabled} aria-describedby="format-help">${options(FORMAT_OPTIONS.map(([id,label])=>[id,label]),type)}</select><p class="hint" id="format-help">${FORMAT_OPTIONS.find(([id])=>id===type)[2]}</p></div>
    <div class="grid-two"><div><label for="event-mode">Who’s playing?</label><select id="event-mode" name="mode" ${t.teams.length || socialFormat(t) ? 'disabled' : ''}>${options([['doubles','Fixed doubles · two per team'],['singles',socialFormat(t)?'Individual players · rotating doubles':'Singles · one player per side']],t.mode)}</select><p class="hint" id="mode-help">${socialFormat(t)?'Add one person per line. The tool makes doubles pairings.':t.teams.length?'Remove the roster to switch singles or doubles.':'Choose singles or fixed doubles.'}</p></div><div><label for="event-courts">How many courts?</label><select id="event-courts" name="courts" ${t.scheduled && socialFormat(t) ? 'disabled' : ''}>${options(Array.from({length:8},(_,i)=>[i+1,`${i+1} court${i?'s':''}`]),t.courts)}</select></div></div>
    <div data-formats="round_robin_playoff" ${type!=='round_robin_playoff'?'hidden':''}><label for="event-advance">Entries in the playoff</label><select id="event-advance" name="advance" ${disabled}>${options([2,4,8].map(n=>[n,`Top ${n}`]),c.advance)}</select></div>
    <div data-formats="pools" ${type!=='pools'?'hidden':''}><label for="event-pools">Number of pools</label><select id="event-pools" name="pools" ${disabled}>${options([[2,'2 pools · at least 4 entries'],[4,'4 pools · at least 8 entries']],c.pools)}</select><p class="hint">Top two active entries from each pool qualify. Pool standings stay separate. Review any ties before starting playoffs.</p></div>
    <div data-formats="single_elimination round_robin_playoff pools" ${!['single_elimination','round_robin_playoff','pools'].includes(type)?'hidden':''}><label for="event-bronze">Third place</label><select id="event-bronze" name="bronze" ${disabled}>${options([['no','Share third place · no extra game'],['yes','Play a bronze game after semifinals']],c.bronze?'yes':'no')}</select><p class="hint">A bronze game is offered when there are semifinals. This is not a full consolation bracket.</p></div>
    <div data-formats="rotating_partners king_queen" ${!socialFormat(t)?'hidden':''}><label for="event-rounds">How many rounds?</label><input id="event-rounds" name="rounds" type="number" min="1" max="30" value="${c.rounds}" ${disabled}><p class="hint">Rotating partners: 4–16 people, with balanced rest turns. King / queen: exactly 4 per court, up to 16. Social court counts stay fixed after starting; the ladder also needs a full roster. Court 1 is highest.</p></div>
    <div><label for="event-target">Play each game to</label><select id="event-target" name="target" ${disabled}>${options([11,15,21].map(n=>[n,`${n} points · win by 2`]),t.target)}</select><p class="hint">One game per match. These are casual house rules. Take breaks whenever needed.</p></div>
    ${t.scheduled?'<p class="hint">Format and scoring are locked. Use “Change roster / format” on the roster step to clear the schedule before changing them.</p>':''}
    <p class="form-error" role="alert" tabindex="-1"></p><div class="form-actions"><button class="button" type="submit">Save & continue →</button>${button('Back to home','home','quiet')}</div>
  </form></section><aside class="stack">${planner}<div class="panel tint"><h2>A format for your day.</h2><p>Round robin and rotating partners keep people playing. Pools reduce preliminary games. Elimination brackets finish with a championship. The court ladder moves people after every round.</p><p class="hint">Fixed formats: 2–16 singles players or teams. Social formats: 4–16 individuals.</p></div><div class="panel"><h2>Your work stays with you.</h2><p>We save after each completed step and confirmed score. Return in the same browser, on this device. Download a copy to keep a spare.</p></div></aside></div>`;
}
function updateFormatFields() {
  const select = $('#event-format'); if (!select) return;
  const type = select.value, social = ['rotating_partners','king_queen'].includes(type);
  $('#format-help').textContent = FORMAT_OPTIONS.find(([key])=>key===type)[2];
  document.querySelectorAll('[data-formats]').forEach(node=>{node.hidden=!node.dataset.formats.split(' ').includes(type); node.querySelectorAll('input,select').forEach(field=>{field.disabled=node.hidden||tournament.scheduled;});});
  const mode = $('#event-mode');
  mode.disabled = Boolean(tournament.teams.length || social);
  if (social && !tournament.teams.length) mode.value='singles';
  mode.options[1].textContent=social?'Individual players · rotating doubles':'Singles · one player per side';
  $('#mode-help').textContent=social?(tournament.mode==='doubles'&&tournament.teams.length?'Remove the fixed-team roster before choosing a social format.':'Add one person per line. The tool makes doubles pairings.'):'Singles players compete alone. Fixed doubles partners stay together.';
}

function teamsView() {
  const t=tournament, type=formatType(t), social=socialFormat(t);
  const label=t.mode==='doubles'?'team':'player';
  const rounds=t.competition?.rounds??0, played=type==='rotating_partners'&&t.scheduled?Math.max(0,...competitionState(t).matches.filter(m=>m.score).map(m=>m.socialRound)):0;
  const windowNote=id=>{const w=t.windows?.[id]; return w&&(w[0]>1||w[1]!==null)?`<span class="badge neutral">${[w[0]>1?`Joins round ${w[0]}`:'',w[1]!==null?`Leaves after round ${w[1]}`:''].filter(Boolean).join(' · ')}</span>`:'';};
  const leaveButton=team=>type==='rotating_partners'&&played+1<rounds&&t.windows?.[team.id]?.[1]==null?button('Done for the day','leave-team','quiet small',`data-id="${team.id}" aria-label="${escape(teamName(team))} is done for the day"`):'';
  const lateForm=type==='rotating_partners'&&t.scheduled&&t.teams.length<16&&played<rounds?`<section class="panel"><form data-form="late" class="form-grid"><h2>Someone just arrived?</h2><div class="grid-two"><div><label for="late-name">Name</label><input id="late-name" name="one" maxlength="60" required autocomplete="off"></div><div><label for="late-round">Joins in round</label><select id="late-round" name="from">${options(Array.from({length:rounds-played},(_,i)=>[played+1+i,`Round ${played+1+i}`]),Math.min(rounds,played+2))}</select></div></div><p class="hint">Scored rounds never change. Pairings from the chosen round on include them, and they start level with the least-played person.</p><p class="form-error" role="alert" tabindex="-1"></p><button type="submit" class="button secondary">Add to the mixer</button></form></section>`:'';
  const list=t.teams.map((team,index)=>`<li class="team-item"><span class="team-label"><small>${social?'PLAYER':'SEED'} ${index+1}</small>${escape(teamName(team))}</span>${t.scheduled?windowNote(team.id):''}<div class="button-row">${!t.scheduled?`${button('↑','move-team','quiet small',`data-id="${team.id}" data-direction="-1" ${index===0?'disabled':''} aria-label="Move ${escape(teamName(team))} up"`)}${button('↓','move-team','quiet small',`data-id="${team.id}" data-direction="1" ${index===t.teams.length-1?'disabled':''} aria-label="Move ${escape(teamName(team))} down"`)}${button('Remove','remove-team','quiet small',`data-id="${team.id}" aria-label="Remove ${escape(teamName(team))}"`)}`:t.withdrawn.includes(team.id)?`<span class="badge neutral">Withdrawn</span>${button('Add back','reinstate-team','quiet small',`data-id="${team.id}" aria-label="Add back ${escape(teamName(team))}"`)}`:type!=='king_queen'?`${leaveButton(team)}${button('Withdraw','withdraw-team','quiet small',`data-id="${team.id}" aria-label="Withdraw ${escape(teamName(team))}"`)}`:''}</div></li>`).join('');
  let ready=true, reason='';
  try { validateTournament({...t,scheduled:true}); } catch(error) { ready=false; reason=error.message; }
  const poolPreview=type==='pools'&&t.teams.length?`<ul>${poolsFor(t).map(pool=>`<li><strong>${pool.name}:</strong> ${pool.teams.map(team=>escape(teamName(team))).join('; ')}</li>`).join('')}</ul>`:'';
  const bracketPreview=!t.scheduled&&ready&&['single_elimination','double_elimination'].includes(type)?`<ul>${competitionState({...t,scheduled:true}).matches.filter(m=>m.id.startsWith('e-w1-')).map(m=>`<li>${escape(sideName(t,m,'a'))} vs ${escape(sideName(t,m,'b'))}</li>`).join('')}</ul>`:'';
  return `${heading('STEP 2 · THE GOOD COMPANY',`Add your ${unit()}.`,`${escape(formatLabel(t))}. ${social?'List individuals; partners are assigned for you.':'Roster order is seeding order. Use the arrows to move an entry.'}`)}<div class="workspace"><div class="stack"><section class="panel"><h2>${t.teams.length} ${unit()} on the list</h2>${list?`<ul class="team-list">${list}</ul>`:'<p class="muted">Add names below, individually or as a pasted list.</p>'}${t.scheduled?`<p class="hint">${type==='king_queen'?'The ladder needs a full roster. For an absence, download a copy and restart with a complete roster.':`Withdrawals keep played games. Later affected results are reviewed before anything is cleared.${type==='rotating_partners'?' “Done for the day” instead removes someone from rounds not yet scored, without forfeiting their games.':''}`}</p>${button('Change roster / format','reset-schedule','secondary')}`:''}</section>
  ${lateForm}${!t.scheduled&&t.teams.length<16?`<section class="panel"><form data-form="team" class="form-grid"><h2>Add a ${label}</h2><div class="${t.mode==='doubles'?'grid-two':''}"><div><label for="player-one">${t.mode==='doubles'?'First player':'Player name'}</label><input id="player-one" name="one" maxlength="60" required autocomplete="off"></div>${t.mode==='doubles'?'<div><label for="player-two">Second player</label><input id="player-two" name="two" maxlength="60" required autocomplete="off"></div>':''}</div><p class="form-error" role="alert" tabindex="-1"></p><button type="submit" class="button secondary">Add ${label}</button></form><details${t.teams.length?'':' open'}><summary>Have a list? Paste it all at once.</summary><form data-form="bulk" class="form-grid"><div><label for="roster-list">One ${label} per line</label><textarea id="roster-list" name="roster" maxlength="4000" required aria-describedby="roster-help" placeholder="${t.mode==='doubles'?'Pat and Lee&#10;Jo and Sam':'Pat&#10;Lee&#10;Jo'}"></textarea><p class="hint" id="roster-help">${t.mode==='doubles'?'Put “and”, “&” or “/” between partners.':'Enter each person on their own line.'} This adds to the list above.</p></div><p class="form-error" role="alert" tabindex="-1"></p><button type="submit" class="button secondary">Add this list</button></form></details></section>`:''}</div>
  <aside class="panel tint"><p class="eyebrow">SCHEDULE PREVIEW</p><h2>${escape(formatLabel(t))}</h2><p>${escape(formatSummary(t))}</p>${poolPreview}${bracketPreview}<p class="hint">${social?'Mixer rests are balanced; partner repeats may be necessary. The ladder changes courts after completed rounds.':'Seeds follow roster order. Byes advance without a played win. Scores can change playoff qualifiers.'}</p>${!ready?`<p role="status">${escape(reason)}</p>`:''}${button(t.scheduled?'Go to the games →':'Make the schedule →',t.scheduled?'go-play':'schedule','',!ready?'disabled':'')}</aside></div>`;
}

function matchCard(match) {
  const t=tournament, score=match.score, a=sideName(t,match,'a'), b=sideName(t,match,'b');
  return `<article class="court-card"><div class="court-head"><span>COURT ${match.court}</span><span>${score?'SCORE SAVED':'READY TO PLAY'}</span></div><div class="court-body"><p class="hint">${escape(match.label)}</p><div class="match-side"><span>${escape(a)}</span><b>${score?score[0]:'—'}</b></div><div class="versus">VERSUS</div><div class="match-side"><span>${escape(b)}</span><b>${score?score[1]:'—'}</b></div>${button(score?'Correct score':'Enter score','score',score?'secondary':'',`data-id="${match.id}" aria-label="${score?'Correct':'Enter'} score for court ${match.court}, ${escape(a)} versus ${escape(b)}"`)}</div></article>`;
}
function qualificationPanel(state) {
  if (!state.needsAdvancement) return '';
  return `<section class="panel tint"><h2>Review the playoff qualifiers</h2><p>Standings set the order. For equal places, choose the order explicitly. Only tied entries can swap. ${formatType(tournament)==='pools'?'The top two active entries in each pool advance.':`The top ${tournament.competition.advance} active entries advance.`}</p><form data-form="advancement" class="form-grid">${state.groups.map(group=>{
    const rows=group.rows.filter(row=>!row.withdrawn);
    return `<fieldset><legend>${escape(group.name)}</legend>${rows.map((row,i)=>{
      const tied=rows.filter(other=>other.rank===row.rank), key=`advance-${group.key}-${i}`;
      return `<div><label for="${key}">Position ${i+1}${tied.length>1?' · tied, choose order':''}</label><select id="${key}" name="${key}" required>${tied.length>1?'<option value="">Choose a tied entry</option>':''}${options(tied.map(other=>[other.id,other.name]),tied.length===1?row.id:'')}</select></div>`;
    }).join('')}${rows.length?'':'<p>No active entries in this pool.</p>'}</fieldset>`;
  }).join('')}<p class="form-error" role="alert" tabindex="-1"></p><button class="button" type="submit">Confirm qualifiers & start playoffs →</button></form></section>`;
}
function scheduleMarkup(state) {
  const t=tournament, activeGroup=state.current[0]?.group;
  return [...new Set(state.matches.map(m=>m.group))].map(group=>`<div class="schedule-group"><h3>${escape(state.matches.find(m=>m.group===group).stage)} · court group ${group}</h3>${state.matches.filter(m=>m.group===group).map(m=>`<div class="schedule-row"><small>${m.status==='bye'?'Bye':`Court ${m.court}`}</small><p>${escape(sideName(t,m,'a'))}<br><small>vs.</small> ${escape(sideName(t,m,'b'))}</p>${m.score?button(`${m.score.join(' – ')} · Correct`,'score','small secondary',`data-id="${m.id}" aria-label="Correct ${escape(m.label)}"`):`<span class="badge neutral">${m.status==='bye'?'Automatic advance':m.status==='walkover'?m.winner.length?`Walkover · ${escape(m.winner.map(id=>teamName(t.teams.find(team=>team.id===id))).join(' & '))} advances`:'Cancelled · both sides withdrawn':m.status==='blocked'?'Awaiting earlier results':m.group===activeGroup?'Playing now':'Waiting'}</span>`}</div>`).join('')}</div>`).join('');
}
function playView() {
  const t=tournament;
  if (!t.scheduled) return `${heading('STEP 3 · LET’S PLAY','Your courts are nearly ready.')}<div class="panel empty"><h2>First, make your schedule.</h2>${button('Go to the roster →','go-teams','')}</div>`;
  const state=competitionState(t), count=state.matches.filter(m=>m.score).length, walkovers=state.matches.filter(m=>m.status==='walkover').length;
  const resting=t.teams.filter(team=>!t.withdrawn.includes(team.id)&&!state.current.some(m=>[...m.a,...m.b].includes(team.id)));
  return `${heading(escape(t.name),state.finished?'That’s a wrap. Good games!':'A good day on the courts.',`${escape(formatLabel(t))} · ${escape(dateLabel(t.date))}`,button('Display board','open-board','secondary small')+button('Print schedule','print-schedule','secondary small'))}<div class="stat-strip"><div><strong>${count}</strong><span>games scored${walkovers?` · ${walkovers} walkovers`:''}</span></div><div><strong>${t.teams.length}</strong><span>${unit()}</span></div><div><strong>${t.target}</strong><span>points · win by 2</span></div></div>
  ${undo?`<p class="notice" role="status">Saved: ${escape(undo.label)}. ${button('Undo','undo','small secondary')}</p>`:''}${qualificationPanel(state)}${state.current.length?`<div class="section-heading"><h2>${escape(state.current[0].stage)} · on court</h2></div><p class="hint">Start this group together. Finish every game here before the next group, and take breaks as needed.</p><div class="court-grid">${state.current.map(matchCard).join('')}</div>${resting.length?`<p class="hint">Off court this group: ${resting.map(team=>escape(teamName(team))).join('; ')}.</p>`:''}`:state.finished?`<section class="panel tint"><h2>Every game is resolved.</h2><div class="button-row">${button('See the results →','go-results','')}${button('Share results','share','secondary')}${button('Download a copy','backup','secondary')}</div></section>`:''}
  <details><summary>Full schedule & score corrections</summary><p class="hint">Future opponents depend on earlier results. Corrections show any later scores that need clearing. ${formatType(t)==='double_elimination'?'A reset final appears only if the lower-bracket finalist wins the first final.':''}${formatType(t)==='king_queen'?'The next round appears after every score in the current round is confirmed.':''}</p>${scheduleMarkup(state)}</details>`;
}
function resultsTable(rows = formatStandings(tournament,competitionState(tournament)), caption='Tournament results') {
  return `<div class="table-wrap" role="region" aria-label="${escape(caption)}" tabindex="0"><table><caption>${escape(caption)}</caption><thead><tr><th scope="col">Place</th><th scope="col">${tournament.mode==='doubles'?'Team':'Player'}</th><th scope="col">Played</th><th scope="col">Won</th><th scope="col" class="optional-column">Lost</th><th scope="col"><abbr title="Points scored minus points conceded">Point margin</abbr></th><th scope="col" class="optional-column">Points scored</th></tr></thead><tbody>${rows.map(row=>`<tr><td><span class="place">${row.rank??'—'}</span></td><td class="name">${escape(row.name)}${row.withdrawn?' <span class="badge neutral">Withdrawn</span>':''}</td><td>${row.played}</td><td>${row.wins}</td><td class="optional-column">${row.losses}</td><td>${row.difference>0?'+':''}${row.difference}</td><td class="optional-column">${row.for}</td></tr>`).join('')}</tbody></table></div>`;
}
function resultsExplanation() {
  const type=formatType(tournament);
  if (type==='rotating_partners') return 'Individual places use win percentage, average point margin, then average points scored, so rest turns do not reward playing more games. The table shows raw totals. Remaining ties share a place.';
  if (type==='king_queen') return 'Final places follow the last round: winning partners on Court 1 share first, losing partners share third; each lower court follows in order. Places appear only after every round is complete.';
  if (type==='round_robin') return 'Ranked by wins, point margin, then points scored. Remaining ties share a place. Walkovers award a win without adding points. Withdrawn entries are unranked.';
  return 'Final places follow bracket finishes, not total wins. They appear after every game is resolved. Entries eliminated in the same round share a place unless a bronze game separates them. Pool-only entries and withdrawn entries have no bracket place. Walkovers add no points.';
}
function resultsContent(state) {
  return `${resultsTable()}<p class="hint">${resultsExplanation()}</p>${state.groups.map(group=>`<div style="margin-top:2rem">${resultsTable(group.rows,`${group.name} · preliminary standings`)}</div>`).join('')}`;
}
function resultsView() {
  if (!tournament.scheduled) return `${heading('STEP 4 · THE RESULTS','The best part is still ahead.')}<div class="panel empty">${button('Go to the roster →','go-teams','')}</div>`;
  const state=competitionState(tournament), count=state.matches.filter(m=>m.score).length;
  return `${heading(state.finished?'THE RESULTS ARE IN':'TOURNAMENT IN PROGRESS',tournament.name,`${escape(formatLabel(tournament))} · ${count} games scored. ${state.finished?'Every game is resolved.':state.needsAdvancement?'Review qualifiers on the Play step.':'More games remain.'}`,button('Print results','print-results','secondary small'))}<section class="panel">${resultsContent(state)}</section><div class="button-row" style="margin-top:1.5rem">${button('Print results','print-results','')}${button('Share results','share','secondary')}${button('Download a copy','backup','secondary')}${button('Back to the games','go-play','secondary')}${button('Use this setup next time','reuse','secondary')}</div>`;
}

const hoursText = m => m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`;
function renderPlan() {
  const box = $('#plan-results'); if (!box) return;
  const entries = Number($('#plan-people').value), minutes = Number($('#plan-minutes').value), perGame = Number($('#plan-game').value), courts = Number($('#event-courts').value);
  if (!(entries >= 2 && entries <= 16 && minutes >= 1 && perGame >= 1)) { box.innerHTML = '<p class="hint">Enter 2–16 people, your time and minutes per game.</p>'; planRows = []; return; }
  planRows = planFormats({ entries, courts, minutes, perGame, individuals: $('#plan-who').value === 'individuals' });
  box.innerHTML = planRows.length ? `<ul class="plan-list">${planRows.map((row, i) => `<li${row.suggested ? ' class="suggested"' : ''}><strong>${escape(row.label)}</strong>${row.suggested ? ` <span class="badge">${row.fits ? 'SUGGESTED' : 'FASTEST'}</span>` : ''}<span class="hint">About ${hoursText(row.minutes)} · ${row.fits ? 'fits your time' : 'longer than your time'} · ${escape(row.detail)}</span>${button('Use this', 'use-plan', 'small secondary', `data-index="${i}"`)}</li>`).join('')}</ul>` : '<p class="hint">Rotating formats need at least four people.</p>';
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return; } catch { /* fall back below */ }
  const area = document.createElement('textarea'); area.value = text; document.body.append(area); area.select();
  const ok = document.execCommand('copy'); area.remove();
  if (!ok) throw new Error('This browser blocked copying. Print the results instead.');
}
// Keep the screen on while courts are being run. Unsupported or refused: nothing changes.
async function keepAwake() {
  if (!['play', 'board'].includes(view)) { wake?.release().catch(() => {}); wake = null; return; }
  try {
    if (document.visibilityState !== 'visible' || wake) return;
    wake = await navigator.wakeLock?.request('screen') ?? null;
    wake?.addEventListener('release', () => { wake = null; });
  } catch { wake = null; }
}
document.addEventListener('visibilitychange', keepAwake);
function boardView() {
  const t = tournament;
  if (!t?.scheduled) return `<div class="board"><h1 id="view-title" tabindex="-1">${t ? escape(t.name) : 'No tournament yet'}</h1><p class="board-note">Waiting for the schedule. This screen updates by itself.</p></div>`;
  const state = competitionState(t), { now, next, finished } = boardModel(state);
  const row = m => `<li class="board-game"><span class="board-court">${m.status === 'blocked' ? 'LATER' : `COURT ${m.court}`}</span><span class="board-side">${escape(sideName(t, m, 'a'))}</span><span class="board-vs">vs</span><span class="board-side">${escape(sideName(t, m, 'b'))}</span>${m.score ? `<b class="board-score">${m.score.join(' – ')}</b>` : ''}</li>`;
  return `<div class="board"><p class="eyebrow">${escape(t.name)} · ${escape(formatLabel(t))}</p><h1 id="view-title" tabindex="-1">${finished ? 'That’s a wrap!' : now.length ? 'On court now' : 'Next up'}</h1>${finished ? resultsTable() : `<ul class="board-list">${now.map(row).join('')}</ul>${next.length ? `<h2>Up next</h2><ul class="board-list next">${next.map(row).join('')}</ul>` : ''}`}<p class="board-note">Updates by itself from the organizer's screen.</p></div>`;
}
function refreshBoard() {
  try { const latest = store.read(); if (store.raw() !== boardRaw) { boardRaw = store.raw(); tournament = latest; render(false); } } catch { /* keep the last good screen */ }
}
const contrastKey = 'open-pickleball-browser:contrast';
function applyContrast(on) {
  document.documentElement.dataset.contrast = on ? 'high' : '';
  document.querySelector('[data-action="contrast"]')?.setAttribute('aria-pressed', String(on));
}
try { applyContrast(storage.getItem(contrastKey) === '1'); } catch { /* preference simply not remembered */ }

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
  lastScoreTriggerId=matchId;
  const match=competitionState(tournament).matches.find(m=>m.id===matchId);
  if (!match || !['ready','scored'].includes(match.status)) throw new Error('That game is not ready for a score.');
  const saved=match.score, scores=draft||saved||['',''];
  pendingScore={match,a:sideName(tournament,match,'a'),b:sideName(tournament,match,'b'),scores:null};
  modal(`<h2 id="modal-title" tabindex="-1">${saved?'Correct the score':'How did the game go?'}</h2><p class="hint">Court ${match.court} · ${escape(match.label)} · to ${tournament.target}, win by 2</p><form data-form="score"><div class="score-inputs"><div><label for="score-a">${escape(pendingScore.a)}</label><input id="score-a" name="a" type="number" inputmode="numeric" min="0" max="999" step="1" required value="${scores[0]}" autofocus></div><div><label for="score-b">${escape(pendingScore.b)}</label><input id="score-b" name="b" type="number" inputmode="numeric" min="0" max="999" step="1" required value="${scores[1]}"></div></div><p class="form-error" role="alert" tabindex="-1"></p><div class="form-actions"><button class="button" type="submit">Review score →</button>${button('Cancel','cancel','secondary')}${saved?button('Clear this score','clear-score','quiet small'):''}</div></form>`);
}
function changeConsequences(plan) {
  const matches=competitionState(tournament).matches;
  return `${plan.advancementReset?'Playoff qualification will need review again. ':''}${plan.cleared.length?`${plan.cleared.length} later score${plan.cleared.length===1?'':'s'} will be cleared: ${plan.cleared.map(id=>matches.find(m=>m.id===id)?.label||id).join('; ')}.`:'Other saved scores stay.'}`;
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
  const t=tournament, state=competitionState(t);
  const schedule=[...new Set(state.matches.map(m=>m.group))].map(group=>`<div class="print-group"><h2>${escape(state.matches.find(m=>m.group===group).stage)} · group ${group}</h2><table><thead><tr><th>Court</th><th>Side 1</th><th>Side 2</th><th>Score / status</th></tr></thead><tbody>${state.matches.filter(m=>m.group===group).map(m=>`<tr><td>${m.court}</td><td>${escape(sideName(t,m,'a'))}</td><td>${escape(sideName(t,m,'b'))}</td><td class="score-blank">${m.score?m.score.join(' – '):m.status==='bye'?'Bye · no game':m.status==='walkover'?'Walkover · no points':'____ : ____'}</td></tr>`).join('')}</tbody></table></div>`).join('');
  $('#print-area').innerHTML=`<h1>${escape(t.name)}</h1><p>${escape(dateLabel(t.date))} · ${escape(formatLabel(t))}${t.venue?` · ${escape(t.venue)}`:''}</p><p>${state.finished?'Final results':'Tournament in progress'} · one game to ${t.target}, win by 2. ${escape(formatSummary(t))}</p>${kind==='schedule'?`<p>Start each court group after the previous one finishes. Future opponents depend on results. Ladder rounds and any reset final are added as results arrive. Reprint after advancement or corrections.</p>${schedule}`:resultsContent(state)}<p class="print-note">Printed ${escape(new Date().toLocaleString())} · Open Pickleball Tourney · A snapshot; later changes are not on this printout.</p>`;
  window.print();
}
async function replaceAllowed(label) {
  if (formDirty && !await ask('Leave these edits?', 'The fields you are editing have not been saved. Leave them behind?', 'Leave edits')) return false;
  if (!tournament && !corrupt) return true;
  return ask(`${label}?`, 'This replaces the tournament saved in this browser. Go back and download a copy first if you want to keep it.', label, true);
}
async function handleAction(action, node) {
  if (['new','sample','reuse','confirm-import','reset-schedule','reload'].includes(action)) undo = null;
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
    const type=$('#practice-format')?.value||'round_robin';
    if (!await replaceAllowed('Start a practice tournament')) return;
    const social=['rotating_partners','king_queen'].includes(type), count=type==='round_robin'?4:8;
    const people=['Pat','Lee','Jo','Sam','Alex','Morgan','Robin','Casey','Ari','Jules','Drew','Kai','Taylor','Chris','Mel','Jesse'];
    await commit({id:uuid(),name:'The Saturday Social · practice',date:today(),venue:'Neighborhood courts',mode:social?'singles':'doubles',courts:2,target:11,scheduled:true,withdrawn:[],scores:{},competition:{type,pools:2,advance:4,rounds:3,bronze:false},teams:Array.from({length:count},(_,i)=>({id:uuid(),players:social?[people[i]]:people.slice(i*2,i*2+2)}))});
    view='play'; render(); announce('Practice tournament ready. All names are examples.'); return;
  }
  if (action==='move-team') {
    if (tournament.scheduled) throw new Error('Reset the schedule before changing seeds.');
    const index=tournament.teams.findIndex(team=>team.id===node.dataset.id), destination=index+Number(node.dataset.direction);
    if (index<0||destination<0||destination>=tournament.teams.length) return;
    await change(t=>{const [team]=t.teams.splice(index,1);t.teams.splice(destination,0,team);});
    render(false); document.querySelector(`[data-action="move-team"][data-id="${node.dataset.id}"]:not([disabled])`)?.focus(); announce('Seed order updated.'); return;
  }
  if (action==='reuse') {
    if (!await replaceAllowed('Use this setup for a new day')) return;
    await change(t=>{t.id=uuid();t.date=today();t.name=`${t.name.replace(/ · next time$/,'').slice(0,85)} · next time`;t.scheduled=false;t.scores={};t.withdrawn=[];delete t.scoreSides;delete t.advancement;delete t.qualifyingWithdrawn;});
    view='setup'; render(); return;
  }
  if (action==='remove-team') {
    if (tournament.scheduled) throw new Error('Reset the schedule before changing the roster.');
    const team = tournament.teams.find(t=>t.id===node.dataset.id);
    if (!team || !await ask('Remove this entry?', `${teamName(team)} will be removed from the roster.`, 'Remove entry',true)) return;
    await change(t=>{t.teams=t.teams.filter(team=>team.id!==node.dataset.id);}); render(false); return;
  }
  if (action==='withdraw-team' || action==='reinstate-team') {
    const team=tournament.teams.find(t=>t.id===node.dataset.id); if (!team) return;
    const withdrawn=action==='withdraw-team';
    const plan=reviseTournament(tournament,{type:'withdrawal',id:team.id,withdrawn});
    if ((withdrawn || plan.cleared.length || plan.advancementReset) && !await ask(`${withdrawn?'Withdraw':'Add back'} ${teamName(team)}?`, `${withdrawn?'Played games stay. Unplayed matchups involving this entry become walkovers; the other side advances without points. ': 'Cancelled games become playable again. '}${changeConsequences(plan)}`,withdrawn?'Withdraw entry':'Add back',Boolean(plan.cleared.length||withdrawn))) return;
    await commit(plan.tournament); render(false); announce(`${teamName(team)} ${withdrawn?'withdrawn':'added back'}.`); return;
  }
  if (action==='reset-schedule') {
    if (!await ask('Change the roster?', 'This clears the schedule, every saved score and any withdrawals. The player list and event details stay. Download a copy first to keep today’s results.', 'Clear schedule & scores',true)) return;
    await change(t=>{t.scheduled=false;t.scores={};t.withdrawn=[];delete t.scoreSides;delete t.advancement;delete t.qualifyingWithdrawn;}); render(); return;
  }
  if (action==='schedule') {
    if (formDirty && !await ask('Make the schedule without these names?', 'The names still in the entry fields have not been added. Go back to add them, or make the schedule using only the roster above.', 'Use the current roster')) return;
    await change(t=>{t.scheduled=true;}); view='play'; render(); announce('Your schedule is ready.'); return;
  }
  if (action==='score') { lastScoreTriggerId=node.dataset.id; scoreDialog(node.dataset.id); return; }
  if (action==='edit-score') { scoreDialog(pendingScore.match.id,pendingScore.scores); return; }
  if (action==='confirm-score') {
    if (!pendingScore?.scores) return;
    const done=pendingScore.match, shown=`${done.label} · ${pendingScore.scores.join(' – ')}`;
    await commit(pendingScore.plan.tournament); undo={id:done.id,score:done.score,label:shown};
    pendingScore=null; $('#modal').close(); render(false); announce(unsaved ? 'Score is in this tab. Download a copy to keep it.' : 'Score saved. Standings updated.'); return;
  }
  if (action==='clear-score') {
    const matchId=pendingScore.match.id, plan=reviseTournament(tournament,{type:'score',id:matchId,score:null});
    if (!await ask('Clear this score?',`This game will need a score again. ${changeConsequences(plan)}`,'Clear score',true)) return;
    await commit(plan.tournament); pendingScore=null; $('#modal').close(); render(false); return;
  }
  if (action==='confirm-import') {
    if (!pendingImport) return;
    await commit(pendingImport); pendingImport=null; $('#modal').close(); view=tournament.scheduled ? 'play' : 'teams'; render(); announce('Saved copy opened.'); return;
  }
  if (action==='leave-team') {
    const team=tournament.teams.find(t=>t.id===node.dataset.id); if (!team) return;
    const after=Math.max(0,...competitionState(tournament).matches.filter(m=>m.score).map(m=>m.socialRound))+1;
    const plan=reviseTournament(tournament,{type:'leave',id:team.id,after});
    if (!await ask(`${teamName(team)} is done for the day?`,`They finish round ${after} and sit out the rounds after it. Scored games stay. Pairings after round ${after} are re-made without them.`,'Remove from later rounds',true)) return;
    await commit(plan.tournament); render(false); announce(`${teamName(team)} will sit out after round ${after}.`); return;
  }
  if (action==='use-plan') {
    const choice=planRows[Number(node.dataset.index)]?.settings; if (!choice) return;
    const put=(id,value)=>{ const field=$(`#${id}`); if (field && value!==undefined) field.value=String(value); };
    put('event-format',choice.type); put('event-courts',choice.courts); put('event-rounds',choice.rounds); put('event-advance',choice.advance); put('event-pools',choice.pools);
    updateFormatFields(); formDirty=true; renderPlan(); announce(`${formatLabel({competition:{type:choice.type}})} selected. Save and continue when ready.`); return;
  }
  if (action==='undo') {
    if (!undo) return;
    const plan=reviseTournament(tournament,{type:'score',id:undo.id,score:undo.score});
    if ((plan.cleared.length||plan.advancementReset) && !await ask('Undo this score?',changeConsequences(plan),'Undo score',true)) return;
    await commit(plan.tournament); undo=null; render(false); announce('Last score undone.'); return;
  }
  if (action==='share') {
    const text=resultsText(tournament,competitionState(tournament),location.protocol==='https:'?location.origin+location.pathname:'');
    if (navigator.share) { try { await navigator.share({title:tournament.name,text}); return; } catch (error) { if (error.name==='AbortError') return; } }
    await copyText(text); announce('Results copied. Paste them into your group chat.'); return;
  }
  if (action==='open-board') {
    if (!window.open(`${location.href.split('#')[0]}#board`,'pickleball-board')) throw new Error('Your browser blocked the new window. Allow pop-ups for this page, then try again.');
    return;
  }
  if (action==='contrast') { const on=document.documentElement.dataset.contrast!=='high'; applyContrast(on); try { storage.setItem(contrastKey,on?'1':'0'); } catch { /* not remembered */ } return; }
  if (action==='print-schedule') return print('schedule');
  if (action==='print-results') return print('results');
  if (action==='help') {
    modal(`<h2 id="modal-title" tabindex="-1">A little help for a good day.</h2><ol><li><strong>Set up:</strong> name the event and choose your courts.</li><li><strong>Add teams:</strong> type names or paste a list. Fixed doubles stay together; social formats pair individuals each round.</li><li><strong>Play:</strong> start one round at a time, then enter and review the scores.</li><li><strong>Results:</strong> see the standings and print them for everyone.</li></ol><p><strong>Where is my tournament?</strong> In this browser, on this device. Use the same website address to come back. Private browsing or clearing browser data can remove it.</p><p><strong>Keep a spare:</strong> “Download a copy” saves a file to your computer. “Open a saved copy” brings it back. Only one tournament is saved here at a time. Save your current one before starting another.</p><p><strong>At the courts:</strong> wait for the footer to say “Ready to reopen offline” before relying on offline use. Print a schedule with blank score spaces as a paper fallback.</p><p><strong>Made for community games:</strong> seven formats: round robin, round robin into playoffs, pools into playoffs, single elimination, double elimination, rotating partners, and king/queen of the court. Up to 16 fixed entries or 16 social players. Give people breaks as needed. No accounts or shared live editing.</p>${button('Got it','cancel','','autofocus')}`); return;
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
      const type=data.get('format')||formatType(base), social=['rotating_partners','king_queen'].includes(type);
      const mode=social&&!base.teams.length?'singles':data.get('mode')||base.mode;
      const competition=base.scheduled?base.competition:{type,pools:Number(data.get('pools')??base.competition?.pools??2),advance:Number(data.get('advance')??base.competition?.advance??4),rounds:Number(data.get('rounds')??base.competition?.rounds??6),bronze:data.get('bronze')==='yes'};
      const next={...base,name:data.get('name'),date:data.get('date'),venue:data.get('venue'),mode,courts:data.has('courts')?Number(data.get('courts')):base.courts,target:data.has('target')?Number(data.get('target')):base.target};
      if (competition) next.competition=competition;
      if (!base.scheduled) { delete next.scoreSides; delete next.advancement; delete next.qualifyingWithdrawn; }
      await commit(next);
      view = tournament?.scheduled ? 'play' : 'teams'; render(); announce(unsaved ? 'Details kept in this tab. Download a copy.' : 'Tournament details saved.');
    }
    if (form.dataset.form==='team' || form.dataset.form==='bulk') {
      if (tournament.scheduled) throw new Error('Reset the schedule before changing the roster.');
      const teams = form.dataset.form==='bulk' ? parseRoster(data.get('roster'),tournament.mode,uuid) : [{id:uuid(),players:tournament.mode==='doubles'?[data.get('one'),data.get('two')]:[data.get('one')]}];
      await change(t=>{t.teams.push(...teams);}); render(false); $('#player-one')?.focus(); announce(`${teams.length} ${teams.length===1?'entry':'entries'} added.`);
    }
    if (form.dataset.form==='late') {
      const team={id:uuid(),players:[String(data.get('one'))]}, from=Number(data.get('from'));
      const plan=reviseTournament(tournament,{type:'join',team,from});
      if (!await ask(`Add ${team.players[0].trim()} in round ${from}?`,`Scored games stay as they are. Pairings from round ${from} on are re-made to include them.`,'Add to the mixer')) return;
      await commit(plan.tournament); render(false); $('#late-name')?.focus(); announce(`${team.players[0].trim()} added from round ${from}.`);
    }
    if (form.dataset.form==='advancement') {
      const state=competitionState(tournament); if (!state.needsAdvancement) throw new Error('Playoff qualification is not ready.');
      const advancement={};
      for (const group of state.groups) advancement[group.key]=group.rows.filter(row=>!row.withdrawn).map((_row,i)=>data.get(`advance-${group.key}-${i}`));
      await commit({...tournament,advancement,qualifyingWithdrawn:[...tournament.withdrawn]}); view='play'; render(); announce('Playoff qualifiers confirmed.');
    }
    if (form.dataset.form==='score') {
      const a = Number(data.get('a')), b = Number(data.get('b'));
      pendingScore.scores = validateScore(a,b,tournament.target);
      pendingScore.plan = reviseTournament(tournament,{type:'score',id:pendingScore.match.id,score:pendingScore.scores});
      const winner = a>b ? pendingScore.a : pendingScore.b;
      modal(`<h2 id="modal-title" tabindex="-1">Does this look right?</h2><div class="score-review"><p>${escape(pendingScore.a)} <strong>${a}</strong></p><p>${escape(pendingScore.b)} <strong>${b}</strong></p><strong>${escape(winner)} wins.</strong></div><p>${escape(changeConsequences(pendingScore.plan))}</p><div class="button-row">${button('Confirm score','confirm-score','','autofocus')}${button('Change the numbers','edit-score','secondary')}${button('Cancel','cancel','quiet')}</div>`);
    }
  } catch (error) { errorAt(form,error); }
  finally { working=false; }
});

$('#main').addEventListener('input', event => { if (event.target.closest('#planner')) return renderPlan(); if (event.target.closest('form')) formDirty=true; });
$('#main').addEventListener('change', event => {
  if (event.target.closest('#planner')) return renderPlan();
  if (event.target.closest('form')) formDirty=true;
  if (event.target.id==='event-format') updateFormatFields();
  if (event.target.id==='event-courts') renderPlan();
  if (event.target.id==='event-target') { const minutes=$('#plan-game'); if (minutes) minutes.value=GAME_MINUTES[event.target.value]; renderPlan(); }
});
$('#backup-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    if (file.size>MAX_FILE_BYTES) throw new Error('Choose a tournament backup smaller than 100 KB.');
    pendingImport=decodeBackup(await file.text());
    const t = pendingImport;
    modal(`<h2 id="modal-title" tabindex="-1">Open this tournament?</h2><div class="score-review"><strong>${escape(t.name)}</strong><p>${escape(dateLabel(t.date))}<br>${t.teams.length} ${t.mode==='singles'?'players':'teams'} · ${escape(formatLabel(t))} · ${Object.keys(t.scores).length} scores</p></div><p>${tournament||corrupt ? 'This replaces the tournament saved in this browser. Go back and download a copy first if you want to keep it.' : 'This saves the tournament in this browser, on this device.'}${formDirty?' Your unsubmitted form edits will also be replaced.':''}</p><div class="button-row">${button('Open this tournament','confirm-import','')}${button('Go back','cancel','secondary','autofocus')}</div>`);
  } catch (error) { pendingImport=null; showProblem(`${error.message} Your current tournament has not been replaced.`); }
});
window.addEventListener('beforeunload', event => {
  if (unsaved || formDirty || pendingScore && $('#modal').open) { event.preventDefault(); event.returnValue=''; }
});
function checkOtherTab() {
  if (view==='board') return refreshBoard();
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
if (view==='board') { boardRaw=store.raw(); setInterval(refreshBoard,3000); }
offlineSetup();
