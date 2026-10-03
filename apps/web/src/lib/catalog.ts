// Catalog fixtures and data helpers migrated from assets/js/catalog.js

export interface CatalogVariant {
  res: string
  codec: string
  audio: string
  bytes: number
}

export interface CatalogMovie {
  id: string
  cat: 'movies'
  kind: 'movie' | 'tv'
  title: string
  fa: string | null
  year: number
  rating: number | null
  genres: string
  audio: string
  art: string
  blurb: string
  variants: CatalogVariant[]
  stream: boolean
  censored: boolean
}

export interface CatalogGamePart {
  n: number
  bytes: number
}

export interface CatalogGame {
  id: string
  cat: 'games'
  kind: 'game'
  title: string
  fa: string | null
  year: number
  rating: number | null
  genres: string
  audio: string
  rated: string
  art: string
  blurb: string
  releaseGroup: string
  version: string
  parts: CatalogGamePart[]
  totalBytes: number
  password: string | null
}

export interface CatalogTrack {
  n: number
  title: string
  sec: number
  lo: number
  hi: number
}

export interface CatalogMusic {
  id: string
  cat: 'music'
  kind: 'track'
  title: string
  fa: string | null
  artist: string
  artistFa: string
  year: number
  rating: null
  genres: string
  mbid: string
  art: string
  blurb: string
  tracks: CatalogTrack[]
}

export type CatalogItem = CatalogMovie | CatalogGame | CatalogMusic

export interface CatalogSource {
  id: string
  name: string
  cat: 'movies' | 'games' | 'music'
  tier: number
  state: 'ok' | 'warn' | 'bad'
  enabled: boolean
  notes: string
  baseUrl: string
  mirrorUrl: string
  tierLabel: string
}

const AR_DIGITS = '٠١٢٣٤٥٦٧٨٩'
const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'

