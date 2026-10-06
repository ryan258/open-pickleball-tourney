import test from 'node:test';
import assert from 'node:assert/strict';
import { validateTournament, competitionState, reviseTournament, encodeBackup, decodeBackup, formatStandings, poolsFor, makeSchedule } from '../assets/js/engine.mjs';

const event = (type, n=8, settings={}) => validateTournament({id:'formats',name:'Format check',date:'2026-10-05',venue:'',mode:'singles',courts:2,target:11,scheduled:true,withdrawn:[],scores:{},teams:Array.from({length:n},(_,i)=>({id:`t${i+1}`,players:[`Player ${i+1}`]})),competition:{type,rounds:6,...settings}});
const score = (t,m,winner=0) => reviseTournament(t,{type:'score',id:m.id,score:winner?[7,11]:[11,7]}).tournament;
function complete(t, decide=()=>0) {
  for (let step=0;step<250;step++) {
    const state=competitionState(t);
    if (state.finished) return t;
    if (state.needsAdvancement) {
      const advancement=Object.fromEntries(state.groups.map(g=>[g.key,g.rows.filter(r=>!r.withdrawn).map(r=>r.id)]));
      t=validateTournament({...t,advancement,qualifyingWithdrawn:[...t.withdrawn]}); continue;
    }
    const m=state.current.find(m=>m.status==='ready');
    assert(m,`No ready match in ${t.competition.type}: ${JSON.stringify(state)}`);
    t=score(t,m,decide(m,step));
  }
  assert.fail('Competition did not finish within its match limit');
}
function integrity(t) {
  const state=competitionState(t), ids=new Set();
  for(const m of state.matches) {
    assert(!ids.has(m.id)); ids.add(m.id);
    assert(m.court>=1&&m.court<=t.courts);
    if(m.a&&m.b) assert.equal(new Set([...m.a,...m.b]).size,m.a.length+m.b.length);
    if(m.score) assert.equal(m.status,'scored');
  }
  for(const group of new Set(state.matches.map(m=>m.group))) {
    const courts=new Set(), players=new Set();
    for(const m of state.matches.filter(m=>m.group===group&&m.status!=='bye')) {
      assert(!courts.has(m.court)); courts.add(m.court);
      for(const id of [...(m.a||[]),...(m.b||[])]) { assert(!players.has(id)); players.add(id); }
    }
  }
  assert.equal(state.invalidScores.length,0);
  assert.deepEqual(decodeBackup(encodeBackup(t)),t);
  return state;
}

test('single elimination: 2–16 seeds, high-seed byes, real champion and stable pairings across court counts',()=>{
  for(let n=2;n<=16;n++) {
    const t=event('single_elimination',n), initial=competitionState(t);
    const size=2**Math.ceil(Math.log2(n)), byes=initial.matches.filter(m=>m.id.startsWith('e-w1')&&m.status==='bye');
    assert.equal(byes.length,size-n);
    assert.deepEqual(new Set(byes.flatMap(m=>m.winner)),new Set(t.teams.slice(0,size-n).map(t=>t.id)));
    const finished=complete(t), state=integrity(finished);
    assert.equal(Object.keys(finished.scores).length,n-1);
    assert.equal(state.champion.length,1);
    assert.equal(formatStandings(finished,state)[0].id,state.champion[0]);
    for(const courts of [1,3,8]) {
      const changed=validateTournament({...finished,courts});
      assert.deepEqual(competitionState(changed).matches.map(m=>[m.id,m.a,m.b]),state.matches.map(m=>[m.id,m.a,m.b]));
    }
  }
});

test('double elimination: every nonchampion has two losses, including 2-entry and non-power-of-two brackets',()=>{
  for(let n=2;n<=16;n++) for(const reset of [false,true]) {
    const finished=complete(event('double_elimination',n),m=>m.id==='e-final-1'&&reset?1:0), state=integrity(finished);
    const losses=new Map(finished.teams.map(t=>[t.id,0]));
    for(const m of state.matches.filter(m=>m.score)) losses.set(m.loser[0],losses.get(m.loser[0])+1);
    assert.equal(Object.keys(finished.scores).length,2*n-2+(reset?1:0));
    assert.equal(state.matches.some(m=>m.id==='e-reset-1'),reset);
    for(const [id,count] of losses) assert.equal(count,id===state.champion[0]?(reset?1:0):2);
    const rows=formatStandings(finished,state);
    assert.equal(rows[0].rank,1); assert.equal(rows[1].rank,2);
    assert(rows.every(r=>Number.isInteger(r.rank)&&r.rank>=1&&r.rank<=n));
  }
});

