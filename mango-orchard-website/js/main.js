document.getElementById('year').textContent = new Date().getFullYear();

const navToggle = document.getElementById('nav-toggle');
const siteNav = document.getElementById('site-nav');

navToggle.addEventListener('click', () => {
  const isOpen = siteNav.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(isOpen));
});

siteNav.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    siteNav.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

const WHATSAPP_NUMBER = '923000000000'; // TODO: replace with the real business WhatsApp number (country code, no + or spaces)

const orderForm = document.getElementById('order-form');
orderForm.addEventListener('submit', (event) => {
  event.preventDefault();

  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const city = document.getElementById('city').value.trim();
  const variety = document.getElementById('variety').value;
  const quantity = document.getElementById('quantity').value;
  const notes = document.getElementById('notes').value.trim();

  const lines = [
    'Hello Mango Orchard! I would like to place an order:',
    `Name: ${name}`,
    `Phone: ${phone}`,
    `City: ${city}`,
    `Variety: ${variety}`,
    `Quantity: ${quantity} kg`,
  ];
  if (notes) lines.push(`Notes: ${notes}`);

  const message = encodeURIComponent(lines.join('\n'));
  window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${message}`, '_blank', 'noopener');
});