export function normalizeFa(input: string | null | undefined): string {
  const s = String(input ?? '')
  let out = ''
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    const ai = AR_DIGITS.indexOf(ch)
    if (ai > -1) {
      out += FA_DIGITS[ai]
      continue
    }
    if (ch === 'ي' || ch === 'ى') {
      out += 'ی'
      continue
    }
    if (ch === 'ك') {
      out += 'ک'
      continue
    }
    if (ch === 'ة') {
      out += 'ه'
      continue
    }
    if (ch === 'ـ') continue
    out += ch
  }
  return out
    .replace(/‌/g, ' ')
    .replace(/[ً-ٟ]/g, '')
    .replace(/[ً-ْ]/g, '')
    .replace(/[۰-۹]/g, (d) => String(FA_DIGITS.indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String(AR_DIGITS.indexOf(d)))
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

export function toFaDigits(n: number | string): string {
  return String(n).replace(/\d/g, (d) => FA_DIGITS[+d])
}

export function fmtMiB(bytes: number): string {
  const v = bytes / 1048576
  return v >= 1024 ? `${(v / 1024).toFixed(2)} GB` : `${v.toFixed(0)} MB`
}

function mp3Bytes(sec: number, kbps: number): number {
  return Math.round((sec * kbps * 1000) / 8)
}

const MOVIES_RAW: [string, string, string, number, 'movie' | 'tv', number | null, string, string, string][] = [
  ['digger', 'Digger', 'دیگر', 2026, 'movie', 7.7, 'Drama · Western', 'EN', '1080p'],
  ['east-of-eden', 'East of Eden', 'باغ بهشت', 2026, 'tv', 8.3, 'Drama · Family', 'EN', '1080p'],
  ['the-uprising', 'The Uprising', 'قیام', 2026, 'movie', 8.0, 'Action · Sci-Fi', 'EN', '4K'],
  ['verity', 'Verity', 'وِریتی', 2026, 'movie', 6.9, 'Thriller', 'EN', '1080p'],
  ['scrubs', 'Scrubs', 'اسکرابز', 2026, 'tv', 7.7, 'Comedy · Medical', 'EN', '1080p'],
  ['runner', 'Runner', 'دونده', 2026, 'movie', 8.2, 'Action · Drama', 'EN', '1080p'],
  ['resident-evil', 'Resident Evil', 'ریسیدنت ایویل', 2026, 'movie', 7.3, 'Horror · Action', 'EN', '4K'],
  ['the-ramparts-of-ice', 'The Ramparts of Ice', 'قلعه یخ', 2026, 'movie', null, 'Drama', 'EN', '1080p'],
  ['soulm8te', 'Soulm8te', 'روح‌ام‌هیتی', 2026, 'movie', 7.4, 'Horror', 'EN', '1080p'],
  ['war', 'War', 'جنگ', 2026, 'tv', 10.0, 'Action · Drama', 'EN', '4K'],
  ['obsession', 'Obsession', 'وسواس', 2026, 'movie', 8.2, 'Thriller · Romance', 'EN', '1080p'],
  ['livestream-from-hell', 'Livestream from Hell', 'پخش زنده از جهنم', 2026, 'movie', 8.1, 'Horror', 'EN', '720p'],
  ['coyote-vs-acme', 'Coyote vs. Acme', 'کویوت در برابر اکمی', 2026, 'movie', 7.6, 'Animation · Comedy', 'EN', '1080p'],
  ['primetime', 'Primetime', 'پرایم‌تایم', 2026, 'movie', 7.0, 'Drama', 'EN', '1080p'],
  ['lanterns', 'Lanterns', 'فانوس‌ها', 2026, 'tv', 8.4, 'Mystery', 'EN', '1080p'],
  ['mobland', 'MobLand', 'موب‌لند', 2025, 'tv', 8.5, 'Crime · Drama', 'EN', '4K'],
  ['avengers-doomsday', 'Avengers: Doomsday', 'اوتیجرز: پایان دنیا', 2026, 'movie', null, 'Action', 'EN', '4K'],
  ['the-odyssey', 'The Odyssey', 'اودیسه', 2026, 'movie', 8.0, 'Action · Adventure', 'EN', '4K'],
  ['unabomber', 'UNABOMBER', 'یونابومبر', 2026, 'movie', 6.7, 'Crime · Thriller', 'EN', '1080p'],
  ['american-horror-story', 'American Horror Story', 'داستان وحشت آمریکایی', 2011, 'tv', 8.1, 'Horror', 'EN', '1080p'],
  ['spider-man-brand-new-day', 'Spider-Man: Brand New Day', 'اسپایدرمن: روزی نو', 2026, 'movie', 7.9, 'Action', 'EN', '4K'],
  ['heart-of-the-beast', 'Heart of the Beast', 'قلب هیولا', 2026, 'movie', 7.6, 'Horror', 'EN', '1080p'],
  ['reacher', 'Reacher', 'ریچر', 2022, 'tv', 8.1, 'Action · Crime', 'EN', '1080p'],
  ['toy-story-5', 'Toy Story 5', 'داستان اسباب‌بازی ۵', 2026, 'movie', 7.1, 'Animation · Family', 'EN', '4K'],
  ['the-love-hypothesis', 'The Love Hypothesis', 'فرضیه عشق', 2026, 'movie', 8.1, 'Romance', 'EN', '1080p'],
  ['the-end-of-oak-street', 'The End of Oak Street', 'پایان خیابان اوک', 2026, 'movie', 7.1, 'Drama', 'EN', '720p'],
  ['the-fix', 'The Fix', 'اصلاح', 2026, 'movie', 7.2, 'Drama', 'EN', '1080p'],
  ['the-simpsons', 'The Simpsons', 'سیمپسون‌ها', 1989, 'tv', 8.0, 'Animation · Comedy', 'EN', '1080p'],
  ['family-guy', 'Family Guy', 'گروه خانوادگی', 1999, 'tv', 7.4, 'Animation · Comedy', 'EN', '1080p'],
  ['the-office', 'The Office', 'آفیس', 2005, 'tv', 8.6, 'Comedy', 'EN', '720p'],
  ['supernatural', 'Supernatural', 'سوپرنچرال', 2005, 'tv', 8.3, 'Fantasy · Horror', 'EN', '1080p'],
  ['greys-anatomy', "Grey's Anatomy", 'کاوش آناتومی', 2005, 'tv', 8.2, 'Medical · Drama', 'EN', '720p'],
  ['the-mentalist', 'The Mentalist', 'ذهن‌خوان', 2008, 'tv', 8.4, 'Crime · Drama', 'EN', '720p'],
  ['law-order', 'Law & Order', 'قانون و ترتیب', 1990, 'tv', 7.3, 'Crime · Legal', 'EN', '720p'],
  ['ncis', 'NCIS', 'ان‌سی‌آی‌اس', 2003, 'tv', 7.6, 'Crime · Drama', 'EN', '720p'],
  ['one-piece', 'One Piece', 'وان پیس', 1999, 'tv', null, 'Animation · Adventure', 'JA', '1080p'],
  ['ted-lasso', 'Ted Lasso', 'تد لاسو', 2020, 'tv', null, 'Comedy · Drama', 'EN', '1080p'],
  ['lioness', 'Lioness', 'لیونس', 2023, 'tv', 8.3, 'Action · Drama', 'EN', '4K'],
  ['running-man', 'Running Man', 'دونده', 2010, 'tv', 8.2, 'Action · Reality', 'KO', '720p'],
  ['the-scandal', 'The Scandal', 'رسوایی', 2026, 'movie', 6.6, 'Thriller', 'EN', '720p'],
  ['re-zero-starting-life-in-another-world', 'Re:Zero − Starting Life in Another World', 'ری: زیرو', 2016, 'tv', 8.4, 'Fantasy · Animation', 'JA', '1080p'],
  ['fx-fighter-kurumi-chan', 'F×Fighter Kurumi-chan', 'فایتکر کورومی', 2026, 'tv', null, 'Action · Animation', 'JA', '1080p'],
  ['other-mommy', 'Other Mommy', 'مادر دیگر', 2026, 'movie', null, 'Horror', 'EN', '720p'],
]

const RES_BPS: Record<string, number> = { '480p': 900, '720p': 1700, '1080p': 3600, '4K': 9500 }

function buildVariants(seed: string, _year: number, type: 'movie' | 'tv', _genres: string): CatalogVariant[] {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  const pick = (n: number) => {
    h = (h * 1103515245 + 12345) >>> 0
    return h % n
  }
  const res = type === 'tv' ? ['480p', '720p', '1080p'] : ['720p', '1080p', '4K']
  const out: CatalogVariant[] = []
  res.forEach((r) => {
    if (pick(4) === 0 && r === '4K') return
    const codec = pick(3) === 0 ? 'x265 / HEVC' : pick(6) === 0 ? 'x264 · 10-bit' : 'x264'
    let audio = pick(2) === 0 ? 'FA dubbed' : pick(3) === 0 ? 'FA soft-sub' : 'Original'
    if (type === 'tv' && audio === 'FA dubbed') audio = 'FA soft-sub'
    const secs = 5400 + pick(5400)
    const bytes = ((secs * RES_BPS[r] * 1000) / 8) * (codec.includes('x265') ? 0.62 : 1)
    out.push({ res: r, codec, audio, bytes: Math.round(bytes) })
  })
  return out.length ? out : [{ res: '1080p', codec: 'x264', audio: 'Original', bytes: 2.1e9 }]
}

export const CATALOG_MOVIES: CatalogMovie[] = MOVIES_RAW.map((m) => {
  const [slug, title, fa, year, type, rating, genres, audioOrig] = m
  return {
    id: slug,
    cat: 'movies',
    kind: type,
    title,
    fa,
    year,
    rating,
    genres,
    audio: audioOrig,
    art: `/images/movies/${slug}.jpg`,
    blurb:
      'Upstream listing resolved across the movie portals for this title. Every format below links straight from your browser to the upstream CDN — nothing is buffered by this site.',
    variants: buildVariants(slug, year, type, genres),
    stream: slug === 'digger' || slug === 'verity' || slug === 'war',
    censored: ['avengers-doomsday', 'the-scandal', 'family-guy', 'one-piece'].includes(slug),
  }
})

const GAMES_RAW: [string, string, string, number, number, string, number, string, string, string][] = [
  ['cyberpunk-2077', 'Cyberpunk 2077', 'سایبرپانک ۲۰۷۷', 2020, 8.4, 'ElAmigos', 42, 'v1.63', 'EN', '64 / 48 / 32'],
  ['elden-ring', 'Elden Ring', 'الدن رینگ', 2022, 9.2, 'DODI', 46, 'v1.16', 'EN', '38 / 30 / 22'],
  ['baldurs-gate-3', "Baldur's Gate 3", 'بالدورز گیت ۳', 2023, 9.4, 'FitGirl', 118, 'v4.4', 'EN', '54 / 40 / 26'],
  ['hogwarts-legacy', 'Hogwarts Legacy', 'میراث هاگوارتس', 2023, 8.6, 'ElAmigos', 44, 'v1.2', 'EN', '40 / 28 / 20'],
  ['red-dead-redemption-2', 'Red Dead Redemption 2', 'رد دد ردمپشن ۲', 2019, 9.3, 'FitGirl', 72, 'v1.31', 'EN', '60 / 44 / 30'],
  ['grand-theft-auto-v', 'Grand Theft Auto V', 'جی‌تی‌ای وی', 2015, 9.2, 'DODI', 46, 'v1.67', 'EN', '34 / 26 / 18'],
  ['the-witcher-3-wild-hunt', 'The Witcher 3: Wild Hunt', 'ویچر ۳', 2015, 9.4, 'FitGirl', 50, 'v4.04', 'EN', '36 / 24 / 16'],
  ['alan-wake-2', 'Alan Wake 2', 'آلن ویک ۲', 2023, 8.9, 'ElAmigos', 70, 'v1.2.1', 'EN', '58 / 42 / 28'],
  ['clair-obscur-expedition-33', 'Clair Obscur: Expedition 33', 'کلره اوبسکور', 2025, 9.1, 'DODI', 55, 'v1.0', 'EN', '30 / 22 / 14'],
  ['death-stranding-2', 'Death Stranding 2', 'دث استرندینگ ۲', 2025, 8.5, 'FitGirl', 68, 'v1.0', 'EN', '26 / 18 / 12'],
  ['kingdom-come-deliverance-2', 'Kingdom Come: Deliverance II', 'کینگدام کام', 2025, 8.9, 'ElAmigos', 96, 'v1.0', 'EN', '48 / 34 / 24'],
  ['marvels-spider-man-2', "Marvel's Spider-Man 2", 'اسپایدرمن ۲', 2024, 8.7, 'DODI', 60, 'v1.3', 'EN', '44 / 30 / 20'],
  ['elden-ring-nightreign', 'Elden Ring: Nightreign', 'الدن رینگ: نایترن', 2025, 8.4, 'ElAmigos', 24, 'v1.3', 'EN', '18 / 14 / 10'],
  ['stardew-valley', 'Stardew Valley', 'استار دیو والی', 2016, 9.0, 'FitGirl', 2, 'v1.6', 'EN', '3 / 2 / 2'],
  ['helldivers-2', 'Helldivers 2', 'هل دایورز ۲', 2024, 8.6, 'DODI', 28, 'v1.001', 'EN', '22 / 16 / 10'],
]

function buildParts(totalGb: number, n: number, seed: string): CatalogGamePart[] {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 131 + seed.charCodeAt(i)) >>> 0
  const raw: number[] = []
  let sum = 0
  for (let i = 0; i < n; i++) {
    h = (h * 1664525 + 1013904223) >>> 0
    const w = 0.6 + (h % 100) / 100
    raw.push(w)
    sum += w
  }
  const total = totalGb * 1073741824
  return raw.map((w, k) => ({
    n: k + 1,
    bytes: Math.round((total * w) / sum),
  }))
}

