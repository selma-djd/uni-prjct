// Small JavaScript helpers (no libraries)

// 1. Mobile menu: show / hide the navigation links
var toggle = document.getElementById("menu-toggle");
var links = document.getElementById("nav-links");
if (toggle && links) {
  toggle.addEventListener("click", function () {
    links.classList.toggle("open");
  });
}

// 2. Ask for confirmation before deleting
var forms = document.querySelectorAll("form.js-confirm");
forms.forEach(function (form) {
  form.addEventListener("submit", function (event) {
    var message = form.getAttribute("data-confirm") || "Are you sure?";
    if (!window.confirm(message)) {
      event.preventDefault();
    }
  });
});

// 3. On the home page, highlight the navbar link of the section being viewed
if (document.body.getAttribute("data-page") === "home") {
  var sections = document.querySelectorAll("section[id]");
  var navLinks = document.querySelectorAll("#nav-links a[data-section]");

  function updateActiveLink() {
    var position = window.scrollY + 120;
    var current = "home";
    sections.forEach(function (section) {
      if (section.offsetTop <= position) {
        current = section.id;
      }
    });
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) {
      current = sections[sections.length - 1].id;
    }
    navLinks.forEach(function (link) {
      if (link.getAttribute("data-section") === current) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });
  }

  window.addEventListener("scroll", updateActiveLink);
  updateActiveLink();

  // close the mobile menu after clicking a link
  navLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      if (links) { links.classList.remove("open"); }
    });
  });
}
