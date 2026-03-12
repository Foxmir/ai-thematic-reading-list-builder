const fs = require('fs');
const path = require('path');
const https = require('https');

const DEFAULT_INPUT = path.join(__dirname, 'books_working.csv');
const DEFAULT_OUTPUT = path.join(__dirname, 'books_metadata_preview.csv');
const REQUEST_GAP_MS = 1500;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requestText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(
        url,
        {
          headers: {
            'User-Agent':
              'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36',
            Accept: 'text/html,application/xhtml+xml',
          },
        },
        (response) => {
          if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
            resolve(requestText(response.headers.location));
            return;
          }

          if (response.statusCode !== 200) {
            reject(new Error(`Request failed: ${response.statusCode} ${url}`));
            return;
          }

          let raw = '';
          response.setEncoding('utf8');
          response.on('data', (chunk) => {
            raw += chunk;
          });
          response.on('end', () => resolve(raw));
        }
      )
      .on('error', reject);
  });
}

function parseCsv(text) {
  const rows = [];
  let current = '';
  let row = [];
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === ',' && !inQuotes) {
      row.push(current);
      current = '';
      continue;
    }

    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') {
        index += 1;
      }
      row.push(current);
      current = '';
      if (row.some((cell) => cell.length > 0)) {
        rows.push(row);
      }
      row = [];
      continue;
    }

    current += char;
  }

  if (current.length > 0 || row.length > 0) {
    row.push(current);
    rows.push(row);
  }

  const [header, ...body] = rows;
  return body.map((cells) => {
    const record = {};
    header.forEach((key, index) => {
      record[key] = cells[index] ?? '';
    });
    return record;
  });
}

function escapeCsvCell(value) {
  const text = String(value ?? '');
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function toCsv(records) {
  if (!records.length) {
    return '';
  }
  const headers = Object.keys(records[0]);
  const lines = [headers.join(',')];
  for (const record of records) {
    lines.push(headers.map((header) => escapeCsvCell(record[header])).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

function cleanText(value) {
  return value
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

function matchMeta(html, propertyName) {
  const pattern = new RegExp(`<meta[^>]+property=["']${propertyName}["'][^>]+content=["']([^"']+)["']`, 'i');
  const match = html.match(pattern);
  return match ? cleanText(match[1]) : '';
}

function matchInfoField(html, fieldName) {
  const infoMatch = html.match(/<div id="info"[\s\S]*?<\/div>/i);
  if (!infoMatch) {
    return '';
  }
  const infoText = cleanText(infoMatch[0]);
  const pattern = new RegExp(`${fieldName}\s*[:：]\s*([^\s].*?)(?=作者\s*[:：]|出版社\s*[:：]|副标题\s*[:：]|原作名\s*[:：]|译者\s*[:：]|出版年\s*[:：]|页数\s*[:：]|定价\s*[:：]|装帧\s*[:：]|ISBN\s*[:：]|$)`);
  const match = infoText.match(pattern);
  return match ? match[1].trim() : '';
}

function matchRating(html) {
  const match = html.match(/<strong[^>]*class="ll rating_num"[^>]*>([^<]+)<\/strong>/i)
    || html.match(/<strong[^>]*>([^<]+)<\/strong>/i);
  return match ? cleanText(match[1]) : '';
}

async function resolveDoubanUrlFromIsbn(isbn) {
  const html = await requestText(`https://m.douban.com/search/?query=${encodeURIComponent(isbn)}`);
  const match = html.match(/href="(https:\/\/m\.douban\.com\/book\/subject\/[^"#?]+)[^"]*"/i);
  return match ? match[1] : '';
}

function normalizeMetadata(html, fallbackUrl) {
  const title = matchMeta(html, 'og:title');
  const description = matchMeta(html, 'og:description');
  const doubanUrl = matchMeta(html, 'og:url') || fallbackUrl;
  const isbn = matchMeta(html, 'book:isbn') || matchInfoField(html, 'ISBN');
  const author = matchInfoField(html, '作者');
  const publisher = matchInfoField(html, '出版社');
  const publishYear = matchInfoField(html, '出版年');
  const rating = matchRating(html);

  return {
    fetched_title: title,
    fetched_author: author,
    fetched_publisher: publisher,
    fetched_publish_year: publishYear,
    fetched_isbn: isbn,
    fetched_rating: rating,
    fetched_description: description,
    fetched_douban_url: doubanUrl,
  };
}

async function enrichRow(row) {
  let detailUrl = row.douban_url.trim();
  if (!detailUrl && row.isbn.trim()) {
    detailUrl = await resolveDoubanUrlFromIsbn(row.isbn.trim());
  }

  if (!detailUrl) {
    return {
      ...row,
      metadata_status: 'skipped-no-url-or-isbn',
      fetched_title: '',
      fetched_author: '',
      fetched_publisher: '',
      fetched_publish_year: '',
      fetched_isbn: '',
      fetched_rating: '',
      fetched_description: '',
      fetched_douban_url: '',
    };
  }

  const html = await requestText(detailUrl);
  const metadata = normalizeMetadata(html, detailUrl);
  return {
    ...row,
    metadata_status: 'fetched',
    ...metadata,
  };
}

async function main() {
  const inputPath = process.argv[2] ? path.resolve(process.argv[2]) : DEFAULT_INPUT;
  const outputPath = process.argv[3] ? path.resolve(process.argv[3]) : DEFAULT_OUTPUT;

  const sourceText = fs.readFileSync(inputPath, 'utf8').replace(/^\uFEFF/, '');
  const rows = parseCsv(sourceText);
  const result = [];

  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    process.stdout.write(`[${index + 1}/${rows.length}] ${row.title}\n`);
    try {
      result.push(await enrichRow(row));
    } catch (error) {
      result.push({
        ...row,
        metadata_status: `error: ${error.message}`,
        fetched_title: '',
        fetched_author: '',
        fetched_publisher: '',
        fetched_publish_year: '',
        fetched_isbn: '',
        fetched_rating: '',
        fetched_description: '',
        fetched_douban_url: '',
      });
    }
    await sleep(REQUEST_GAP_MS);
  }

  fs.writeFileSync(outputPath, toCsv(result), 'utf8');
  process.stdout.write(`写入完成: ${outputPath}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});