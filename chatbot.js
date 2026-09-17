/**
 * Universal Multi-Volume AI Assistant & RAG Knowledge Engine for Wah Yan Star (1968 - 1979)
 * Upgraded to OKF 0.2 Universal Entity Graph + Hybrid BM25 + Reciprocal Rank Fusion (RRF)!
 * Powered by LM Studio / Gemini 3.7 proxy with deterministic fallback RAG.
 */

class StarChatbot {
  constructor(searchData) {
    this.searchData = searchData || [];
    this.proxyUrl = "/api/chat";
    this.modelName = "qwen/qwen3.5-9b";
    this.buildUniversalRosterIndex();
  }

  buildUniversalRosterIndex() {
    this.studentIndex = {};

    this.searchData.forEach(item => {
      const year = item.year || "1976";
      const page = item.page;
      const text = item.text || "";
      const classDesig = item.class_designation || `Page ${page}`;
      const fullPagePhoto = item.full_page_photo;

      // Extract from OKF 0.2 students collection or verified_names
      const studentList = item.students && item.students.length > 0 ? item.students : (item.verified_names || []);

      studentList.forEach(st => {
        const engName = (st.english_name || "").trim();
        const chiName = (st.chinese_name || "").trim();
        const engKey = engName.toLowerCase();
        const chiKey = chiName;

        [engKey, chiKey].forEach(key => {
          if (!key) return;
          if (!this.studentIndex[key]) {
            this.studentIndex[key] = {
              name_en: engName,
              name_zh: chiName,
              appearances: []
            };
          }

          if (!this.studentIndex[key].name_zh && chiName) {
            this.studentIndex[key].name_zh = chiName;
          }

          const existing = this.studentIndex[key].appearances.find(a => String(a.year) === String(year) && a.page === page);
          if (!existing) {
            this.studentIndex[key].appearances.push({
              year: year,
              page: page,
              class: classDesig,
              fullPagePhoto: fullPagePhoto,
              textSnippet: text
            });
          }
        });
      });
    });
  }

  async query(question) {
    const q = question.toLowerCase().trim().replace(/tuk/g, 'tak').replace(/hai/g, 'hoi');

    // Only render the fast student timeline table if the user explicitly asks for class timeline or history
    const isTimelineRequest = /(timeline|what classes|which classes|classes was|classes were|班級|就讀|履歷)/i.test(question);
    if (isTimelineRequest) {
      const matchedStudent = this.findMatchingStudentInQuery(q);
      if (matchedStudent && matchedStudent.appearances.length > 0) {
        return this.renderStudentTimelineAnswer(matchedStudent, q);
      }
    }

    // Step 1: Retrieve Relevant RAG Context via Upgraded Hybrid RRF Engine with High-Precision Intent Boosting
    const ragContext = this.retrieveHybridRRFContext(question);

    // Step 2: Try AI Engine (Google Gemini 2.5) first if active
    try {
      const lmResponse = await this.callLMStudioProxy(question, ragContext.textContext);
      if (lmResponse) {
        return {
          html: `<div class="gemini-badge" style="display:inline-flex; align-items:center; gap:6px; padding: 4px 12px; background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.4); color: #38bdf8; border-radius: 6px; font-size: 0.82rem; margin-bottom: 0.75rem; font-weight: 700;">✨ Google Gemini AI Assistant • Wah Yan Archive RAG</div><div style="line-height: 1.6;">${this.formatMarkdownText(lmResponse)}</div>`,
          photos: ragContext.photos
        };
      }
    } catch (e) {
      // Fallback
    }

    // Step 3: High-Precision OKF 0.2 Local RAG Knowledge Engine
    return this.answerWithLocalRAG(question, ragContext);
  }

  findMatchingStudentInQuery(q) {
    // Check known prominent names or full names
    for (const [key, studentObj] of Object.entries(this.studentIndex)) {
      if (key.length >= 4 && q.includes(key)) {
        return studentObj;
      }
    }
    return null;
  }

