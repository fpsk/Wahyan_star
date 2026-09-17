/**
 * Wah Yan Star Multi-Year Archive Application Client Logic
 * Handles Search, Year Filters, Category Filters, Dynamic Chatbot, Clear History, and Photo Lightbox Modal
 * Includes Sticky Floating Enlarge Toolbar (+50%), 180° Rotate Button & Click-to-Enlarge on Image!
 */

let searchData = [];
let verifiedRoster = [];
let currentYearFilter = 'all';
let currentCategoryFilter = 'all';
let chatbot = null;

let currentSearchResults = [];
let displayedCardCount = 12;
let currentZoomScale = 1.0;
let currentRotationDegrees = 0;
let bilingualDict = { en_to_zh: {}, zh_to_en: {} };

const ASSET_VERSION = '20260917_1545';

// Cloudflare R2 Public CDN URL (serves photos at gigabit edge speed)
const R2_PUBLIC_URL = 'https://pub-363483551a3a4e7e9c3596046307f77b.r2.dev';


function getPhotoUrl(filename) {
  if (!filename) return '';
  if (R2_PUBLIC_URL) {
    return `${R2_PUBLIC_URL.replace(/\/$/, '')}/${filename}`;
  }
  return `./okf_output/photos/${filename}?v=${ASSET_VERSION}`;
}


// Initialize Web Application
document.addEventListener('DOMContentLoaded', async () => {
  await loadDatasets();
  setupEventListeners();
  renderYearFilterPills();
  performSearch();
});

// Global Image Fallback Handler (recovers if browser requests .png or .webp)
function handleImageError(img) {
  if (!img || img.dataset.retried) return;
  img.dataset.retried = '1';
  if (img.src.includes('.png')) {
    img.src = img.src.replace('.png', '.webp');
  } else if (img.src.includes('.webp')) {
    img.src = img.src.replace('.webp', '.png');
  }
}

// Load Search Datasets
async function loadDatasets() {
  try {
    const searchRes = await fetch('./okf_search_data.json?v=' + Date.now(), { cache: 'no-store' });
    searchData = await searchRes.json();

    // Sanitize any raw JSON strings defensively and preserve tokens
    searchData.forEach(item => {
      item.text = sanitizeOcrText(item.text, item);
    });

    const rosterRes = await fetch('./okf_verified_roster.json?v=' + Date.now(), { cache: 'no-store' });
    verifiedRoster = await rosterRes.json();

    try {
      const dictRes = await fetch('./okf_bilingual_dictionary.json?v=' + Date.now(), { cache: 'no-store' });
      bilingualDict = await dictRes.json();
    } catch (e) {
      console.warn("Bilingual dictionary load skipped:", e);
    }

    if (typeof StarChatbot !== 'undefined') {
      chatbot = new StarChatbot(searchData);
    }

    console.log(`Loaded ${searchData.length} master index entries, ${verifiedRoster.length} verified roster names, and bilingual dictionary.`);
  } catch (err) {
    console.error("Failed to load dataset files:", err);
    document.getElementById('resultsStats').textContent = "Error loading dataset. Please make sure the HTTP server is running.";
  }
}

