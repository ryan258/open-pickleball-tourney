import test from 'node:test';
import assert from 'node:assert/strict';
import { makeSchedule, isWalkover, validateTournament, validateScore, standings, encodeBackup, decodeBackup, parseRoster } from '../assets/js/engine.mjs';
import { createStore, ConflictError } from '../assets/js/storage.mjs';

const event = (count=4) => ({id:'event',name:'Saturday',date:'2026-10-05',venue:'Park',mode:'singles',courts:2,target:11,teams:Array.from({length:count},(_,i)=>({id:`t${i}`,players:[`Player ${i}`]})),scheduled:true,withdrawn:[],scores:{}});

test('every pair meets once, each entry gets n−1 games, and court groups never double-book',()=>{
  for (let n=2;n<=16;n++) for (let courts=1;courts<=8;courts++) {
    const teams=event(n).teams, matches=makeSchedule(teams,courts), pairs=new Set(), groups=new Map(), appearances=new Map();
    assert.equal(matches.length,n*(n-1)/2);
    for (const m of matches) {
      const pair=[m.a,m.b].sort().join('/'); assert(!pairs.has(pair)); pairs.add(pair);
      const group=groups.get(m.group)||{people:new Set(),courts:new Set()};
      assert(m.court>=1&&m.court<=courts); assert(!group.courts.has(m.court)); group.courts.add(m.court);
      for (const id of [m.a,m.b]) { assert(!group.people.has(id)); group.people.add(id); appearances.set(id,(appearances.get(id)||0)+1); }
      groups.set(m.group,group);
    }
    assert(teams.every(t=>appearances.get(t.id)===n-1));
    const minGroups = Math.max(Math.ceil(matches.length / Math.min(courts, Math.floor(n / 2))), n % 2 === 0 ? n - 1 : n);
    assert.equal(groups.size, minGroups);
  }
  assert.equal(new Set(makeSchedule(event(16).teams, 7).map(m => m.group)).size, 18);
  assert.equal(new Set(makeSchedule(event(8).teams, 3).map(m => m.group)).size, 10);
  assert.equal(new Set(makeSchedule(event(6).teams, 2).map(m => m.group)).size, 8);
});
test('completed scores stop at the first winning margin, including deuce',()=>{
  for (const target of [11,15,21]) {
    for (const scores of [[target,0],[target,target-2],[target+1,target-1],[target+8,target+6]]) assert.deepEqual(validateScore(...scores,target),scores);
    for (const scores of [[target-1,0],[target,target-1],[target+1,target-2],[target+7,0],[0,0],[-1,target],[1.5,target],[NaN,target]]) assert.throws(()=>validateScore(...scores,target));
  }
});
test('standings keep true ties and recalculate after correction or removal',()=>{
  const t=event(3); t.courts=1;
  // A three-way cycle, all games 11–9: all teams must share first place.
  for (const m of makeSchedule(t.teams,1)) {
    const winner = m.a==='t0'&&m.b==='t1'||m.a==='t1'&&m.b==='t0' ? 't0' : m.a==='t1'&&m.b==='t2'||m.a==='t2'&&m.b==='t1' ? 't1' : 't2';
    t.scores[m.id]=m.a===winner?[11,9]:[9,11];
  }
  assert(standings(t).every(row=>row.rank===1&&row.wins===1&&row.difference===0&&row.played===2));
  const first=makeSchedule(t.teams,1)[0]; t.scores[first.id]=[11,0];
  assert.equal(standings(t)[0].id,first.a);
  delete t.scores[first.id]; assert.equal(standings(t).reduce((sum,row)=>sum+row.played,0),4);
});
test('changing court count keeps every match ID on the same pairing, so scores stay valid',()=>{
  const t=event(6), pairs=courts=>new Map(makeSchedule(t.teams,courts).map(m=>[m.id,`${m.a}/${m.b}`]));
  for (let n=2;n<=16;n++) { t.teams=event(n).teams; const base=pairs(1); for (let c=2;c<=8;c++) assert.deepEqual(pairs(c),base); }
  t.teams=event(6).teams; t.courts=3; t.scores.m1=[11,7]; t.scores.m2=[11,9];
  t.courts=2;
  const kept=validateTournament(t);
  assert.deepEqual(kept.scores,{m1:[11,7],m2:[11,9]});
});
test('a withdrawal is a marked walkover: opponent wins, no points are invented, and it is reversible',()=>{
  const t=event(4); t.courts=2;
  const [first]=makeSchedule(t.teams,2); // t0 vs t3
  assert.deepEqual([first.a,first.b],['t0','t3']);
  t.scores[first.id]=[11,5]; t.withdrawn=['t3'];
  const kept=validateTournament(t), matches=makeSchedule(kept.teams,kept.courts);
  assert.deepEqual(kept.withdrawn,['t3']);
  assert.equal(matches.filter(m=>isWalkover(kept,m)).length,2);
  assert(!isWalkover(kept,first)); // a real result stays real
  const row=id=>standings(kept).find(r=>r.id===id);
  assert.deepEqual([row('t0').played,row('t0').wins,row('t0').for,row('t0').difference],[1,1,11,6]);
  for (const id of ['t1','t2']) assert.deepEqual([row(id).played,row(id).wins,row(id).walkovers,row(id).for,row(id).against],[1,1,1,0,0]);
  assert.deepEqual([row('t3').played,row('t3').wins,row('t3').losses,row('t3').for,row('t3').against,row('t3').withdrawn],[3,0,3,5,11,true]);
  assert.equal(standings(kept).at(-1).id,'t3'); assert.equal(row('t3').rank,null); // withdrawn: listed last, unranked
  assert.deepEqual(decodeBackup(encodeBackup(kept)).withdrawn,['t3']);
  const back={...kept,withdrawn:[]}; // reinstating restores unplayed games
  assert.equal(makeSchedule(back.teams,back.courts).filter(m=>isWalkover(back,m)).length,0);
  assert.equal(standings(back).reduce((sum,r)=>sum+r.played,0),2);
  const two=standings({...kept,withdrawn:['t2','t3']}); // t2 v t3: both gone, so no result for either
  assert.deepEqual(['t2','t3'].map(id=>two.find(r=>r.id===id).played),[2,2]);
});
test('withdrawn lists must name rostered entries once and need a schedule; older backups load without one',()=>{
  const t=event(4);
  for (const withdrawn of [['nobody'],['t1','t1'],'t1']) assert.throws(()=>validateTournament({...t,withdrawn}));
  assert.throws(()=>validateTournament({...t,scheduled:false,withdrawn:['t1']}));
  const {withdrawn,...legacy}=t; assert.deepEqual(validateTournament(legacy).withdrawn,[]);
});
test('backups round trip and reject malformed, foreign, oversized, and impossible records',()=>{
  const t=event(); t.scores.m1=[11,7];
  assert.deepEqual(decodeBackup(encodeBackup(t)),t);
  for (const change of [t=>t.date='2026-02-30',t=>t.teams[1].id=t.teams[0].id,t=>t.teams[1].players=['Player 0'],t=>t.scores.m999=[11,0],t=>t.scores.m1=[11,10],t=>t.courts=0,t=>t.scheduled=false,t=>t.teams=[],t=>t.teams[0].players=['Pat','Lee']]) {
    const bad=structuredClone(t); change(bad); assert.throws(()=>validateTournament(bad));
  }
  assert.throws(()=>decodeBackup('{oops')); assert.throws(()=>decodeBackup('x'.repeat(100001)));
  assert.throws(()=>decodeBackup(JSON.stringify({format:'django',version:1,tournament:t})));
  assert.throws(()=>decodeBackup(JSON.stringify({format:'open-pickleball-browser',version:2,tournament:t})));
  const dirty={...t,html:'<script>bad</script>',standings:[{rank:1}],schedule:[]};
  assert.deepEqual(validateTournament(dirty),t);
  assert.equal(parseRoster('Pat / Lee\nJo / Sam','doubles',()=> 'id').length,2);
  assert.deepEqual(parseRoster('Pat and Lee\nJo & Sam\nAl + Bo\nAndy Anders / Lee\nPat AND Jo','doubles',()=> 'id').map(t=>t.players),[['Pat','Lee'],['Jo','Sam'],['Al','Bo'],['Andy Anders','Lee'],['Pat','Jo']]);
  assert.deepEqual(parseRoster('Sandy / Pat','singles',()=> 'id').map(t=>t.players),[['Sandy / Pat']]);
  assert.throws(()=>parseRoster('Pat / Lee\nJo','doubles',()=> 'id'),/Line 2/);
});
test('storage preserves the old copy on failure and rejects a stale tab',async()=>{
  const t=event(); let raw=encodeBackup(t), failWrite=false;
  const storage={getItem:()=>raw,setItem:(_key,value)=>{if(failWrite)throw new Error('Quota exceeded');raw=value;}};
  let chain=Promise.resolve();
  const locks={request:(_key,fn)=>{const job=chain.then(fn);chain=job.catch(()=>{});return job;}};
  const first=createStore(storage,locks,'event'),second=createStore(storage,locks,'event');
  first.read(); second.read();
  const next={...t,name:'Changed'}; failWrite=true;
  await assert.rejects(first.save(next),/Quota/); assert.deepEqual(decodeBackup(raw),t);
  failWrite=false; await first.save(next);
  await assert.rejects(second.save({...t,name:'Stale overwrite'}),ConflictError); assert.equal(decodeBackup(raw).name,'Changed');
  second.read(); await second.save({...next,name:'Reloaded'}); assert.equal(decodeBackup(raw).name,'Reloaded');
  const unavailable=createStore(storage,null,'event'); unavailable.read();
  await assert.rejects(unavailable.save(t),/browser/); assert.equal(decodeBackup(raw).name,'Reloaded');
});
test('simultaneous tabs serialize so exactly one different edit is saved',async()=>{
  let raw=encodeBackup(event()),chain=Promise.resolve();
  const storage={getItem:()=>raw,setItem:(_key,value)=>{raw=value;}};
  const locks={request:(_key,fn)=>{const job=chain.then(fn);chain=job.catch(()=>{});return job;}};
  const a=createStore(storage,locks,'event'),b=createStore(storage,locks,'event');a.read();b.read();
  const outcomes=await Promise.allSettled([a.save({...event(),name:'A'}),b.save({...event(),name:'B'})]);
  assert.equal(outcomes.filter(r=>r.status==='fulfilled').length,1);
  assert(outcomes.find(r=>r.status==='rejected').reason instanceof ConflictError);
});
test('deleting removes the saved copy but never another tab\'s newer work',async()=>{
  let raw=encodeBackup(event()),chain=Promise.resolve();
  const storage={getItem:()=>raw,setItem:(_key,value)=>{raw=value;},removeItem:()=>{raw=null;}};
  const locks={request:(_key,fn)=>{const job=chain.then(fn);chain=job.catch(()=>{});return job;}};
  const a=createStore(storage,locks,'event'),b=createStore(storage,locks,'event');a.read();b.read();
  await a.save({...event(),name:'Newer'});
  await assert.rejects(b.remove(),ConflictError); assert.equal(decodeBackup(raw).name,'Newer');
  b.read(); await b.remove(); assert.equal(raw,null); assert.equal(b.read(),null);
  await assert.rejects(createStore(storage,null,'event').remove(),/browser/);
});
