// Open Pickleball Tourney - Interactive Documentation Script

document.addEventListener('DOMContentLoaded', () => {
  // Tab Switching Logic
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetTab = button.getAttribute('data-tab');

      // Update button states
      tabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      // Update content visibility
      tabContents.forEach(content => {
        if (content.id === targetTab) {
          content.classList.add('active');
        } else {
          content.classList.remove('active');
        }
      });
    });
  });

  // Copy to Clipboard Logic
  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.getAttribute('data-clipboard-target');
      const targetElement = document.getElementById(targetId);
      if (!targetElement) return;

      const codeText = targetElement.innerText || targetElement.textContent;

      try {
        await navigator.clipboard.writeText(codeText.trim());
        const originalText = btn.innerText;
        btn.innerText = 'Copied! ✓';
        btn.style.color = '#a3e635';
        btn.style.borderColor = 'rgba(163, 230, 53, 0.4)';

        setTimeout(() => {
          btn.innerText = originalText;
          btn.style.color = '';
          btn.style.borderColor = '';
        }, 2000);
      } catch (err) {
        console.error('Failed to copy text: ', err);
      }
    });
  });
});
