let movieDetailsModal;

document.addEventListener('DOMContentLoaded', () => {
  const input = document.querySelector('#autoComplete');
  const button = document.querySelector('.movie-button');

  if (!input || !button) return;

  input.addEventListener('input', () => {
    button.disabled = !input.value.trim();
  });

  button.addEventListener('click', () => searchRecommendations(input.value));

  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      searchRecommendations(input.value);
    }
  });

  movieDetailsModal = createMovieDetailsModal();
});

function createMovieDetailsModal() {
  const modal = document.createElement('div');
  modal.className = 'movie-details-modal';
  modal.hidden = true;
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'movieDetailsTitle');

  const dialog = document.createElement('div');
  dialog.className = 'movie-details-dialog';
  const closeButton = document.createElement('button');
  closeButton.className = 'details-close';
  closeButton.type = 'button';
  closeButton.setAttribute('aria-label', 'Close movie details');
  closeButton.innerHTML = '&times;';

  const poster = document.createElement('img');
  poster.className = 'details-poster';
  poster.alt = '';
  const content = document.createElement('div');
  content.className = 'details-content';
  const source = document.createElement('span');
  source.className = 'source-badge details-source';
  const title = document.createElement('h2');
  title.id = 'movieDetailsTitle';
  const metadata = document.createElement('p');
  metadata.className = 'details-metadata';
  const infoLabel = document.createElement('h3');
  infoLabel.className = 'details-info-label';
  const info = document.createElement('p');
  info.className = 'details-info';
  const reasons = document.createElement('section');
  reasons.className = 'details-reasons';
  const reasonsTitle = document.createElement('h3');
  reasonsTitle.textContent = 'Why this movie?';
  const reasonsList = document.createElement('ul');
  const reasonsNote = document.createElement('p');
  reasonsNote.className = 'details-reasons-note';
  reasons.append(reasonsTitle, reasonsList, reasonsNote);
  const searchButton = document.createElement('button');
  searchButton.className = 'details-search-button';
  searchButton.type = 'button';
  searchButton.innerHTML = 'Find recommendations <i class="fa fa-arrow-right" aria-hidden="true"></i>';

  content.append(source, title, metadata, infoLabel, info, reasons, searchButton);
  dialog.append(closeButton, poster, content);
  modal.appendChild(dialog);
  document.body.appendChild(modal);

  const close = () => {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
  };
  closeButton.addEventListener('click', close);
  modal.addEventListener('click', event => {
    if (event.target === modal) close();
  });
  searchButton.addEventListener('click', () => {
    close();
    searchRecommendations(searchButton.dataset.title);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) close();
  });

  return { modal, poster, source, title, metadata, infoLabel, info, reasons, reasonsList, reasonsNote, searchButton };
}

function openMovieDetails(movie, source) {
  if (!movieDetailsModal) return;
  const isTmdb = source === 'tmdb';
  const { modal, poster, source: sourceElement, title, metadata, infoLabel, info, reasons, reasonsList, reasonsNote, searchButton } = movieDetailsModal;
  const titleText = movie.title || 'Untitled';
  const metadataItems = [];

  if (movie.rating !== null && movie.rating !== undefined && movie.rating !== '' && Number.isFinite(Number(movie.rating))) {
    metadataItems.push(`★ ${Number(movie.rating).toFixed(1)} / 10`);
  }
  if (movie.release_date) metadataItems.push(movie.release_date.slice(0, 4));
  if (!isTmdb && movie.genre) metadataItems.push(movie.genre);

  sourceElement.className = `source-badge details-source ${isTmdb ? 'tmdb-badge' : 'local-badge'}`;
  sourceElement.textContent = isTmdb ? 'TMDB' : 'LOCAL ML';
  title.textContent = titleText;
  metadata.textContent = metadataItems.join('  •  ') || 'Movie details';
  const overview = !isTmdb && movie.overview
    ? shortenOverview(movie.overview, 280)
    : movie.overview;
  infoLabel.textContent = overview ? 'Overview' : 'Genres';
  info.textContent = overview
    || movie.genre
    || 'No overview or genre information is available for this movie.';

  reasonsList.replaceChildren();
  const matching = movie.matching_features || {};
  const matchingRows = [
    ['genres', 'Similar genres', values => values.join(' • ')],
    ['cast', 'Shared cast', values => values.join(' • ')],
    ['director', 'Similar director', value => value],
    ['shared_genres', 'Related genres', values => values.join(' • ')]
  ];
  matchingRows.forEach(([key, label, format]) => {
    if (!matching[key] || (Array.isArray(matching[key]) && !matching[key].length)) return;
    const row = document.createElement('li');
    const labelElement = document.createElement('strong');
    labelElement.textContent = label;
    const value = document.createElement('span');
    value.textContent = format(matching[key]);
    row.append(labelElement, value);
    reasonsList.appendChild(row);
  });
  reasonsNote.textContent = isTmdb
    ? 'TMDB does not publish an exact reason for each recommendation. Related genres are shown as helpful shared metadata.'
    : '';
  reasonsNote.hidden = !isTmdb;
  reasons.hidden = !isTmdb && !reasonsList.childElementCount;
  searchButton.dataset.title = titleText;

  if (movie.poster) {
    poster.src = movie.poster;
    poster.alt = `${titleText} poster`;
    poster.hidden = false;
  } else {
    poster.removeAttribute('src');
    poster.alt = '';
    poster.hidden = true;
  }

  modal.hidden = false;
  document.body.classList.add('modal-open');
  modal.querySelector('.details-close').focus();
}