function sanitizeOcrText(text, item = null) {
  if (!text) return '';
  if (text.startsWith('[') && text.includes('"text":')) {
    try {
      const parsed = JSON.parse(text);
      if (item && Array.isArray(parsed)) {
        item._tokens = parsed.map(o => (o.text || '').trim()).filter(Boolean);
      }
      return parsed.map(o => o.text || '').join(' ');
    } catch (e) {
      return text.replace(/\{"width".*?"text":"/g, ' ')
                 .replace(/","x":\d+\.\d+,"y":\d+\.\d+,"height":\d+\.\d+\}/g, ' ')
                 .replace(/[{}"]/g, '');
    }
  }
  return text;
}

// Render Multi-Year Filter Pills dynamically
function renderYearFilterPills() {
  const container = document.getElementById('yearFilters');
  if (!container) return;

  const rawYears = Array.from(new Set(searchData.map(item => String(item.year)))).sort();
  
  let html = `<button type="button" class="filter-chip year-chip active" data-year="all" onclick="setYearFilter('all', this)">All Years (全部年份)</button>`;

  rawYears.forEach(year => {
    let displayLabel = year;
    if (year === 'Reunion_Gala') {
      displayLabel = '🎉 Reunion Gala (同窗重聚專輯)';
    } else if (year === '1975_F5_Alumni' || year === 'F5_Alumni') {
      displayLabel = '🎓 1975 (F5 Alumni Book)';
    } else if (/^\d{4}$/.test(year)) {
      displayLabel = `${year} Volume`;
    }
    html += `<button type="button" class="filter-chip year-chip" data-year="${year}" onclick="setYearFilter('${year}', this)">${displayLabel}</button>`;
  });

  container.innerHTML = html;
}

// Set Active Year Filter
function setYearFilter(year, element = null) {
  currentYearFilter = year;
  document.querySelectorAll('.year-chip').forEach(btn => {
    if (element) {
      btn.classList.remove('active');
    } else {
      if (btn.getAttribute('data-year') === String(year)) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });
  if (element) element.classList.add('active');
  performSearch();
}

// Setup Keyboard Shortcuts & Controls
function setupEventListeners() {
  const searchInput = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearBtn');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearBtn.style.display = e.target.value ? 'block' : 'none';
      performSearch();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearBtn.style.display = 'none';
      searchInput.focus();
      performSearch();
    });
  }

  // Category filter listeners
  document.querySelectorAll('.category-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
      e.target.classList.add('active');
      currentCategoryFilter = e.target.getAttribute('data-filter');
      performSearch();
    });
  });

  // Global Keyboard Shortcut: '/' to focus search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT') {
      e.preventDefault();
      switchTab('search');
      searchInput.focus();
    }
    if (e.key === 'Escape') {
      closeLightbox();
    }
    const modal = document.getElementById('lightboxModal');
    if (modal && modal.classList.contains('active') && document.activeElement.tagName !== 'INPUT') {
      if (e.key === 'ArrowLeft' || e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        navigateLightboxPage(-1);
      } else if (e.key === 'ArrowRight' || e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        navigateLightboxPage(1);
      } else if (e.key === 'r' || e.key === 'R') {
        if (e.shiftKey) {
          rotateLightboxImage(180);
        } else {
          rotateLightboxImage(90);
        }
      } else if (e.key === 'f' || e.key === 'F') {
        rotateLightboxImage(180);
      } else if (e.key === '+' || e.key === '=') {
        zoomLightbox(0.25);
      } else if (e.key === '-' || e.key === '_') {
        zoomLightbox(-0.25);
      } else if (e.key === '0') {
        resetLightboxZoom();
      }
    }
  });

  // Lightbox Mouse & Touch Pan / Swipe Support
  const modalBody = document.getElementById('modalBody');
  const modalImg = document.getElementById('modalImage');
  let isDragging = false;
  let startX = 0, startY = 0;
  let scrollLeftStart = 0, scrollTopStart = 0;

  if (modalBody) {
    // Desktop Mouse Drag-to-Pan support when zoomed in
    modalBody.addEventListener('mousedown', (e) => {
      if (e.target.closest('#lightboxToolbar') || e.target.closest('.modal-header') || e.target.closest('.lightbox-float-nav')) return;
      if (currentZoomScale > 1.0) {
        isDragging = true;
        modalBody.style.cursor = 'grabbing';
        startX = e.pageX - modalBody.offsetLeft;
        startY = e.pageY - modalBody.offsetTop;
        scrollLeftStart = modalBody.scrollLeft;
        scrollTopStart = modalBody.scrollTop;
      }
    });

    modalBody.addEventListener('mouseleave', () => {
      isDragging = false;
      modalBody.style.cursor = '';
    });

    modalBody.addEventListener('mouseup', () => {
      isDragging = false;
      modalBody.style.cursor = '';
    });

    modalBody.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      e.preventDefault();
      const x = e.pageX - modalBody.offsetLeft;
      const y = e.pageY - modalBody.offsetTop;
      const walkX = (x - startX);
      const walkY = (y - startY);
      modalBody.scrollLeft = scrollLeftStart - walkX;
      modalBody.scrollTop = scrollTopStart - walkY;
    });

    // Mobile & Tablet Touch Controls: Touch Pan, Swipe Navigation, Pinch Zoom & Double-Tap
    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;
    let touchScrollLeftStart = 0;
    let touchScrollTopStart = 0;
    let isTouchPanning = false;
    let lastTapTime = 0;
    let initialPinchDistance = null;
    let initialPinchScale = 1.0;

    modalBody.addEventListener('touchstart', (e) => {
      if (e.target.closest('#lightboxToolbar') || e.target.closest('.modal-header') || e.target.closest('.lightbox-float-nav')) return;

      if (e.touches.length === 1) {
        const touch = e.touches[0];
        touchStartX = touch.pageX;
        touchStartY = touch.pageY;
        touchStartTime = Date.now();
        touchScrollLeftStart = modalBody.scrollLeft;
        touchScrollTopStart = modalBody.scrollTop;

        if (currentZoomScale > 1.0) {
          isTouchPanning = true;
        } else {
          isTouchPanning = false;
        }
      } else if (e.touches.length === 2) {
        // Pinch-to-zoom start
        isTouchPanning = false;
        initialPinchDistance = Math.hypot(
          e.touches[0].pageX - e.touches[1].pageX,
          e.touches[0].pageY - e.touches[1].pageY
        );
        initialPinchScale = currentZoomScale;
      }
    }, { passive: false });

    modalBody.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && isTouchPanning && currentZoomScale > 1.0) {
        // Prevent background scroll while panning inside zoomed lightbox
        e.preventDefault();
        const touch = e.touches[0];
        const deltaX = touch.pageX - touchStartX;
        const deltaY = touch.pageY - touchStartY;
        modalBody.scrollLeft = touchScrollLeftStart - deltaX;
        modalBody.scrollTop = touchScrollTopStart - deltaY;
      } else if (e.touches.length === 2 && initialPinchDistance) {
        // Two-finger pinch zoom
        e.preventDefault();
        const dist = Math.hypot(
          e.touches[0].pageX - e.touches[1].pageX,
          e.touches[0].pageY - e.touches[1].pageY
        );
        const factor = dist / initialPinchDistance;
        let newScale = Math.round((initialPinchScale * factor) * 100) / 100;
        if (newScale < 0.5) newScale = 0.5;
        if (newScale > 4.0) newScale = 4.0;
        currentZoomScale = newScale;
        applyZoomScale();
      }
    }, { passive: false });

    modalBody.addEventListener('touchend', (e) => {
      if (initialPinchDistance && e.touches.length < 2) {
        initialPinchDistance = null;
      }

      if (isTouchPanning) {
        isTouchPanning = false;
        return;
      }

      // Single-finger swipe left/right page navigation when at base zoom scale
      if (e.changedTouches.length === 1 && currentZoomScale <= 1.0) {
        const touch = e.changedTouches[0];
        const deltaX = touch.pageX - touchStartX;
        const deltaY = touch.pageY - touchStartY;
        const elapsed = Date.now() - touchStartTime;

        // Swipe threshold: fast gesture (< 650ms), at least 45px, predominantly horizontal
        if (elapsed < 650 && Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY) * 1.25) {
          if (deltaX < -45) {
            // Swipe Left -> Next Page
            navigateLightboxPage(1);
          } else if (deltaX > 45) {
            // Swipe Right -> Previous Page
            navigateLightboxPage(-1);
          }
        }
      }
    });

    // Double-tap zoom on modal image
    if (modalImg) {
      modalImg.addEventListener('touchend', (e) => {
        if (e.changedTouches.length === 1) {
          const now = Date.now();
          const timeSinceLastTap = now - lastTapTime;
          const touch = e.changedTouches[0];
          const distMoved = Math.hypot(touch.pageX - touchStartX, touch.pageY - touchStartY);

          if (timeSinceLastTap > 0 && timeSinceLastTap < 320 && distMoved < 15) {
            // Double-tap detected
            e.preventDefault();
            handleImageClickZoom();
            lastTapTime = 0;
          } else {
            lastTapTime = now;
          }
        }
      });
    }
  }
}

// Common activity / English dictionary terms that shouldn't be treated as Chinese personal names
const commonEnglishWords = new Set([
  'swimming', 'swim', 'table tennis', 'tennis', 'football', 'soccer', 'basketball', 
  'speech', 'drama', 'debate', 'choir', 'music', 'orchestra', 'scout', 'scouts', 
  'athletics', 'sports', 'badminton', 'volleyball', 'chess', 'fencing', 'judo',
  'library', 'photographic', 'science', 'art', 'reunion', 'alumni', 'staff', 'teacher',
  'principal', 'father', 'brother', 'president', 'prefect', 'editor', 'secretary'
]);

function findMatchingQuoteIndex(str) {
  if (!str || str.length < 2) return -1;
  const open = str[0];
  const matching = { '“': '”', '‘': '’', '「': '」', '『': '』', '«': '»' };
  const target = matching[open] || open;
  for (let i = 1; i < str.length; i++) {
    if (str[i] === target) return i;
  }
  return -1;
}

