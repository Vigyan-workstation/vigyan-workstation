// Vigyan Pro — Mathematical Typography & Markdown Engine
// Renders LaTeX (\[...\], \(...\), $$...$$, $...$), Markdown headers, lists, code, and bold text.
// Uses local bundled KaTeX typography with full delimiter normalization.

declare const katex: {
  renderToString: (
    tex: string,
    opts: { throwOnError: boolean; displayMode: boolean }
  ) => string;
};

/**
 * Convert raw AI response into publishing-grade mathematical typography.
 */
export function renderMath(text: string): string {
  if (!text) return "";

  // Normalize Windows newlines and multiple backslashes before brackets
  let src = text.replace(/\r\n/g, "\n");

  const placeholders: { id: string; html: string }[] = [];
  const makePlaceholder = (html: string) => {
    const id = `__VG_MATH_PH_${placeholders.length}__`;
    placeholders.push({ id, html });
    return id;
  };

  // 1. Triple-backtick code blocks
  src = src.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const safeCode = escapeHtml(code.trim());
    return makePlaceholder(
      `<pre class="bg-s1 border border-b2 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-platinum"><code>${safeCode}</code></pre>`
    );
  });

  // 2. Display Math: \\[ ... \\], \[ ... \], $$ ... $$
  // Matches any sequence of 1+ backslashes followed by [ and ending with 1+ backslashes ]
  src = src.replace(/(?:\\+\[|\$\$)([\s\S]*?)(?:\\+\]|\$\$)/g, (_, tex) => {
    return makePlaceholder(renderKatexSafe(tex.trim(), true));
  });

  // 3. Inline Math: \\( ... \\), \( ... \)
  src = src.replace(/\\+\(([\s\S]*?)\\+\)/g, (_, tex) => {
    return makePlaceholder(renderKatexSafe(tex.trim(), false));
  });

  // 4. Inline Math: $ ... $ (avoid currency amounts like $100)
  src = src.replace(/(?:^|[\s(])\$([^$\n]+)\$(?=[\s),.?!:;]|$)/g, (fullMatch, tex) => {
    if (!/^\d+[\s.,]/.test(tex) && tex.length < 120 && !tex.includes("\n")) {
      return ` ${makePlaceholder(renderKatexSafe(tex.trim(), false))}`;
    }
    return fullMatch;
  });

  // 5. Line-by-line markdown formatting
  const lines = src.split("\n");
  const formattedLines: string[] = [];

  for (let line of lines) {
    const trimmed = line.trim();

    // H3: ### ...
    if (trimmed.startsWith("### ")) {
      formattedLines.push(
        `<div class="mt-4 mb-2 text-xs font-semibold tracking-wider uppercase text-emerald flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-emerald"></span>${escapeHtml(trimmed.slice(4))}</div>`
      );
      continue;
    }

    // H2: ## ...
    if (trimmed.startsWith("## ")) {
      formattedLines.push(
        `<div class="mt-3 mb-1.5 text-sm font-bold text-platinum tracking-wide">${escapeHtml(trimmed.slice(3))}</div>`
      );
      continue;
    }

    // H1: # ...
    if (trimmed.startsWith("# ")) {
      formattedLines.push(
        `<div class="mt-4 mb-2 text-base font-bold text-platinum tracking-tight">${escapeHtml(trimmed.slice(2))}</div>`
      );
      continue;
    }

    // Numbered List: 1. ...
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      formattedLines.push(
        `<div class="flex items-start gap-2 my-1 text-platinum"><span class="font-mono text-xs text-muted min-w-[1.2rem] mt-0.5">${numMatch[1]}.</span><span>${formatInline(numMatch[2])}</span></div>`
      );
      continue;
    }

    // Bullet List: - ... or * ... or • ...
    const bulletMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    if (bulletMatch) {
      formattedLines.push(
        `<div class="flex items-start gap-2 my-1 pl-2 text-muted"><span class="text-dimmed mt-1">•</span><span class="text-platinum">${formatInline(bulletMatch[1])}</span></div>`
      );
      continue;
    }

    // Empty blank line -> vertical spacer
    if (!trimmed) {
      formattedLines.push('<div class="h-1.5"></div>');
      continue;
    }

    // Regular paragraph
    formattedLines.push(`<p class="my-1 text-platinum leading-relaxed">${formatInline(line)}</p>`);
  }

  let finalHtml = formattedLines.join("");

  // Re-inject mathematical typography placeholders
  for (const { id, html } of placeholders) {
    finalHtml = finalHtml.replace(id, html);
  }

  return finalHtml;
}

function formatInline(str: string): string {
  let s = escapeHtml(str);
  // Bold **...**
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-platinum">$1</strong>');
  // Inline code `...`
  s = s.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  return s;
}

function renderKatexSafe(tex: string, displayMode: boolean): string {
  if (typeof katex === "undefined") {
    return `<code class="text-muted font-mono">${escapeHtml(tex)}</code>`;
  }
  try {
    return katex.renderToString(tex, {
      throwOnError: false,
      displayMode,
    });
  } catch {
    return `<code class="text-muted font-mono">${escapeHtml(tex)}</code>`;
  }
}

/**
 * Extracts any plottable 1D algebraic function (e.g. x^2 + x - 12, sin(x), etc.)
 * from the user query or assistant response.
 */
export function extractPlottableFormula(text: string): string | null {
  if (!text) return null;

  // Check for equations like x^2 + x - 12 = 0 or x^2 - 4x - 5 = 0
  const eqMatch = text.match(/(?:(?:solve|plot|graph|curve)\s+)?([x0-9\+\-\*\/\^\(\)\.\s]+)\s*=\s*0/i);
  if (eqMatch && eqMatch[1]) {
    const expr = eqMatch[1].trim().replace(/\^/g, "**");
    if (expr.includes("x") && expr.length < 50) return expr;
  }

  // Explicit quadratic or polynomial in LaTeX
  const latexMatch = text.match(/(?:\\+\[|\$\$)\s*([x0-9\+\-\*\/\^\(\)\.\s]+)\s*=\s*0\s*(?:\\+\]|\$\$)/);
  if (latexMatch && latexMatch[1]) {
    const expr = latexMatch[1].trim().replace(/\^/g, "**");
    if (expr.includes("x")) return expr;
  }

  return null;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