export const CATALOG_GAMES: CatalogGame[] = GAMES_RAW.map((g) => {
  const parts = buildParts(g[6], 6 + (g[0].length % 4), g[0])
  const releaseGroup = g[5]
  const pw =
    releaseGroup === 'ElAmigos'
      ? null
      : releaseGroup === 'DODI'
        ? `${g[7]}-${2160 + (g[0].length % 7)}`
        : `fitgirl-${1100 + (g[0].length % 9)}`
  if (g[0] === 'the-witcher-3-wild-hunt') parts.splice(2, 1)
  const totalBytes = parts.reduce((a, p) => a + p.bytes, 0)
  return {
    id: g[0],
    cat: 'games',
    kind: 'game',
    title: g[1],
    fa: g[2],
    year: g[3],
    rating: g[4],
    genres: 'RPG · Open world',
    audio: 'EN',
    rated: g[8],
    art: `/images/games/${g[0]}.jpg`,
    blurb:
      'Multi-part archive from the game portals. Parts are listed in strict order; the extraction password is shown once and can be copied in one click.',
    releaseGroup,
    version: g[7],
    parts,
    totalBytes,
    password: pw,
  }
})

const RELEASES_RAW: [string, string, string, string, string, string, number, [string, number][]][] = [
  [
    'sogand',
    'Sogand',
    'سوگند',
    'Man',
    'aad50170',
    'sogand-man',
    2020,
    [
      ['Delkhor', 224],
      ['Top (Ft. Zakhmi & Behzad Leito)', 228],
      ['Dardesar', 189],
      ['Hamgonah', 324],
      ['Tehran', 213],
      ['Modele-Man', 251],
    ],
  ],
  [
    'khune',
    'Sogand',
    'سوگند',
    'Khune',
    'aad50170',
    'sogand-khune',
    2024,
    [
      ['Khune', 216],
      ['Neshastom', 200],
      ['Zamin Gerde', 204],
      ['Barax', 245],
      ['Yarab', 203],
      ['Dooram', 121],
    ],
  ],
  [
    'googoosh',
    'Googoosh',
    'گوگوش',
    'The Best of Googoosh 3 — Doe Mahi',
    '460ca408',
    'googoosh-best-of-3',
    1997,
    [
      ['Gol Bi Goldoun', 268],
      ['Sahel Va Darya', 265],
      ['Bizar', 264],
      ['Sekeh Khorshid', 194],
      ['Doe Mahi', 356],
      ['Yadet Basheh', 276],
      ['Anrouz', 176],
      ['Sabz-O-Sefeed', 180],
      ['Gol Gham', 265],
      ['Daryaye Entezar', 156],
      ['Koucheh', 231],
      ['Felfel', 191],
      ['Jomeh', 258],
      ['Shad E Shad', 174],
    ],
  ],
  [
    'aghaye-past',
    'Ali Azimi',
    'علی عظیمی',
    'Aghaye Past (Me. Mean)',
    'ecf0e464',
    'ali-azimi-aghaye-past',
    2013,
    [
      ['Toye Hammal', 285],
      ['Aah Az Eshgh', 258],
      ['Aghaye Past', 220],
      ['Pishdaramad', 298],
      ['Az To Boridam', 202],
      ['Entekhab e Sadeh', 193],
      ['Az Roozha', 235],
      ['Taraneh Saz', 163],
      ['Si o Seh', 204],
    ],
  ],
  [
    'ezzat-ziad',
    'Ali Azimi',
    'علی عظیمی',
    'Ezzat Ziad',
    '1355ab92',
    'ali-azimi-ezzat-ziad',
    2016,
    [
      ['Zendegi', 385],
      ['Shaparak', 261],
      ['Donya Jaye Gozare', 238],
      ['Farda Soraghe Man Bia', 356],
      ['Harf Bezan', 260],
      ['Ahange Aroosi', 260],
      ['Ahange Shaad', 207],
      ['Ahange Shoari', 301],
      ['Ezzat Ziad', 242],
      ['Norooz Too Raheh', 277],
    ],
  ],
  [
    'parchame-sefid',
    'Mohsen Chavoshi',
    'محسن چاوشی',
    'Parchame Sefid',
    '15bc55ef',
    'mohsen-chavoshi-parchame-sefid',
    2011,
    [
      ['Mardom Azar', 188],
      ['Javabam Nakon', 196],
      ['Khane Haftsad', 231],
      ['Ba man Bemoon', 213],
      ['Khabe Bad az Zohr', 224],
      ['Begoo Magoo', 269],
      ['Ghatar', 395],
      ['Parchame Sefid', 335],
      ['Taghas', 194],
      ['Har rooz Paeize', 223],
    ],
  ],
  [
    'man-khode-an-sizdaham',
    'Mohsen Chavoshi',
    'محسن چاوشی',
    'Man Khod An Sizdaham',
    'f32ad6fe',
    'mohsen-chavoshi-man-khode-an-sizdaham',
    2013,
    [
      ['Ghalat Kardam Ghalat', 269],
      ['Koo Be Koo', 318],
      ['Ramidim', 208],
      ['Negar', 247],
      ['Setamgar', 309],
      ['Shir Marda', 180],
      ['Man Khod An Sizdaham', 207],
      ['Ghorazeh Chin', 274],
      ['Bahram Goor', 379],
    ],
  ],
  [
    'nasime-vasl',
    'Homayoun Shajarian',
    'همایون شجریان',
    'Nasime Vasl',
    '143f254a',
    'shajarian-nasime-vasl',
    2003,
    [
      ['Tasnife Havaye Gerye', 433],
      ['Nasime Sahar', 980],
      ['Tasnife Khaneye Soda', 393],
      ['Tasnife Eshgh Az Koja', 393],
      ['Tasnife Hasele Omr', 333],
      ['Tasnife Daftare Del', 315],
      ['Tasnife Sokoot', 351],
      ['Tasnife Nasime Vasl', 393],
    ],
  ],
  [
    'naashakiba',
    'Homayoun Shajarian',
    'همایون شجریان',
    'Naashakiba',
    '88132ba2',
    'shajarian-naashakiba',
    2004,
    [
      ['Che Daanestam', 446],
      ['Saz Va Avaze Shoor Naashakibaa', 822],
      ['Tasnife Meye Eshgh', 381],
      ["Ghateh’ye Bi Kalaam Haamoun", 364],
      ['Avaze Zahre Shirin', 343],
      ['Saz Va Avaze Dashti Daaghe Dousti', 438],
      ['Tasnife Penhaan Cho Del', 484],
      ['Raghse Choub', 313],
    ],
  ],
  [
    'zendouni',
    'Dariush Eghbali',
    'داریوش اقبالی',
    'Zendouni',
    '95eac07e',
    'dariush-zendouni',
    1991,
    [
      ['Khasteham', 250],
      ['Bahar Khamoush', 343],
      ['Shabaneh', 342],
      ['Nefrin', 312],
      ['Karoun', 506],
      ['Salam', 287],
      ['Zendouni', 208],
      ['LayLayee', 287],
      ['Sedayam Kon', 544],
      ['Pesaram', 249],
      ['Ali konkouri', 305],
    ],
  ],
]