function splitOutsideQuotes(str, delimiterRegex) {
  const quoteChars = /['"‘’“”「」『』«»]/;
  const pieces = [];
  let current = '';
  let activeQuote = null;

  let i = 0;
  while (i < str.length) {
    const ch = str[i];
    if (activeQuote) {
      current += ch;
      if (
        ch === activeQuote ||
        (activeQuote === '“' && ch === '”') ||
        (activeQuote === '‘' && ch === '’') ||
        (activeQuote === '「' && ch === '」') ||
        (activeQuote === '『' && ch === '』') ||
        (activeQuote === '«' && ch === '»')
      ) {
        activeQuote = null;
      }
      i++;
    } else if (quoteChars.test(ch)) {
      activeQuote = ch;
      current += ch;
      i++;
    } else {
      const sub = str.slice(i);
      const match = sub.match(delimiterRegex);
      if (match && match.index === 0) {
        if (current.trim().length > 0) {
          pieces.push(current.trim());
        }
        current = '';
        i += match[0].length;
      } else {
        current += ch;
        i++;
      }
    }
  }
  if (current.trim().length > 0) {
    pieces.push(current.trim());
  }
  return pieces;
}

function parseSingleTerm(rawToken, globalExact = false) {
  let t = rawToken.trim();
  let isExact = globalExact;

  const firstChar = t.charAt(0);
  const lastChar = t.charAt(t.length - 1);
  const isQuoted = (
    (firstChar === '"' && lastChar === '"') ||
    (firstChar === "'" && lastChar === "'") ||
    (firstChar === '“' && lastChar === '”') ||
    (firstChar === '‘' && lastChar === '’') ||
    (firstChar === '「' && lastChar === '」') ||
    (firstChar === '『' && lastChar === '』') ||
    (firstChar === '«' && lastChar === '»')
  ) && t.length >= 2;

  if (isQuoted) {
    isExact = true;
    t = t.substring(1, t.length - 1).trim();
  } else if (!globalExact) {
    if ((t.startsWith('"') || t.startsWith("'") || t.startsWith('“') || t.startsWith('‘')) && t.length > 1) {
      isExact = true;
      t = t.slice(1).trim();
    } else if ((t.endsWith('"') || t.endsWith("'") || t.endsWith('”') || t.endsWith('’')) && t.length > 1) {
      isExact = true;
      t = t.slice(0, -1).trim();
    }
  }

  return {
    raw: rawToken,
    term: t.toLowerCase(),
    displayTerm: t,
    isExact: isExact
  };
}

// Parse search query into AND clauses, where each clause can contain multiple OR terms
function parseSearchQuery(rawInput) {
  if (!rawInput) return [];
  let input = rawInput.trim();
  const quoteChars = /['"‘’“”「」『』«»]/;
  let globalExact = false;

  // Outer quotes stripped only when wrapping a comma-separated query
  if (input.length >= 2 && quoteChars.test(input[0])) {
    const matchIdx = findMatchingQuoteIndex(input);
    if (matchIdx === input.length - 1 && (input.includes(',') || input.includes('，'))) {
      input = input.substring(1, input.length - 1).trim();
      globalExact = true;
    }
  }

  // 1. Split into AND clauses by comma
  const andClausesRaw = splitOutsideQuotes(input, /^[,，]/);

  // 2. Split each clause into OR terms by " OR ", " or ", " | ", " 或 ", " / "
  const clauses = [];
  const orRegex = /^(?:\s+(?:OR|or|\||或)\s+|\s*\/\s*|\s*\|\s*)/;

  for (const rawClause of andClausesRaw) {
    const orPieces = splitOutsideQuotes(rawClause, orRegex);
    const terms = orPieces
      .map(p => parseSingleTerm(p, globalExact))
      .filter(t => t.term.length > 0);

    if (terms.length > 0) {
      clauses.push({
        rawClause: rawClause,
        hasOr: terms.length > 1,
        terms: terms
      });
    }
  }

  return clauses;
}

// Backward-compatible flat term extractor
function parseSearchTerms(rawInput) {
  const clauses = parseSearchQuery(rawInput);
  return clauses.flatMap(c => c.terms);
}

// Check if a single page item satisfies the overall search query (AND of clauses, OR of terms within each clause)
function itemMatchesQuery(item, clauses) {
  if (!clauses || clauses.length === 0) return true;
  return clauses.every(clause => {
    return clause.terms.some(termObj => itemMatchesTerm(item, termObj));
  });
}

function matchTextExact(text, term) {
  if (!text || !term) return false;
  const isChinese = /[\u4e00-\u9fff]/.test(term);
  if (isChinese) {
    const pat = new RegExp('(?<![\\u4e00-\\u9fff])' + escapeRegex(term) + '(?![\\u4e00-\\u9fff])', 'i');
    return pat.test(text);
  }

  const words = term.trim().split(/\s+/).filter(Boolean);
  const termLetterPattern = words.map(word => {
    return Array.from(word).map(c => {
      if (/[a-zA-Z]/.test(c)) {
        return '[' + c.toUpperCase() + c.toLowerCase() + ']';
      }
      return escapeRegex(c);
    }).join('');
  }).join('\\s+');

  if (commonEnglishWords.has(term.toLowerCase()) || words.length >= 3) {
    const regex = new RegExp('(?<![A-Za-z0-9])' + termLetterPattern + '(?![A-Za-z0-9])');
    return regex.test(text);
  }

  // 1-2 word names: cannot be followed by another capitalized name word (e.g. Fai, Him, Keung)
  const nonNameNextWords = '(?!\\s+(?:Gala|Day|Singles|Doubles|Club|Society|Team|School|College|University|Prize|Cup|Medal|Championship|Was|Is|Won|Scored|Spoke|Awarded|Brown)\\b)';
  const regex = new RegExp('(?<![A-Za-z0-9])' + termLetterPattern + '(?![A-Za-z0-9])' + nonNameNextWords + '(?!\\s+[A-Z][a-z]+)');
  return regex.test(text);
}

function matchEntityExact(name, term) {
  if (!name) return false;
  const s = cleanField(name).trim().toLowerCase();
  if (s === term) return true;
  const stripped = s.replace(/\s*[\(\（\[][^\)\）\]]+[\)\）\]]/g, '').trim();
  if (stripped === term) return true;
  const withoutTitle = stripped.replace(/^(mr\.|mrs\.|miss|ms\.|fr\.|father|rev\.|brother|dr\.|prof\.)\s+/i, '').trim();
  return withoutTitle === term;
}

/// Perform Client-Side Multi-Year Search with Multi-Term AND (Comma) & OR Logic
function performSearch() {
  const rawInput = document.getElementById('searchInput').value;
  const clauses = parseSearchQuery(rawInput);

  let filtered = searchData;

  if (currentYearFilter !== 'all') {
    filtered = filtered.filter(item => {
      const y = String(item.year);
      if (currentYearFilter === '1975') {
        return y === '1975' || y === '1975_F5_Alumni' || y === 'F5_Alumni';
      }
      return y === currentYearFilter;
    });
  }

  if (currentCategoryFilter === 'staff_speeches') {
    filtered = filtered.filter(item => item.is_staff_activity === true);
  } else if (currentCategoryFilter === 'photos') {
    filtered = filtered.filter(item => item.photos && item.photos.length > 0);
  } else if (currentCategoryFilter === 'staff') {
    filtered = filtered.filter(item => {
      const t = (item.text || '').toLowerCase();
      return t.includes('staff') || t.includes('teacher') || t.includes('principal') || t.includes('教員') || t.includes('神父');
    });
  } else if (currentCategoryFilter === 'graduates') {
    filtered = filtered.filter(item => {
      const t = (item.text || '').toLowerCase();
      return t.includes('form 5') || t.includes('form 6') || t.includes('matriculation') || t.includes('畢業') || t.includes('同學錄');
    });
  } else if (currentCategoryFilter === 'sports') {
    filtered = filtered.filter(item => {
      const t = (item.text || '').toLowerCase();
      return t.includes('swimming') || t.includes('football') || t.includes('basketball') || t.includes('society') || t.includes('club') || t.includes('champion');
    });
  }

  if (clauses.length > 0) {
    filtered = filtered.filter(item => itemMatchesQuery(item, clauses));
  }

  currentSearchResults = filtered;
  displayedCardCount = 12;
  renderCurrentPageResults(clauses);

}

