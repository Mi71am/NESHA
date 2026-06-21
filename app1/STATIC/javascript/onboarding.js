(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll('.hero-slide'));
  var dots = Array.prototype.slice.call(document.querySelectorAll('.dot'));
  var nextButton = document.getElementById('nextSlideBtn');
  var root = document.getElementById('heroSlides');
  var bannerTagline = document.getElementById('bannerTagline');
  var current = 0;

  if (!slides.length) {
    return;
  }

  function renderSlide(index) {
    current = (index + slides.length) % slides.length;

    slides.forEach(function (slide, i) {
      slide.classList.toggle('is-active', i === current);
    });

    dots.forEach(function (dot, i) {
      dot.classList.toggle('is-active', i === current);
    });

    if (bannerTagline) {
      bannerTagline.textContent = slides[current].getAttribute('data-banner') || '';
    }
  }

  function nextSlide() {
    renderSlide(current + 1);
  }

  if (nextButton) {
    nextButton.addEventListener('click', function () {
      nextSlide();
    });
  }

  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      var index = Number(dot.getAttribute('data-slide'));
      renderSlide(index);
    });
  });

  var touchStartX = 0;
  var touchEndX = 0;

  if (root) {
    root.addEventListener('touchstart', function (event) {
      touchStartX = event.changedTouches[0].screenX;
    });

    root.addEventListener('touchend', function (event) {
      touchEndX = event.changedTouches[0].screenX;
      var delta = touchEndX - touchStartX;

      if (Math.abs(delta) < 40) {
        return;
      }

      if (delta < 0) {
        nextSlide();
      } else {
        renderSlide(current - 1);
      }
    });
  }

  renderSlide(0);
})();