test('bronze game separates semifinal losers; without it they share third',()=>{
  for(const bronze of [false,true]) {
    const t=complete(event('single_elimination',8,{bronze})), state=integrity(t);
    assert.equal(Object.keys(t.scores).length,bronze?8:7);
    const ranks=formatStandings(t,state).map(r=>r.rank);
    assert.equal(ranks.filter(r=>r===3).length,bronze?1:2);
    assert.equal(ranks.filter(r=>r===4).length,bronze?1:0);
  }
});

test('pool seeding, separate standings, crossed qualifiers and uneven pools',()=>{
  for(const pools of [2,4]) for(let n=pools*2;n<=16;n++) {
    const initial=event('pools',n,{pools}), membership=poolsFor(initial);
    assert(Math.max(...membership.map(p=>p.teams.length))-Math.min(...membership.map(p=>p.teams.length))<=1);
    const t=complete(initial), state=integrity(t), qualifierPool=new Map(membership.flatMap((p,i)=>p.teams.map(t=>[t.id,i])));
    assert.equal(state.groups.length,pools);
    assert.equal(Object.keys(t.scores).length,membership.reduce((sum,p)=>sum+p.teams.length*(p.teams.length-1)/2,0)+pools*2-1);
    for(const m of state.matches.filter(m=>m.id.startsWith('e-w1'))) assert.notEqual(qualifierPool.get(m.a[0]),qualifierPool.get(m.b[0]));
  }
});

test('playoff qualification waits for all preliminary games and explicitly accepts only tied swaps',()=>{
  let t=event('round_robin_playoff',3,{advance:2});
  const early={...t,advancement:{all:['t1','t2','t3']}};
  assert.throws(()=>validateTournament(early),/order/);
  for(const m of competitionState(t).matches) {
    const winner=m.a[0]==='t1'&&m.b[0]==='t2'||m.a[0]==='t2'&&m.b[0]==='t1'?'t1':m.a[0]==='t2'&&m.b[0]==='t3'||m.a[0]==='t3'&&m.b[0]==='t2'?'t2':'t3';
    t=score(t,m,m.a[0]===winner?0:1);
  }
  let state=competitionState(t);
  assert(state.needsAdvancement); assert(!state.finished); assert(state.groups[0].rows.every(r=>r.rank===1));
  t=validateTournament({...t,advancement:{all:['t3','t2','t1']}});
  state=competitionState(t); assert.deepEqual(new Set(state.current[0].a.concat(state.current[0].b)),new Set(['t3','t2']));
  assert.throws(()=>validateTournament({...t,advancement:{all:['t3','t3','t1']}}),/order/);
  const done=complete(t), changed=reviseTournament(done,{type:'score',id:state.groups[0].matches[0].id,score:[11,0]});
  assert(changed.advancementReset); assert.equal(changed.cleared.length,1); assert(competitionState(changed.tournament).needsAdvancement);
  const ordered=competitionState(changed.tournament).groups[0].rows.map(r=>r.id);
  assert.throws(()=>validateTournament({...changed.tournament,advancement:{all:ordered.toReversed()}}),/order/);
});

test('rotating partners: 4–16 individuals, balanced rests, no player/court clashes, individual statistics',()=>{
  for(let n=4;n<=16;n++) for(const courts of [1,2,4,8]) {
    const t=validateTournament({...event('rotating_partners',n),courts}), state=integrity(t), counts=new Map(t.teams.map(t=>[t.id,0]));
    for(const m of state.matches) {assert.equal(m.a.length,2); assert.equal(m.b.length,2); for(const id of [...m.a,...m.b]) counts.set(id,counts.get(id)+1);}
    assert.equal(state.matches.length,6*Math.min(courts,Math.floor(n/4)));
    assert(Math.max(...counts.values())-Math.min(...counts.values())<=1);
  }
  const t=event('rotating_partners',4,{rounds:3}), state=competitionState(t), partners=new Set(state.matches.flatMap(m=>[m.a.toSorted().join('/'),m.b.toSorted().join('/')]));
  assert.equal(partners.size,6);
  const done=complete(t), rows=formatStandings(done,integrity(done));
  assert(rows.every(r=>r.played===3)); assert.equal(rows.reduce((n,r)=>n+r.for,0),3*18*2);
});

