/* ============================================
   STILL — Main JS
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* --- Nav scroll state --- */
  const nav = document.querySelector('.nav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  /* --- Mobile nav toggle --- */
  const hamburger = document.querySelector('.nav__hamburger');
  const mobileNav = document.querySelector('.nav__mobile');
  if (hamburger && mobileNav) {
    hamburger.addEventListener('click', () => {
      const open = hamburger.classList.toggle('open');
      mobileNav.classList.toggle('open', open);
      document.body.style.overflow = open ? 'hidden' : '';
    });
  }

  /* --- Accordions --- */
  document.querySelectorAll('.accordion__trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const item = trigger.closest('.accordion__item');
      const isOpen = item.classList.contains('open');
      // Close all
      document.querySelectorAll('.accordion__item').forEach(i => i.classList.remove('open'));
      // Open this one unless it was already open
      if (!isOpen) item.classList.add('open');
    });
  });

  /* --- Size selector --- */
  document.querySelectorAll('.size-btn:not(.unavailable)').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.product-sizes__grid');
      group.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  /* --- Color selector --- */
  document.querySelectorAll('.color-swatch').forEach(swatch => {
    swatch.addEventListener('click', () => {
      const group = swatch.closest('.product-colors__options');
      group.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
      swatch.classList.add('active');
    });
  });

  /* --- Gallery thumbnails --- */
  document.querySelectorAll('.product-gallery__thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
      const gallery = thumb.closest('.product-gallery__main');
      gallery.querySelectorAll('.product-gallery__thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  });

  /* --- Filter tabs (shop) --- */
  document.querySelectorAll('.filter-label[data-filter]').forEach(filter => {
    filter.addEventListener('click', () => {
      document.querySelectorAll('.filter-label[data-filter]').forEach(f => f.classList.remove('active'));
      filter.classList.add('active');
      const cat = filter.dataset.filter;
      document.querySelectorAll('.product-card[data-category]').forEach(card => {
        card.style.display = (cat === 'all' || card.dataset.category === cat) ? 'block' : 'none';
      });
    });
  });

  /* --- Cart count (UI only) --- */
  const cartCount = document.querySelector('.nav__cart-count');
  const addToCartBtn = document.querySelector('.btn-primary');
  if (addToCartBtn && cartCount) {
    let count = 0;
    addToCartBtn.addEventListener('click', () => {
      // Check size is selected
      const selectedSize = document.querySelector('.size-btn.active');
      if (!selectedSize) {
        addToCartBtn.textContent = 'Select a size';
        setTimeout(() => addToCartBtn.textContent = 'Add to Cart', 1800);
        return;
      }
      count++;
      cartCount.textContent = count;
      addToCartBtn.textContent = 'Added';
      addToCartBtn.style.background = '#4A7A5A';
      setTimeout(() => {
        addToCartBtn.textContent = 'Add to Cart';
        addToCartBtn.style.background = '';
      }, 2000);
    });
  }

  /* --- Email form --- */
  const emailForm = document.querySelector('.email-capture__form');
  if (emailForm) {
    emailForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = emailForm.querySelector('.email-capture__input');
      const btn = emailForm.querySelector('.email-capture__submit');
      if (input.value && input.value.includes('@')) {
        btn.textContent = 'Done';
        input.value = '';
        input.placeholder = 'You\'re on the list.';
        setTimeout(() => btn.textContent = 'Join', 3000);
      }
    });
  }

  /* --- Smooth appear on scroll --- */
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));

});