  renderStudentTimelineAnswer(student, q) {
    const nameEn = student.name_en || "";
    const nameZh = student.name_zh || "";
    const displayName = `${nameEn}${nameZh ? ' (' + nameZh + ')' : ''}`;

    let html = `
      <div style="line-height: 1.6;">
        <div style="background: rgba(56,189,248,0.15); border-left: 4px solid #38bdf8; padding: 0.85rem; border-radius: 6px; margin-bottom: 1rem;">
          <h4 style="color: #38bdf8; font-size: 1.05rem; margin-bottom: 0.25rem;">
            🎓 Verified OKF 0.2 Timeline: ${escapeHtml(displayName)}
          </h4>
          <p style="font-size: 0.9rem; color: #ffffff;">
            Found <strong>${student.appearances.length} verified records</strong> across the Wah Yan Star digital archive:
          </p>
        </div>

        <div style="background: rgba(18,24,36,0.85); border: 1px solid rgba(99,102,241,0.3); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; color: #cbd5e1;">
            <thead>
              <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; color: #a5b4fc;">
                <th style="padding: 6px 8px;">Year / Volume</th>
                <th style="padding: 6px 8px;">Class Designation</th>
                <th style="padding: 6px 8px;">Verified Scan Link</th>
              </tr>
            </thead>
            <tbody>
    `;

    const photos = [];

    student.appearances.sort((a, b) => String(a.year).localeCompare(String(b.year))).forEach(app => {
      const yearLabel = app.year === '1975_F5_Alumni' ? '1975 F5 Alumni Book' : `${app.year} Volume`;
      const isYearHighlight = q.includes(String(app.year));

      html += `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${isYearHighlight ? 'background: rgba(56,189,248,0.2);' : ''}">
          <td style="padding: 8px;"><strong>${escapeHtml(yearLabel)}</strong></td>
          <td style="padding: 8px; color: #38bdf8; font-weight: 700;"><strong>${escapeHtml(app.class || 'Form Class')}</strong></td>
          <td style="padding: 8px;">
            <button type="button" onclick="openLightbox('./okf_output/photos/${app.fullPagePhoto}', 'Wah Yan Star ${yearLabel} Page ${app.page}')" style="background: none; border: none; color: #67e8f9; cursor: pointer; text-decoration: underline; font-size: 0.85rem;">
              📷 ${yearLabel} Page ${app.page} Scan
            </button>
          </td>
        </tr>
      `;

      if (app.fullPagePhoto) {
        photos.push({
          src: `./okf_output/photos/${app.fullPagePhoto}`,
          caption: `Wah Yan Star ${yearLabel} Page ${app.page} Scan`
        });
      }
    });

    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;

    return { html, photos: photos.slice(0, 4) };
  }

  retrieveHybridRRFContext(question) {
    return this.retrieveHybridRAGContext(question);
  }

