// Paste into DevTools on a local preview with NO saved event. Uses only the real
// organizer controls and cleans up its own record. Returns a PASS/FAIL report.
(async () => {
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const pause = () => new Promise(resolve => setTimeout(resolve, 25));
  const until = async (condition, label) => { for(let i=0;i<120;i++) { if(condition()) return; await pause(); } throw new Error(`Timed out: ${label}`); };
  const key = () => Object.keys(localStorage).find(key => key.startsWith('open-pickleball-browser:'));
  if (key()) throw new Error('Use a fresh/private browser window; this one holds a saved event.');
  const report = [], check = (name, condition) => { if (!condition) throw new Error(name); report.push({check:name,result:'PASS'}); };
  const click = async selector => { const el=$(selector); if (!el || el.disabled) throw new Error(`Missing or disabled: ${selector}`); el.click(); await pause(); };
  const submit = async selector => { $(selector).requestSubmit(); await pause(); };
  const saved = () => JSON.parse(localStorage.getItem(key())).tournament;
  const errors = () => !$('#problem').hidden ? $('#problem').textContent : $$('.form-error').map(el=>el.textContent).filter(Boolean).join('; ');
  async function game(selector, a=11, b=7) {
    await click(selector); await until(()=>$('#score-a'),'score dialog'); $('#score-a').value=a; $('#score-b').value=b;
    await submit('[data-form="score"]'); await until(()=>$('[data-action="confirm-score"]'),'score review'); check('score review names a winner',/wins\./.test($('#modal-content').textContent));
    await click('[data-action="confirm-score"]'); await until(()=>!$('#modal').open,'score saved');
    if (errors()) throw new Error(errors());
  }
  async function finish() {
    for(let i=0;i<160;i++) {
      if($('[data-form="advancement"]')) {
        for(const fieldset of $$('[data-form="advancement"] fieldset')) {
          const used=new Set();
          for(const select of fieldset.querySelectorAll('select')) {
            select.value=[...select.options].find(option=>option.value&&!used.has(option.value)).value; used.add(select.value);
          }
        }
        await submit('[data-form="advancement"]'); await until(()=>!$('[data-form="advancement"]'),'playoff draw');
      } else if($('.court-card [data-action="score"]')) await game('.court-card [data-action="score"]:not(.secondary)');
      else if($('[data-action="go-results"]')) return;
      else throw new Error(`No next step: ${errors()||$('#main').textContent.slice(-300)}`);
    }
    throw new Error('Event did not complete');
  }
  const realPrint=window.print;
  try {
    for(const type of ['round_robin','round_robin_playoff','pools','single_elimination','double_elimination','rotating_partners','king_queen']) {
      if(!$('#practice-format')) await click('[data-action="home"]');
      $('#practice-format').value=type; await click('[data-action="sample"]');
      if($('#modal').open) await click('[data-action="accept"]');
      await until(()=>$$('.court-card').length>0&&!$('#modal').open,'practice event');
      check(`${type}: practice opens`,saved().competition.type===type&&$$('.court-card').length>0);
      await finish();
      check(`${type}: completes without errors`,!errors());
      await click('[data-view="results"]');
      check(`${type}: results render`,!!$('tbody tr')&&/THE RESULTS ARE IN/.test($('#main').textContent));
      window.print=()=>{}; await click('[data-action="print-results"]');
      check(`${type}: printable results name the format`,$('#print-area').textContent.includes(saved().name)&&!!$('#print-area table'));
      await click('[data-view="play"]'); await click('[data-action="print-schedule"]');
      check(`${type}: printable schedule contains score spaces or scores`,$('#print-area').textContent.includes('Side 1'));
      await click('[data-view="setup"]');
      check(`${type}: scheduled format locked`,$('#event-format').disabled);
      if(['rotating_partners','king_queen'].includes(type)) check(`${type}: scheduled court count locked`,$('#event-courts').disabled);
    }
    // Exercise the ordinary new-event path, including automatic individual mode.
    await click('[data-action="home"]'); await click('[data-action="new"]'); await click('[data-action="accept"]');
    $('#event-format').value='king_queen'; $('#event-format').dispatchEvent(new Event('change',{bubbles:true}));
    $('#event-rounds').value='2';
    check('social setup selects individuals',$('#event-mode').value==='singles'&&$('#event-mode').disabled);
    await submit('[data-form="setup"]'); await until(()=>$('#roster-list'),'roster screen');
    $('#roster-list').value='One\nTwo\nThree\nFour\nFive\nSix\nSeven\nEight'; await submit('[data-form="bulk"]'); await until(()=>saved().teams.length===8,'bulk roster');
    await click('[data-action="move-team"][data-direction="1"]'); check('seed arrows reorder roster',saved().teams[1].players[0]==='One');
    await click('[data-action="schedule"]'); await until(()=>$('.court-card'),'schedule'); await finish();
    const source=localStorage.getItem(key());
    await click('.schedule-row [data-action="score"]'); await until(()=>$('#score-a'),'correction dialog'); $('#score-a').value='7'; $('#score-b').value='11'; await submit('[data-form="score"]');
    check('ladder correction warns about later results',/2 later scores will be cleared/.test($('#modal-content').textContent));
    await click('[data-action="cancel"]'); check('cancel preserves all saved results',localStorage.getItem(key())===source);
    await game('.schedule-row [data-action="score"]',7,11); check('confirmed correction clears later round',Object.keys(saved().scores).length===2);
    check('final browser state has no error',!errors());
  } catch(error) { report.push({check:error.message,result:'FAIL'}); }
  finally { window.print=realPrint; const current=key(); if(current) localStorage.removeItem(current); }
  const failures=report.filter(row=>row.result==='FAIL');
  const result={passed:report.length-failures.length,failed:failures.length,failures,checks:report.filter(row=>row.check!=='score review names a winner')};
  console.table(result.checks); return result;
})();