function cleanField(val) {
  if (!val) return '';
  const s = String(val);
  if (s.startsWith('[') || s.startsWith('{')) {
    return sanitizeOcrText(s);
  }
  return s;
}

function getBilingualAliases(termObj) {
  if (!termObj || !bilingualDict) return [];
  const rawTerm = (typeof termObj === 'string') ? termObj : (termObj.term || termObj.displayTerm || '');
  const t = rawTerm.trim();
  const tLower = t.toLowerCase();
  const aliases = [];
  if (bilingualDict.en_to_zh && bilingualDict.en_to_zh[tLower]) {
    aliases.push(...bilingualDict.en_to_zh[tLower]);
  }
  if (bilingualDict.zh_to_en && bilingualDict.zh_to_en[t]) {
    aliases.push(...bilingualDict.zh_to_en[t]);
  }
  return aliases;
}

// Check if a single page item satisfies a search term across text, metadata, entities & activities (including bilingual aliases)
function itemMatchesTerm(item, termObj) {
  if (!termObj) return true;
  if (itemMatchesTermDirect(item, termObj)) return true;

  const aliases = getBilingualAliases(termObj);
  for (const a of aliases) {
    if (itemMatchesTermDirect(item, { term: a.toLowerCase(), displayTerm: a, isExact: termObj.isExact })) {
      return true;
    }
  }
  return false;
}

function itemMatchesTermDirect(item, termObj) {
  if (!termObj) return true;
  const term = (typeof termObj === 'string') ? termObj.toLowerCase().trim() : (termObj.term || '').toLowerCase().trim();
  const isExact = (typeof termObj === 'object') ? !!termObj.isExact : false;
  if (!term) return true;

  if (!isExact) {
    // 1. Broad substring match across text, summary & title
    const cleanText = (item.text || '').toLowerCase();
    if (cleanText.includes(term)) return true;
    const cleanSummary = cleanField(item.summary || '').toLowerCase();
    if (cleanSummary.includes(term)) return true;
    if (item.title && item.title.toLowerCase().includes(term)) return true;

    // 2. Year & Page & Class Designation & Section Type
    if (item.year && String(item.year).toLowerCase() === term) return true;
    if (item.year && String(item.year).toLowerCase().includes(term) && !/^\d{4}$/.test(term)) return true;
    if (term === String(item.page) || term === `page ${item.page}` || term === `p.${item.page}` || term === `p${item.page}`) return true;
    if (item.section_type && item.section_type.toLowerCase().includes(term)) return true;
    if (item.class_designation && item.class_designation.toLowerCase().includes(term)) return true;

    // 3. Students (OKF 0.2 structured entities)
    if (item.students && item.students.some(s => 
      (s.english_name && cleanField(s.english_name).toLowerCase().includes(term)) || 
      (s.chinese_name && cleanField(s.chinese_name).toLowerCase().includes(term))
    )) return true;

    // 4. Staff members & Teachers
    if (item.staff && item.staff.some(s => 
      (s.english_name && cleanField(s.english_name).toLowerCase().includes(term)) || 
      (s.chinese_name && cleanField(s.chinese_name).toLowerCase().includes(term)) ||
      (s.title_or_role && cleanField(s.title_or_role).toLowerCase().includes(term)) ||
      (s.department_or_subject && cleanField(s.department_or_subject).toLowerCase().includes(term))
    )) return true;

    // 5. Ground-truth verified student roster
    if (item.verified_names && item.verified_names.some(v => 
      (v.english_name && cleanField(v.english_name).toLowerCase().includes(term)) || 
      (v.chinese_name && cleanField(v.chinese_name).toLowerCase().includes(term))
    )) return true;

    // 6. Activities, Clubs & Societies (OKF 0.2 entities)
    if (item.activities && item.activities.some(act => {
      const club = cleanField(act.club_name || '').toLowerCase();
      const event = cleanField(act.event_or_activity || '').toLowerCase();
      const pEn = cleanField(act.participant_name_en || '').toLowerCase();
      const pZh = cleanField(act.participant_name_zh || '').toLowerCase();
      const role = cleanField(act.role || '').toLowerCase();
      return club.includes(term) || event.includes(term) || pEn.includes(term) || pZh.includes(term) || role.includes(term);
    })) return true;

    // 7. Sports records & athletic events (OKF 0.2 entities)
    if (item.sports_records && item.sports_records.some(sp => {
      const evt = cleanField(sp.event_name || '').toLowerCase();
      const athEn = cleanField(sp.athlete_name_en || '').toLowerCase();
      const athZh = cleanField(sp.athlete_name_zh || '').toLowerCase();
      const cat = cleanField(sp.category_or_grade || '').toLowerCase();
      const rec = cleanField(sp.record_or_time || '').toLowerCase();
      return evt.includes(term) || athEn.includes(term) || athZh.includes(term) || cat.includes(term) || rec.includes(term);
    })) return true;

    return false;
  }

  // --- EXACT / QUOTED SEARCH ---
  // 1. Year & Page & Class Designation & Section Type
  if (item.year && String(item.year).toLowerCase() === term) return true;
  if (term === String(item.page) || term === `page ${item.page}` || term === `p.${item.page}` || term === `p${item.page}`) return true;
  if (item.section_type && item.section_type.toLowerCase() === term) return true;
  if (item.class_designation && item.class_designation.toLowerCase() === term) return true;

  // 2. Structured Students & Verified Names
  if (item.verified_names && item.verified_names.some(v => matchEntityExact(v.english_name, term) || matchEntityExact(v.chinese_name, term))) return true;
  if (item.students && item.students.some(s => matchEntityExact(s.english_name, term) || matchEntityExact(s.chinese_name, term))) return true;
  if (item.staff && item.staff.some(s => matchEntityExact(s.english_name, term) || matchEntityExact(s.chinese_name, term))) return true;
  if (item.activities && item.activities.some(act => matchEntityExact(act.participant_name_en, term) || matchEntityExact(act.participant_name_zh, term) || matchEntityExact(act.club_name, term) || matchEntityExact(act.event_or_activity, term))) return true;
  if (item.sports_records && item.sports_records.some(sp => matchEntityExact(sp.athlete_name_en, term) || matchEntityExact(sp.athlete_name_zh, term) || matchEntityExact(sp.event_name, term))) return true;

  // 3. OCR Tokens (individual bounding box strings, e.g. 'Li Chi Fai')
  if (item._tokens && item._tokens.length > 0) {
    for (const tok of item._tokens) {
      if (tok.toLowerCase() === term) return true;
      if (matchEntityExact(tok, term)) return true;
    }
  }

  // 4. Clean Text & Summary & Title
  const cleanText = item.text || '';
  if (matchTextExact(cleanText, term)) return true;
  const cleanSummary = cleanField(item.summary || '');
  if (matchTextExact(cleanSummary, term)) return true;
  if (item.title && matchTextExact(item.title, term)) return true;

  return false;
}