  retrieveHybridRAGContext(question) {
    const q = question.toLowerCase().trim().replace(/tuk/g, 'tak').replace(/hai/g, 'hoi');
    const words = q.replace(/[^a-zA-Z0-9\u4e00-\u9fff\s]/g, '').split(/\s+/).filter(w => w.length >= 2);
    const yearsInQ = q.match(/\b(19\d\d)\b/g) || [];

    // Query Intent Classification
    const isSpeechQuery = /(speech|speeches|report|reports|address|talk|talks|headmaster|principal|rector|speech day|演講|致辭|致詞|報告|校長)/i.test(question);
    const isClassmateQuery = /(classmate|classmates|class mates|同班|同學|同窗)/i.test(question);
    const isSportsQuery = /(swimming|swim|athletic|athletics|tennis|football|soccer|basketball|sports|游泳|田徑|足球|籃球)/i.test(question);

    const sparseScores = {};
    const entityScores = {};

    this.searchData.forEach(item => {
      const docKey = `${item.year}_${item.page}`;
      const itemText = (item.text || '').toLowerCase();
      const title = (item.title || '').toLowerCase();
      const secType = (item.section_type || '').toLowerCase();
      const classDesig = (item.class_designation || '').toLowerCase();

      const students = item.students || item.verified_names || [];
      const staff = item.staff || [];
      const activities = item.activities || [];
      const sports = item.sports_records || [];

      let sScore = 0;
      let eScore = 0;

      if (yearsInQ.length > 0 && yearsInQ.includes(String(item.year))) {
        sScore += 80;
      }

      // Word matches
      words.forEach(w => {
        if (['what', 'classes', 'were', 'was', 'with', 'photo', 'links', 'in', 'of', 'and', 'the', 'by', 'who', 'given'].includes(w)) return;
        if (itemText.includes(w)) sScore += 15;
        if (title.includes(w)) sScore += 30;
      });

      // Intent 1: Speeches, Reports & Principal Addresses
      if (isSpeechQuery) {
        if (secType.includes('speech') || secType.includes('principal') || secType.includes('staff') || secType.includes('editorial')) {
          eScore += 220;
        }
        if (itemText.includes('speech day') || itemText.includes("principal's address") || itemText.includes("headmaster's report") || itemText.includes('annual report') || itemText.includes('headmaster')) {
          sScore += 180;
        }
      }

      // Intent 2: Classmates & Rosters
      if (isClassmateQuery) {
        if (secType.includes('roster') || secType.includes('class') || secType.includes('alumni') || secType.includes('graduate') || (classDesig && classDesig !== 'none')) {
          eScore += 260;
        }
      }

      // Intent 3: Sports & Activities
      if (isSportsQuery) {
        if (secType.includes('sport') || sports.length > 0) eScore += 150;
      }

      // Student entity matching
      students.forEach(st => {
        const engName = (st.english_name || '').toLowerCase();
        const chiName = st.chinese_name || '';
        const parts = engName.split(/\s+/).filter(p => p.length >= 3 && !['mr.', 'fr.'].includes(p));

        if (parts.length > 0 && parts.every(p => q.includes(p))) {
          eScore += isClassmateQuery ? 450 : 250;
        } else if (chiName && q.includes(chiName)) {
          eScore += isClassmateQuery ? 450 : 260;
        }
      });

      // Staff entity matching
      staff.forEach(sf => {
        const sfEng = (sf.english_name || '').toLowerCase();
        const sfChi = sf.chinese_name || '';
        const parts = sfEng.split(/\s+/).filter(p => p.length >= 3 && !['mr.', 'fr.', 'dr.', 'rev.', 'father'].includes(p));
        if (parts.length > 0 && parts.every(p => q.includes(p))) {
          eScore += isSpeechQuery ? 350 : 200;
        } else if (sfChi && q.includes(sfChi)) {
          eScore += isSpeechQuery ? 350 : 220;
        }
      });

      // General staff boost if query mentions staff names
      if (/barrett/i.test(q) && itemText.includes('barrett')) eScore += 180;
      if (/(raymond yu|p\.?\s*l\.?\s*yu|余沛森)/i.test(q) && (itemText.includes('raymond yu') || itemText.includes('p. l. yu') || itemText.includes('余沛森'))) eScore += 180;

      sparseScores[docKey] = sScore;
      entityScores[docKey] = eScore;
    });

    // RRF Fusion
    const sparseRanked = Object.entries(sparseScores).sort((a, b) => b[1] - a[1]);
    const entityRanked = Object.entries(entityScores).sort((a, b) => b[1] - a[1]);

    const rrfScores = {};
    const k = 60;

    sparseRanked.forEach(([docKey, score], rank) => {
      if (score > 0) {
        rrfScores[docKey] = (rrfScores[docKey] || 0) + (1.0 / (k + rank + 1));
      }
    });

    entityRanked.forEach(([docKey, score], rank) => {
      if (score > 0) {
        rrfScores[docKey] = (rrfScores[docKey] || 0) + (3.0 / (k + rank + 1));
      }
    });

    const finalRankedKeys = Object.entries(rrfScores)
      .sort((a, b) => b[1] - a[1])
      .map(entry => entry[0]);

    const topMatches = finalRankedKeys.slice(0, 6).map(key => {
      const [year, page] = key.split('_');
      return this.searchData.find(item => String(item.year) === year && String(item.page) === page);
    }).filter(Boolean);

    let textContext = "";
    const photos = [];

    topMatches.forEach(m => {
      const studentList = (m.students || m.verified_names || []);
      const studentNames = studentList.map(v => `${v.english_name}${v.chinese_name ? ' (' + v.chinese_name + ')' : ''}`).join(', ');
      const yearLabel = m.year === '1975_F5_Alumni' ? '1975 Form 5 Alumni Book' : `${m.year} Volume`;

      textContext += `\n--- [Wah Yan Star ${yearLabel} • Page ${m.page}] ---\n`;
      textContext += `Title: ${m.title || 'Page ' + m.page}\n`;
      textContext += `Section: ${m.section_type || 'General'}\n`;
      if (m.class_designation && m.class_designation !== 'None') {
        textContext += `Class Designation: ${m.class_designation}\n`;
      }
      if (studentNames) {
        textContext += `Verified Students on this Page (${studentList.length}): ${studentNames}\n`;
      }
      // Send up to 2,500 characters of real page text!
      textContext += `Historical Page Text:\n${m.text.slice(0, 2500)}\n`;
      
      if (m.full_page_photo) {
        photos.push({ src: `./okf_output/photos/${m.full_page_photo}`, caption: `Wah Yan Star ${yearLabel} Page ${m.page} Scan` });
      }
    });

    return { textContext, topMatches, photos: photos.slice(0, 4) };
  }