export const CATALOG_MUSIC: CatalogMusic[] = RELEASES_RAW.map((r) => {
  const tracks = r[7].map((t, i) => {
    const sec = t[1]
    return {
      n: i + 1,
      title: t[0],
      sec,
      lo: mp3Bytes(sec, 128),
      hi: mp3Bytes(sec, 320),
    }
  })
  return {
    id: r[0],
    cat: 'music',
    kind: 'track',
    title: r[3],
    fa: null,
    artist: r[1],
    artistFa: r[2],
    year: r[6],
    art: `/images/music/${r[5]}.jpg`,
    rating: null,
    genres: 'Persian pop / classical',
    mbid: r[4],
    blurb:
      'Preview streams inline from the upstream CDN. 128 and 320 kbps MP3s are direct links — this site never relays the audio.',
    tracks,
  }
})

export const CATALOG_SOURCES: CatalogSource[] = [
  ['film2media', 'Film2Media', 'movies', 1, 'ok', true, 'poster, dub + soft-sub variants, 4K'],
  ['avamovie', 'AvaMovie', 'movies', 1, 'ok', true, 'largest movie mirror set'],
  ['zarfilm', 'Zarfilm', 'movies', 2, 'ok', true, 'fast CDN, frequent domain rotation'],
  ['mobomovie', 'MoboMovie', 'movies', 2, 'warn', true, 'slow; degraded after 3 timeouts'],
  ['yasdl', 'YasDL', 'games', 1, 'ok', true, 'ordered parts + password on page'],
  ['downloadha', 'Downloadha', 'games', 2, 'ok', true, 'fallback mirror'],
  ['game2dl', 'Game2DL', 'games', 3, 'bad', false, 'TLS errors — disabled until fixed'],
  ['persiandl', 'PersianDL', 'games', 3, 'ok', true, 'small releases only'],
  ['nex1music', 'Nex1Music', 'music', 1, 'ok', true, '128/320 tiers per track'],
  ['popmusic', 'Pop-Music', 'music', 2, 'ok', true, 'album-oriented'],
  ['radiojavan', 'RadioJavan', 'music', 1, 'ok', true, 'preview player source'],
  ['upmusic', 'UpMusic', 'music', 2, 'ok', true, 'fallback for RadioJavan'],
].map((s) => ({
  id: s[0] as string,
  name: s[1] as string,
  cat: s[2] as 'movies' | 'games' | 'music',
  tier: s[3] as number,
  state: s[4] as 'ok' | 'warn' | 'bad',
  enabled: s[5] as boolean,
  notes: s[6] as string,
  baseUrl: '',
  mirrorUrl: '',
  tierLabel: s[3] === 1 ? 'Tier 1' : s[3] === 2 ? 'Tier 2' : 'Tier 3',
}))