function renderCurrentPageResults(clauses = []) {
  const resultsGrid = document.getElementById('resultsGrid');
  const resultsStats = document.getElementById('resultsStats');

  // Normalize: handle both array of clauses and array of terms
  const normClauses = clauses.map(c => (c && c.terms) ? c : { rawClause: c.raw || c.term, hasOr: false, terms: [c] });
  const allTerms = normClauses.flatMap(c => c.terms);

  const allTermsWithAliases = [];
  for (const t of allTerms) {
    allTermsWithAliases.push(t);
    const aliases = getBilingualAliases(t);
    for (const a of aliases) {
      allTermsWithAliases.push({ term: a.toLowerCase(), displayTerm: a, isExact: t.isExact });
    }
  }

  const totalMatches = currentSearchResults.length;
  let statsText = `Showing <strong>${Math.min(displayedCardCount, totalMatches)}</strong> of <strong>${totalMatches}</strong> matching pages`;

  if (currentYearFilter !== 'all') {
    let yearFilterBadge = `${escapeHtml(currentYearFilter)} Volume`;
    if (currentYearFilter === '1975_F5_Alumni' || currentYearFilter === 'F5_Alumni') {
      yearFilterBadge = '🎓 1975 (F5 Alumni Book)';
    } else if (currentYearFilter === '1975') {
      yearFilterBadge = '1975 Volume & Alumni Book';
    } else if (currentYearFilter === 'Reunion_Gala') {
      yearFilterBadge = '🎉 Reunion Gala';
    }
    statsText += ` in <span style="background: rgba(234,179,8,0.2); color: #fde047; border: 1px solid rgba(234,179,8,0.4); padding: 2px 8px; border-radius: 6px; font-weight: 700;">${yearFilterBadge}</span>`;
  }

  if (normClauses.length > 0) {
    const clauseBadges = normClauses.map(clause => {
      const formattedTerms = clause.terms.map(t => {
        const dTerm = escapeHtml(t.displayTerm || t.term || t);
        if (t.isExact) {
          return `<span style="background: rgba(16,185,129,0.2); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.5); padding: 2px 8px; border-radius: 6px; font-weight: 600;">"${dTerm}" <small style="font-size: 0.72rem; color: #a7f3d0;">(Exact / 精確)</small></span>`;
        }
        return `<span style="background: rgba(99,102,241,0.25); color: #c7d2fe; border: 1px solid rgba(99,102,241,0.4); padding: 2px 8px; border-radius: 6px; font-weight: 600;">${dTerm}</span>`;
      });

      if (clause.hasOr) {
        return `<span style="border: 1px dashed rgba(244,114,182,0.6); background: rgba(244,114,182,0.12); padding: 3px 8px; border-radius: 8px;">(${formattedTerms.join(' <strong style="color: #f472b6; font-size: 0.82rem;">OR</strong> ')})</span>`;
      }
      return formattedTerms.join('');
    });

    statsText += ` for: ${clauseBadges.join(' <strong style="color: #38bdf8;">AND</strong> ')}`;
  }
  statsText += ` (Master Archive: ${searchData.length} entries • OKF 0.2 Graph)`;
  resultsStats.innerHTML = statsText;

  if (totalMatches === 0) {
    resultsGrid.innerHTML = `
      <div class="no-results" style="text-align: center; padding: 2.5rem 1rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🔍</div>
        <h3>No matching archive pages found${currentYearFilter !== 'all' ? ` in ${escapeHtml(currentYearFilter)} Volume` : ''}</h3>
        <p style="margin-top: 0.5rem; color: var(--text-muted); max-width: 520px; margin-left: auto; margin-right: auto;">
          ${currentYearFilter !== 'all' 
            ? `No pages matched within the <strong>${escapeHtml(currentYearFilter)} Volume</strong>. These people or terms may appear together in another yearbook volume (e.g. 1972, 1974, or 1975)!` 
            : (normClauses.length > 1 ? `No pages matched all ${normClauses.length} criteria simultaneously. Try broadening one of the terms or checking spelling.` : 'Try broadening your search term.')}
        </p>
        ${currentYearFilter !== 'all' ? `
          <button type="button" class="tab-btn" onclick="setYearFilter('all')" style="margin-top: 1.25rem; padding: 0.75rem 1.75rem; background: linear-gradient(135deg, #4f46e5, #6366f1); color: #fff; border: none; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 0.95rem; box-shadow: 0 4px 15px rgba(99,102,241,0.4);">
            🌐 Switch to "All Years (全部年份)" (Search all 12 volumes)
          </button>
        ` : ''}
      </div>
    `;
    return;
  }

  const visibleItems = currentSearchResults.slice(0, displayedCardCount);
  let cardsHtml = visibleItems.map(item => renderResultCard(item, allTermsWithAliases)).join('');

  if (displayedCardCount < totalMatches) {
    cardsHtml += `
      <div style="grid-column: 1 / -1; text-align: center; margin: 2rem 0;">
        <button type="button" class="tab-btn" onclick="loadMoreCards()" style="padding: 0.85rem 2.5rem; font-size: 1rem; background: linear-gradient(135deg, #4f46e5, #6366f1); color: #fff; border: none; border-radius: 12px; cursor: pointer; box-shadow: 0 4px 20px rgba(99,102,241,0.3);">
          📥 Load More Pages (${totalMatches - displayedCardCount} remaining)
        </button>
      </div>
    `;
  }

  resultsGrid.innerHTML = cardsHtml;
}

function loadMoreCards() {
  const rawInput = document.getElementById('searchInput').value;
  const clauses = parseSearchQuery(rawInput);
  displayedCardCount += 12;
  renderCurrentPageResults(clauses);
}