test('court ladder moves winners up, losers down, splits partners, and corrects dependent rounds',()=>{
  for(const n of [4,8,12,16]) {
    const t=validateTournament({...event('king_queen',8),teams:event('rotating_partners',n).teams,courts:n/4});
    let round=t; const first=competitionState(t).matches;
    for(const m of first) round=score(round,m);
    const next=competitionState(round).matches.filter(m=>m.socialRound===2);
    first.forEach((m,i)=>{
      const winning=m.a, losing=m.b;
      const up=next[Math.max(0,i-1)], down=next[Math.min(first.length-1,i+1)];
      assert(winning.every(id=>[...up.a,...up.b].includes(id))); assert(losing.every(id=>[...down.a,...down.b].includes(id)));
      assert(up.a.includes(winning[0])!==up.a.includes(winning[1]));
    });
    const done=complete(t), state=integrity(done), changed=reviseTournament(done,{type:'score',id:first[0].id,score:[7,11]});
    assert.equal(changed.cleared.length,(6-1)*(n/4));
    assert.equal(Object.keys(changed.tournament.scores).length,n/4);
    assert.equal(state.champion.length,2); assert.equal(formatStandings(done,state).filter(r=>r.rank===1).length,2);
    assert.throws(()=>reviseTournament(done,{type:'withdrawal',id:'t1',withdrawn:true}),/full roster/);
  }
});

test('correction removes changed opponents, preserves unrelated results, and can remove a reset final',()=>{
  const t=complete(event('single_elimination',8)), before=competitionState(t);
  const first=before.matches.find(m=>m.id==='e-w1-1'), plan=reviseTournament(t,{type:'score',id:first.id,score:[7,11]});
  assert.deepEqual(new Set(plan.cleared),new Set(['e-w2-1','e-w3-1']));
  assert.equal(Object.keys(plan.tournament.scores).length,5); assert(!competitionState(plan.tournament).finished);
  const same=reviseTournament(t,{type:'score',id:first.id,score:[11,0]}); assert.equal(same.cleared.length,0);
  const d=complete(event('double_elimination',4),m=>m.id==='e-final-1'?1:0);
  const corrected=reviseTournament(d,{type:'score',id:'e-final-1',score:[11,3]});
  assert.deepEqual(corrected.cleared,['e-reset-1']); assert(competitionState(corrected.tournament).finished);
});

test('withdrawals preserve played games, award no invented points, and reinstate with affected results cleared',()=>{
  for(const type of ['single_elimination','double_elimination','pools','round_robin_playoff','rotating_partners']) {
    let t=event(type), m=competitionState(t).current[0]; t=score(t,m);
    const withdrawn=reviseTournament(t,{type:'withdrawal',id:m.a[0],withdrawn:true}).tournament;
    assert.deepEqual(withdrawn.scores[m.id],t.scores[m.id]); integrity(withdrawn);
    const done=complete(withdrawn); integrity(done);
    const back=reviseTournament(done,{type:'withdrawal',id:m.a[0],withdrawn:false}); integrity(back.tournament);
    const rows=formatStandings(done,competitionState(done)); assert.equal(rows.find(r=>r.id===m.a[0]).rank,null);
  }
});

