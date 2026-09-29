/* global films */

(() => {
    const input = document.querySelector("#autoComplete");
    const results = document.querySelector("#movieSuggestions");

    if (!input || !results) return;

    const movieTitles = Array.isArray(films)
        ? [...new Set(films.filter(title => typeof title === "string" && title.trim()))]
        : [];
    let matches = [];
    let activeIndex = -1;

    function closeSuggestions() {
        matches = [];
        activeIndex = -1;
        results.hidden = true;
        results.replaceChildren();
    }

    function selectMovie(title) {
        input.value = title;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        closeSuggestions();
        input.focus();
    }

    function renderSuggestions(query) {
        const normalizedQuery = query.trim().toLocaleLowerCase();
        if (normalizedQuery.length < 2) return closeSuggestions();

        matches = movieTitles
            .filter(title => title.toLocaleLowerCase().includes(normalizedQuery))
            .slice(0, 8);
        activeIndex = -1;
        results.replaceChildren();

        if (!matches.length) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "movie-suggestion-empty";
            emptyItem.textContent = "No matching movies";
            results.appendChild(emptyItem);
        } else {
            matches.forEach(title => {
                const item = document.createElement("li");
                const button = document.createElement("button");
                button.type = "button";
                button.className = "movie-suggestion";
                button.textContent = title;
                button.addEventListener("mousedown", event => {
                    event.preventDefault();
                    selectMovie(title);
                });
                item.appendChild(button);
                results.appendChild(item);
            });
        }
        results.hidden = false;
    }

    function setActiveSuggestion(index) {
        results.querySelectorAll(".movie-suggestion").forEach((item, itemIndex) => {
            item.classList.toggle("is-active", itemIndex === index);
        });
    }

    input.addEventListener("input", () => renderSuggestions(input.value));
    input.addEventListener("keydown", event => {
        if (results.hidden || !matches.length) return;
        if (event.key === "ArrowDown") {
            event.preventDefault();
            activeIndex = (activeIndex + 1) % matches.length;
            setActiveSuggestion(activeIndex);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            activeIndex = (activeIndex - 1 + matches.length) % matches.length;
            setActiveSuggestion(activeIndex);
        } else if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            selectMovie(matches[activeIndex]);
        } else if (event.key === "Escape") {
            closeSuggestions();
        }
    });
    input.addEventListener("blur", () => window.setTimeout(closeSuggestions, 150));
})();