function renderResultCard(item, terms = []) {
  const title = item.title || `Wah Yan Star ${item.year} - Page ${item.page}`;
  let yearLabel = `${item.year} Volume`;
  const isAlumniBook = item.year === '1975_F5_Alumni' || item.year === 'F5_Alumni';
  if (item.year === 'Reunion_Gala') {
    yearLabel = '🎉 Reunion Gala';
  } else if (isAlumniBook) {
    yearLabel = '🎓 1975 Form 5 Alumni Book';
  }

  const text = item.text || '';
  const photos = item.photos || [];
  const fullPagePhoto = item.full_page_photo;
  const sectionType = item.section_type || 'General';

  let snippet = text.slice(0, 220);
  if (terms && terms.length > 0) {
    let firstIdx = -1;
    for (const termObj of terms) {
      const t = (typeof termObj === 'string') ? termObj.toLowerCase() : (termObj.term || '').toLowerCase();
      if (!t) continue;
      const idx = text.toLowerCase().indexOf(t);
      if (idx !== -1 && (firstIdx === -1 || idx < firstIdx)) {
        firstIdx = idx;
      }
    }
    if (firstIdx !== -1) {
      const start = Math.max(0, firstIdx - 60);
      const end = Math.min(text.length, firstIdx + 140);
      snippet = (start > 0 ? '...' : '') + text.slice(start, end) + (end < text.length ? '...' : '');
    }
  }

  const highlightedSnippet = (terms && terms.length > 0) ? highlightText(snippet, terms) : escapeHtml(snippet);

  let profilesHtml = '';
  if (isAlumniBook && item.students && item.students.length > 0) {
    const studentChips = item.students.map(s => {
      const cls = s.class_designation ? ` <span style="opacity: 0.75; font-size: 0.74rem;">[${escapeHtml(s.class_designation)}]</span>` : '';
      const role = s.role ? ` <span style="color: #fde047; font-size: 0.74rem;">(${escapeHtml(s.role)})</span>` : '';
      return `<span style="background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); padding: 2px 7px; border-radius: 6px; font-size: 0.8rem; color: #c7d2fe; display: inline-block;"><strong>${escapeHtml(s.english_name)} (${escapeHtml(s.chinese_name)})</strong>${role}${cls}</span>`;
    }).join(' ');

    profilesHtml = `
      <div style="margin-bottom: 8px; padding: 6px 10px; background: rgba(15,23,42,0.7); border-radius: 8px; border-left: 3px solid #6366f1;">
        <div style="font-size: 0.78rem; font-weight: 700; color: #a5b4fc; margin-bottom: 4px;">🎓 Form 5 Profiles on this page:</div>
        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
          ${studentChips}
        </div>
      </div>
    `;
  }

  return `
    <div class="card">
      <div class="card-header">
        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
          <button type="button" 
                  class="page-badge" 
                  onclick="openLightbox(getPhotoUrl('${fullPagePhoto}'), '${escapeHtml(title)} - Full Page View', '${item.year}', ${item.page})" 
                  title="Click to view full page scan in full size">
            📄 ${escapeHtml(yearLabel)} • Page ${item.page} ↗
          </button>
          ${isAlumniBook ? `
            <button type="button" 
                    class="page-badge" 
                    style="background: rgba(234,179,8,0.18); color: #fde047; border: 1px solid rgba(234,179,8,0.45); cursor: pointer;" 
                    onclick="openLightbox(getPhotoUrl('1975_page_100_full.webp'), '1975 Form 5 Graduation Rosters (Pages 100-103) - Full Page View', '1975', 100)" 
                    title="Cross-reference: Wah Yan Star 1975 Form 5 Graduation Rosters (Pages 100-103)">
              📋 1975 Roster ↗
            </button>
          ` : ''}
          ${sectionType !== 'General' ? `<span class="page-badge" style="background: rgba(16,185,129,0.2); color: #34d399;">🏷️ ${escapeHtml(sectionType)}</span>` : ''}
        </div>
        <button type="button" class="zoom-btn" onclick="openLightboxAndEnlarge(getPhotoUrl('${fullPagePhoto}'), '${escapeHtml(title)} - Full Preview', '${item.year}', ${item.page})" style="background: linear-gradient(135deg, #4f46e5, #6366f1); color: #fff; border: none; padding: 5px 12px; font-size: 0.8rem; font-weight: 700; border-radius: 6px; cursor: pointer;" title="Enlarge (+50%)">
          🔍 Enlarge (+50%)
        </button>
      </div>

      <div class="card-snippet">
        ${profilesHtml}
        <p>${highlightedSnippet || '<em>Scanned image page / Roster page.</em>'}</p>
      </div>

      <div class="photo-gallery">
        ${photos && photos.length > 0 ? (
          photos.slice(0, 4).map(p => `
            <img src="${getPhotoUrl(p)}" 
                 alt="Extracted Photo" 
                 class="photo-thumb" 
                 loading="lazy"
                 decoding="async"
                 onerror="handleImageError(this)"
                 title="Click to view photo"
                 onclick="openLightbox(getPhotoUrl('${p}'), '${escapeHtml(title)} - Extracted Photo', '${item.year}', ${item.page})">
          `).join('')
        ) : (fullPagePhoto ? `
          <img src="${getPhotoUrl(fullPagePhoto)}" 
               alt="Page Scan" 
               class="photo-thumb" 
               loading="lazy"
               decoding="async"
               onerror="handleImageError(this)"
               title="Click to view full page scan"
               onclick="openLightbox(getPhotoUrl('${fullPagePhoto}'), '${escapeHtml(title)} - Full Preview', '${item.year}', ${item.page})">
        ` : '')}
      </div>
    </div>
  `;
}

function highlightText(text, terms) {
  if (!text) return '';
  if (!terms) return escapeHtml(text);
  const termList = Array.isArray(terms) ? terms : [terms];
  const validTerms = termList.map(t => {
    if (typeof t === 'string') return { term: t.trim().toLowerCase(), isExact: false };
    return { term: (t.term || '').trim().toLowerCase(), isExact: !!t.isExact };
  }).filter(t => t.term.length > 0);

  if (validTerms.length === 0) return escapeHtml(text);

  let escaped = escapeHtml(text);
  const sorted = [...validTerms].sort((a, b) => b.term.length - a.term.length);

  for (const item of sorted) {
    const escTerm = escapeRegex(escapeHtml(item.term));
    let regex;
    if (item.isExact) {
      if (/[\u4e00-\u9fff]/.test(item.term)) {
        regex = new RegExp(`(?<![\\u4e00-\\u9fff])(${escTerm})(?![\\u4e00-\\u9fff])`, 'gi');
      } else {
        regex = new RegExp(`(?<![A-Za-z0-9])(${escTerm})(?![A-Za-z0-9])`, 'gi');
      }
    } else {
      regex = new RegExp(`(${escTerm})`, 'gi');
    }
    escaped = escaped.replace(regex, '<mark>$1</mark>');
  }
  return escaped;
}

function applyPresetSearch(term) {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.value = term;
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) clearBtn.style.display = 'block';
    performSearch();
    searchInput.focus();
  }
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
}

function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(view => view.classList.remove('active'));

  const tabSearch = document.getElementById('tabSearch');
  const viewSearch = document.getElementById('viewSearch');
  const tabChat = document.getElementById('tabChat');
  const viewChat = document.getElementById('viewChat');

  if (tab === 'search') {
    if (tabSearch) tabSearch.classList.add('active');
    if (viewSearch) viewSearch.classList.add('active');
  } else if (tab === 'chat') {
    if (tabChat) tabChat.classList.add('active');
    if (viewChat) viewChat.classList.add('active');
  }
}

