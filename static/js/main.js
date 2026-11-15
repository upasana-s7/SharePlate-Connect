/**
 * main.js — SharePlate Connect global JavaScript
 * Stage 1: mobile navigation hamburger menu only.
 */

document.addEventListener("DOMContentLoaded", function () {

  // -----------------------------------------------------------------------
  // Mobile navigation toggle
  // -----------------------------------------------------------------------
  const hamburgerBtn = document.getElementById("hamburgerBtn");
  const navLinks     = document.getElementById("navLinks");

  if (hamburgerBtn && navLinks) {
    hamburgerBtn.addEventListener("click", function () {
      const isOpen = navLinks.classList.toggle("open");
      // Update aria attribute for accessibility
      hamburgerBtn.setAttribute("aria-expanded", isOpen);
    });

    // Close menu when a link inside it is clicked (nice UX on mobile)
    navLinks.querySelectorAll(".nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        navLinks.classList.remove("open");
        hamburgerBtn.setAttribute("aria-expanded", "false");
      });
    });
  }

});