function shortenOverview(text, maxLength) {
  const normalized = String(text).replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) return normalized;
  const cutoff = normalized.lastIndexOf(' ', maxLength);
  return `${normalized.slice(0, cutoff > 0 ? cutoff : maxLength)}…`;
}

async function searchRecommendations(title) {
  const movieTitle = (title || '').trim();
  const button = document.querySelector('.movie-button');

  if (!movieTitle) {
    showSearchError('Please enter a movie title.');
    return;
  }

  button.disabled = true;
  button.innerHTML = 'Finding recommendations…';

  try {
    const response = await fetch('/similarity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
      body: new URLSearchParams({ name: movieTitle })
    });
    const payload = await response.json();

    if (!response.ok) throw new Error(payload.error || 'The recommendation service could not be reached.');

    renderRecommendations(payload);
  } catch (error) {
    showSearchError(error.message || 'The recommendation service could not be reached. Please try again.');
  } finally {
    button.disabled = false;
    button.innerHTML = 'Find recommendations <i class="fa fa-arrow-right" aria-hidden="true"></i>';
  }
}

function showSearchError(message) {
  const results = document.querySelector('.results');
  const fail = document.querySelector('.fail');
  results.style.display = 'none';
  results.replaceChildren();
  fail.querySelector('h3').textContent = message;
  fail.style.display = 'block';
}

function renderRecommendations(payload) {
  const results = document.querySelector('.results');
  const fail = document.querySelector('.fail');
  const recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : [];

  if (!recommendations.length) {
    showSearchError('No recommendations were found for this movie.');
    return;
  }

  fail.style.display = 'none';
  results.replaceChildren();

  const heading = document.createElement('h2');
  heading.id = 'name';
  heading.className = 'text-uppercase';
  heading.textContent = `${payload.source === 'tmdb' ? 'TMDB' : 'Local'} recommendations for ${payload.title}`;
  results.appendChild(heading);

  if (payload.selected && payload.selected.overview) {
    const overview = document.createElement('p');
    overview.className = 'search-overview';
    overview.textContent = payload.selected.overview;
    results.appendChild(overview);
  }

  const content = document.createElement('div');
  content.className = 'movie-content';
  recommendations.forEach(movie => {
    const card = document.createElement('button');
    card.className = 'card recommendation-card';
    card.type = 'button';

    if (movie.poster) {
      const poster = document.createElement('img');
      poster.className = 'card-img-top';
      poster.src = movie.poster;
      poster.alt = `${movie.title} poster`;
      card.appendChild(poster);
      card.dataset.poster = movie.poster;
    } else {
      const placeholder = document.createElement('div');
      placeholder.className = 'poster-placeholder';
      placeholder.textContent = 'No poster available';
      card.appendChild(placeholder);
    }

    const badge = document.createElement('span');
    badge.className = `source-badge ${payload.source === 'tmdb' ? 'tmdb-badge' : 'local-badge'}`;
    badge.textContent = payload.source === 'tmdb' ? 'TMDB' : 'LOCAL ML';
    card.appendChild(badge);

    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h5');
    title.className = 'card-title';
    title.textContent = movie.title || 'Untitled';
    body.appendChild(title);

    const metadata = document.createElement('div');
    metadata.className = 'card-metadata';
    if (movie.rating !== null && movie.rating !== undefined && movie.rating !== '' && Number.isFinite(Number(movie.rating))) {
      const rating = document.createElement('span');
      rating.innerHTML = `<i class="fa fa-star" aria-hidden="true"></i> ${Number(movie.rating).toFixed(1)}`;
      metadata.appendChild(rating);
    }

    if (movie.release_date) {
      const year = document.createElement('p');
      year.className = 'card-text card-year';
      year.textContent = movie.release_date.slice(0, 4);
      metadata.appendChild(year);
    }

    if (metadata.childElementCount) body.appendChild(metadata);

    const infoLabel = document.createElement('span');
    infoLabel.className = 'card-info-label';
    infoLabel.textContent = 'About this movie';
    const details = document.createElement('p');
    details.className = 'card-hover-info';
    details.textContent = movie.overview || movie.genre || 'Additional movie details are not available.';
    body.append(infoLabel, details);

    card.appendChild(body);
    card.addEventListener('click', () => openMovieDetails(
      { ...movie, poster: card.dataset.poster || movie.poster },
      payload.source
    ));
    content.appendChild(card);
  });

  results.appendChild(content);
  results.style.display = 'block';
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