export const EXPANSION_TARGETS = {
  movies: { target: 20, live: 4 },
  music: { target: 20, live: 4 },
  games: { target: 8, live: 4 },
}

export const ALL_CATALOG: CatalogItem[] = [
  ...CATALOG_MOVIES,
  ...CATALOG_GAMES,
  ...CATALOG_MUSIC,
]

export function searchCatalog(cat: 'movies' | 'games' | 'music' | 'all', q: string): CatalogItem[] {
  const n = normalizeFa(q)
  if (!n) return []
  const pool = cat === 'all' ? ALL_CATALOG : ALL_CATALOG.filter((i) => i.cat === cat)
  const raw = n.split(' ').filter(Boolean)
  const years = raw.filter((t) => /^\d{4}$/.test(t))
  const terms = raw.filter((t) => !/^\d{4}$/.test(t))
  const scored: { it: CatalogItem; score: number }[] = []

  pool.forEach((it) => {
    const hay = normalizeFa(
      [
        it.title,
        it.fa || '',
        'artist' in it ? it.artist : '',
        'artistFa' in it ? it.artistFa : '',
        it.genres || '',
        it.year,
        'releaseGroup' in it ? it.releaseGroup : '',
      ].join(' ')
    )
    let hits = 0
    let score = 0
    terms.forEach((t) => {
      if (hay.includes(t)) {
        hits += 1
        score += 3
      } else if (t.length > 3 && hay.includes(t.slice(0, Math.ceil(t.length * 0.75)))) {
        hits += 1
        score += 1
      }
    })
    if (terms.length && !hits) return
    if (years.length) {
      const okYear = years.some((y) => normalizeFa(String(it.year)) === y)
      if (!okYear) return
      score += 2
    }
    if (normalizeFa(it.title) === n) score += 8
    if (score) scored.push({ it, score })
  })

  scored.sort((a, b) => b.score - a.score)
  return scored.map((s) => s.it)
}

export function getCatalogItemById(id: string): CatalogItem | undefined {
  return ALL_CATALOG.find((i) => i.id === id)
}