// Interactive Lightbox Modal & Zoom & Rotate Controls (+50% Enlarge, 180° Rotate, Page Navigation)
let baseImageWidth = 0;
let baseImageHeight = 0;
let currentLightboxYear = null;
let currentLightboxPage = null;
let currentLightboxMaxPage = null;

function openLightbox(imageSrc, title, year = null, page = null) {
  const modal = document.getElementById('lightboxModal');
  const modalImg = document.getElementById('modalImage');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const wrapper = document.getElementById('modalImageWrapper');
  const spinner = document.getElementById('modalSpinner');

  // Show spinner and hide previous image to avoid stale image flashes
  if (spinner) spinner.style.display = 'flex';
  modalImg.style.opacity = '0';
  modalImg.style.transition = 'opacity 0.25s ease-in';

  modalImg.src = imageSrc;
  modalTitle.textContent = title;

  // Resolve year and page if not explicitly provided
  if (!year || !page) {
    const match = imageSrc.match(/([A-Za-z0-9_]+)_page_(\d+)/);
    if (match) {
      year = match[1];
      page = parseInt(match[2], 10);
    } else {
      const titleMatch = title.match(/(\d{4}|F5_Alumni|Reunion_Gala).*?Page\s+(\d+)/i);
      if (titleMatch) {
        year = titleMatch[1];
        page = parseInt(titleMatch[2], 10);
      }
    }
  }

  currentLightboxYear = year ? String(year) : null;
  currentLightboxPage = page ? parseInt(page, 10) : null;
  updateLightboxNavigationUI();
  
  // Reset zoom scale and rotation
  currentZoomScale = 1.0;
  currentRotationDegrees = 0;
  baseImageWidth = 0;
  baseImageHeight = 0;

  // Reset styles
  modalImg.style.width = '';
  modalImg.style.height = '';
  modalImg.style.maxWidth = '100%';
  modalImg.style.maxHeight = '75vh';
  modalImg.style.transform = 'none';

  if (wrapper) {
    wrapper.style.width = '';
    wrapper.style.height = '';
    wrapper.style.margin = 'auto';
  }

  modal.classList.add('active');

  const onImageReady = () => {
    if (spinner) spinner.style.display = 'none';
    modalImg.style.opacity = '1';
    baseImageWidth = modalImg.clientWidth || modalImg.naturalWidth;
    baseImageHeight = modalImg.clientHeight || modalImg.naturalHeight;
    applyZoomScale();
    if (modalBody) {
      modalBody.scrollTop = 0;
      modalBody.scrollLeft = 0;
    }
    // Prefetch next and previous full pages in the background
    prefetchAdjacentPages(currentLightboxYear, currentLightboxPage);
  };

  if (modalImg.complete && modalImg.naturalWidth > 0) {
    onImageReady();
  } else {
    modalImg.onload = onImageReady;
  }
}

function prefetchAdjacentPages(year, page) {
  if (!year || !page || !searchData || searchData.length === 0) return;
  const maxPage = getMaxPageForYear(year);
  // Prefetch next page
  if (page < maxPage) {
    const nextItem = searchData.find(item => String(item.year) === String(year) && item.page === page + 1);
    const nextPhoto = nextItem?.full_page_photo || `${year}_page_${String(page + 1).padStart(3, '0')}_full.webp`;
    const imgNext = new Image();
    imgNext.src = getPhotoUrl(nextPhoto);
  }
  // Prefetch previous page
  if (page > 1) {
    const prevItem = searchData.find(item => String(item.year) === String(year) && item.page === page - 1);
    const prevPhoto = prevItem?.full_page_photo || `${year}_page_${String(page - 1).padStart(3, '0')}_full.webp`;
    const imgPrev = new Image();
    imgPrev.src = getPhotoUrl(prevPhoto);
  }
}


function openLightboxAndEnlarge(imageSrc, title, year = null, page = null) {
  openLightbox(imageSrc, title, year, page);
  zoomLightbox(0.50); // Immediately enlarge +50%
}

function updateLightboxNavigationUI() {
  const floatingPrevBtn = document.getElementById('floatingPrevBtn');
  const floatingNextBtn = document.getElementById('floatingNextBtn');
  const tbPrevBtn = document.getElementById('tbPrevBtn');
  const tbNextBtn = document.getElementById('tbNextBtn');
  const pageNavIndicator = document.getElementById('pageNavIndicator');

  if (!currentLightboxYear || !currentLightboxPage || !searchData || searchData.length === 0) {
    if (floatingPrevBtn) floatingPrevBtn.style.display = 'none';
    if (floatingNextBtn) floatingNextBtn.style.display = 'none';
    if (tbPrevBtn) tbPrevBtn.style.display = 'none';
    if (tbNextBtn) tbNextBtn.style.display = 'none';
    if (pageNavIndicator) pageNavIndicator.style.display = 'none';
    return;
  }

  const yearPages = searchData
    .filter(item => String(item.year) === String(currentLightboxYear))
    .sort((a, b) => a.page - b.page);

  if (yearPages.length <= 1) {
    if (floatingPrevBtn) floatingPrevBtn.style.display = 'none';
    if (floatingNextBtn) floatingNextBtn.style.display = 'none';
    if (tbPrevBtn) tbPrevBtn.style.display = 'none';
    if (tbNextBtn) tbNextBtn.style.display = 'none';
    if (pageNavIndicator) pageNavIndicator.style.display = 'none';
    return;
  }

  const minPage = yearPages[0].page;
  const maxPage = yearPages[yearPages.length - 1].page;
  currentLightboxMaxPage = maxPage;

  const hasPrev = currentLightboxPage > minPage;
  const hasNext = currentLightboxPage < maxPage;

  [floatingPrevBtn, tbPrevBtn].forEach(btn => {
    if (btn) {
      btn.style.display = 'flex';
      btn.disabled = !hasPrev;
      btn.title = hasPrev ? `Previous Page (Page ${currentLightboxPage - 1}) • Shortcut: ←` : 'At First Page';
    }
  });

  [floatingNextBtn, tbNextBtn].forEach(btn => {
    if (btn) {
      btn.style.display = 'flex';
      btn.disabled = !hasNext;
      btn.title = hasNext ? `Next Page (Page ${currentLightboxPage + 1}) • Shortcut: →` : 'At Last Page';
    }
  });

  if (pageNavIndicator) {
    pageNavIndicator.style.display = 'inline-block';
    let yearDisplay = currentLightboxYear;
    if (yearDisplay === '1975_F5_Alumni' || yearDisplay === 'F5_Alumni') yearDisplay = 'Form 5';
    else if (yearDisplay === 'Reunion_Gala') yearDisplay = 'Gala';
    pageNavIndicator.textContent = `${yearDisplay} • Pg ${currentLightboxPage} / ${maxPage}`;
  }
}