test('new backups are version 2, old backups remain version 1, and malformed or unreachable results are rejected',()=>{
  const old={id:'old',name:'Legacy',date:'2026-10-05',venue:'',mode:'singles',courts:2,target:11,teams:event('single_elimination',4).teams,scheduled:true,scores:{m1:[11,7]},withdrawn:[]};
  assert.deepEqual(decodeBackup(encodeBackup(old)),old); assert.equal(JSON.parse(encodeBackup(old)).version,1);
  for(const type of ['single_elimination','double_elimination','pools','round_robin_playoff','rotating_partners','king_queen']) {
    const t=event(type), m=competitionState(t).current[0], saved=score(t,m), source=JSON.parse(encodeBackup(saved));
    assert.equal(source.version,2); integrity(saved);
    assert.throws(()=>validateTournament({...saved,scoreSides:{...saved.scoreSides,[m.id]:'[["wrong"],["opponent"]]'}}),/opponents/);
    assert.throws(()=>validateTournament({...saved,scores:{...saved.scores,unknown:[11,7]}}),/opponents/);
    assert.throws(()=>decodeBackup(JSON.stringify({...source,version:1})),/version/);
  }
  const t=event('single_elimination');
  assert.throws(()=>validateTournament({...t,scores:{'e-w3-1':[11,7]},scoreSides:{'e-w3-1':'[["t1"],["t2"]]'}}),/opponents/);
  for(const competition of [{type:'unknown'},{type:'pools',pools:3},{type:'rotating_partners',rounds:31},{type:'single_elimination',bronze:'yes'}]) assert.throws(()=>validateTournament({...t,competition}));
  assert.throws(()=>event('rotating_partners',3),/four/);
  assert.throws(()=>event('king_queen',7),/exactly four/);
  assert.throws(()=>event('pools',3),/at least 4/);
  assert.throws(()=>validateTournament({...t,competition:{type:'rotating_partners'},mode:'doubles',teams:t.teams.map(x=>({...x,players:[...x.players,`Partner ${x.id}`]}))}),/individual/);
  assert.deepEqual(makeSchedule(old.teams,old.courts).find(m=>m.id==='m1').a,'t1');
});

test('confirmed pools keep their seeds and played playoff scores when someone withdraws during playoffs',()=>{
  let t=event('pools');
  while(!competitionState(t).needsAdvancement) t=score(t,competitionState(t).current.find(m=>m.status==='ready'));
  let state=competitionState(t);
  const advancement=Object.fromEntries(state.groups.map(g=>[g.key,g.rows.map(r=>r.id)]));
  t=validateTournament({...t,advancement,qualifyingWithdrawn:[]});
  const semi=competitionState(t).current[0]; t=score(t,semi);
  const plan=reviseTournament(t,{type:'withdrawal',id:semi.a[0],withdrawn:true});
  assert.equal(plan.advancementReset,false); assert.equal(plan.cleared.length,0);
  assert.deepEqual(plan.tournament.scores[semi.id],t.scores[semi.id]);
  assert.deepEqual(plan.tournament.advancement,t.advancement);
  integrity(complete(plan.tournament));
});

test('preliminary walkovers remain frozen after qualification and later reinstatement',()=>{
  let t=reviseTournament(event('round_robin_playoff',6),{type:'withdrawal',id:'t6',withdrawn:true}).tournament;
  while(!competitionState(t).needsAdvancement) t=score(t,competitionState(t).current.find(m=>m.status==='ready'));
  const advancement={all:competitionState(t).groups[0].rows.filter(r=>!r.withdrawn).map(r=>r.id)};
  t=validateTournament({...t,advancement,qualifyingWithdrawn:['t6']});
  const next=reviseTournament(t,{type:'withdrawal',id:'t6',withdrawn:false});
  assert(!next.advancementReset); assert.deepEqual(next.tournament.qualifyingWithdrawn,['t6']);
  assert(!competitionState(next.tournament).groups[0].rows.filter(r=>!r.withdrawn).some(r=>r.id==='t6'));
  integrity(complete(next.tournament));
});

test('varied double-elimination outcomes preserve the two-loss invariant',()=>{
  for(const n of [3,5,8,11,16]) for(let seed=1;seed<=4;seed++) {
    let value=seed;
    const t=complete(event('double_elimination',n),()=>{value=(Math.imul(value,1664525)+1013904223)>>>0;return value>>>31;});
    const state=integrity(t), losses=new Map(t.teams.map(team=>[team.id,0]));
    for(const m of state.matches.filter(m=>m.score)) losses.set(m.loser[0],losses.get(m.loser[0])+1);
    assert([...losses].every(([id,count])=>id===state.champion[0]?count<2:count===2));
  }
});
