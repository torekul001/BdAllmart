document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.m-sidebar details');
  const quantity = document.querySelector('[data-unit-price]');
  const total = document.querySelector('[data-checkout-total]');
  if (quantity && total) quantity.addEventListener('input', () => {
    const amount = Number(quantity.value) * Number(quantity.dataset.unitPrice) / 100;
    total.textContent = new Intl.NumberFormat('en-US', {style:'currency',currency:'BDT'}).format(Number.isFinite(amount) ? amount : 0);
  });
  if (menu && window.matchMedia('(max-width: 850px)').matches) menu.open = false;
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => { if (!window.confirm(form.dataset.confirm)) event.preventDefault(); });
  });
  document.querySelectorAll('[data-wizard]').forEach(form => {
    const steps = [...form.querySelectorAll('[data-step]')];
    const markers = [...form.querySelectorAll('.steps li')];
    const prev = form.querySelector('[data-prev]');
    const next = form.querySelector('[data-next]');
    const counter = form.querySelector('[data-step-count]');
    let index = 0;
    function show() {
      steps.forEach((step, i) => { step.hidden = i !== index; });
      markers.forEach((marker, i) => { marker.classList.toggle('active', i === index); });
      prev.hidden = index === 0;
      next.hidden = index === steps.length - 1;
      counter.textContent = `${index + 1} / ${steps.length}`;
    }
    next.addEventListener('click', () => {
      const fields = [...steps[index].querySelectorAll('input,select,textarea')];
      const invalid = fields.find(field => !field.disabled && !field.checkValidity());
      if (invalid) { invalid.reportValidity(); return; }
      index += 1; show(); steps[index].querySelector('input,select,textarea')?.focus();
    });
    prev.addEventListener('click', () => { index -= 1; show(); });
    form.addEventListener('invalid', event => {
      const invalidIndex = steps.findIndex(step => step.contains(event.target));
      if (invalidIndex >= 0 && invalidIndex !== index) { index = invalidIndex; show(); }
    }, true);
    form.addEventListener('keydown', event => {
      if (event.key === 'Enter' && event.target.tagName === 'INPUT' && index < steps.length - 1) { event.preventDefault(); next.click(); }
    });
    const kind = form.querySelector('#listing-kind');
    function selectKind() {
      form.querySelectorAll('[data-kind]').forEach(group => {
        group.hidden = group.dataset.kind !== kind.value;
        group.querySelectorAll('input,textarea,select').forEach(field => { field.disabled = group.hidden; });
      });
    }
    kind?.addEventListener('change', selectKind);
    selectKind(); show();
  });
});