function navigateLightboxPage(delta) {
  if (!currentLightboxYear || !currentLightboxPage) return;
  const targetPage = currentLightboxPage + delta;

  const targetItem = searchData.find(item => 
    String(item.year) === String(currentLightboxYear) && item.page === targetPage
  );

  if (targetItem) {
    const fullPhoto = targetItem.full_page_photo || `${targetItem.year}_page_${String(targetItem.page).padStart(3, '0')}_full.webp`;
    const title = targetItem.title || `Wah Yan Star ${targetItem.year} - Page ${targetItem.page}`;
    
    openLightbox(
      getPhotoUrl(fullPhoto), 
      `${title} - Full Page View`, 
      targetItem.year, 
      targetItem.page
    );
  }
}

function closeLightbox() {
  const modal = document.getElementById('lightboxModal');
  modal.classList.remove('active');
}

function zoomLightbox(delta) {
  currentZoomScale += delta;
  if (currentZoomScale < 0.5) currentZoomScale = 0.5;
  if (currentZoomScale > 4.0) currentZoomScale = 4.0;
  applyZoomScale();
}

function handleImageClickZoom() {
  if (currentZoomScale < 2.0) {
    zoomLightbox(0.5);
  } else {
    resetLightboxZoom();
  }
}

function rotateLightboxImage(degrees = 180) {
  currentRotationDegrees = (currentRotationDegrees + degrees) % 360;
  if (currentRotationDegrees < 0) currentRotationDegrees += 360;
  applyZoomScale();
}

function resetLightboxZoom() {
  currentZoomScale = 1.0;
  currentRotationDegrees = 0;
  applyZoomScale();
  const modalBody = document.getElementById('modalBody');
  if (modalBody) {
    modalBody.scrollTop = 0;
    modalBody.scrollLeft = 0;
  }
}

function applyZoomScale() {
  const modalImg = document.getElementById('modalImage');
  const modalBody = document.getElementById('modalBody');
  const wrapper = document.getElementById('modalImageWrapper');
  const zoomIndicator = document.getElementById('zoomIndicator');
  
  if (!modalImg) return;

  if (!baseImageWidth && modalImg.clientWidth) {
    baseImageWidth = modalImg.clientWidth;
    baseImageHeight = modalImg.clientHeight;
  }

  const isRotatedSideways = (currentRotationDegrees === 90 || currentRotationDegrees === 270);
  const viewportW = modalBody ? modalBody.clientWidth : window.innerWidth;
  const viewportH = modalBody ? modalBody.clientHeight : window.innerHeight;

  if (currentZoomScale <= 1.0) {
    modalImg.style.maxWidth = '100%';
    modalImg.style.maxHeight = '75vh';
    modalImg.style.width = 'auto';
    modalImg.style.height = 'auto';

    if (wrapper) {
      wrapper.style.width = '';
      wrapper.style.height = '';
      wrapper.style.margin = 'auto';
    }
  } else {
    modalImg.style.maxWidth = 'none';
    modalImg.style.maxHeight = 'none';

    const targetW = Math.round((baseImageWidth || 650) * currentZoomScale);
    modalImg.style.width = `${targetW}px`;
    modalImg.style.height = 'auto';

    let layoutW = targetW;
    let layoutH = modalImg.clientHeight || Math.round((baseImageHeight || 900) * currentZoomScale);

    if (isRotatedSideways) {
      layoutW = layoutH;
      layoutH = targetW;
    }

    if (wrapper) {
      wrapper.style.width = `${layoutW}px`;
      wrapper.style.height = `${layoutH}px`;

      // Check overflow: if content is wider or taller than container, do NOT use 'auto' margin.
      // 'auto' margin in flex containers causes negative overflow coordinates, which permanently
      // clips the left/top edges and prevents the scrollbar from scrolling to them!
      const overflowsX = layoutW > (viewportW - 32);
      const overflowsY = layoutH > (viewportH - 32);

      wrapper.style.marginLeft = overflowsX ? '0.5rem' : 'auto';
      wrapper.style.marginRight = overflowsX ? '0.5rem' : 'auto';
      wrapper.style.marginTop = overflowsY ? '0.5rem' : 'auto';
      wrapper.style.marginBottom = overflowsY ? '0.5rem' : 'auto';
    }
  }

  modalImg.style.transformOrigin = 'center center';
  modalImg.style.transform = `rotate(${currentRotationDegrees}deg)`;

  if (zoomIndicator) {
    const rotLabel = currentRotationDegrees ? ` • ${currentRotationDegrees}°` : '';
    zoomIndicator.textContent = `${Math.round(currentZoomScale * 100)}% Scale${rotLabel}`;
  }
}

function handleChatSubmit(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return false;

  askChatbot(query);
  input.value = '';
  return false;
}

function clearChatHistory() {
  const chatLog = document.getElementById('chatLog');
  if (!chatLog) return;

  chatLog.innerHTML = `
    <div class="chat-message bot-msg">
      <div class="msg-author">🤖 Wah Yan Star AI Assistant</div>
      <div class="msg-body">
        Chat history cleared! Connected to Local LM Studio AI Model (\`http://localhost:1234\`) with local RAG fallback. Type any student or teacher name to start.
      </div>
    </div>
  `;
}

async function askChatbot(question) {
  switchTab('chat');
  const chatLog = document.getElementById('chatLog');

  const userMsgDiv = document.createElement('div');
  userMsgDiv.className = 'chat-message user-msg';
  userMsgDiv.innerHTML = `
    <div class="msg-author">You</div>
    <div class="msg-body">${escapeHtml(question)}</div>
  `;
  chatLog.appendChild(userMsgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;

  const thinkingMsgDiv = document.createElement('div');
  thinkingMsgDiv.className = 'chat-message bot-msg';
  thinkingMsgDiv.id = 'thinkingMsg';
  thinkingMsgDiv.innerHTML = `
    <div class="msg-author">🤖 Wah Yan Star AI Assistant</div>
    <div class="msg-body"><em style="color: #a5b4fc;">Thinking & querying LM Studio local model / dataset...</em></div>
  `;
  chatLog.appendChild(thinkingMsgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;

  if (chatbot) {
    try {
      const res = await chatbot.query(question);
      if (thinkingMsgDiv) thinkingMsgDiv.remove();

      const botMsgDiv = document.createElement('div');
      botMsgDiv.className = 'chat-message bot-msg';
      botMsgDiv.innerHTML = `
        <div class="msg-author">🤖 Wah Yan Star AI Assistant</div>
        <div class="msg-body">${res.html}</div>
        ${res.photos && res.photos.length > 0 ? `
          <div class="photo-gallery" style="margin-top: 0.85rem;">
            ${res.photos.map(p => `
              <img src="${p.src}" class="photo-thumb" loading="lazy" onclick="openLightbox('${p.src}', '${escapeHtml(p.caption)}')" title="${escapeHtml(p.caption)}">
            `).join('')}
          </div>
        ` : ''}
      `;
      chatLog.appendChild(botMsgDiv);
    } catch (chatErr) {
      console.error("Chat error:", chatErr);
      if (thinkingMsgDiv) thinkingMsgDiv.remove();
    }
  }

  chatLog.scrollTop = chatLog.scrollHeight;
}