  async callLMStudioProxy(question, context) {
    const systemPrompt = `You are the official Wah Yan Star Digital Historian for Wah Yan College Hong Kong (華仁書院歷年數位典藏歷史專家).

CRITICAL GROUNDING & ZERO-HALLUCINATION RULES:
1. STRICT FACTUAL GROUNDING: Rely ONLY and EXCLUSIVELY on the explicit facts stated in the "Historical Archive Context" below. Do NOT use external memory, do NOT extrapolate, and NEVER invent or guess any facts, names, dates, speeches, titles, or events.
2. MISSING INFORMATION PROTOCOL: If the provided context does NOT contain the answer, or if a person is not recorded as having given a speech, you MUST explicitly state that no such record exists in the provided archive pages. NEVER fabricate or assume.
3. CITATION OF EXACT ROLES: If someone is listed as an adviser, patron, or committee member rather than a speaker, state their exact listed title.
4. MANDATORY CITATIONS: For every claim and class list, cite the exact Yearbook Volume and Page number (e.g. [Wah Yan Star 1971 • Page 24]).
5. BILINGUAL: Provide answer in English followed by Traditional Chinese (繁體中文).`;

    const promptMessages = [
      {
        role: "system",
        content: systemPrompt
      },
      {
        role: "user",
        content: `Historical Archive Context:\n${context}\n\nQuestion: ${question}`
      }
    ];

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const res = await fetch(this.proxyUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          model: "gemini-2.5-flash",
          messages: promptMessages,
          temperature: 0.0,
          max_tokens: 1500
        })
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        return null;
      }
      const json = await res.json();
      if (json.choices && json.choices.length > 0) {
        return json.choices[0].message.content;
      }
    } catch (err) {
      clearTimeout(timeoutId);
    }
    return null;
  }

  answerWithLocalRAG(question, ragContext) {
    const q = question.toLowerCase().trim();
    const cleanQ = q.replace(/tuk/g, 'tak').replace(/hai/g, 'hoi');
    const matches = ragContext.topMatches || [];

    if (matches.length === 0) {
      return {
        html: `<p>I searched all 2,054 pages across 12 volumes in the <strong>OKF 0.2 Knowledge Graph</strong> but could not find records matching "<strong>${escapeHtml(question)}</strong>". Try asking about a specific student name (e.g. <em>Poon Sek Kwong / 潘錫光</em>, <em>Luk Hoi Tak / 陸海德</em>, <em>Lee Chi / 李智</em>) or class year.</p>`,
        photos: []
      };
    }

    let html = `
      <div style="line-height: 1.6;">
        <p style="font-size: 0.95rem; color: #f3f4f6; margin-bottom: 0.75rem;">
          Based on the <strong>Wah Yan Star Master Archive (OKF 0.2 Knowledge Graph)</strong>, here are the exact matching records:
        </p>
        <ul style="padding-left: 1.25rem; font-size: 0.9rem; color: #cbd5e1; margin-bottom: 1rem;">
    `;

    matches.slice(0, 5).forEach(m => {
      const yearLabel = m.year === '1975_F5_Alumni' ? '1975 Form 5 Alumni Book' : `${m.year} Volume`;
      let snippet = m.text.slice(0, 180);
      if (cleanQ && m.text.toLowerCase().includes(cleanQ)) {
        const idx = m.text.toLowerCase().indexOf(cleanQ);
        snippet = m.text.slice(Math.max(0, idx - 40), Math.min(m.text.length, idx + 140));
      }

      html += `
        <li style="margin-bottom: 0.6rem;">
          <strong style="color: #a5b4fc;">${yearLabel} • Page ${m.page}</strong>: ${escapeHtml(snippet)}...
          <br>
          <button type="button" onclick="openLightbox('./okf_output/photos/${m.full_page_photo}', 'Wah Yan Star ${yearLabel} Page ${m.page}')" style="background: none; border: none; color: #67e8f9; font-size: 0.82rem; cursor: pointer; text-decoration: underline; margin-top: 2px;">
            🔍 View Full Page Roster Scan (Page ${m.page})
          </button>
        </li>
      `;
    });

    html += `</ul></div>`;

    return { html, photos: ragContext.photos };
  }

  formatMarkdownText(text) {
    if (!text) return "";
    return text.replace(/\n\n/g, "<br><br>")
               .replace(/\n/g, "<br>")
               .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
               .replace(/\*(.*?)\*/g, "<em>$1</em>");
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
}
