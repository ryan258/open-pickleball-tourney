// Browser smoke check for the organizer workflow. No dependencies.
// Use: serve the site (./play, or a static build), open it in a browser with NO saved
// tournament (a private window is easiest), paste this file into the DevTools console.
// It refuses to run over an existing saved tournament and removes its own record at the end.
(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const click = async s => { const n = $(s); if (!n) throw new Error(`Missing ${s}`); n.click(); await wait(350); };
  const rows = () => $$('tbody tr').map(tr => [...tr.children].map(td => td.textContent.replace(/\s+/g, ' ').trim()));
  const storedKey = () => Object.keys(localStorage).find(k => k.startsWith('open-pickleball-browser:'));
  const results = [], check = (name, ok) => results.push({ result: ok ? 'PASS' : 'FAIL', check: name });
  if (storedKey()) return console.error('Refused: this browser holds a saved tournament. Save a backup, then use a private window.');
  async function enterScore(trigger, a, b) {
    await click(trigger);
    $('#score-a').value = a; $('#score-b').value = b;
    $('#modal form').requestSubmit(); await wait(350);
  }
  try {
    await click('[data-action="sample"]');
    check('practice tournament opens on the play step with two court cards', $$('.court-card').length === 2);

    await click('[data-action="score"]');
    check('score dialog has no forfeit shortcut', !$('#modal [data-action^="forfeit"]'));
    $('#score-a').value = 10; $('#score-b').value = 9; $('#modal form').requestSubmit(); await wait(350);
    check('an unfinished score is rejected in place', $('#modal .form-error').textContent.trim() !== '' && !!$('#score-a'));
    $('#score-a').value = 11; $('#score-b').value = 5; $('#modal form').requestSubmit(); await wait(350);
    check('a valid score goes to review naming a winner', /wins\./.test($('#modal-content').textContent));
    await click('#modal [data-action="confirm-score"]');
    check('confirmed score shows as saved', /SCORE SAVED/.test($('.court-card').textContent));

    $('#main details').open = true;
    await enterScore('.schedule-row [data-action="score"]', 11, 7);
    await click('#modal [data-action="confirm-score"]');
    check('correcting from the full schedule keeps that panel open', $('#main details').open && /11 – 7/.test($('.schedule-row').textContent));

    await click('[data-view="teams"]');
    await click('[data-action="withdraw-team"]');
    await click('#modal [data-action="accept"]');
    await click('[data-view="results"]');
    const withdrawn = rows(), pointsTotal = withdrawn.reduce((sum, r) => sum + Number(r[6]), 0);
    check('withdrawn entry is labelled, unranked and listed last', /Withdrawn/.test(withdrawn.at(-1)[1]) && withdrawn.at(-1)[0] === '—');
    check('walkovers add no points: table total equals the one real game (11 + 7)', pointsTotal === 18);
    check('the withdrawal is in the saved record', JSON.parse(localStorage.getItem(storedKey())).tournament.withdrawn.length === 1);

    await click('[data-view="teams"]');
    await click('[data-action="reinstate-team"]');
    await click('[data-view="results"]');
    check('reinstating removes the withdrawn label', !rows().some(r => /Withdrawn/.test(r[1])));

    await click('[data-view="setup"]');
    check('court count stays editable after scheduling', !$('#event-courts').disabled);
    $('#event-courts').value = '1'; $('form[data-form="setup"]').requestSubmit(); await wait(450);
    await click('[data-view="play"]');
    check('changing courts mid-event keeps the saved score', /11 – 7/.test($('.schedule-row').textContent));
    check('no problem banner is showing', $('#problem').hidden);
  } catch (error) { check(`unexpected error: ${error.message}`, false); }
  finally { const key = storedKey(); if (key) localStorage.removeItem(key); }
  console.table(results);
  console.log(results.every(r => r.result === 'PASS') ? 'SMOKE PASS — reload the page to clear the test state.' : 'SMOKE FAIL — see the table.');
})();
